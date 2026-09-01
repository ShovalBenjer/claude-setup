#!/usr/bin/env python3
"""Heading citation profile: how heading paths distribute across citation counts.

heading_domain_profile.py profiles headings by semantic domains.
heading_tag_profile.py profiles headings by chunk tags.
No tool cross-tabulates chunks.heading_path with chunks.citation_count to
measure which document sections carry the most citations, or how citation
density distributes across heading paths.

Usage:
    python tools/corpus/heading_citation_profile.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_citation_profile.py by-bucket [--db PATH] [--json]
    python tools/corpus/heading_citation_profile.py concentration [--db PATH] [--json]
    python tools/corpus/heading_citation_profile.py summary [--db PATH] [--json]
    python tools/corpus/heading_citation_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _cite_bucket(n: int) -> str:
    if n == 0:
        return "0"
    if n <= 5:
        return "1-5"
    if n <= 20:
        return "6-20"
    return "21+"


def citations_by_heading(conn) -> list[dict]:
    """Citation statistics per heading path."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.citation_count) AS total_citations,
               ROUND(AVG(c.citation_count), 4) AS avg_citations,
               MIN(c.citation_count) AS min_citations,
               MAX(c.citation_count) AS max_citations
        FROM chunks c
        GROUP BY c.heading_path
        ORDER BY total_citations DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "total_chunks": r[1],
            "total_citations": r[2],
            "avg_citations": r[3],
            "min_citations": r[4],
            "max_citations": r[5],
            "citation_spread": r[5] - r[4],
        }
        for r in rows
    ]


def headings_by_bucket(conn) -> list[dict]:
    """Heading distribution per citation bucket."""
    rows = conn.execute(
        "SELECT c.heading_path, c.citation_count FROM chunks c"
    ).fetchall()
    buckets: dict[str, dict] = {}
    headings_per_bucket: dict[str, set] = {}
    for heading, cite_count in rows:
        b = _cite_bucket(cite_count)
        if b not in buckets:
            buckets[b] = {"total_chunks": 0, "total_citations": 0}
            headings_per_bucket[b] = set()
        buckets[b]["total_chunks"] += 1
        buckets[b]["total_citations"] += cite_count
        headings_per_bucket[b].add(heading)
    return sorted(
        [
            {
                "bucket": b,
                "distinct_headings": len(headings_per_bucket[b]),
                "total_chunks": buckets[b]["total_chunks"],
                "total_citations": buckets[b]["total_citations"],
            }
            for b in buckets
        ],
        key=lambda r: r["total_chunks"],
        reverse=True,
    )


