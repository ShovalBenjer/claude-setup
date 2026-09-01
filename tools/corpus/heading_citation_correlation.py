#!/usr/bin/env python3
"""Heading citation correlation: how heading paths relate to citations.

heading_tag_correlation.py measures heading paths against chunk tags.
heading_edge_correlation.py measures heading paths against claim edges.
No tool measures which heading paths concentrate citations, whether
deeper headings produce more or fewer citations, or how verification
rates vary across heading structures.

Usage:
    python tools/corpus/heading_citation_correlation.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_citation_correlation.py by-depth [--db PATH] [--json]
    python tools/corpus/heading_citation_correlation.py verification [--db PATH] [--json]
    python tools/corpus/heading_citation_correlation.py summary [--db PATH] [--json]
    python tools/corpus/heading_citation_correlation.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def citations_by_heading(conn) -> list[dict]:
    """Citation distribution per heading path."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(ci.citation_id) AS total_citations,
               COUNT(DISTINCT c.chunk_id) AS citing_chunks,
               SUM(ci.verified) AS verified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY c.heading_path
        ORDER BY total_citations DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "total_citations": r[1],
            "citing_chunks": r[2],
            "verified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[3] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def citations_by_heading_depth(conn) -> list[dict]:
    """Citation statistics grouped by heading depth (separator count + 1)."""
    rows = conn.execute(
        """
        SELECT depth,
               COUNT(*) AS total_citations,
               COUNT(DISTINCT chunk_id) AS citing_chunks,
               SUM(verified) AS verified,
               COUNT(DISTINCT target_uri) AS distinct_targets
        FROM (
            SELECT ci.citation_id, ci.verified, ci.target_uri, ci.chunk_id,
                   LENGTH(c.heading_path) - LENGTH(REPLACE(c.heading_path, '/', '')) + 1 AS depth
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            WHERE c.heading_path IS NOT NULL
        )
        GROUP BY depth
        ORDER BY depth
        """
    ).fetchall()
    return [
        {
            "depth": r[0],
            "total_citations": r[1],
            "citing_chunks": r[2],
            "verified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[3] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def heading_verification_profile(conn) -> list[dict]:
    """Verification rate per heading, filtered to headings with at least 2 citations."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified,
               SUM(CASE WHEN ci.verified = 0 THEN 1 ELSE 0 END) AS unverified
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY c.heading_path
        HAVING COUNT(ci.citation_id) >= 2
        ORDER BY CAST(SUM(ci.verified) AS REAL) / COUNT(ci.citation_id) DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "total": r[1],
            "verified": r[2],
            "unverified": r[3],
            "verification_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def heading_citation_summary(conn) -> dict:
    """Aggregate heading-citation correlation statistics."""
    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]

    total_verified = conn.execute(
        "SELECT SUM(verified) FROM citations"
    ).fetchone()[0] or 0

    headings_with_citations = conn.execute(
        """
        SELECT COUNT(DISTINCT c.heading_path)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        """
    ).fetchone()[0]

    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks WHERE heading_path IS NOT NULL"
    ).fetchone()[0]

    max_depth_row = conn.execute(
        """
        SELECT MAX(LENGTH(c.heading_path) - LENGTH(REPLACE(c.heading_path, '/', '')) + 1)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        WHERE c.heading_path IS NOT NULL
        """
    ).fetchone()
    max_cited_depth = max_depth_row[0] if max_depth_row[0] is not None else 0

    avg_citations_per_heading = conn.execute(
        """
        SELECT ROUND(AVG(cite_count), 4)
        FROM (
            SELECT c.heading_path, COUNT(ci.citation_id) AS cite_count
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            GROUP BY c.heading_path
        )
        """
    ).fetchone()[0]

    return {
        "total_citations": total_citations,
        "total_verified": total_verified,
        "overall_verification_rate": round(total_verified / max(total_citations, 1), 4),
        "headings_with_citations": headings_with_citations,
        "total_headings": total_headings,
        "heading_citation_coverage": round(headings_with_citations / max(total_headings, 1), 4),
        "max_cited_depth": max_cited_depth,
        "avg_citations_per_heading": avg_citations_per_heading or 0.0,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1: "intro", c2: "intro/details", c3: "methods", c4: "methods" (no citations)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro/details", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 15, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 25, "jkl", 4000, 0, "accepted", None, t1))

        # Citations: intro has 3 (2 verified), intro/details has 1 (0 verified), methods has 2 (1 verified)
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci1", "c1", "http://example.com/a", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci2", "c1", "http://example.com/b", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci3", "c1", "http://example.com/c", None, "note", None, 0, None))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci4", "c2", "http://example.com/d", None, "ref", None, 0, None))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci5", "c3", "http://example.com/a", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci6", "c3", "http://example.com/e", None, None, None, 0, None))
        conn.commit()

        # 1. by-heading: "intro" has 3 citations
        bh = citations_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["total_citations"] == 3
        ok += 1

        # 2. "intro" has 2 verified
        assert intro["verified"] == 2
        ok += 1

        # 3. "intro/details" has 1 citation
        details = [r for r in bh if r["heading_path"] == "intro/details"][0]
        assert details["total_citations"] == 1
        ok += 1

        # 4. "methods" has 2 citations
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["total_citations"] == 2
        ok += 1

        # 5. by-depth: depth 1 has 5 citations (intro=3, methods=2)
        bd = citations_by_heading_depth(conn)
        d1 = [r for r in bd if r["depth"] == 1][0]
        assert d1["total_citations"] == 5
        ok += 1

        # 6. depth 2 has 1 citation (intro/details=1)
        d2 = [r for r in bd if r["depth"] == 2][0]
        assert d2["total_citations"] == 1
        ok += 1

        # 7. verification profile: "intro" has rate 2/3
        vp = heading_verification_profile(conn)
        intro_vp = [r for r in vp if r["heading_path"] == "intro"][0]
        assert intro_vp["verification_rate"] == round(2 / 3, 4)
        ok += 1

        # 8. "methods" has rate 1/2 = 0.5
        methods_vp = [r for r in vp if r["heading_path"] == "methods"][0]
        assert methods_vp["verification_rate"] == 0.5
        ok += 1

        # 9. "intro/details" not in verification (only 1 citation, below threshold)
        details_vp = [r for r in vp if r["heading_path"] == "intro/details"]
        assert len(details_vp) == 0
        ok += 1

        # 10. summary: total_citations = 6
        s = heading_citation_summary(conn)
        assert s["total_citations"] == 6
        ok += 1

        # 11. headings_with_citations = 3 (intro, intro/details, methods)
        assert s["headings_with_citations"] == 3
        ok += 1

        # 12. max_cited_depth = 2 (intro/details)
        assert s["max_cited_depth"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["heading_citation_coverage"] == s["heading_citation_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = heading_citation_summary(conn)
        assert s["total_citations"] == 0
        assert s["headings_with_citations"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading citation correlation analysis")
    ap.add_argument("command", choices=["by-heading", "by-depth", "verification", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_citation_correlation selftest ({ok} checks)")
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
                print(f"{'heading_path':<30} {'citations':<10} {'chunks':<8} {'verified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['total_citations']:<10} {r['citing_chunks']:<8} {r['verified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "by-depth":
        rows = citations_by_heading_depth(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading citation data found.")
            else:
                print(f"{'depth':<8} {'citations':<10} {'chunks':<8} {'verified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['depth']:<8} {r['total_citations']:<10} {r['citing_chunks']:<8} {r['verified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "verification":
        rows = heading_verification_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No headings with multiple citations found.")
            else:
                print(f"{'heading_path':<30} {'total':<8} {'verified':<10} {'unverified':<10} {'rate'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['total']:<8} {r['verified']:<10} {r['unverified']:<10} {r['verification_rate']:.4f}")
    elif args.command == "summary":
        s = heading_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
