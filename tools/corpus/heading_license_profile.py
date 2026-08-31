#!/usr/bin/env python3
"""Heading license profile: how heading paths distribute across license types.

heading_publisher_profile.py cross-tabulates headings with publishers.
heading_kind_profile.py cross-tabulates headings with source kind.
No tool cross-tabulates chunks.heading_path with sources.license_spdx to
measure whether certain document sections appear more under specific
licenses, or how section structure distributes across licensing terms.

Usage:
    python tools/corpus/heading_license_profile.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_license_profile.py by-license [--db PATH] [--json]
    python tools/corpus/heading_license_profile.py concentration [--db PATH] [--json]
    python tools/corpus/heading_license_profile.py summary [--db PATH] [--json]
    python tools/corpus/heading_license_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def licenses_by_heading(conn) -> list[dict]:
    """License distribution per heading path."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT s.license_spdx) AS distinct_licenses,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        GROUP BY c.heading_path
        ORDER BY total_chunks DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_licenses": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def headings_by_license(conn) -> list[dict]:
    """Heading distribution per license type."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT c.heading_path) AS distinct_headings,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        GROUP BY s.license_spdx
        ORDER BY total_chunks DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license": r[0],
            "distinct_headings": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def heading_license_concentration(conn) -> list[dict]:
    """Per-heading license concentration, filtered to headings with at least 2 chunks."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT s.license_spdx) AS distinct_licenses,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        GROUP BY c.heading_path
        HAVING COUNT(c.chunk_id) >= 2
        ORDER BY distinct_licenses DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_licenses": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
            "license_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def heading_license_summary(conn) -> dict:
    """Aggregate heading-license statistics."""
    total_headings = conn.execute(
        """
        SELECT COUNT(DISTINCT c.heading_path)
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        """
    ).fetchone()[0]

    total_chunks = conn.execute(
        """
        SELECT COUNT(*)
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        """
    ).fetchone()[0]

    total_licenses = conn.execute(
        """
        SELECT COUNT(DISTINCT s.license_spdx)
        FROM chunks c
        JOIN sources s ON c.source_id = s.source_id
        """
    ).fetchone()[0]

    headings_multi_license = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.heading_path
            FROM chunks c
            JOIN sources s ON c.source_id = s.source_id
            GROUP BY c.heading_path
            HAVING COUNT(DISTINCT s.license_spdx) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.heading_path, s.license_spdx
            FROM chunks c
            JOIN sources s ON c.source_id = s.source_id
            GROUP BY c.heading_path, s.license_spdx
        )
        """
    ).fetchone()[0]

    return {
        "total_headings": total_headings,
        "total_chunks": total_chunks,
        "total_licenses": total_licenses,
        "headings_multi_license": headings_multi_license,
        "multi_license_rate": round(headings_multi_license / max(total_headings, 1), 4),
        "distinct_heading_license_pairs": distinct_pairs,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # s1: MIT, s2: Apache-2.0, s3: MIT
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "Apache-2.0", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "repo", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None))

        # intro: c1 in s1(MIT), c2 in s2(Apache-2.0); methods: c3 in s1(MIT), c4 in s3(MIT); results: c5 in s2(Apache-2.0)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s2", 1, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 2, "methods", "claim", None, "t", "t", 25, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "methods", "claim", None, "t", "t", 35, "jkl", 4000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s2", 2, "results", "claim", None, "t", "t", 40, "mno", 5000, 0, "accepted", None, t1))
        conn.commit()

        # 1. by-heading: intro has 2 distinct licenses (MIT, Apache-2.0)
        bh = licenses_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["distinct_licenses"] == 2
        ok += 1

        # 2. intro has 2 total chunks
        assert intro["total_chunks"] == 2
        ok += 1

        # 3. methods has 1 distinct license (MIT only, s1 and s3 both MIT)
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["distinct_licenses"] == 1
        ok += 1

        # 4. by-license: "MIT" has 2 headings (intro, methods)
        bl = headings_by_license(conn)
        mit = [r for r in bl if r["license"] == "MIT"][0]
        assert mit["distinct_headings"] == 2
        ok += 1

        # 5. "Apache-2.0" has 2 headings (intro, results)
        apache = [r for r in bl if r["license"] == "Apache-2.0"][0]
        assert apache["distinct_headings"] == 2
        ok += 1

        # 6. MIT has 3 chunks (c1, c3, c4)
        assert mit["total_chunks"] == 3
        ok += 1

        # 7. concentration: intro has 2 licenses, 2 chunks
        conc = heading_license_concentration(conn)
        intro_conc = [r for r in conc if r["heading_path"] == "intro"][0]
        assert intro_conc["distinct_licenses"] == 2
        ok += 1

        # 8. methods has 1 license, 2 chunks
        methods_conc = [r for r in conc if r["heading_path"] == "methods"][0]
        assert methods_conc["distinct_licenses"] == 1
        ok += 1

        # 9. results not in concentration (only 1 chunk, below threshold)
        results_conc = [r for r in conc if r["heading_path"] == "results"]
        assert len(results_conc) == 0
        ok += 1

        # 10. summary: total_headings = 3
        s = heading_license_summary(conn)
        assert s["total_headings"] == 3
        ok += 1

        # 11. total_licenses = 2 (MIT, Apache-2.0)
        assert s["total_licenses"] == 2
        ok += 1

        # 12. headings_multi_license = 1 (intro)
        assert s["headings_multi_license"] == 1
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_license_rate"] == s["multi_license_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = heading_license_summary(conn)
        assert s["total_headings"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading license profile analysis")
    ap.add_argument("command", choices=["by-heading", "by-license", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_license_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = licenses_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading license data found.")
            else:
                print(f"{'heading_path':<30} {'licenses':<10} {'chunks':<8} {'words'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['distinct_licenses']:<10} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "by-license":
        rows = headings_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license heading data found.")
            else:
                print(f"{'license':<20} {'headings':<10} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['license']:<20} {r['distinct_headings']:<10} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "concentration":
        rows = heading_license_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No headings with multiple chunks found.")
            else:
                print(f"{'heading_path':<30} {'licenses':<10} {'chunks':<8} {'words':<12} {'ratio'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['distinct_licenses']:<10} {r['total_chunks']:<8} {r['total_words']:<12} {r['license_ratio']:.4f}")
    elif args.command == "summary":
        s = heading_license_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
