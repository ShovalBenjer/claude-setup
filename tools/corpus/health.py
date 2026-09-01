#!/usr/bin/env python3
"""Corpus health oracle: aggregates defect queries and tool signals into a verdict.

Runs the section 4.4 defect queries (uncited accepted claims, unresolved
contradictions), checks embedding freshness, reports staleness distribution
and artifact implementation coverage, and produces a structured health report
with a pass/fail exit code suitable for gate.py integration.

Usage:
  python tools/corpus/health.py check [--db PATH] [--json]   # full health check, exit 1 on defects
  python tools/corpus/health.py selftest                      # prove the module works
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

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "state" / "corpus.db"


def _connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _table_exists(conn, name):
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row[0] > 0


def uncited_claims(conn):
    """Section 4.4 defect query 1: accepted claim chunks with no verified citation."""
    if not _table_exists(conn, "chunks"):
        return []
    return conn.execute(
        "SELECT c.chunk_id, s.canonical_uri, substr(c.norm_text, 1, 80) AS preview "
        "FROM chunks c JOIN sources s USING(source_id) "
        "LEFT JOIN citations ci ON ci.chunk_id = c.chunk_id AND ci.verified = 1 "
        "WHERE c.kind = 'claim' AND c.status = 'accepted' AND ci.citation_id IS NULL"
    ).fetchall()


def unresolved_contradictions(conn):
    """Section 4.4 defect query 2: accepted chunks on an unresolved contradiction."""
    if not _table_exists(conn, "claim_edges"):
        return []
    return conn.execute(
        "SELECT e.edge_id, e.confidence, e.basis, "
        "       a.chunk_id AS a_chunk, b.chunk_id AS b_chunk, "
        "       sa.canonical_uri AS a_source, sb.canonical_uri AS b_source "
        "FROM claim_edges e "
        "JOIN chunks a ON a.chunk_id = e.source_chunk "
        "JOIN chunks b ON b.chunk_id = e.target_chunk "
        "JOIN sources sa ON sa.source_id = a.source_id "
        "JOIN sources sb ON sb.source_id = b.source_id "
        "WHERE e.edge_type = 'contradicts' AND e.resolution IS NULL "
        "  AND a.status = 'accepted' AND b.status = 'accepted' "
        "ORDER BY e.confidence DESC"
    ).fetchall()


def embedding_status(conn, db_path=None):
    """Check whether corpus vectors are current, stale, or missing."""
    dp = db_path or DEFAULT_DB
    vec_dir = dp.parent if isinstance(dp, Path) else Path(dp).parent
    vec_npy = vec_dir / "corpus-vec.npy"
    vec_json = vec_dir / "corpus-vec.json"

    gen_row = conn.execute(
        "SELECT value FROM corpus_meta WHERE key='generation'"
    ).fetchone()
    corpus_gen = int(gen_row[0]) if gen_row else 0

    if not vec_npy.exists() or not vec_json.exists():
        return {"status": "not_fitted", "corpus_generation": corpus_gen}

    try:
        with open(vec_json) as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"status": "not_fitted", "corpus_generation": corpus_gen}

    vec_gen = meta.get("generation", -1)
    result = {
        "corpus_generation": corpus_gen,
        "vec_generation": vec_gen,
        "n_chunks": meta.get("n_chunks", 0),
        "components": meta.get("components", 0),
    }

    if vec_gen != corpus_gen:
        result["status"] = "stale"
    else:
        result["status"] = "current"

    return result


def staleness_distribution(conn):
    """Count sources by liveness and flag those older than 18 months."""
    if not _table_exists(conn, "sources"):
        return {"total": 0, "by_liveness": {}}

    rows = conn.execute(
        "SELECT liveness, count(*) AS cnt FROM sources GROUP BY liveness"
    ).fetchall()
    by_liveness = {r["liveness"]: r["cnt"] for r in rows}
    total = sum(by_liveness.values())

    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=548)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    stale_sources = conn.execute(
        "SELECT count(*) FROM sources WHERE upstream_mtime < ? AND upstream_mtime != ''",
        (cutoff_str,),
    ).fetchone()[0]

    return {
        "total": total,
        "by_liveness": by_liveness,
        "upstream_stale_18mo": stale_sources,
    }


def artifact_coverage(conn):
    """Report artifact implementation coverage."""
    if not _table_exists(conn, "artifacts"):
        return {"total": 0, "implemented": 0, "unimplemented": 0, "rate": 0.0}

    total = conn.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    impl = conn.execute(
        "SELECT count(*) FROM artifacts WHERE implemented = 1"
    ).fetchone()[0]

    return {
        "total": total,
        "implemented": impl,
        "unimplemented": total - impl,
        "rate": round(impl / total, 3) if total > 0 else 0.0,
    }


def chunk_status_summary(conn):
    """Summary of chunks by status."""
    if not _table_exists(conn, "chunks"):
        return {"total": 0, "by_status": {}, "by_kind": {}}

    by_status = conn.execute(
        "SELECT status, count(*) AS cnt FROM chunks GROUP BY status"
    ).fetchall()
    by_kind = conn.execute(
        "SELECT kind, count(*) AS cnt FROM chunks GROUP BY kind"
    ).fetchall()
    total = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]

    return {
        "total": total,
        "by_status": {r["status"]: r["cnt"] for r in by_status},
        "by_kind": {r["kind"]: r["cnt"] for r in by_kind},
    }


def check(db_path=None, as_json=False):
    """Run full health check. Returns (report_dict, exit_code)."""
    dp = Path(db_path) if db_path else DEFAULT_DB
    if not dp.exists():
        report = {"verdict": "NO_CORPUS", "reason": f"{dp} not found"}
        return report, 1

    conn = _connect(dp)

    uncited = uncited_claims(conn)
    contradictions = unresolved_contradictions(conn)
    embed = embedding_status(conn, dp)
    staleness = staleness_distribution(conn)
    artifacts = artifact_coverage(conn)
    chunks = chunk_status_summary(conn)

    defects = []
    if uncited:
        defects.append(f"{len(uncited)} uncited accepted claims")
    if contradictions:
        defects.append(f"{len(contradictions)} unresolved contradictions")
    if embed["status"] == "stale":
        defects.append("embedding vectors stale (generation mismatch)")

    verdict = "HEALTHY" if not defects else "DEFECTS"
    exit_code = 0 if not defects else 1

    report = {
        "verdict": verdict,
        "defects": defects,
        "uncited_claims": len(uncited),
        "unresolved_contradictions": len(contradictions),
        "embedding": embed,
        "staleness": staleness,
        "artifacts": artifacts,
        "chunks": chunks,
    }

    conn.close()
    return report, exit_code


def _print_report(report):
    """Human-readable output."""
    v = report["verdict"]
    print(f"corpus health: {v}")

    if report.get("reason"):
        print(f"  {report['reason']}")
        return

    print(f"\n  chunks: {report['chunks']['total']}")
    for status, cnt in sorted(report["chunks"]["by_status"].items()):
        print(f"    {status}: {cnt}")

    print(f"\n  uncited accepted claims: {report['uncited_claims']}")
    print(f"  unresolved contradictions: {report['unresolved_contradictions']}")

    embed = report["embedding"]
    print(f"\n  embedding: {embed['status']}")
    if embed.get("n_chunks"):
        print(f"    vectors: {embed['n_chunks']} chunks, {embed.get('components', '?')} components")
    print(f"    corpus generation: {embed['corpus_generation']}")
    if "vec_generation" in embed:
        print(f"    vector generation: {embed['vec_generation']}")

    staleness = report["staleness"]
    print(f"\n  sources: {staleness['total']}")
    for liveness, cnt in sorted(staleness["by_liveness"].items()):
        print(f"    {liveness}: {cnt}")
    if staleness.get("upstream_stale_18mo"):
        print(f"    upstream >18mo: {staleness['upstream_stale_18mo']}")

    arts = report["artifacts"]
    print(f"\n  artifacts: {arts['total']} total, {arts['implemented']} implemented ({arts['rate']:.1%})")

    if report["defects"]:
        print(f"\n  defects:")
        for d in report["defects"]:
            print(f"    - {d}")


def selftest():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = _connect(db_path)

        conn.executescript("""
            CREATE TABLE corpus_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO corpus_meta VALUES ('schema_version', '1');
            INSERT INTO corpus_meta VALUES ('generation', '3');

            CREATE TABLE sources (
                source_id TEXT PRIMARY KEY, canonical_uri TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL, title TEXT NOT NULL,
                license_spdx TEXT NOT NULL, license_verdict TEXT NOT NULL,
                license_evidence TEXT NOT NULL, publisher TEXT,
                published_utc TEXT, fetched_utc TEXT NOT NULL,
                upstream_rev TEXT, upstream_mtime TEXT,
                liveness TEXT NOT NULL, content_sha256 TEXT NOT NULL,
                bytes INTEGER NOT NULL, supersedes TEXT
            );

            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL, heading_path TEXT NOT NULL,
                kind TEXT NOT NULL, lang TEXT, norm_text TEXT NOT NULL,
                raw_text TEXT NOT NULL, word_count INTEGER NOT NULL,
                norm_sha256 TEXT NOT NULL, simhash INTEGER NOT NULL,
                citation_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL, status_reason TEXT,
                ingested_utc TEXT NOT NULL,
                UNIQUE(source_id, ordinal)
            );

            CREATE TABLE citations (
                citation_id TEXT PRIMARY KEY, chunk_id TEXT NOT NULL,
                target_uri TEXT NOT NULL, target_source_id TEXT,
                tag TEXT, locator TEXT,
                verified INTEGER NOT NULL DEFAULT 0, verified_utc TEXT
            );

            CREATE TABLE claim_edges (
                edge_id TEXT PRIMARY KEY,
                source_chunk TEXT NOT NULL, target_chunk TEXT NOT NULL,
                edge_type TEXT NOT NULL, basis TEXT NOT NULL,
                confidence REAL NOT NULL, detected_utc TEXT NOT NULL,
                resolution TEXT, resolved_utc TEXT
            );

            CREATE TABLE artifacts (
                artifact_id TEXT PRIMARY KEY, chunk_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL, name TEXT NOT NULL,
                version TEXT, snippet TEXT,
                implemented INTEGER NOT NULL, evidence_path TEXT
            );

            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                norm_text, heading_path, content='chunks', content_rowid='rowid',
                tokenize='porter unicode61'
            );
        """)

        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        conn.execute(
            "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s_test1", "/test/file.md", "local_md", "Test", "MIT", "vendor",
             "manual", None, None, now, None, now, "live",
             hashlib.sha256(b"test").hexdigest(), 100, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("c_cited", "s_test1", 0, "H1", "claim", None,
             "cited claim text", "cited claim text", 3,
             hashlib.sha256(b"cited").hexdigest(), 0, 1,
             "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("c_uncited", "s_test1", 1, "H1", "claim", None,
             "uncited claim text", "uncited claim text", 3,
             hashlib.sha256(b"uncited").hexdigest(), 0, 0,
             "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("c_code", "s_test1", 2, "H1", "code", "python",
             "print('hello')", "print('hello')", 1,
             hashlib.sha256(b"code").hexdigest(), 0, 0,
             "accepted", None, now),
        )

        conn.execute(
            "INSERT INTO citations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("ci_1", "c_cited", "https://example.com", None, "[S1]", None, 1, now),
        )

        conn.execute(
            "INSERT INTO claim_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("e_1", "c_cited", "c_uncited", "contradicts", "negation",
             0.85, now, None, None),
        )

        conn.execute(
            "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("a_1", "c_code", "library", "numpy", "2.2.6", "import numpy", 1,
             "requirements.txt:3"),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("a_2", "c_code", "library", "torch", None, "import torch", 0, None),
        )

        conn.commit()

        def t(name, cond):
            if not cond:
                failures.append(name)
                print(f"  FAIL: {name}")

        uc = uncited_claims(conn)
        t("uncited_claims finds uncited accepted claim", len(uc) == 1)
        t("uncited_claims returns correct chunk", len(uc) == 1 and uc[0]["chunk_id"] == "c_uncited")

        ct = unresolved_contradictions(conn)
        t("unresolved_contradictions finds open edge", len(ct) == 1)
        t("contradiction has correct confidence", len(ct) == 1 and abs(ct[0]["confidence"] - 0.85) < 0.01)

        embed = embedding_status(conn, db_path)
        t("embedding reports not_fitted when no vectors", embed["status"] == "not_fitted")
        t("embedding reports correct generation", embed["corpus_generation"] == 3)

        staleness = staleness_distribution(conn)
        t("staleness counts sources", staleness["total"] == 1)
        t("staleness by_liveness has live", staleness["by_liveness"].get("live") == 1)

        arts = artifact_coverage(conn)
        t("artifact total", arts["total"] == 2)
        t("artifact implemented count", arts["implemented"] == 1)
        t("artifact rate", abs(arts["rate"] - 0.5) < 0.01)

        chunks = chunk_status_summary(conn)
        t("chunk total", chunks["total"] == 3)
        t("chunk by_status has accepted", chunks["by_status"].get("accepted") == 3)

        report, code = check(db_path)
        t("check returns DEFECTS when uncited and contradicted", report["verdict"] == "DEFECTS")
        t("exit code is 1 on defects", code == 1)
        t("defect list names uncited", any("uncited" in d for d in report["defects"]))
        t("defect list names contradictions", any("contradict" in d for d in report["defects"]))

        conn.execute("DELETE FROM claim_edges")
        conn.execute(
            "INSERT INTO citations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("ci_2", "c_uncited", "https://example.com/2", None, "[S2]", None, 1, now),
        )
        conn.commit()

        report2, code2 = check(db_path)
        t("check returns HEALTHY when defects cleared", report2["verdict"] == "HEALTHY")
        t("exit code is 0 when healthy", code2 == 0)

        conn.close()

    status = "PASS" if not failures else "FAIL"
    checks = 18 - len(failures)
    print(f"selftest: {status} ({checks}/18 checks)")
    return not failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="Corpus health oracle")
    sub = parser.add_subparsers(dest="cmd")

    p_check = sub.add_parser("check", help="full health check")
    p_check.add_argument("--db", default=str(DEFAULT_DB), help="corpus database path")
    p_check.add_argument("--json", action="store_true", dest="as_json", help="JSON output")

    sub.add_parser("selftest", help="prove the module works")

    args = parser.parse_args(argv)

    if args.cmd == "selftest":
        ok = selftest()
        sys.exit(0 if ok else 1)
    elif args.cmd == "check" or args.cmd is None:
        db = args.db if hasattr(args, "db") else str(DEFAULT_DB)
        as_json = args.as_json if hasattr(args, "as_json") else False
        report, code = check(db)
        if as_json:
            print(json.dumps(report, indent=2))
        else:
            _print_report(report)
        sys.exit(code)


if __name__ == "__main__":
    main()