def heading_citation_concentration(conn) -> list[dict]:
    """Per-heading citation concentration ordered by citation spread."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.citation_count) AS total_citations,
               ROUND(AVG(c.citation_count), 4) AS avg_citations,
               MIN(c.citation_count) AS min_citations,
               MAX(c.citation_count) AS max_citations
        FROM chunks c
        GROUP BY c.heading_path
        ORDER BY (MAX(c.citation_count) - MIN(c.citation_count)) DESC, total_citations DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "total_chunks": r[1],
            "total_citations": r[2],
            "avg_citations": r[3],
            "min_citations": r[4],
            "max_citations": r[5],
            "citation_spread": r[5] - r[4],
        }
        for r in rows
    ]


def heading_citation_summary(conn) -> dict:
    """Aggregate heading-citation statistics."""
    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks"
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    total_citations = conn.execute(
        "SELECT COALESCE(SUM(citation_count), 0) FROM chunks"
    ).fetchone()[0]

    avg_citations = conn.execute(
        "SELECT ROUND(COALESCE(AVG(citation_count), 0), 4) FROM chunks"
    ).fetchone()[0]

    cited_headings = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT heading_path
            FROM chunks
            GROUP BY heading_path
            HAVING SUM(citation_count) > 0
        )
        """
    ).fetchone()[0]

    uneven_headings = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT heading_path
            FROM chunks
            GROUP BY heading_path
            HAVING COUNT(chunk_id) >= 2
               AND MAX(citation_count) > MIN(citation_count)
        )
        """
    ).fetchone()[0]

    return {
        "total_headings": total_headings,
        "total_chunks": total_chunks,
        "total_citations": total_citations,
        "avg_citations": avg_citations,
        "cited_headings": cited_headings,
        "cited_heading_rate": round(cited_headings / max(total_headings, 1), 4),
        "uneven_citation_headings": uneven_headings,
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

        # intro: c1 (cite=0), c2 (cite=10) -- uneven; methods: c3 (cite=5), c4 (cite=5) -- even; results: c5 (cite=25)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1001, 10, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 5, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 35, "jkl", 2001, 5, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3000, 25, "accepted", None, t1))
        conn.commit()

        # 1. by-heading: intro citation_spread = 10
        bh = citations_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["citation_spread"] == 10
        ok += 1

        # 2. methods citation_spread = 0
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["citation_spread"] == 0
        ok += 1

        # 3. results total_citations = 25
        results = [r for r in bh if r["heading_path"] == "results"][0]
        assert results["total_citations"] == 25
        ok += 1

        # 4. by-bucket: bucket "0" has 1 chunk (c1)
        bb = headings_by_bucket(conn)
        b0 = [r for r in bb if r["bucket"] == "0"][0]
        assert b0["total_chunks"] == 1
        ok += 1

        # 5. bucket "1-5" has 2 chunks (c3, c4)
        b15 = [r for r in bb if r["bucket"] == "1-5"][0]
        assert b15["total_chunks"] == 2
        ok += 1

        # 6. bucket "21+" has 1 chunk (c5)
        b21 = [r for r in bb if r["bucket"] == "21+"][0]
        assert b21["total_chunks"] == 1
        ok += 1

        # 7. concentration: intro ordered first (spread=10)
        conc = heading_citation_concentration(conn)
        assert conc[0]["heading_path"] == "intro"
        ok += 1

        # 8. methods has spread=0
        c_methods = [r for r in conc if r["heading_path"] == "methods"][0]
        assert c_methods["citation_spread"] == 0
        ok += 1

        # 9. results has spread=0 (single chunk)
        c_results = [r for r in conc if r["heading_path"] == "results"][0]
        assert c_results["citation_spread"] == 0
        ok += 1

        # 10. summary: total_headings = 3
        s = heading_citation_summary(conn)
        assert s["total_headings"] == 3
        ok += 1

        # 11. cited_headings = 3 (all have at least one cited chunk, intro has c2=10, methods has c3=5+c4=5, results has c5=25)
        assert s["cited_headings"] == 3
        ok += 1

        # 12. total_citations = 0+10+5+5+25 = 45
        assert s["total_citations"] == 45
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cited_heading_rate"] == s["cited_heading_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = heading_citation_summary(conn)
        assert s["total_headings"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading citation profile analysis")
    ap.add_argument("command", choices=["by-heading", "by-bucket", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_citation_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = citations_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading citation data found.")
            else:
                print(f"{'heading':<20} {'chunks':<8} {'total':<8} {'avg':<10} {'min':<6} {'max':<6} {'spread'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['total_chunks']:<8} {r['total_citations']:<8} {r['avg_citations']:<10.4f} {r['min_citations']:<6} {r['max_citations']:<6} {r['citation_spread']}")
    elif args.command == "by-bucket":
        rows = headings_by_bucket(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No citation data found.")
            else:
                print(f"{'bucket':<10} {'headings':<10} {'chunks':<8} {'citations'}")
                for r in rows:
                    print(f"{r['bucket']:<10} {r['distinct_headings']:<10} {r['total_chunks']:<8} {r['total_citations']}")
    elif args.command == "concentration":
        rows = heading_citation_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading citation data found.")
            else:
                print(f"{'heading':<20} {'chunks':<8} {'total':<8} {'avg':<10} {'min':<6} {'max':<6} {'spread'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['total_chunks']:<8} {r['total_citations']:<8} {r['avg_citations']:<10.4f} {r['min_citations']:<6} {r['max_citations']:<6} {r['citation_spread']}")
    elif args.command == "summary":
        s = heading_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
