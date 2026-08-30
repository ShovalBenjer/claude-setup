#!/usr/bin/env python3
"""Tag store: persists auto-tagger results into the chunk_tags table.

Bridges the gap between the in-memory tagger (which computes but
discards tags) and downstream tools (retrieval, search, export) that
need persisted tag data for faceted queries and filtering.

Usage:
    python tools/corpus/tag_store.py persist [--db PATH] [--top-k N] [--min-score F] [--dry-run]
    python tools/corpus/tag_store.py lookup --chunk-id CID [--db PATH] [--json]
    python tools/corpus/tag_store.py find --tag TAG [--db PATH] [--min-score F] [--json]
    python tools/corpus/tag_store.py stats [--db PATH] [--json]
    python tools/corpus/tag_store.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402
from tagger import DOMAIN_VOCAB, tag_chunks  # noqa: E402


def persist_tags(conn, top_k: int = 3, min_score: float = 0.01,
                 dry_run: bool = False) -> dict:
    tagged = tag_chunks(conn, top_k=top_k, min_score=min_score)

    now = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    inserted = 0
    updated = 0
    unchanged = 0

    for result in tagged:
        chunk_id = result["chunk_id"]
        for tag_entry in result["tags"]:
            tag = tag_entry["tag"]
            score = tag_entry["score"]

            existing = conn.execute(
                "SELECT score FROM chunk_tags "
                "WHERE chunk_id = ? AND tag = ?",
                (chunk_id, tag),
            ).fetchone()

            if existing is None:
                if not dry_run:
                    conn.execute(
                        "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
                        "VALUES (?, ?, ?, ?)",
                        (chunk_id, tag, score, now),
                    )
                inserted += 1
            elif abs(existing[0] - score) > 0.0001:
                if not dry_run:
                    conn.execute(
                        "UPDATE chunk_tags SET score = ?, tagged_utc = ? "
                        "WHERE chunk_id = ? AND tag = ?",
                        (score, now, chunk_id, tag),
                    )
                updated += 1
            else:
                unchanged += 1

    if not dry_run:
        conn.commit()

    return {
        "chunks_tagged": len(tagged),
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "dry_run": dry_run,
    }


def lookup_chunk_tags(conn, chunk_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT tag, score, tagged_utc FROM chunk_tags "
        "WHERE chunk_id = ? ORDER BY score DESC",
        (chunk_id,),
    ).fetchall()
    return [{"tag": r[0], "score": r[1], "tagged_utc": r[2]} for r in rows]


def find_by_tag(conn, tag: str, min_score: float = 0.0) -> list[dict]:
    rows = conn.execute(
        "SELECT ct.chunk_id, ct.score, ct.tagged_utc, "
        "c.source_id, c.kind, c.status, c.heading_path "
        "FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE ct.tag = ? AND ct.score >= ? AND c.status != 'superseded' "
        "ORDER BY ct.score DESC",
        (tag, min_score),
    ).fetchall()
    return [{
        "chunk_id": r[0], "score": r[1], "tagged_utc": r[2],
        "source_id": r[3], "kind": r[4], "status": r[5],
        "heading_path": r[6],
    } for r in rows]


def tag_store_stats(conn) -> dict:
    total_rows = conn.execute("SELECT COUNT(*) FROM chunk_tags").fetchone()[0]
    distinct_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_tags"
    ).fetchone()[0]
    distinct_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]

    by_tag = conn.execute(
        "SELECT tag, COUNT(*), ROUND(AVG(score), 4) "
        "FROM chunk_tags GROUP BY tag ORDER BY COUNT(*) DESC"
    ).fetchall()

    active_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    return {
        "total_tag_rows": total_rows,
        "distinct_chunks_tagged": distinct_chunks,
        "distinct_tags_used": distinct_tags,
        "active_chunks": active_chunks,
        "coverage": round(distinct_chunks / active_chunks, 3) if active_chunks else 0,
        "by_tag": [{"tag": r[0], "count": r[1], "avg_score": r[2]}
                   for r in by_tag],
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
             "sqlite database uses fts5 for full text search with porter "
             "stemming tokenizer. the query engine supports bm25 ranking "
             "and reranking with vector similarity scores.",
             "raw", 25, _sha256("c1"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "Testing", "prose", None,
             "python pytest framework provides test fixtures and assertions. "
             "coverage reports measure code quality. unittest mock objects "
             "help isolate components during regression testing.",
             "raw", 22, _sha256("c2"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 2, "Old", "prose", None,
             "this chunk is superseded and should not appear.",
             "raw", 9, _sha256("c3"), 0, 0, "superseded", "old", now),
        )
        conn.commit()

        # Check 1: dry run does not persist
        result = persist_tags(conn, dry_run=True)
        assert result["dry_run"] is True
        count = conn.execute("SELECT COUNT(*) FROM chunk_tags").fetchone()[0]
        assert count == 0
        checks += 1

        # Check 2: persist creates rows
        result = persist_tags(conn, dry_run=False)
        assert result["chunks_tagged"] >= 2
        assert result["inserted"] > 0
        count = conn.execute("SELECT COUNT(*) FROM chunk_tags").fetchone()[0]
        assert count > 0
        checks += 1

        # Check 3: lookup returns tags for a chunk
        tags = lookup_chunk_tags(conn, "c1")
        assert len(tags) > 0
        assert all("tag" in t and "score" in t for t in tags)
        checks += 1

        # Check 4: tags are sorted by score desc
        scores = [t["score"] for t in tags]
        assert scores == sorted(scores, reverse=True)
        checks += 1

        # Check 5: lookup for unknown chunk returns empty
        assert lookup_chunk_tags(conn, "nonexistent") == []
        checks += 1

        # Check 6: find_by_tag returns matching chunks
        tag_name = tags[0]["tag"]
        found = find_by_tag(conn, tag_name)
        assert len(found) > 0
        assert any(f["chunk_id"] == "c1" for f in found)
        checks += 1

        # Check 7: find_by_tag excludes superseded
        all_found_ids = [f["chunk_id"] for f in find_by_tag(conn, tag_name)]
        assert "c3" not in all_found_ids
        checks += 1

        # Check 8: find_by_tag min_score filter
        high_score = find_by_tag(conn, tag_name, min_score=999.0)
        assert len(high_score) == 0
        checks += 1

        # Check 9: re-persist is idempotent (unchanged count)
        result2 = persist_tags(conn, dry_run=False)
        assert result2["unchanged"] > 0
        assert result2["inserted"] == 0
        checks += 1

        # Check 10: stats work
        stats = tag_store_stats(conn)
        assert stats["total_tag_rows"] > 0
        assert stats["distinct_chunks_tagged"] >= 2
        assert stats["distinct_tags_used"] > 0
        assert stats["coverage"] > 0
        assert len(stats["by_tag"]) > 0
        checks += 1

        # Check 11: chunk_tags table has correct schema
        row = conn.execute(
            "SELECT chunk_id, tag, score, tagged_utc FROM chunk_tags LIMIT 1"
        ).fetchone()
        assert row is not None
        assert isinstance(row[2], float)
        checks += 1

        # Check 12: primary key prevents duplicate (chunk_id, tag)
        existing_row = conn.execute(
            "SELECT chunk_id, tag FROM chunk_tags LIMIT 1"
        ).fetchone()
        try:
            conn.execute(
                "INSERT INTO chunk_tags VALUES (?, ?, 0.5, ?)",
                (existing_row[0], existing_row[1], now),
            )
            assert False, "should have raised IntegrityError"
        except Exception:
            pass
        checks += 1

        # Check 13: empty corpus
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        result = persist_tags(empty_conn, dry_run=False)
        assert result["chunks_tagged"] == 0
        assert result["inserted"] == 0
        stats = tag_store_stats(empty_conn)
        assert stats["total_tag_rows"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS tag_store selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tag store")
    sub = parser.add_subparsers(dest="cmd")

    p_persist = sub.add_parser("persist", help="Persist auto-tagger results to DB")
    p_persist.add_argument("--db", default=str(DEFAULT_DB))
    p_persist.add_argument("--top-k", type=int, default=3)
    p_persist.add_argument("--min-score", type=float, default=0.01)
    p_persist.add_argument("--dry-run", action="store_true")

    p_lookup = sub.add_parser("lookup", help="Look up tags for a chunk")
    p_lookup.add_argument("--chunk-id", required=True)
    p_lookup.add_argument("--db", default=str(DEFAULT_DB))
    p_lookup.add_argument("--json", action="store_true")

    p_find = sub.add_parser("find", help="Find chunks by tag")
    p_find.add_argument("--tag", required=True)
    p_find.add_argument("--db", default=str(DEFAULT_DB))
    p_find.add_argument("--min-score", type=float, default=0.0)
    p_find.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats", help="Tag store statistics")
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

    if args.cmd == "persist":
        conn = connect(args.db)
        result = persist_tags(conn, top_k=args.top_k,
                              min_score=args.min_score,
                              dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "PERSISTED"
        print(f"  {mode}: {result['chunks_tagged']} chunk(s) tagged, "
              f"{result['inserted']} new, {result['updated']} updated, "
              f"{result['unchanged']} unchanged")
        conn.close()

    elif args.cmd == "lookup":
        conn = connect(args.db)
        tags = lookup_chunk_tags(conn, args.chunk_id)
        if args.json:
            print(json.dumps(tags, indent=2))
        else:
            if not tags:
                print(f"  No tags for chunk {args.chunk_id}")
            else:
                print(f"  Tags for {args.chunk_id}:")
                for t in tags:
                    print(f"    {t['tag']:16s}  score={t['score']:.4f}")
        conn.close()

    elif args.cmd == "find":
        conn = connect(args.db)
        results = find_by_tag(conn, args.tag, min_score=args.min_score)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"  No chunks for tag '{args.tag}'")
            else:
                print(f"  {len(results)} chunk(s) for '{args.tag}':")
                for r in results[:50]:
                    print(f"    {r['chunk_id'][:12]}  {r['kind']:6s}  "
                          f"score={r['score']:.4f}  {r['status']}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = tag_store_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total tag rows:       {stats['total_tag_rows']}")
            print(f"  Chunks tagged:        {stats['distinct_chunks_tagged']}")
            print(f"  Tags used:            {stats['distinct_tags_used']}")
            print(f"  Active chunks:        {stats['active_chunks']}")
            print(f"  Coverage:             {stats['coverage']:.1%}")
            print("  By tag:")
            for t in stats["by_tag"]:
                print(f"    {t['tag']:16s}: {t['count']:5d}  "
                      f"avg={t['avg_score']:.4f}")
        conn.close()


if __name__ == "__main__":
    main()
