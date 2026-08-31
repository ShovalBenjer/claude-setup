#!/usr/bin/env python3
"""Simhash status profile: how simhash collision groups distribute across chunk statuses.

simhash_edge_profile.py profiles simhash groups by claim edges.
No tool cross-tabulates chunks.simhash with chunks.status to measure
whether near-duplicate clusters (shared simhash values) concentrate in
accepted versus quarantined or rejected chunks, or how quality
distributes across content similarity groups.

Usage:
    python tools/corpus/simhash_status_profile.py by-simhash [--db PATH] [--json]
    python tools/corpus/simhash_status_profile.py by-status [--db PATH] [--json]
    python tools/corpus/simhash_status_profile.py concentration [--db PATH] [--json]
    python tools/corpus/simhash_status_profile.py summary [--db PATH] [--json]
    python tools/corpus/simhash_status_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def statuses_by_simhash(conn) -> list[dict]:
    """Status distribution per simhash value (groups with 2+ chunks only)."""
    rows = conn.execute(
        """
        SELECT simhash,
               COUNT(DISTINCT status) AS distinct_statuses,
               COUNT(chunk_id) AS total_chunks,
               SUM(word_count) AS total_words
        FROM chunks
        GROUP BY simhash
        HAVING COUNT(chunk_id) >= 2
        ORDER BY total_chunks DESC, simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_statuses": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def simhash_groups_by_status(conn) -> list[dict]:
    """Simhash group distribution per chunk status."""
    rows = conn.execute(
        """
        SELECT status,
               COUNT(DISTINCT simhash) AS distinct_simhashes,
               COUNT(chunk_id) AS total_chunks,
               SUM(word_count) AS total_words
        FROM chunks
        GROUP BY status
        ORDER BY total_chunks DESC, status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "distinct_simhashes": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def simhash_status_concentration(conn) -> list[dict]:
    """Per-simhash status concentration: groups with 2+ chunks, ordered by status diversity."""
    rows = conn.execute(
        """
        SELECT simhash,
               COUNT(DISTINCT status) AS distinct_statuses,
               COUNT(chunk_id) AS total_chunks,
               SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS accepted,
               SUM(CASE WHEN status = 'quarantined' THEN 1 ELSE 0 END) AS quarantined,
               SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected
        FROM chunks
        GROUP BY simhash
        HAVING COUNT(chunk_id) >= 2
        ORDER BY distinct_statuses DESC, total_chunks DESC, simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_statuses": r[1],
            "total_chunks": r[2],
            "accepted": r[3],
            "quarantined": r[4],
            "rejected": r[5],
            "acceptance_rate": round(r[3] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def simhash_status_summary(conn) -> dict:
    """Aggregate simhash-status statistics."""
    total_simhashes = conn.execute(
        "SELECT COUNT(DISTINCT simhash) FROM chunks"
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    collision_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT simhash
            FROM chunks
            GROUP BY simhash
            HAVING COUNT(chunk_id) >= 2
        )
        """
    ).fetchone()[0]

    chunks_in_collisions = conn.execute(
        """
        SELECT COALESCE(SUM(cnt), 0)
        FROM (
            SELECT COUNT(chunk_id) AS cnt
            FROM chunks
            GROUP BY simhash
            HAVING COUNT(chunk_id) >= 2
        )
        """
    ).fetchone()[0]

    mixed_status_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT simhash
            FROM chunks
            GROUP BY simhash
            HAVING COUNT(chunk_id) >= 2
               AND COUNT(DISTINCT status) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT simhash, status
            FROM chunks
            GROUP BY simhash, status
        )
        """
    ).fetchone()[0]

    return {
        "total_simhashes": total_simhashes,
        "total_chunks": total_chunks,
        "collision_groups": collision_groups,
        "chunks_in_collisions": chunks_in_collisions,
        "mixed_status_groups": mixed_status_groups,
        "mixed_status_rate": round(mixed_status_groups / max(collision_groups, 1), 4),
        "distinct_simhash_status_pairs": distinct_pairs,
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

        # simhash 1000: c1 accepted, c2 quarantined (mixed); simhash 2000: c3 accepted, c4 accepted (uniform); simhash 3000: c5 rejected (singleton)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1000, 0, "quarantined", "low quality", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 35, "jkl", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3000, 0, "rejected", "duplicate", t1))
        conn.commit()

        # 1. by-simhash: simhash 1000 has 2 distinct statuses
        bs = statuses_by_simhash(conn)
        g1000 = [r for r in bs if r["simhash"] == 1000][0]
        assert g1000["distinct_statuses"] == 2
        ok += 1

        # 2. simhash 2000 has 1 distinct status
        g2000 = [r for r in bs if r["simhash"] == 2000][0]
        assert g2000["distinct_statuses"] == 1
        ok += 1

        # 3. simhash 3000 not in results (singleton)
        g3000 = [r for r in bs if r["simhash"] == 3000]
        assert len(g3000) == 0
        ok += 1

        # 4. by-status: "accepted" has 2 distinct simhashes (1000, 2000)
        bst = simhash_groups_by_status(conn)
        accepted = [r for r in bst if r["status"] == "accepted"][0]
        assert accepted["distinct_simhashes"] == 2
        ok += 1

        # 5. "quarantined" has 1 simhash (1000)
        quarantined = [r for r in bst if r["status"] == "quarantined"][0]
        assert quarantined["distinct_simhashes"] == 1
        ok += 1

        # 6. "rejected" has 1 simhash (3000)
        rejected = [r for r in bst if r["status"] == "rejected"][0]
        assert rejected["distinct_simhashes"] == 1
        ok += 1

        # 7. concentration: simhash 1000 acceptance_rate = 0.5
        conc = simhash_status_concentration(conn)
        c1000 = [r for r in conc if r["simhash"] == 1000][0]
        assert c1000["acceptance_rate"] == 0.5
        ok += 1

        # 8. simhash 2000 acceptance_rate = 1.0
        c2000 = [r for r in conc if r["simhash"] == 2000][0]
        assert c2000["acceptance_rate"] == 1.0
        ok += 1

        # 9. simhash 3000 not in concentration (singleton)
        c3000 = [r for r in conc if r["simhash"] == 3000]
        assert len(c3000) == 0
        ok += 1

        # 10. summary: collision_groups = 2 (1000, 2000)
        s = simhash_status_summary(conn)
        assert s["collision_groups"] == 2
        ok += 1

        # 11. chunks_in_collisions = 4 (c1,c2,c3,c4)
        assert s["chunks_in_collisions"] == 4
        ok += 1

        # 12. mixed_status_groups = 1 (1000)
        assert s["mixed_status_groups"] == 1
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["mixed_status_rate"] == s["mixed_status_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = simhash_status_summary(conn)
        assert s["total_simhashes"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Simhash status profile analysis")
    ap.add_argument("command", choices=["by-simhash", "by-status", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS simhash_status_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-simhash":
        rows = statuses_by_simhash(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<16} {'statuses':<10} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_statuses']:<10} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "by-status":
        rows = simhash_groups_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status simhash data found.")
            else:
                print(f"{'status':<14} {'simhashes':<12} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['distinct_simhashes']:<12} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "concentration":
        rows = simhash_status_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<16} {'statuses':<10} {'chunks':<8} {'accepted':<10} {'quarantined':<12} {'rejected':<10} {'rate'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_statuses']:<10} {r['total_chunks']:<8} {r['accepted']:<10} {r['quarantined']:<12} {r['rejected']:<10} {r['acceptance_rate']:.4f}")
    elif args.command == "summary":
        s = simhash_status_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
