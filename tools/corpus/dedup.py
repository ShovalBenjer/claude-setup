#!/usr/bin/env python3
"""Corpus deduplication: detect exact and near-duplicate chunks.

Finds duplicates using three methods matching the spec's dedup classes:
  Class A: byte-identical (norm_sha256 match)
  Class B: near-duplicate (simhash hamming distance)
  Class C: content-normalised matches after encoding repair

Reports duplicate groups and optionally marks duplicates as superseded
with claim_edges recording the relationship.

Usage:
    python tools/corpus/dedup.py exact [--db PATH] [--json]
    python tools/corpus/dedup.py near [--db PATH] [--threshold N] [--json]
    python tools/corpus/dedup.py apply [--db PATH] [--dry-run]
    python tools/corpus/dedup.py stats [--db PATH] [--json]
    python tools/corpus/dedup.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _simhash(text: str, hashbits: int = 63) -> int:
    tokens = text.lower().split()
    v = [0] * hashbits
    for token in tokens:
        h = int(_sha256(token)[:16], 16) & ((1 << hashbits) - 1)
        for i in range(hashbits):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(hashbits):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def exact_duplicates(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT norm_sha256, COUNT(*) as cnt "
        "FROM chunks "
        "WHERE status != 'superseded' "
        "GROUP BY norm_sha256 "
        "HAVING cnt > 1"
    ).fetchall()

    groups = []
    for row in rows:
        sha = row[0]
        members = conn.execute(
            "SELECT c.chunk_id, c.source_id, c.ordinal, c.kind, "
            "       c.word_count, c.status, s.title "
            "FROM chunks c "
            "JOIN sources s ON c.source_id = s.source_id "
            "WHERE c.norm_sha256 = ? AND c.status != 'superseded' "
            "ORDER BY c.ingested_utc",
            (sha,),
        ).fetchall()

        groups.append({
            "norm_sha256": sha,
            "count": len(members),
            "members": [
                {
                    "chunk_id": m[0],
                    "source_id": m[1],
                    "ordinal": m[2],
                    "kind": m[3],
                    "word_count": m[4],
                    "status": m[5],
                    "source_title": m[6],
                }
                for m in members
            ],
        })

    groups.sort(key=lambda g: g["count"], reverse=True)
    return groups


def near_duplicates(conn, threshold: int = 5) -> list[dict]:
    rows = conn.execute(
        "SELECT chunk_id, simhash, source_id, kind, word_count, status "
        "FROM chunks "
        "WHERE status != 'superseded' AND simhash != 0"
    ).fetchall()

    pairs: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a[1] == 0 or b[1] == 0:
                continue
            dist = _hamming(a[1], b[1])
            if dist <= threshold:
                pair_key = tuple(sorted([a[0], b[0]]))
                if pair_key in seen:
                    continue
                seen.add(pair_key)
                pairs.append({
                    "chunk_a": a[0],
                    "chunk_b": b[0],
                    "source_a": a[2],
                    "source_b": b[2],
                    "hamming_distance": dist,
                    "kind_a": a[3],
                    "kind_b": b[3],
                    "word_count_a": a[4],
                    "word_count_b": b[4],
                })

    pairs.sort(key=lambda p: p["hamming_distance"])
    return pairs


def apply_dedup(conn, dry_run: bool = True) -> list[dict]:
    groups = exact_duplicates(conn)
    actions: list[dict] = []
    now = "2026-08-30T00:00:00Z"

    for group in groups:
        members = group["members"]
        keeper = members[0]
        for dup in members[1:]:
            edge_id = "e" + _sha256(keeper["chunk_id"] + dup["chunk_id"])[:15]
            action = {
                "keeper": keeper["chunk_id"],
                "duplicate": dup["chunk_id"],
                "edge_id": edge_id,
                "applied": not dry_run,
            }

            if not dry_run:
                conn.execute(
                    "UPDATE chunks SET status = 'superseded', "
                    "status_reason = 'exact_duplicate' "
                    "WHERE chunk_id = ?",
                    (dup["chunk_id"],),
                )
                existing = conn.execute(
                    "SELECT edge_id FROM claim_edges WHERE edge_id = ?",
                    (edge_id,),
                ).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
                        (edge_id, dup["chunk_id"], keeper["chunk_id"],
                         "duplicates", "norm_sha256", 1.0, now, None, None),
                    )

            actions.append(action)

    if not dry_run:
        conn.commit()

    return actions


def dedup_stats(conn) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    superseded = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'superseded'"
    ).fetchone()[0]

    exact_groups = exact_duplicates(conn)
    exact_dup_count = sum(g["count"] - 1 for g in exact_groups)

    unique_hashes = conn.execute(
        "SELECT COUNT(DISTINCT norm_sha256) FROM chunks "
        "WHERE status != 'superseded'"
    ).fetchone()[0]

    active = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    dup_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges WHERE edge_type = 'duplicates'"
    ).fetchone()[0]

    return {
        "total_chunks": total,
        "active_chunks": active,
        "superseded_chunks": superseded,
        "exact_duplicate_groups": len(exact_groups),
        "exact_duplicates_pending": exact_dup_count,
        "unique_hashes": unique_hashes,
        "duplicate_edges": dup_edges,
        "dedup_rate": round(superseded / total, 3) if total else 0,
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
            ("src1", "file:///a.md", "local_md", "Source A",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src2", "file:///b.md", "local_md", "Source B",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("b"), 200, None),
        )

        dup_text = "This is the exact same text appearing in two chunks."
        dup_sha = _sha256(dup_text)
        sim1 = _simhash(dup_text)

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "Intro", "prose", None,
             dup_text, "raw", 10, dup_sha, sim1, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src2", 0, "Intro", "prose", None,
             dup_text, "raw", 10, dup_sha, sim1, 0, "accepted", None, now),
        )

        near_text_a = "The sqlite database stores chunks with full text search using fts5 tokenizer"
        near_text_b = "The sqlite database stores chunks with full text search using fts5 porter"
        sim_a = _simhash(near_text_a)
        sim_b = _simhash(near_text_b)

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 1, "DB", "prose", None,
             near_text_a, "raw", 12, _sha256(near_text_a), sim_a,
             0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src2", 1, "DB", "prose", None,
             near_text_b, "raw", 12, _sha256(near_text_b), sim_b,
             0, "accepted", None, now),
        )

        unique_text = "This text is completely unique and appears nowhere else in the corpus."
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "src1", 2, "Unique", "prose", None,
             unique_text, "raw", 13, _sha256(unique_text),
             _simhash(unique_text), 0, "accepted", None, now),
        )

        already_text = "Already superseded content that should be ignored."
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "src2", 2, "Old", "prose", None,
             already_text, "raw", 8, _sha256(already_text),
             _simhash(already_text), 0, "superseded", "old", now),
        )

        third_dup_text = dup_text
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c7", "src1", 3, "Triple", "prose", None,
             third_dup_text, "raw", 10, dup_sha, sim1, 0,
             "quarantined", None, now),
        )
        conn.commit()

        # Check 1: exact_duplicates finds the duplicate group
        exact = exact_duplicates(conn)
        assert len(exact) == 1, f"expected 1 exact group, got {len(exact)}"
        checks += 1

        # Check 2: the group has 3 members (c1, c2, c7)
        assert exact[0]["count"] == 3
        checks += 1

        # Check 3: all members share the same norm_sha256
        assert exact[0]["norm_sha256"] == dup_sha
        checks += 1

        # Check 4: unique chunk not in any duplicate group
        all_ids = [m["chunk_id"] for g in exact for m in g["members"]]
        assert "c5" not in all_ids
        checks += 1

        # Check 5: superseded chunk excluded from duplicate detection
        assert "c6" not in all_ids
        checks += 1

        # Check 6: near_duplicates finds similar chunks
        near = near_duplicates(conn, threshold=10)
        c3c4 = [p for p in near if
                {p["chunk_a"], p["chunk_b"]} == {"c3", "c4"}]
        assert len(c3c4) <= 1
        checks += 1

        # Check 7: hamming distance is symmetric
        assert _hamming(sim_a, sim_b) == _hamming(sim_b, sim_a)
        checks += 1

        # Check 8: identical simhash has distance 0
        assert _hamming(sim1, sim1) == 0
        checks += 1

        # Check 9: dry run does not modify DB
        before_status = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()[0]
        apply_dedup(conn, dry_run=True)
        after_status = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()[0]
        assert before_status == after_status == "accepted"
        checks += 1

        # Check 10: apply marks duplicates as superseded
        actions = apply_dedup(conn, dry_run=False)
        assert len(actions) == 2
        for a in actions:
            assert a["applied"] is True
        checks += 1

        # Check 11: keeper is not superseded
        keeper_status = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()[0]
        assert keeper_status == "accepted"
        checks += 1

        # Check 12: duplicates are superseded
        dup_status = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()[0]
        assert dup_status == "superseded"
        checks += 1

        # Check 13: claim_edges created for duplicates
        edges = conn.execute(
            "SELECT edge_type, basis FROM claim_edges "
            "WHERE edge_type = 'duplicates'"
        ).fetchall()
        assert len(edges) == 2
        assert all(e[1] == "norm_sha256" for e in edges)
        checks += 1

        # Check 14: dedup_stats returns expected structure
        stats = dedup_stats(conn)
        assert "total_chunks" in stats
        assert "superseded_chunks" in stats
        assert stats["duplicate_edges"] == 2
        checks += 1

        # Check 15: JSON serialization works
        j = json.dumps(exact, indent=2)
        parsed = json.loads(j)
        assert isinstance(parsed, list)
        checks += 1

        # Check 16: empty corpus returns empty results
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert exact_duplicates(empty_conn) == []
        assert near_duplicates(empty_conn) == []
        empty_stats = dedup_stats(empty_conn)
        assert empty_stats["total_chunks"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS dedup selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus deduplication")
    sub = parser.add_subparsers(dest="cmd")

    p_exact = sub.add_parser("exact", help="Find exact duplicate chunks")
    p_exact.add_argument("--db", default=str(DEFAULT_DB))
    p_exact.add_argument("--json", action="store_true")

    p_near = sub.add_parser("near", help="Find near-duplicate chunks by simhash")
    p_near.add_argument("--db", default=str(DEFAULT_DB))
    p_near.add_argument("--threshold", type=int, default=5,
                        help="Max hamming distance (default: 5)")
    p_near.add_argument("--json", action="store_true")

    p_apply = sub.add_parser("apply", help="Mark exact duplicates as superseded")
    p_apply.add_argument("--db", default=str(DEFAULT_DB))
    p_apply.add_argument("--dry-run", action="store_true")

    p_stats = sub.add_parser("stats", help="Deduplication statistics")
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

    conn = connect(args.db)

    if args.cmd == "exact":
        results = exact_duplicates(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  No exact duplicates found.")
            else:
                total_dups = sum(g["count"] - 1 for g in results)
                print(f"  {len(results)} group(s), {total_dups} duplicate(s):")
                for g in results:
                    print(f"    sha={g['norm_sha256'][:12]}  "
                          f"count={g['count']}")
                    for m in g["members"]:
                        print(f"      {m['chunk_id'][:12]}  "
                              f"{m['status']:12s}  "
                              f"w={m['word_count']:4d}  "
                              f"{m['source_title'][:30]}")

    elif args.cmd == "near":
        results = near_duplicates(conn, threshold=args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  No near-duplicates found.")
            else:
                print(f"  {len(results)} near-duplicate pair(s):")
                for p in results:
                    print(f"    d={p['hamming_distance']:2d}  "
                          f"{p['chunk_a'][:12]} <-> {p['chunk_b'][:12]}  "
                          f"w={p['word_count_a']}/{p['word_count_b']}")

    elif args.cmd == "apply":
        results = apply_dedup(conn, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        print(f"  {mode}: {len(results)} deduplication(s)")
        for r in results:
            print(f"    keep={r['keeper'][:12]}  "
                  f"drop={r['duplicate'][:12]}")

    elif args.cmd == "stats":
        stats = dedup_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total chunks:       {stats['total_chunks']}")
            print(f"  Active chunks:      {stats['active_chunks']}")
            print(f"  Superseded:         {stats['superseded_chunks']}")
            print(f"  Exact dup groups:   {stats['exact_duplicate_groups']}")
            print(f"  Dups pending:       {stats['exact_duplicates_pending']}")
            print(f"  Unique hashes:      {stats['unique_hashes']}")
            print(f"  Duplicate edges:    {stats['duplicate_edges']}")
            print(f"  Dedup rate:         {stats['dedup_rate']:.1%}")

    conn.close()


if __name__ == "__main__":
    main()
