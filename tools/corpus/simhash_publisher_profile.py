#!/usr/bin/env python3
"""Simhash publisher profile: how simhash collision groups distribute across publishers.

simhash_liveness_profile.py profiles simhash groups by source liveness.
simhash_kind_profile.py profiles simhash groups by source kind.
No tool cross-tabulates chunks.simhash with sources.publisher to measure
whether near-duplicate clusters span multiple publishers, or how content
similarity distributes across content sources.

Usage:
    python tools/corpus/simhash_publisher_profile.py by-simhash [--db PATH] [--json]
    python tools/corpus/simhash_publisher_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/simhash_publisher_profile.py concentration [--db PATH] [--json]
    python tools/corpus/simhash_publisher_profile.py summary [--db PATH] [--json]
    python tools/corpus/simhash_publisher_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def publishers_by_simhash(conn) -> list[dict]:
    """Publisher distribution per simhash collision group (groups with 2+ chunks)."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT s.publisher) AS distinct_publishers,
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
            "distinct_publishers": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def simhash_groups_by_publisher(conn) -> list[dict]:
    """Simhash group distribution per publisher."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT c.simhash) AS distinct_simhashes,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        GROUP BY s.publisher
        ORDER BY total_chunks DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_simhashes": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def simhash_publisher_concentration(conn) -> list[dict]:
    """Per-simhash publisher concentration: groups with 2+ chunks, ordered by publisher diversity."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT s.publisher) AS distinct_publishers,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        GROUP BY c.simhash
        HAVING COUNT(c.chunk_id) >= 2
        ORDER BY distinct_publishers DESC, total_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_publishers": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
            "publisher_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def simhash_publisher_summary(conn) -> dict:
    """Aggregate simhash-publisher statistics."""
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

    cross_publisher_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash
            FROM chunks c
            JOIN sources s ON c.source_id = s.source_id
            GROUP BY c.simhash
            HAVING COUNT(c.chunk_id) >= 2
               AND COUNT(DISTINCT s.publisher) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash, s.publisher
            FROM chunks c
            JOIN sources s ON c.source_id = s.source_id
            GROUP BY c.simhash, s.publisher
        )
        """
    ).fetchone()[0]

    return {
        "total_simhashes": total_simhashes,
        "total_chunks": total_chunks,
        "collision_groups": collision_groups,
        "cross_publisher_groups": cross_publisher_groups,
        "cross_publisher_rate": round(cross_publisher_groups / max(collision_groups, 1), 4),
        "distinct_simhash_publisher_pairs": distinct_pairs,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # s1: acme, s2: globex, s3: acme
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "repo", "S3", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "ghi", 150, None))

        # simhash 1000: c1 in s1(acme), c2 in s2(globex) -- cross-publisher; simhash 2000: c3 in s1(acme), c4 in s3(acme) -- same; simhash 3000: c5 in s2(globex) -- singleton
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s2", 1, "intro", "claim", None, "t", "t", 30, "def", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 2, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "methods", "claim", None, "t", "t", 35, "jkl", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s2", 2, "results", "claim", None, "t", "t", 40, "mno", 3000, 0, "accepted", None, t1))
        conn.commit()

        # 1. by-simhash: simhash 1000 has 2 distinct publishers (acme, globex)
        bs = publishers_by_simhash(conn)
        g1000 = [r for r in bs if r["simhash"] == 1000][0]
        assert g1000["distinct_publishers"] == 2
        ok += 1

        # 2. simhash 2000 has 1 distinct publisher (acme)
        g2000 = [r for r in bs if r["simhash"] == 2000][0]
        assert g2000["distinct_publishers"] == 1
        ok += 1

        # 3. simhash 3000 not in results (singleton)
        g3000 = [r for r in bs if r["simhash"] == 3000]
        assert len(g3000) == 0
        ok += 1

        # 4. by-publisher: "acme" has 2 distinct simhashes (1000, 2000)
        bp = simhash_groups_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["distinct_simhashes"] == 2
        ok += 1

        # 5. "globex" has 2 distinct simhashes (1000, 3000)
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["distinct_simhashes"] == 2
        ok += 1

        # 6. acme has 3 chunks (c1, c3, c4)
        assert acme["total_chunks"] == 3
        ok += 1

        # 7. concentration: simhash 1000 publisher_ratio = 2/2 = 1.0
        conc = simhash_publisher_concentration(conn)
        c1000 = [r for r in conc if r["simhash"] == 1000][0]
        assert c1000["publisher_ratio"] == 1.0
        ok += 1

        # 8. simhash 2000 publisher_ratio = 1/2 = 0.5
        c2000 = [r for r in conc if r["simhash"] == 2000][0]
        assert c2000["publisher_ratio"] == 0.5
        ok += 1

        # 9. simhash 3000 not in concentration (singleton)
        c3000 = [r for r in conc if r["simhash"] == 3000]
        assert len(c3000) == 0
        ok += 1

        # 10. summary: collision_groups = 2 (1000, 2000)
        s = simhash_publisher_summary(conn)
        assert s["collision_groups"] == 2
        ok += 1

        # 11. cross_publisher_groups = 1 (1000)
        assert s["cross_publisher_groups"] == 1
        ok += 1

        # 12. total_simhashes = 3
        assert s["total_simhashes"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cross_publisher_rate"] == s["cross_publisher_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = simhash_publisher_summary(conn)
        assert s["total_simhashes"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Simhash publisher profile analysis")
    ap.add_argument("command", choices=["by-simhash", "by-publisher", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS simhash_publisher_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-simhash":
        rows = publishers_by_simhash(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<16} {'publishers':<12} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_publishers']:<12} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "by-publisher":
        rows = simhash_groups_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher simhash data found.")
            else:
                print(f"{'publisher':<20} {'simhashes':<12} {'chunks':<8} {'words'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['distinct_simhashes']:<12} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "concentration":
        rows = simhash_publisher_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<16} {'publishers':<12} {'chunks':<8} {'words':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_publishers']:<12} {r['total_chunks']:<8} {r['total_words']:<12} {r['publisher_ratio']:.4f}")
    elif args.command == "summary":
        s = simhash_publisher_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
