#!/usr/bin/env python3
"""Corpus diff: what changed since a given date.

Compares current corpus state against a cutoff timestamp to show new
sources, new chunks, status changes, and contradiction activity.
Useful for tracking corpus evolution between sessions.

Usage:
    python tools/corpus/diff.py since DATE [--db PATH] [--json]
    python tools/corpus/diff.py snapshot [--db PATH]
    python tools/corpus/diff.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _parse_date(s: str) -> str:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            datetime.datetime.strptime(s, fmt)
            if fmt == "%Y-%m-%d":
                return s + "T00:00:00Z"
            return s
        except ValueError:
            continue
    raise ValueError(f"cannot parse date: {s}")


def snapshot(conn) -> dict:
    """Capture current corpus state as a summary."""
    sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    status_rows = conn.execute(
        "SELECT status, COUNT(*) FROM chunks GROUP BY status"
    ).fetchall()
    by_status = {r[0]: r[1] for r in status_rows}

    citations = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]
    contradictions = conn.execute(
        "SELECT COUNT(*) FROM claim_edges "
        "WHERE edge_type = 'contradicts' AND resolution IS NULL"
    ).fetchone()[0]
    artifacts = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    implemented = conn.execute(
        "SELECT COUNT(*) FROM artifacts WHERE implemented = 1"
    ).fetchone()[0]

    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "timestamp": now,
        "sources": sources,
        "chunks": chunks,
        "by_status": by_status,
        "citations": citations,
        "unresolved_contradictions": contradictions,
        "artifacts": artifacts,
        "implemented_artifacts": implemented,
    }


def diff_since(conn, cutoff: str) -> dict:
    """Compute what changed since cutoff timestamp."""

    new_sources = conn.execute(
        "SELECT source_id, canonical_uri, title, kind "
        "FROM sources WHERE fetched_utc >= ?",
        (cutoff,),
    ).fetchall()

    new_chunks = conn.execute(
        "SELECT chunk_id, source_id, kind, status, word_count "
        "FROM chunks WHERE ingested_utc >= ?",
        (cutoff,),
    ).fetchall()

    new_chunk_status: dict[str, int] = {}
    for r in new_chunks:
        s = r[3]
        new_chunk_status[s] = new_chunk_status.get(s, 0) + 1

    new_citations = conn.execute(
        "SELECT COUNT(*) FROM citations c "
        "JOIN chunks ch ON c.chunk_id = ch.chunk_id "
        "WHERE ch.ingested_utc >= ?",
        (cutoff,),
    ).fetchone()[0]

    new_contradictions = conn.execute(
        "SELECT COUNT(*) FROM claim_edges "
        "WHERE edge_type = 'contradicts' AND detected_utc >= ?",
        (cutoff,),
    ).fetchone()[0]

    resolved_contradictions = conn.execute(
        "SELECT COUNT(*) FROM claim_edges "
        "WHERE edge_type = 'contradicts' AND resolution IS NOT NULL "
        "AND detected_utc >= ?",
        (cutoff,),
    ).fetchone()[0]

    new_artifacts = conn.execute(
        "SELECT a.name, a.artifact_type, a.implemented "
        "FROM artifacts a "
        "JOIN chunks ch ON a.chunk_id = ch.chunk_id "
        "WHERE ch.ingested_utc >= ?",
        (cutoff,),
    ).fetchall()

    total_now = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    total_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]

    return {
        "cutoff": cutoff,
        "new_sources": [
            {"source_id": r[0], "uri": r[1], "title": r[2], "kind": r[3]}
            for r in new_sources
        ],
        "new_chunks": {
            "total": len(new_chunks),
            "by_status": new_chunk_status,
            "details": [
                {"chunk_id": r[0], "source_id": r[1], "kind": r[2],
                 "status": r[3], "word_count": r[4]}
                for r in new_chunks[:50]
            ],
        },
        "new_citations": new_citations,
        "new_contradictions": new_contradictions,
        "resolved_contradictions": resolved_contradictions,
        "new_artifacts": [
            {"name": r[0], "type": r[1], "implemented": bool(r[2])}
            for r in new_artifacts[:50]
        ],
        "corpus_totals": {
            "sources": total_sources,
            "chunks": total_now,
        },
    }


def selftest() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)

        old_ts = "2026-08-01T00:00:00Z"
        new_ts = "2026-08-29T00:00:00Z"

        def add_source(sid, uri, fetched):
            conn.execute(
                "INSERT INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes, supersedes) "
                "VALUES (?, ?, 'local_md', 'Test', 'MIT', 'vendor', "
                " 'test', ?, 'live', ?, ?, 100, NULL)",
                (sid, uri, fetched, fetched, _sha256(sid)),
            )

        def add_chunk(cid, sid, text, status, ingested, ordinal=0):
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', 'prose', ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, ordinal, text, text, len(text.split()),
                 _sha256(text), status, ingested),
            )

        # old data
        add_source("s_old", "/old/file.md", old_ts)
        add_chunk("c_old", "s_old", "old content from before cutoff", "accepted", old_ts)

        # new data
        add_source("s_new", "/new/file.md", new_ts)
        add_chunk("c_new1", "s_new", "new content after cutoff date", "accepted", new_ts, ordinal=0)
        add_chunk("c_new2", "s_new", "more new content quarantined", "quarantined", new_ts, ordinal=1)

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES (?, ?, ?, ?, ?, 0)",
            ("cit1", "c_new1", "https://example.com", "ref", "p1"),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, 'contradicts', 'test', 0.8, ?)",
            ("e1", "c_new1", "c_old", new_ts),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc, resolution) "
            "VALUES (?, ?, ?, 'contradicts', 'test', 0.9, ?, 'resolved')",
            ("e2", "c_old", "c_new1", new_ts),
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, snippet, implemented, evidence_path) "
            "VALUES (?, ?, 'library', 'newtool', 'snippet', 1, '/path')",
            ("a1", "c_new1"),
        )
        conn.commit()

        cutoff = "2026-08-15T00:00:00Z"

        # 1: diff returns new sources after cutoff
        d = diff_since(conn, cutoff)
        checks += 1
        if len(d["new_sources"]) != 1:
            failures.append(
                f"new_sources = {len(d['new_sources'])}, expected 1"
            )

        # 2: diff returns new chunks after cutoff
        checks += 1
        if d["new_chunks"]["total"] != 2:
            failures.append(
                f"new chunks total = {d['new_chunks']['total']}, expected 2"
            )

        # 3: new chunks by_status has correct breakdown
        checks += 1
        bs = d["new_chunks"]["by_status"]
        if bs.get("accepted") != 1 or bs.get("quarantined") != 1:
            failures.append(f"by_status = {bs}, expected 1 accepted + 1 quarantined")

        # 4: new citations counted
        checks += 1
        if d["new_citations"] != 1:
            failures.append(
                f"new_citations = {d['new_citations']}, expected 1"
            )

        # 5: new contradictions counted
        checks += 1
        if d["new_contradictions"] != 2:
            failures.append(
                f"new_contradictions = {d['new_contradictions']}, expected 2"
            )

        # 6: resolved contradictions counted
        checks += 1
        if d["resolved_contradictions"] != 1:
            failures.append(
                f"resolved = {d['resolved_contradictions']}, expected 1"
            )

        # 7: new artifacts listed
        checks += 1
        if len(d["new_artifacts"]) != 1:
            failures.append(
                f"new_artifacts = {len(d['new_artifacts'])}, expected 1"
            )

        # 8: artifact has correct fields
        checks += 1
        if d["new_artifacts"]:
            a = d["new_artifacts"][0]
            if a["name"] != "newtool" or not a["implemented"]:
                failures.append(f"artifact fields wrong: {a}")

        # 9: corpus_totals reflect full state
        checks += 1
        if d["corpus_totals"]["sources"] != 2:
            failures.append(
                f"total sources = {d['corpus_totals']['sources']}, expected 2"
            )
        if d["corpus_totals"]["chunks"] != 3:
            failures.append(
                f"total chunks = {d['corpus_totals']['chunks']}, expected 3"
            )

        # 10: cutoff before all data returns everything
        d_all = diff_since(conn, "2020-01-01T00:00:00Z")
        checks += 1
        if d_all["new_chunks"]["total"] != 3:
            failures.append(
                f"full diff chunks = {d_all['new_chunks']['total']}, expected 3"
            )

        # 11: cutoff after all data returns nothing
        d_empty = diff_since(conn, "2027-01-01T00:00:00Z")
        checks += 1
        if d_empty["new_chunks"]["total"] != 0:
            failures.append("future cutoff should return 0 new chunks")

        # 12: snapshot captures current state
        s = snapshot(conn)
        checks += 1
        if s["sources"] != 2:
            failures.append(f"snapshot sources = {s['sources']}, expected 2")
        if s["chunks"] != 3:
            failures.append(f"snapshot chunks = {s['chunks']}, expected 3")

        # 13: snapshot has timestamp
        checks += 1
        if "timestamp" not in s:
            failures.append("snapshot missing timestamp")

        # 14: snapshot by_status breakdown
        checks += 1
        if s["by_status"].get("accepted") != 2:
            failures.append(
                f"snapshot accepted = {s['by_status'].get('accepted')}, "
                f"expected 2"
            )

        # 15: snapshot unresolved contradictions
        checks += 1
        if s["unresolved_contradictions"] != 1:
            failures.append(
                f"snapshot unresolved = {s['unresolved_contradictions']}, "
                f"expected 1"
            )

        # 16: JSON serializable
        checks += 1
        try:
            json.dumps(d)
            json.dumps(s)
        except (TypeError, ValueError) as e:
            failures.append(f"not JSON-serializable: {e}")

        # 17: new source has correct fields
        checks += 1
        if d["new_sources"]:
            ns = d["new_sources"][0]
            required = {"source_id", "uri", "title", "kind"}
            missing = required - set(ns.keys())
            if missing:
                failures.append(f"new source missing fields: {missing}")

        # 18: chunk details capped at 50
        checks += 1
        if len(d["new_chunks"]["details"]) > 50:
            failures.append("chunk details should be capped at 50")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS diff selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_s = sub.add_parser("since", help="Show changes since a date")
    p_s.add_argument("date", help="Cutoff date (YYYY-MM-DD or ISO8601)")
    p_s.add_argument("--db", default=None)
    p_s.add_argument("--json", action="store_true", dest="as_json")

    p_snap = sub.add_parser("snapshot", help="Capture current corpus state")
    p_snap.add_argument("--db", default=None)

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    db = args.db
    conn = connect(db)

    if args.command == "snapshot":
        s = snapshot(conn)
        print(json.dumps(s, indent=2))
        conn.close()
        return 0

    if args.command == "since":
        try:
            cutoff = _parse_date(args.date)
        except ValueError as e:
            print(f"  error: {e}")
            conn.close()
            return 1

        d = diff_since(conn, cutoff)
        conn.close()

        if args.as_json:
            print(json.dumps(d, indent=2))
            return 0

        print(f"  Changes since {cutoff}")
        print()
        print(f"  New sources: {len(d['new_sources'])}")
        for s in d["new_sources"][:10]:
            print(f"    + {s['title']} ({s['kind']})")
        print()

        nc = d["new_chunks"]
        print(f"  New chunks: {nc['total']}")
        for status, count in nc["by_status"].items():
            print(f"    {status}: {count}")
        print()

        print(f"  New citations: {d['new_citations']}")
        print(f"  New contradictions: {d['new_contradictions']}")
        print(f"  Resolved contradictions: {d['resolved_contradictions']}")
        print()

        if d["new_artifacts"]:
            print(f"  New artifacts: {len(d['new_artifacts'])}")
            for a in d["new_artifacts"][:10]:
                impl = "implemented" if a["implemented"] else "unimplemented"
                print(f"    {a['name']} ({a['type']}, {impl})")
            print()

        t = d["corpus_totals"]
        print(f"  Corpus now: {t['sources']} sources, {t['chunks']} chunks")

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
