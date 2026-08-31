#!/usr/bin/env python3
"""Heading status profile: how chunk statuses distribute across heading paths.

heading_citation_correlation.py correlates headings with citations.
heading_tag_correlation.py correlates headings with tags.
No tool cross-tabulates chunks.heading_path with chunks.status to
measure whether certain document sections produce more accepted versus
quarantined or rejected chunks, or how quality distributes across
document structure.

Usage:
    python tools/corpus/heading_status_profile.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_status_profile.py by-status [--db PATH] [--json]
    python tools/corpus/heading_status_profile.py acceptance [--db PATH] [--json]
    python tools/corpus/heading_status_profile.py summary [--db PATH] [--json]
    python tools/corpus/heading_status_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def statuses_by_heading(conn) -> list[dict]:
    """Chunk status distribution per heading path."""
    rows = conn.execute(
        """
        SELECT heading_path,
               COUNT(DISTINCT status) AS distinct_statuses,
               COUNT(chunk_id) AS total_chunks,
               SUM(word_count) AS total_words
        FROM chunks
        GROUP BY heading_path
        ORDER BY total_chunks DESC, heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_statuses": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def headings_by_status(conn) -> list[dict]:
    """Heading distribution per chunk status."""
    rows = conn.execute(
        """
        SELECT status,
               COUNT(DISTINCT heading_path) AS distinct_headings,
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
            "distinct_headings": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def heading_acceptance_rate(conn) -> list[dict]:
    """Per-heading acceptance rate, filtered to headings with at least 2 chunks."""
    rows = conn.execute(
        """
        SELECT heading_path,
               COUNT(chunk_id) AS total_chunks,
               SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS accepted,
               SUM(CASE WHEN status = 'quarantined' THEN 1 ELSE 0 END) AS quarantined,
               SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected
        FROM chunks
        GROUP BY heading_path
        HAVING COUNT(chunk_id) >= 2
        ORDER BY CAST(SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS REAL)
                 / COUNT(chunk_id) DESC, heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "total_chunks": r[1],
            "accepted": r[2],
            "quarantined": r[3],
            "rejected": r[4],
            "acceptance_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def heading_status_summary(conn) -> dict:
    """Aggregate heading-status statistics."""
    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks"
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    total_accepted = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'accepted'"
    ).fetchone()[0]

    overall_acceptance_rate = round(total_accepted / max(total_chunks, 1), 4)

    headings_multi_status = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT heading_path
            FROM chunks
            GROUP BY heading_path
            HAVING COUNT(DISTINCT status) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT heading_path, status
            FROM chunks
            GROUP BY heading_path, status
        )
        """
    ).fetchone()[0]

    return {
        "total_headings": total_headings,
        "total_chunks": total_chunks,
        "total_accepted": total_accepted,
        "overall_acceptance_rate": overall_acceptance_rate,
        "headings_multi_status": headings_multi_status,
        "multi_status_rate": round(headings_multi_status / max(total_headings, 1), 4),
        "distinct_heading_status_pairs": distinct_pairs,
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

        # intro: 2 accepted, 1 quarantined; methods: 1 accepted, 1 rejected; results: 1 accepted
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "intro", "claim", None, "t", "t", 25, "ghi", 3000, 0, "quarantined", "low quality", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 35, "jkl", 4000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "methods", "claim", None, "t", "t", 15, "mno", 5000, 0, "rejected", "duplicate", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "s1", 6, "results", "claim", None, "t", "t", 40, "pqr", 6000, 0, "accepted", None, t1))
        conn.commit()

        # 1. by-heading: intro has 2 distinct statuses (accepted, quarantined)
        bh = statuses_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["distinct_statuses"] == 2
        ok += 1

        # 2. intro has 3 total chunks
        assert intro["total_chunks"] == 3
        ok += 1

        # 3. methods has 2 distinct statuses (accepted, rejected)
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["distinct_statuses"] == 2
        ok += 1

        # 4. by-status: "accepted" has 3 headings
        bs = headings_by_status(conn)
        accepted = [r for r in bs if r["status"] == "accepted"][0]
        assert accepted["distinct_headings"] == 3
        ok += 1

        # 5. "quarantined" has 1 heading (intro)
        quarantined = [r for r in bs if r["status"] == "quarantined"][0]
        assert quarantined["distinct_headings"] == 1
        ok += 1

        # 6. "rejected" has 1 heading (methods)
        rejected = [r for r in bs if r["status"] == "rejected"][0]
        assert rejected["distinct_headings"] == 1
        ok += 1

        # 7. acceptance: intro rate = 2/3
        ar = heading_acceptance_rate(conn)
        intro_ar = [r for r in ar if r["heading_path"] == "intro"][0]
        assert intro_ar["acceptance_rate"] == round(2 / 3, 4)
        ok += 1

        # 8. methods rate = 1/2 = 0.5
        methods_ar = [r for r in ar if r["heading_path"] == "methods"][0]
        assert methods_ar["acceptance_rate"] == 0.5
        ok += 1

        # 9. results not in acceptance (only 1 chunk, below threshold)
        results_ar = [r for r in ar if r["heading_path"] == "results"]
        assert len(results_ar) == 0
        ok += 1

        # 10. summary: total_headings = 3
        s = heading_status_summary(conn)
        assert s["total_headings"] == 3
        ok += 1

        # 11. total_accepted = 4 (c1, c2, c4, c6)
        assert s["total_accepted"] == 4
        ok += 1

        # 12. headings_multi_status = 2 (intro, methods)
        assert s["headings_multi_status"] == 2
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
        s = heading_status_summary(conn)
        assert s["total_headings"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading status profile analysis")
    ap.add_argument("command", choices=["by-heading", "by-status", "acceptance", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_status_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = statuses_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading status data found.")
            else:
                print(f"{'heading_path':<30} {'statuses':<10} {'chunks':<8} {'words'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['distinct_statuses']:<10} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "by-status":
        rows = headings_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status heading data found.")
            else:
                print(f"{'status':<14} {'headings':<10} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['distinct_headings']:<10} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "acceptance":
        rows = heading_acceptance_rate(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No headings with multiple chunks found.")
            else:
                print(f"{'heading_path':<30} {'chunks':<8} {'accepted':<10} {'quarantined':<12} {'rejected':<10} {'rate'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['total_chunks']:<8} {r['accepted']:<10} {r['quarantined']:<12} {r['rejected']:<10} {r['acceptance_rate']:.4f}")
    elif args.command == "summary":
        s = heading_status_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
