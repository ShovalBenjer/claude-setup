#!/usr/bin/env python3
"""Chunk versioning: track content changes across re-ingestions.

Records a version snapshot each time a chunk's content hash changes,
enabling history browsing, content-drift detection, and audit trails
for how the corpus evolves over time.

Usage:
    python tools/corpus/chunk_versions.py snapshot [--db PATH] [--dry-run]
    python tools/corpus/chunk_versions.py history --chunk-id CID [--db PATH] [--json]
    python tools/corpus/chunk_versions.py drift [--db PATH] [--json]
    python tools/corpus/chunk_versions.py stats [--db PATH] [--json]
    python tools/corpus/chunk_versions.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _now_utc():
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot_versions(conn, dry_run: bool = False) -> dict:
    """Record a version for every chunk whose hash is not yet tracked."""
    now = _now_utc()
    chunks = conn.execute(
        "SELECT chunk_id, norm_sha256, word_count FROM chunks "
        "WHERE status != 'superseded'"
    ).fetchall()

    new_versions = 0
    unchanged = 0
    chunks_seen = 0

    for row in chunks:
        chunk_id = row[0]
        current_hash = row[1]
        word_count = row[2]
        chunks_seen += 1

        latest = conn.execute(
            "SELECT version_num, norm_sha256 FROM chunk_versions "
            "WHERE chunk_id = ? ORDER BY version_num DESC LIMIT 1",
            (chunk_id,),
        ).fetchone()

        if latest is None:
            if not dry_run:
                vid = _sha256(f"{chunk_id}:1:{now}")
                conn.execute(
                    "INSERT INTO chunk_versions "
                    "(version_id, chunk_id, version_num, norm_sha256, "
                    " word_count, snapshot_utc) "
                    "VALUES (?, ?, 1, ?, ?, ?)",
                    (vid, chunk_id, current_hash, word_count, now),
                )
            new_versions += 1
        elif latest[1] != current_hash:
            next_num = latest[0] + 1
            if not dry_run:
                vid = _sha256(f"{chunk_id}:{next_num}:{now}")
                conn.execute(
                    "INSERT INTO chunk_versions "
                    "(version_id, chunk_id, version_num, norm_sha256, "
                    " word_count, snapshot_utc) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (vid, chunk_id, next_num, current_hash, word_count, now),
                )
            new_versions += 1
        else:
            unchanged += 1

    if not dry_run:
        conn.commit()

    return {
        "chunks_seen": chunks_seen,
        "new_versions": new_versions,
        "unchanged": unchanged,
        "dry_run": dry_run,
    }


def chunk_history(conn, chunk_id: str) -> list[dict]:
    """Return version history for a chunk, newest first."""
    rows = conn.execute(
        "SELECT version_num, norm_sha256, word_count, snapshot_utc "
        "FROM chunk_versions WHERE chunk_id = ? "
        "ORDER BY version_num DESC",
        (chunk_id,),
    ).fetchall()
    return [
        {"version": r[0], "norm_sha256": r[1],
         "word_count": r[2], "snapshot_utc": r[3]}
        for r in rows
    ]


def detect_drift(conn) -> list[dict]:
    """Find chunks with multiple versions (content changed over time)."""
    rows = conn.execute(
        "SELECT cv.chunk_id, COUNT(*) AS versions, "
        "MIN(cv.snapshot_utc) AS first_seen, "
        "MAX(cv.snapshot_utc) AS last_changed, "
        "c.heading_path, c.source_id "
        "FROM chunk_versions cv "
        "JOIN chunks c ON c.chunk_id = cv.chunk_id "
        "GROUP BY cv.chunk_id HAVING COUNT(*) > 1 "
        "ORDER BY COUNT(*) DESC"
    ).fetchall()
    return [
        {"chunk_id": r[0], "versions": r[1], "first_seen": r[2],
         "last_changed": r[3], "heading_path": r[4], "source_id": r[5]}
        for r in rows
    ]


def version_stats(conn) -> dict:
    """Summary statistics for chunk versioning."""
    total_versions = conn.execute(
        "SELECT COUNT(*) FROM chunk_versions"
    ).fetchone()[0]
    versioned_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_versions"
    ).fetchone()[0]
    multi_version = conn.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT chunk_id FROM chunk_versions "
        "  GROUP BY chunk_id HAVING COUNT(*) > 1"
        ")"
    ).fetchone()[0]
    active_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    max_versions = conn.execute(
        "SELECT chunk_id, COUNT(*) AS c FROM chunk_versions "
        "GROUP BY chunk_id ORDER BY c DESC LIMIT 1"
    ).fetchone()

    return {
        "total_version_rows": total_versions,
        "versioned_chunks": versioned_chunks,
        "multi_version_chunks": multi_version,
        "active_chunks": active_chunks,
        "coverage": round(versioned_chunks / active_chunks, 3)
        if active_chunks else 0,
        "most_revised": {
            "chunk_id": max_versions[0],
            "versions": max_versions[1],
        } if max_versions else None,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Test Doc",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "Database", "prose", None,
             "sqlite database full text search with fts5",
             "raw", 7, _sha256("sqlite database full text search with fts5"),
             0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "Testing", "prose", None,
             "pytest framework provides test fixtures",
             "raw", 5, _sha256("pytest framework provides test fixtures"),
             0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 2, "Old", "prose", None,
             "this chunk is superseded",
             "raw", 4, _sha256("this chunk is superseded"),
             0, 0, "superseded", "old", now),
        )
        conn.commit()

        # Check 1: dry run does not persist
        result = snapshot_versions(conn, dry_run=True)
        assert result["dry_run"] is True
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_versions"
        ).fetchone()[0]
        assert count == 0
        checks += 1

        # Check 2: snapshot creates initial versions
        result = snapshot_versions(conn, dry_run=False)
        assert result["chunks_seen"] == 2
        assert result["new_versions"] == 2
        checks += 1

        # Check 3: re-snapshot is idempotent
        result2 = snapshot_versions(conn, dry_run=False)
        assert result2["unchanged"] == 2
        assert result2["new_versions"] == 0
        checks += 1

        # Check 4: history returns versions
        hist = chunk_history(conn, "c1")
        assert len(hist) == 1
        assert hist[0]["version"] == 1
        checks += 1

        # Check 5: history for unknown chunk is empty
        assert chunk_history(conn, "nonexistent") == []
        checks += 1

        # Check 6: superseded chunks are excluded
        hist_sup = chunk_history(conn, "c3")
        assert len(hist_sup) == 0
        checks += 1

        # Check 7: content change creates new version
        new_text = "sqlite database fts5 with porter tokenizer"
        new_hash = _sha256(new_text)
        conn.execute(
            "UPDATE chunks SET norm_text = ?, norm_sha256 = ?, word_count = ? "
            "WHERE chunk_id = 'c1'",
            (new_text, new_hash, 6),
        )
        conn.commit()
        result3 = snapshot_versions(conn, dry_run=False)
        assert result3["new_versions"] == 1
        assert result3["unchanged"] == 1
        checks += 1

        # Check 8: history now has two versions
        hist2 = chunk_history(conn, "c1")
        assert len(hist2) == 2
        assert hist2[0]["version"] == 2
        assert hist2[1]["version"] == 1
        checks += 1

        # Check 9: versions sorted newest first
        versions = [h["version"] for h in hist2]
        assert versions == sorted(versions, reverse=True)
        checks += 1

        # Check 10: drift detects multi-version chunks
        drifted = detect_drift(conn)
        assert len(drifted) == 1
        assert drifted[0]["chunk_id"] == "c1"
        assert drifted[0]["versions"] == 2
        checks += 1

        # Check 11: stats work
        stats = version_stats(conn)
        assert stats["total_version_rows"] == 3
        assert stats["versioned_chunks"] == 2
        assert stats["multi_version_chunks"] == 1
        assert stats["coverage"] > 0
        assert stats["most_revised"]["chunk_id"] == "c1"
        assert stats["most_revised"]["versions"] == 2
        checks += 1

        # Check 12: primary key prevents duplicate version numbers
        existing = conn.execute(
            "SELECT version_id, chunk_id, version_num FROM chunk_versions LIMIT 1"
        ).fetchone()
        try:
            conn.execute(
                "INSERT INTO chunk_versions VALUES (?, ?, ?, ?, 5, ?)",
                ("dup", existing[1], existing[2], "somehash", now),
            )
            assert False, "should have raised IntegrityError"
        except Exception:
            pass
        checks += 1

        # Check 13: empty corpus
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        result = snapshot_versions(empty_conn, dry_run=False)
        assert result["chunks_seen"] == 0
        assert result["new_versions"] == 0
        empty_conn.close()
        checks += 1

        # Check 14: word_count tracked in version
        hist_wc = chunk_history(conn, "c1")
        assert hist_wc[0]["word_count"] == 6
        assert hist_wc[1]["word_count"] == 7
        checks += 1

        conn.close()

    print(f"PASS chunk_versions selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Chunk versioning")
    sub = parser.add_subparsers(dest="cmd")

    p_snap = sub.add_parser("snapshot",
                            help="Record version for changed chunks")
    p_snap.add_argument("--db", default=str(DEFAULT_DB))
    p_snap.add_argument("--dry-run", action="store_true")

    p_hist = sub.add_parser("history", help="Version history for a chunk")
    p_hist.add_argument("--chunk-id", required=True)
    p_hist.add_argument("--db", default=str(DEFAULT_DB))
    p_hist.add_argument("--json", action="store_true")

    p_drift = sub.add_parser("drift", help="Find chunks with content drift")
    p_drift.add_argument("--db", default=str(DEFAULT_DB))
    p_drift.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats", help="Versioning statistics")
    p_stats.add_argument("--db", default=str(DEFAULT_DB))
    p_stats.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "snapshot":
        conn = connect(args.db)
        result = snapshot_versions(conn, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "SNAPSHOT"
        print(f"  {mode}: {result['chunks_seen']} chunk(s) seen, "
              f"{result['new_versions']} new version(s), "
              f"{result['unchanged']} unchanged")
        conn.close()

    elif args.cmd == "history":
        conn = connect(args.db)
        hist = chunk_history(conn, args.chunk_id)
        if args.json:
            print(json.dumps(hist, indent=2))
        else:
            if not hist:
                print(f"  No version history for {args.chunk_id}")
            else:
                print(f"  {len(hist)} version(s) for {args.chunk_id}:")
                for h in hist:
                    print(f"    v{h['version']}  words={h['word_count']}  "
                          f"sha={h['norm_sha256'][:12]}  {h['snapshot_utc']}")
        conn.close()

    elif args.cmd == "drift":
        conn = connect(args.db)
        drifted = detect_drift(conn)
        if args.json:
            print(json.dumps(drifted, indent=2))
        else:
            if not drifted:
                print("  No content drift detected")
            else:
                print(f"  {len(drifted)} chunk(s) with content drift:")
                for d in drifted[:50]:
                    print(f"    {d['chunk_id'][:12]}  "
                          f"v{d['versions']}  {d['heading_path']}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = version_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total versions:       {stats['total_version_rows']}")
            print(f"  Versioned chunks:     {stats['versioned_chunks']}")
            print(f"  Multi-version:        {stats['multi_version_chunks']}")
            print(f"  Active chunks:        {stats['active_chunks']}")
            print(f"  Coverage:             {stats['coverage']:.1%}")
            if stats["most_revised"]:
                mr = stats["most_revised"]
                print(f"  Most revised:         {mr['chunk_id'][:12]} "
                      f"({mr['versions']} versions)")
        conn.close()


if __name__ == "__main__":
    main()
