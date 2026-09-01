#!/usr/bin/env python3
"""Publisher status profile: how publishers distribute across chunk statuses.

publisher_liveness_profile.py profiles publishers by source liveness.
publisher_tag_profile.py profiles publishers by tag vocabulary.
No tool joins sources.publisher with chunks.status to measure which
publishers produce accepted versus quarantined or rejected chunks,
or how chunk quality distributes across publishers.

Usage:
    python tools/corpus/publisher_status_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/publisher_status_profile.py by-status [--db PATH] [--json]
    python tools/corpus/publisher_status_profile.py acceptance [--db PATH] [--json]
    python tools/corpus/publisher_status_profile.py summary [--db PATH] [--json]
    python tools/corpus/publisher_status_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def statuses_by_publisher(conn) -> list[dict]:
    """Chunk status distribution per publisher."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT c.status) AS distinct_statuses,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        GROUP BY s.publisher
        ORDER BY total_chunks DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_statuses": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def publishers_by_status(conn) -> list[dict]:
    """Publisher distribution per chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(DISTINCT s.publisher) AS distinct_publishers,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY c.status
        ORDER BY total_chunks DESC, c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "distinct_publishers": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def publisher_acceptance_rate(conn) -> list[dict]:
    """Per-publisher acceptance rate, filtered to publishers with at least 2 chunks."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(CASE WHEN c.status = 'accepted' THEN 1 ELSE 0 END) AS accepted,
               SUM(CASE WHEN c.status = 'quarantined' THEN 1 ELSE 0 END) AS quarantined,
               SUM(CASE WHEN c.status = 'rejected' THEN 1 ELSE 0 END) AS rejected
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        GROUP BY s.publisher
        HAVING COUNT(c.chunk_id) >= 2
        ORDER BY CAST(SUM(CASE WHEN c.status = 'accepted' THEN 1 ELSE 0 END) AS REAL)
                 / COUNT(c.chunk_id) DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "total_chunks": r[1],
            "accepted": r[2],
            "quarantined": r[3],
            "rejected": r[4],
            "acceptance_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def publisher_status_summary(conn) -> dict:
    """Aggregate publisher-status statistics."""
    total_publishers = conn.execute(
        "SELECT COUNT(DISTINCT publisher) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    publishers_with_chunks = conn.execute(
        """
        SELECT COUNT(DISTINCT s.publisher)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        WHERE s.publisher IS NOT NULL
        """
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    total_accepted = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'accepted'"
    ).fetchone()[0]

    overall_acceptance_rate = round(total_accepted / max(total_chunks, 1), 4)

    publishers_multi_status = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT s.publisher
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            WHERE s.publisher IS NOT NULL
            GROUP BY s.publisher
            HAVING COUNT(DISTINCT c.status) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT s.publisher, c.status
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            GROUP BY s.publisher, c.status
        )
        """
    ).fetchone()[0]

    return {
        "total_publishers": total_publishers,
        "publishers_with_chunks": publishers_with_chunks,
        "total_chunks": total_chunks,
        "total_accepted": total_accepted,
        "overall_acceptance_rate": overall_acceptance_rate,
        "publishers_multi_status": publishers_multi_status,
        "multi_status_rate": round(publishers_multi_status / max(publishers_with_chunks, 1), 4),
        "distinct_publisher_status_pairs": distinct_pairs,
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
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None))

        # acme: 2 accepted, 1 quarantined; globex: 1 accepted, 1 rejected; null pub: 1 accepted
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "results", "claim", None, "t", "t", 25, "ghi", 3000, 0, "quarantined", "low quality", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s2", 1, "intro", "claim", None, "t", "t", 35, "jkl", 4000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s2", 2, "methods", "claim", None, "t", "t", 15, "mno", 5000, 0, "rejected", "duplicate", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "s3", 1, "intro", "claim", None, "t", "t", 40, "pqr", 6000, 0, "accepted", None, t1))
        conn.commit()

        # 1. by-publisher: acme has 2 distinct statuses (accepted, quarantined)
        bp = statuses_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["distinct_statuses"] == 2
        ok += 1

        # 2. acme has 3 total chunks
        assert acme["total_chunks"] == 3
        ok += 1

        # 3. globex has 2 distinct statuses (accepted, rejected)
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["distinct_statuses"] == 2
        ok += 1

        # 4. by-status: "accepted" has 2 named publishers (acme, globex)
        bs = publishers_by_status(conn)
        accepted = [r for r in bs if r["status"] == "accepted"][0]
        assert accepted["distinct_publishers"] == 2
        ok += 1

        # 5. "quarantined" has 1 named publisher (acme)
        quarantined = [r for r in bs if r["status"] == "quarantined"][0]
        assert quarantined["distinct_publishers"] == 1
        ok += 1

        # 6. "rejected" has 1 named publisher (globex)
        rejected = [r for r in bs if r["status"] == "rejected"][0]
        assert rejected["distinct_publishers"] == 1
        ok += 1

        # 7. acceptance: acme rate = 2/3
        ar = publisher_acceptance_rate(conn)
        acme_ar = [r for r in ar if r["publisher"] == "acme"][0]
        assert acme_ar["acceptance_rate"] == round(2 / 3, 4)
        ok += 1

        # 8. globex rate = 1/2 = 0.5
        globex_ar = [r for r in ar if r["publisher"] == "globex"][0]
        assert globex_ar["acceptance_rate"] == 0.5
        ok += 1

        # 9. null publisher not in acceptance (only 1 chunk, below threshold)
        null_ar = [r for r in ar if r["publisher"] is None]
        assert len(null_ar) == 0
        ok += 1

        # 10. summary: total_publishers = 2 (acme, globex)
        s = publisher_status_summary(conn)
        assert s["total_publishers"] == 2
        ok += 1

        # 11. total_accepted = 4 (c1, c2, c4, c6)
        assert s["total_accepted"] == 4
        ok += 1

        # 12. publishers_multi_status = 2 (acme, globex both have >1 status)
        assert s["publishers_multi_status"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["overall_acceptance_rate"] == s["overall_acceptance_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = publisher_status_summary(conn)
        assert s["total_publishers"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Publisher status profile analysis")
    ap.add_argument("command", choices=["by-publisher", "by-status", "acceptance", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS publisher_status_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-publisher":
        rows = statuses_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher status data found.")
            else:
                print(f"{'publisher':<20} {'statuses':<10} {'chunks':<8} {'words'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['distinct_statuses']:<10} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "by-status":
        rows = publishers_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status publisher data found.")
            else:
                print(f"{'status':<14} {'publishers':<12} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['distinct_publishers']:<12} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "acceptance":
        rows = publisher_acceptance_rate(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publishers with multiple chunks found.")
            else:
                print(f"{'publisher':<20} {'chunks':<8} {'accepted':<10} {'quarantined':<12} {'rejected':<10} {'rate'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['total_chunks']:<8} {r['accepted']:<10} {r['quarantined']:<12} {r['rejected']:<10} {r['acceptance_rate']:.4f}")
    elif args.command == "summary":
        s = publisher_status_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
