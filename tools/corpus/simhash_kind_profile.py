#!/usr/bin/env python3
"""Simhash kind profile: how simhash collision groups distribute across source kinds.

simhash_edge_profile.py profiles simhash groups by claim edges.
simhash_status_profile.py profiles simhash groups by chunk status.
No tool cross-tabulates chunks.simhash with sources.kind to measure
whether near-duplicate clusters appear more in certain source formats,
or how content similarity distributes across source kinds.

Usage:
    python tools/corpus/simhash_kind_profile.py by-simhash [--db PATH] [--json]
    python tools/corpus/simhash_kind_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/simhash_kind_profile.py concentration [--db PATH] [--json]
    python tools/corpus/simhash_kind_profile.py summary [--db PATH] [--json]
    python tools/corpus/simhash_kind_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def kinds_by_simhash(conn) -> list[dict]:
    """Kind distribution per simhash collision group (groups with 2+ chunks)."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT s.kind) AS distinct_kinds,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        GROUP BY c.simhash
        HAVING COUNT(c.chunk_id) >= 2
        ORDER BY total_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_kinds": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def simhash_groups_by_kind(conn) -> list[dict]:
    """Simhash group distribution per source kind."""
    rows = conn.execute(
        """
        SELECT s.kind,
               COUNT(DISTINCT c.simhash) AS distinct_simhashes,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        GROUP BY s.kind
        ORDER BY total_chunks DESC, s.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "distinct_simhashes": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def simhash_kind_concentration(conn) -> list[dict]:
    """Per-simhash kind concentration: groups with 2+ chunks, ordered by kind diversity."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT s.kind) AS distinct_kinds,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        GROUP BY c.simhash
        HAVING COUNT(c.chunk_id) >= 2
        ORDER BY distinct_kinds DESC, total_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_kinds": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
            "kind_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def simhash_kind_summary(conn) -> dict:
    """Aggregate simhash-kind statistics."""
    total_simhashes = conn.execute(
        "SELECT COUNT(DISTINCT c.simhash) FROM chunks c JOIN sources s ON c.source_id = s.source_id"
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks c JOIN sources s ON c.source_id = s.source_id"
    ).fetchone()[0]

    collision_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash
            FROM chunks c
            JOIN sources s ON c.source_id = s.source_id
            GROUP BY c.simhash
            HAVING COUNT(c.chunk_id) >= 2
        )
        """
    ).fetchone()[0]

    cross_kind_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash
            FROM chunks c
            JOIN sources s ON c.source_id = s.source_id
            GROUP BY c.simhash
            HAVING COUNT(c.chunk_id) >= 2
               AND COUNT(DISTINCT s.kind) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash, s.kind
            FROM chunks c
            JOIN sources s ON c.source_id = s.source_id
            GROUP BY c.simhash, s.kind
        )
        """
    ).fetchone()[0]

    return {
        "total_simhashes": total_simhashes,
        "total_chunks": total_chunks,
        "collision_groups": collision_groups,
        "cross_kind_groups": cross_kind_groups,
        "cross_kind_rate": round(cross_kind_groups / max(collision_groups, 1), 4),
        "distinct_simhash_kind_pairs": distinct_pairs,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # s1: local_md, s2: repo, s3: paper
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "repo", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "paper", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None))

        # simhash 1000: c1 in s1(local_md), c2 in s2(repo) -- cross-kind; simhash 2000: c3,c4 both in s1(local_md) -- same kind; simhash 3000: c5 in s3(paper) -- singleton
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s2", 1, "intro", "claim", None, "t", "t", 30, "def", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 2, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 3, "methods", "claim", None, "t", "t", 35, "jkl", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s3", 1, "results", "claim", None, "t", "t", 40, "mno", 3000, 0, "accepted", None, t1))
        conn.commit()

        # 1. by-simhash: simhash 1000 has 2 distinct kinds (local_md, repo)
        bs = kinds_by_simhash(conn)
        g1000 = [r for r in bs if r["simhash"] == 1000][0]
        assert g1000["distinct_kinds"] == 2
        ok += 1

        # 2. simhash 2000 has 1 distinct kind (local_md)
        g2000 = [r for r in bs if r["simhash"] == 2000][0]
        assert g2000["distinct_kinds"] == 1
        ok += 1

        # 3. simhash 3000 not in results (singleton)
        g3000 = [r for r in bs if r["simhash"] == 3000]
        assert len(g3000) == 0
        ok += 1

        # 4. by-kind: "local_md" has 2 distinct simhashes (1000, 2000)
        bk = simhash_groups_by_kind(conn)
        local_md = [r for r in bk if r["kind"] == "local_md"][0]
        assert local_md["distinct_simhashes"] == 2
        ok += 1

        # 5. "repo" has 1 simhash (1000)
        repo = [r for r in bk if r["kind"] == "repo"][0]
        assert repo["distinct_simhashes"] == 1
        ok += 1

        # 6. "paper" has 1 simhash (3000)
        paper = [r for r in bk if r["kind"] == "paper"][0]
        assert paper["distinct_simhashes"] == 1
        ok += 1

        # 7. concentration: simhash 1000 kind_ratio = 2/2 = 1.0
        conc = simhash_kind_concentration(conn)
        c1000 = [r for r in conc if r["simhash"] == 1000][0]
        assert c1000["kind_ratio"] == 1.0
        ok += 1

        # 8. simhash 2000 kind_ratio = 1/2 = 0.5
        c2000 = [r for r in conc if r["simhash"] == 2000][0]
        assert c2000["kind_ratio"] == 0.5
        ok += 1

        # 9. simhash 3000 not in concentration (singleton)
        c3000 = [r for r in conc if r["simhash"] == 3000]
        assert len(c3000) == 0
        ok += 1

        # 10. summary: collision_groups = 2 (1000, 2000)
        s = simhash_kind_summary(conn)
        assert s["collision_groups"] == 2
        ok += 1

        # 11. cross_kind_groups = 1 (1000)
        assert s["cross_kind_groups"] == 1
        ok += 1

        # 12. total_simhashes = 3
        assert s["total_simhashes"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cross_kind_rate"] == s["cross_kind_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = simhash_kind_summary(conn)
        assert s["total_simhashes"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Simhash kind profile analysis")
    ap.add_argument("command", choices=["by-simhash", "by-kind", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS simhash_kind_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-simhash":
        rows = kinds_by_simhash(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<16} {'kinds':<8} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_kinds']:<8} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "by-kind":
        rows = simhash_groups_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind simhash data found.")
            else:
                print(f"{'kind':<20} {'simhashes':<12} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['kind']:<20} {r['distinct_simhashes']:<12} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "concentration":
        rows = simhash_kind_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<16} {'kinds':<8} {'chunks':<8} {'words':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_kinds']:<8} {r['total_chunks']:<8} {r['total_words']:<12} {r['kind_ratio']:.4f}")
    elif args.command == "summary":
        s = simhash_kind_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
