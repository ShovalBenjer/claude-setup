#!/usr/bin/env python3
"""Proactive staleness sweep for the research corpus (spec section 7.3).

Walks all sources, re-hashes local files, updates liveness and
content_sha256, checks fetch age and source age, and produces a
structured report of what drifted, what is stale, and what is dead.

Unlike the per-query staleness in retrieve.py, this tool updates the
database: a drifted local file gets its hash and liveness corrected
so subsequent queries see the new state.

Usage:
    python tools/corpus/staleness.py sweep [--db PATH] [--json]
    python tools/corpus/staleness.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    SCHEMA_SQL,
    _sha256,
    connect,
    init_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

STALE_SOURCE_DAYS = 548
UNVERIFIED_FETCH_DAYS = 90


def _now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_utc(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, fmt).replace(
                tzinfo=datetime.timezone.utc
            )
        except ValueError:
            continue
    return None


def _hash_file(path):
    try:
        content = path.read_text(errors="replace")
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    except (OSError, PermissionError):
        return None


def sweep(db_path=None):
    """Walk all sources, check freshness, update DB, return report."""
    dp = Path(db_path) if db_path else DEFAULT_DB
    conn = connect(str(dp))

    sources = conn.execute(
        "SELECT source_id, canonical_uri, kind, liveness, "
        "content_sha256, fetched_utc, upstream_mtime FROM sources"
    ).fetchall()

    now = _now_utc()
    drifted = []
    gone = []
    stale = []
    unverified = []
    revived = []
    updates = []

    for src in sources:
        sid = src["source_id"]
        uri = src["canonical_uri"]
        kind = src["kind"]
        old_hash = src["content_sha256"]
        old_liveness = src["liveness"]

        if kind == "local_md":
            p = Path(uri)
            if not p.is_absolute():
                p = REPO_ROOT / p

            if p.exists():
                new_hash = _hash_file(p)
                if new_hash and new_hash != old_hash:
                    new_bytes = p.stat().st_size
                    new_mtime = datetime.datetime.fromtimestamp(
                        p.stat().st_mtime, tz=datetime.timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")
                    conn.execute(
                        "UPDATE sources SET content_sha256 = ?, bytes = ?, "
                        "upstream_mtime = ?, liveness = 'live' "
                        "WHERE source_id = ?",
                        (new_hash, new_bytes, new_mtime, sid),
                    )
                    updates.append(sid)
                    drifted.append({
                        "source_id": sid,
                        "uri": uri,
                        "old_hash": old_hash[:12],
                        "new_hash": new_hash[:12],
                    })
                    if old_liveness == "dead":
                        revived.append({"source_id": sid, "uri": uri})

                elif old_liveness == "dead":
                    conn.execute(
                        "UPDATE sources SET liveness = 'live' WHERE source_id = ?",
                        (sid,),
                    )
                    updates.append(sid)
                    revived.append({"source_id": sid, "uri": uri})

            else:
                if old_liveness != "dead":
                    conn.execute(
                        "UPDATE sources SET liveness = 'dead' WHERE source_id = ?",
                        (sid,),
                    )
                    updates.append(sid)
                    gone.append({"source_id": sid, "uri": uri})

        upstream_mtime = _parse_utc(src["upstream_mtime"])
        if upstream_mtime:
            age_days = (now - upstream_mtime).days
            if age_days > STALE_SOURCE_DAYS and old_liveness not in ("stale", "dead", "archived"):
                conn.execute(
                    "UPDATE sources SET liveness = 'stale' WHERE source_id = ?",
                    (sid,),
                )
                updates.append(sid)
                stale.append({
                    "source_id": sid,
                    "uri": uri,
                    "age_days": age_days,
                })

        fetched_utc = _parse_utc(src["fetched_utc"])
        if fetched_utc:
            fetch_age = (now - fetched_utc).days
            if fetch_age > UNVERIFIED_FETCH_DAYS:
                unverified.append({
                    "source_id": sid,
                    "uri": uri,
                    "fetch_age_days": fetch_age,
                })

    vec_status = _check_vectors(dp)

    if updates:
        conn.commit()
    conn.close()

    total_sources = len(sources)
    report = {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db": str(dp),
        "total_sources": total_sources,
        "drifted": drifted,
        "gone_dead": gone,
        "stale_18mo": stale,
        "unverified_90d": unverified,
        "revived": revived,
        "vectors": vec_status,
        "updates_applied": len(set(updates)),
        "verdict": _verdict(drifted, gone, stale, unverified, vec_status),
    }
    return report


def _check_vectors(db_path):
    dp = Path(db_path) if db_path else DEFAULT_DB
    npy_path = dp.parent / "corpus-vec.npy"
    meta_path = dp.parent / "corpus-vec.json"

    if not meta_path.exists():
        return {"status": "not_fitted", "current": True}

    meta = json.loads(meta_path.read_text())
    conn = connect(str(dp))
    gen_row = conn.execute(
        "SELECT value FROM corpus_meta WHERE key = 'generation'"
    ).fetchone()
    conn.close()

    if not gen_row:
        return {"status": "no_generation", "current": False}

    db_gen = gen_row["value"]
    vec_gen = str(meta.get("generation", ""))

    if db_gen == vec_gen:
        return {
            "status": "current",
            "current": True,
            "generation": db_gen,
            "n_chunks": meta.get("n_chunks", 0),
            "n_components": meta.get("n_components", 0),
        }
    else:
        return {
            "status": "stale",
            "current": False,
            "db_generation": db_gen,
            "vec_generation": vec_gen,
        }


def _verdict(drifted, gone, stale, unverified, vec_status):
    issues = []
    if drifted:
        issues.append(f"{len(drifted)} drifted")
    if gone:
        issues.append(f"{len(gone)} dead")
    if stale:
        issues.append(f"{len(stale)} stale")
    if not vec_status.get("current", True):
        issues.append("vectors stale")
    if not issues:
        return "FRESH"
    return "DRIFT: " + ", ".join(issues)


def _print_report(report):
    print(f"staleness sweep: {report['verdict']}")
    print(f"  sources: {report['total_sources']}")
    print(f"  updates applied: {report['updates_applied']}")
    if report["drifted"]:
        print(f"\n  drifted ({len(report['drifted'])}):")
        for d in report["drifted"]:
            print(f"    {d['uri']}  {d['old_hash']}..→{d['new_hash']}..")
    if report["gone_dead"]:
        print(f"\n  gone/dead ({len(report['gone_dead'])}):")
        for d in report["gone_dead"]:
            print(f"    {d['uri']}")
    if report["stale_18mo"]:
        print(f"\n  stale >18mo ({len(report['stale_18mo'])}):")
        for d in report["stale_18mo"][:5]:
            print(f"    {d['uri']}  ({d['age_days']}d)")
        if len(report["stale_18mo"]) > 5:
            print(f"    ... and {len(report['stale_18mo']) - 5} more")
    if report["unverified_90d"]:
        print(f"\n  unverified >90d ({len(report['unverified_90d'])}):")
        for d in report["unverified_90d"][:5]:
            print(f"    {d['uri']}  ({d['fetch_age_days']}d)")
        if len(report["unverified_90d"]) > 5:
            print(f"    ... and {len(report['unverified_90d']) - 5} more")
    if report["revived"]:
        print(f"\n  revived ({len(report['revived'])}):")
        for d in report["revived"]:
            print(f"    {d['uri']}")
    vec = report["vectors"]
    print(f"\n  vectors: {vec['status']}")


def selftest():
    failures = []

    def t(name, cond):
        if not cond:
            failures.append(name)
            print(f"  FAIL: {name}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "test.db"

        conn = connect(str(db_path))
        init_schema(conn)
        conn.close()

        report = sweep(db_path)
        t("empty corpus is FRESH", report["verdict"] == "FRESH")
        t("zero sources", report["total_sources"] == 0)
        t("zero updates", report["updates_applied"] == 0)
        t("report has timestamp", "timestamp" in report)
        t("report has vectors", "vectors" in report)

        conn = connect(str(db_path))
        test_file = tmp_path / "test_source.md"
        test_file.write_text("# Test\nSome content here.")
        file_hash = hashlib.sha256(
            test_file.read_text().encode("utf-8")
        ).hexdigest()
        now = _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
        sid = "s" + _sha256(str(test_file))[:16]
        cid = "c" + _sha256("some content here")[:16]
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid, str(test_file), "local_md", "Test Source",
                "MIT", "vendor", "manual", None, None,
                now, None, now, "live", file_hash,
                len("# Test\nSome content here."), None,
            ),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                cid, sid, 0, "Test", "prose", None,
                "some content here", "Some content here.", 3,
                _sha256("some content here"), 0, 0,
                "accepted", None, now,
            ),
        )
        conn.commit()
        conn.close()

        report = sweep(db_path)
        t("one source found", report["total_sources"] == 1)
        t("no drift on unchanged file", len(report["drifted"]) == 0)
        t("FRESH when no drift", report["verdict"] == "FRESH")

        test_file.write_text("# Test\nModified content here.")
        report = sweep(db_path)
        t("detects drift", len(report["drifted"]) == 1)
        t("drift verdict", "drifted" in report["verdict"].lower() or "DRIFT" in report["verdict"])
        t("update applied for drift", report["updates_applied"] == 1)

        conn = connect(str(db_path))
        row = conn.execute(
            "SELECT content_sha256 FROM sources WHERE source_id = ?", (sid,)
        ).fetchone()
        conn.close()
        new_hash = hashlib.sha256(
            "# Test\nModified content here.".encode("utf-8")
        ).hexdigest()
        t("hash updated in DB", row["content_sha256"] == new_hash)

        report2 = sweep(db_path)
        t("re-sweep after update is FRESH", report2["verdict"] == "FRESH")

        test_file.unlink()
        report = sweep(db_path)
        t("detects dead file", len(report["gone_dead"]) == 1)
        t("dead verdict", "dead" in report["verdict"].lower() or "DRIFT" in report["verdict"])

        conn = connect(str(db_path))
        row = conn.execute(
            "SELECT liveness FROM sources WHERE source_id = ?", (sid,)
        ).fetchone()
        conn.close()
        t("liveness set to dead", row["liveness"] == "dead")

        test_file.write_text("# Revived\nBack again.")
        report = sweep(db_path)
        t("detects revival", len(report["revived"]) == 1)

        conn = connect(str(db_path))
        row = conn.execute(
            "SELECT liveness FROM sources WHERE source_id = ?", (sid,)
        ).fetchone()
        conn.close()
        t("liveness restored to live", row["liveness"] == "live")

        conn = connect(str(db_path))
        old_mtime = (
            _now_utc() - datetime.timedelta(days=600)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "UPDATE sources SET upstream_mtime = ?, liveness = 'live' WHERE source_id = ?",
            (old_mtime, sid),
        )
        conn.commit()
        conn.close()
        report = sweep(db_path)
        t("detects stale source", len(report["stale_18mo"]) == 1)

        conn = connect(str(db_path))
        old_fetch = (
            _now_utc() - datetime.timedelta(days=120)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "UPDATE sources SET fetched_utc = ? WHERE source_id = ?",
            (old_fetch, sid),
        )
        conn.commit()
        conn.close()
        report = sweep(db_path)
        t("detects unverified fetch", len(report["unverified_90d"]) == 1)

    status = "PASS" if not failures else "FAIL"
    checks = 18 - len(failures)
    print(f"selftest: {status} ({checks}/18 checks)")
    return not failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="Corpus staleness sweep")
    sub = parser.add_subparsers(dest="cmd")

    p_sweep = sub.add_parser("sweep", help="run staleness sweep")
    p_sweep.add_argument("--db", default=str(DEFAULT_DB))
    p_sweep.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="prove the module works")

    args = parser.parse_args(argv)

    if args.cmd == "selftest":
        ok = selftest()
        sys.exit(0 if ok else 1)
    elif args.cmd == "sweep" or args.cmd is None:
        db = args.db if hasattr(args, "db") else str(DEFAULT_DB)
        as_json = args.as_json if hasattr(args, "as_json") else False
        report = sweep(db)
        if as_json:
            print(json.dumps(report, indent=2))
        else:
            _print_report(report)


if __name__ == "__main__":
    main()
