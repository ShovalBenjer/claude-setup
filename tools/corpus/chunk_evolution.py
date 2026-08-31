#!/usr/bin/env python3
"""Chunk evolution: tracks how chunk content changes across re-ingestions.

Uses the chunk_versions table to identify most-revised chunks, content
drift patterns, and word count trends over time.

Usage:
    python tools/corpus/chunk_evolution.py most-revised [--db PATH] [--top N] [--json]
    python tools/corpus/chunk_evolution.py drift [--db PATH] [--json]
    python tools/corpus/chunk_evolution.py history --chunk-id CID [--db PATH] [--json]
    python tools/corpus/chunk_evolution.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def most_revised(conn, top_n: int = 20) -> list[dict]:
    """Chunks with the most version entries, ranked by revision count."""
    if not _table_exists(conn, "chunk_versions"):
        return []

    rows = conn.execute(
        "SELECT cv.chunk_id, count(*) AS rev_count, "
        "min(cv.snapshot_utc) AS first_seen, "
        "max(cv.snapshot_utc) AS last_seen, "
        "c.kind, c.status "
        "FROM chunk_versions cv "
        "JOIN chunks c ON c.chunk_id = cv.chunk_id "
        "GROUP BY cv.chunk_id "
        "HAVING rev_count > 1 "
        "ORDER BY rev_count DESC "
        "LIMIT ?",
        (top_n,),
    ).fetchall()

    return [
        {"chunk_id": r[0], "revision_count": r[1],
         "first_seen": r[2], "last_seen": r[3],
         "kind": r[4], "status": r[5]}
        for r in rows
    ]


def content_drift(conn) -> dict:
    """Corpus-wide content drift statistics from chunk_versions."""
    if not _table_exists(conn, "chunk_versions"):
        return {"chunks_with_versions": 0, "single_version": 0,
                "multi_version": 0, "total_revisions": 0,
                "avg_revisions": 0.0, "max_revisions": 0,
                "word_count_changes": []}

    stats = conn.execute(
        "SELECT count(DISTINCT chunk_id) AS chunks, "
        "count(*) AS total_versions "
        "FROM chunk_versions"
    ).fetchone()

    chunks_with_versions = stats[0]
    total_versions = stats[1]

    if chunks_with_versions == 0:
        return {"chunks_with_versions": 0, "single_version": 0,
                "multi_version": 0, "total_revisions": 0,
                "avg_revisions": 0.0, "max_revisions": 0,
                "word_count_changes": []}

    multi = conn.execute(
        "SELECT count(*) FROM ("
        "  SELECT chunk_id FROM chunk_versions "
        "  GROUP BY chunk_id HAVING count(*) > 1"
        ")"
    ).fetchone()[0]

    single = chunks_with_versions - multi

    max_rev = conn.execute(
        "SELECT max(cnt) FROM ("
        "  SELECT count(*) AS cnt FROM chunk_versions "
        "  GROUP BY chunk_id"
        ")"
    ).fetchone()[0]

    rows = conn.execute(
        "SELECT cv.chunk_id, cv.version_num, cv.word_count "
        "FROM chunk_versions cv "
        "WHERE cv.chunk_id IN ("
        "  SELECT chunk_id FROM chunk_versions "
        "  GROUP BY chunk_id HAVING count(*) > 1"
        ") "
        "ORDER BY cv.chunk_id, cv.version_num"
    ).fetchall()

    wc_changes = []
    prev: dict[str, int] = {}
    for r in rows:
        cid = r[0]
        wc = r[2]
        if cid in prev:
            delta = wc - prev[cid]
            if delta != 0:
                wc_changes.append({
                    "chunk_id": cid,
                    "version_num": r[1],
                    "word_count_delta": delta,
                })
        prev[cid] = wc

    return {
        "chunks_with_versions": chunks_with_versions,
        "single_version": single,
        "multi_version": multi,
        "total_revisions": total_versions,
        "avg_revisions": round(total_versions / chunks_with_versions, 2),
        "max_revisions": max_rev,
        "word_count_changes": wc_changes,
    }


def chunk_history(conn, chunk_id: str) -> dict:
    """Full version history for one chunk."""
    if not _table_exists(conn, "chunk_versions"):
        return {"chunk_id": chunk_id, "versions": [],
                "error": "chunk_versions table not found"}

    chunk_row = conn.execute(
        "SELECT chunk_id, kind, status, word_count "
        "FROM chunks WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchone()
    if not chunk_row:
        return {"chunk_id": chunk_id, "versions": [],
                "error": "chunk not found"}

    rows = conn.execute(
        "SELECT version_id, version_num, norm_sha256, word_count, "
        "snapshot_utc "
        "FROM chunk_versions WHERE chunk_id = ? "
        "ORDER BY version_num ASC",
        (chunk_id,),
    ).fetchall()

    versions = []
    prev_wc = None
    for r in rows:
        wc = r[3]
        delta = None
        if prev_wc is not None:
            delta = wc - prev_wc
        versions.append({
            "version_id": r[0], "version_num": r[1],
            "norm_sha256": r[2], "word_count": wc,
            "word_count_delta": delta, "snapshot_utc": r[4],
        })
        prev_wc = wc

    return {
        "chunk_id": chunk_id,
        "kind": chunk_row[1],
        "status": chunk_row[2],
        "current_word_count": chunk_row[3],
        "version_count": len(versions),
        "versions": versions,
    }


# ── selftest ─────────────────────────────────────────────────────────


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        t1 = "2026-07-01T10:00:00Z"
        t2 = "2026-08-01T10:00:00Z"
        t3 = "2026-08-15T10:00:00Z"

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(1, 4):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (f"c{i}", "s1", i - 1, f"H{i}", "claim", "en",
                 f"text{i}", f"text{i}", 10 * i, f"n{i}", now),
            )

        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v1_1", "c1", 1, "sha_v1", 10, t1),
        )
        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v1_2", "c1", 2, "sha_v2", 15, t2),
        )
        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v1_3", "c1", 3, "sha_v3", 12, t3),
        )

        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v2_1", "c2", 1, "sha_v2_1", 20, t1),
        )
        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v2_2", "c2", 2, "sha_v2_2", 20, t2),
        )

        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v3_1", "c3", 1, "sha_v3_1", 30, t1),
        )
        conn.commit()

        # 1: most revised returns multi-version chunks
        mr = most_revised(conn, top_n=10)
        assert len(mr) == 2
        assert mr[0]["chunk_id"] == "c1"
        assert mr[0]["revision_count"] == 3
        checks += 1

        # 2: second most revised
        assert mr[1]["chunk_id"] == "c2"
        assert mr[1]["revision_count"] == 2
        checks += 1

        # 3: single-version chunks excluded
        mr_ids = {m["chunk_id"] for m in mr}
        assert "c3" not in mr_ids
        checks += 1

        # 4: top_n limit
        mr2 = most_revised(conn, top_n=1)
        assert len(mr2) == 1
        checks += 1

        # 5: content drift stats
        cd = content_drift(conn)
        assert cd["chunks_with_versions"] == 3
        assert cd["multi_version"] == 2
        assert cd["single_version"] == 1
        checks += 1

        # 6: drift totals
        assert cd["total_revisions"] == 6
        assert cd["max_revisions"] == 3
        checks += 1

        # 7: word count changes detected
        wcc = cd["word_count_changes"]
        c1_changes = [w for w in wcc if w["chunk_id"] == "c1"]
        assert len(c1_changes) == 2
        assert c1_changes[0]["word_count_delta"] == 5
        assert c1_changes[1]["word_count_delta"] == -3
        checks += 1

        # 8: no word count change for c2 (same wc across versions)
        c2_changes = [w for w in wcc if w["chunk_id"] == "c2"]
        assert len(c2_changes) == 0
        checks += 1

        # 9: chunk history
        h = chunk_history(conn, "c1")
        assert h["version_count"] == 3
        assert h["kind"] == "claim"
        checks += 1

        # 10: version ordering and deltas
        assert h["versions"][0]["word_count_delta"] is None
        assert h["versions"][1]["word_count_delta"] == 5
        assert h["versions"][2]["word_count_delta"] == -3
        checks += 1

        # 11: nonexistent chunk
        h2 = chunk_history(conn, "nonexistent")
        assert "error" in h2
        checks += 1

        # 12: JSON serialisable
        _ = json.dumps(mr)
        _ = json.dumps(cd)
        _ = json.dumps(h)
        checks += 1

        # 13: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert most_revised(conn2) == []
        cd2 = content_drift(conn2)
        assert cd2["chunks_with_versions"] == 0
        checks += 1

        # 14: avg revisions
        assert cd["avg_revisions"] == 2.0
        checks += 1

    print(f"PASS chunk_evolution selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk evolution: content change tracking"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_mr = sub.add_parser("most-revised",
                          help="Chunks with most revisions")
    p_mr.add_argument("--db", default=DEFAULT_DB)
    p_mr.add_argument("--top", type=int, default=20)
    p_mr.add_argument("--json", action="store_true")

    p_dr = sub.add_parser("drift",
                          help="Corpus-wide content drift stats")
    p_dr.add_argument("--db", default=DEFAULT_DB)
    p_dr.add_argument("--json", action="store_true")

    p_hi = sub.add_parser("history",
                          help="Version history for one chunk")
    p_hi.add_argument("--chunk-id", required=True)
    p_hi.add_argument("--db", default=DEFAULT_DB)
    p_hi.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "most-revised":
        result = most_revised(conn, top_n=args.top)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Most revised chunks: {len(result)}")
            for r in result:
                print(f"  {r['chunk_id']}: {r['revision_count']} revisions "
                      f"({r['kind']}, {r['status']})")

    elif args.cmd == "drift":
        result = content_drift(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Chunks versioned: {result['chunks_with_versions']}")
            print(f"  Single version: {result['single_version']}")
            print(f"  Multi version: {result['multi_version']}")
            print(f"  Total revisions: {result['total_revisions']}")
            print(f"  Avg revisions: {result['avg_revisions']}")
            print(f"  Max revisions: {result['max_revisions']}")
            wcc = result["word_count_changes"]
            if wcc:
                print(f"  Word count changes: {len(wcc)}")

    elif args.cmd == "history":
        result = chunk_history(conn, args.chunk_id)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if "error" in result:
                print(f"Chunk {args.chunk_id}: {result['error']}")
                return
            print(f"Chunk: {result['chunk_id']} ({result['kind']}, "
                  f"{result['status']})")
            print(f"  Versions: {result['version_count']}")
            for v in result["versions"]:
                delta = ""
                if v["word_count_delta"] is not None:
                    delta = f" ({v['word_count_delta']:+d})"
                print(f"    v{v['version_num']}: {v['word_count']} words"
                      f"{delta} @ {v['snapshot_utc']}")

    conn.close()


if __name__ == "__main__":
    main()
