#!/usr/bin/env python3
"""Heading simhash profile: how heading paths distribute across simhash collision groups.

heading_edge_profile.py profiles headings by claim edges.
simhash_publisher_profile.py profiles simhash groups by publisher.
No tool cross-tabulates chunks.heading_path with chunks.simhash to measure
whether structurally similar chunks cluster under the same headings, or how
simhash collision groups distribute across heading paths.

Usage:
    python tools/corpus/heading_simhash_profile.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_simhash_profile.py by-group [--db PATH] [--json]
    python tools/corpus/heading_simhash_profile.py concentration [--db PATH] [--json]
    python tools/corpus/heading_simhash_profile.py summary [--db PATH] [--json]
    python tools/corpus/heading_simhash_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def simhash_by_heading(conn) -> list[dict]:
    """Simhash collision statistics per heading path."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(c.chunk_id) AS total_chunks,
               COUNT(DISTINCT c.simhash) AS distinct_simhashes,
               SUM(CASE WHEN c.simhash IN (
                   SELECT simhash FROM chunks
                   WHERE simhash IS NOT NULL
                   GROUP BY simhash HAVING COUNT(*) >= 2
               ) THEN 1 ELSE 0 END) AS collision_chunks
        FROM chunks c
        WHERE c.simhash IS NOT NULL
        GROUP BY c.heading_path
        ORDER BY collision_chunks DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "total_chunks": r[1],
            "distinct_simhashes": r[2],
            "collision_chunks": r[3],
            "collision_rate": round(r[3] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def headings_by_simhash_group(conn) -> list[dict]:
    """Heading distribution per simhash collision group."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT c.heading_path) AS distinct_headings,
               COUNT(c.chunk_id) AS group_size
        FROM chunks c
        WHERE c.simhash IS NOT NULL
          AND c.simhash IN (
              SELECT simhash FROM chunks
              WHERE simhash IS NOT NULL
              GROUP BY simhash HAVING COUNT(*) >= 2
          )
        GROUP BY c.simhash
        ORDER BY distinct_headings DESC, group_size DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_headings": r[1],
            "group_size": r[2],
            "cross_heading": r[1] > 1,
        }
        for r in rows
    ]


def heading_simhash_concentration(conn) -> list[dict]:
    """Per-heading simhash collision concentration."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(c.chunk_id) AS total_chunks,
               COUNT(DISTINCT c.simhash) AS distinct_simhashes,
               SUM(CASE WHEN c.simhash IN (
                   SELECT simhash FROM chunks
                   WHERE simhash IS NOT NULL
                   GROUP BY simhash HAVING COUNT(*) >= 2
               ) THEN 1 ELSE 0 END) AS collision_chunks
        FROM chunks c
        WHERE c.simhash IS NOT NULL
        GROUP BY c.heading_path
        ORDER BY collision_chunks DESC, total_chunks DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "total_chunks": r[1],
            "distinct_simhashes": r[2],
            "collision_chunks": r[3],
            "collision_rate": round(r[3] / max(r[1], 1), 4),
            "simhash_ratio": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def heading_simhash_summary(conn) -> dict:
    """Aggregate heading-simhash statistics."""
    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks WHERE simhash IS NOT NULL"
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE simhash IS NOT NULL"
    ).fetchone()[0]

    collision_groups = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT simhash FROM chunks
            WHERE simhash IS NOT NULL
            GROUP BY simhash HAVING COUNT(*) >= 2
        )
        """
    ).fetchone()[0]

    cross_heading_groups = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT c.simhash
            FROM chunks c
            WHERE c.simhash IS NOT NULL
              AND c.simhash IN (
                  SELECT simhash FROM chunks
                  WHERE simhash IS NOT NULL
                  GROUP BY simhash HAVING COUNT(*) >= 2
              )
            GROUP BY c.simhash
            HAVING COUNT(DISTINCT c.heading_path) > 1
        )
        """
    ).fetchone()[0]

    headings_with_collisions = conn.execute(
        """
        SELECT COUNT(DISTINCT c.heading_path)
        FROM chunks c
        WHERE c.simhash IS NOT NULL
          AND c.simhash IN (
              SELECT simhash FROM chunks
              WHERE simhash IS NOT NULL
              GROUP BY simhash HAVING COUNT(*) >= 2
          )
        """
    ).fetchone()[0]

    return {
        "total_headings": total_headings,
        "total_chunks": total_chunks,
        "collision_groups": collision_groups,
        "cross_heading_groups": cross_heading_groups,
        "cross_heading_rate": round(cross_heading_groups / max(collision_groups, 1), 4),
        "headings_with_collisions": headings_with_collisions,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        # intro: c1 (simhash 1000), c2 (simhash 1000) -- collision within heading
        # methods: c3 (simhash 1000) -- collision cross-heading with intro
        # results: c4 (simhash 2000), c5 (simhash 2000) -- collision within heading
        # discuss: c6 (simhash 3000) -- singleton, no collision
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "results", "claim", None, "t", "t", 35, "jkl", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "s1", 6, "discuss", "claim", None, "t", "t", 15, "pqr", 3000, 0, "accepted", None, t1))
        conn.commit()

        # 1. by-heading: intro has 2 collision_chunks (c1, c2 in simhash 1000 group)
        bh = simhash_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["collision_chunks"] == 2
        ok += 1

        # 2. methods has 1 collision_chunk (c3 in simhash 1000 group)
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["collision_chunks"] == 1
        ok += 1

        # 3. results has 2 collision_chunks (c4, c5 in simhash 2000 group)
        results = [r for r in bh if r["heading_path"] == "results"][0]
        assert results["collision_chunks"] == 2
        ok += 1

        # 4. discuss has 0 collision_chunks (c6 is singleton)
        discuss = [r for r in bh if r["heading_path"] == "discuss"][0]
        assert discuss["collision_chunks"] == 0
        ok += 1

        # 5. by-group: simhash 1000 spans 2 headings (intro, methods)
        bg = headings_by_simhash_group(conn)
        g1000 = [r for r in bg if r["simhash"] == 1000][0]
        assert g1000["distinct_headings"] == 2
        ok += 1

        # 6. simhash 1000 is cross_heading = True
        assert g1000["cross_heading"] is True
        ok += 1

        # 7. simhash 2000 spans 1 heading (results), cross_heading = False
        g2000 = [r for r in bg if r["simhash"] == 2000][0]
        assert g2000["cross_heading"] is False
        ok += 1

        # 8. simhash 3000 (singleton) not in by-group results
        g3000 = [r for r in bg if r["simhash"] == 3000]
        assert len(g3000) == 0
        ok += 1

        # 9. concentration: intro simhash_ratio = 1/2 = 0.5 (1 distinct simhash, 2 chunks)
        conc = heading_simhash_concentration(conn)
        c_intro = [r for r in conc if r["heading_path"] == "intro"][0]
        assert c_intro["simhash_ratio"] == 0.5
        ok += 1

        # 10. summary: collision_groups = 2 (simhash 1000 and 2000)
        s = heading_simhash_summary(conn)
        assert s["collision_groups"] == 2
        ok += 1

        # 11. cross_heading_groups = 1 (only simhash 1000 spans intro+methods)
        assert s["cross_heading_groups"] == 1
        ok += 1

        # 12. total_headings = 4
        assert s["total_headings"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cross_heading_rate"] == s["cross_heading_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = heading_simhash_summary(conn)
        assert s["total_headings"] == 0
        assert s["collision_groups"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading simhash profile analysis")
    ap.add_argument("command", choices=["by-heading", "by-group", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_simhash_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = simhash_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading simhash data found.")
            else:
                print(f"{'heading':<20} {'chunks':<8} {'simhashes':<12} {'collisions':<12} {'rate'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['total_chunks']:<8} {r['distinct_simhashes']:<12} {r['collision_chunks']:<12} {r['collision_rate']:.4f}")
    elif args.command == "by-group":
        rows = headings_by_simhash_group(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<12} {'headings':<10} {'size':<6} {'cross_heading'}")
                for r in rows:
                    print(f"{r['simhash']:<12} {r['distinct_headings']:<10} {r['group_size']:<6} {r['cross_heading']}")
    elif args.command == "concentration":
        rows = heading_simhash_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading simhash data found.")
            else:
                print(f"{'heading':<20} {'chunks':<8} {'simhashes':<12} {'collisions':<12} {'coll_rate':<12} {'sim_ratio'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['total_chunks']:<8} {r['distinct_simhashes']:<12} {r['collision_chunks']:<12} {r['collision_rate']:<12.4f} {r['simhash_ratio']:.4f}")
    elif args.command == "summary":
        s = heading_simhash_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
