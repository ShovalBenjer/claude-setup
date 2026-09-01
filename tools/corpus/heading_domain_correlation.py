#!/usr/bin/env python3
"""Heading domain correlation: how heading paths relate to semantic domains.

heading_tag_correlation.py measures heading paths against chunk tags.
heading_depth_analysis.py profiles heading path depths.
No tool measures which heading paths concentrate which domains,
whether deeper headings attract different domain profiles, or
how domain diversity varies across heading structures.

Usage:
    python tools/corpus/heading_domain_correlation.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_domain_correlation.py by-depth [--db PATH] [--json]
    python tools/corpus/heading_domain_correlation.py diversity [--db PATH] [--json]
    python tools/corpus/heading_domain_correlation.py summary [--db PATH] [--json]
    python tools/corpus/heading_domain_correlation.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def domains_by_heading(conn) -> list[dict]:
    """Domain distribution per heading path."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS domain_assignments,
               COUNT(DISTINCT c.chunk_id) AS chunks_at_heading,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        ORDER BY domain_assignments DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_domains": r[1],
            "domain_assignments": r[2],
            "chunks_at_heading": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def domains_by_heading_depth(conn) -> list[dict]:
    """Domain statistics grouped by heading depth (separator count + 1)."""
    rows = conn.execute(
        """
        SELECT depth, COUNT(DISTINCT domain) AS distinct_domains,
               COUNT(*) AS domain_assignments,
               COUNT(DISTINCT chunk_id) AS classified_chunks,
               ROUND(AVG(score), 4) AS avg_score
        FROM (
            SELECT cd.domain, cd.score, cd.chunk_id,
                   LENGTH(c.heading_path) - LENGTH(REPLACE(c.heading_path, '/', '')) + 1 AS depth
            FROM chunk_domains cd
            JOIN chunks c ON c.chunk_id = cd.chunk_id
            WHERE c.heading_path IS NOT NULL
        )
        GROUP BY depth
        ORDER BY depth
        """
    ).fetchall()
    return [
        {
            "depth": r[0],
            "distinct_domains": r[1],
            "domain_assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def heading_domain_diversity(conn) -> list[dict]:
    """Per-heading domain diversity: ratio of distinct domains to total assignments."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS chunk_count
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        HAVING COUNT(cd.domain) >= 2
        ORDER BY CAST(COUNT(DISTINCT cd.domain) AS REAL) / COUNT(cd.domain), c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_domains": r[1],
            "total_assignments": r[2],
            "chunk_count": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def heading_domain_summary(conn) -> dict:
    """Aggregate heading-domain correlation statistics."""
    total_classified = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_domains"
    ).fetchone()[0]

    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]

    headings_with_domains = conn.execute(
        """
        SELECT COUNT(DISTINCT c.heading_path)
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks WHERE heading_path IS NOT NULL"
    ).fetchone()[0]

    max_depth_row = conn.execute(
        """
        SELECT MAX(LENGTH(c.heading_path) - LENGTH(REPLACE(c.heading_path, '/', '')) + 1)
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        """
    ).fetchone()
    max_classified_depth = max_depth_row[0] if max_depth_row[0] is not None else 0

    avg_domains_per_heading = conn.execute(
        """
        SELECT ROUND(AVG(dom_count), 4)
        FROM (
            SELECT c.heading_path, COUNT(cd.domain) AS dom_count
            FROM chunks c
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY c.heading_path
        )
        """
    ).fetchone()[0]

    return {
        "total_classified_chunks": total_classified,
        "total_distinct_domains": total_domains,
        "headings_with_domains": headings_with_domains,
        "total_headings": total_headings,
        "heading_domain_coverage": round(headings_with_domains / max(total_headings, 1), 4),
        "max_classified_depth": max_classified_depth,
        "avg_domains_per_heading": avg_domains_per_heading or 0.0,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1: heading "intro", c2: heading "intro/details", c3: heading "methods", c4: heading "methods" (no domains)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro/details", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 15, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 25, "jkl", 4000, 0, "accepted", None, t1))

        # Domains: c1 has ML+NLP, c2 has ML, c3 has NLP+bio
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ML", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "NLP", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "ML", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "NLP", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "bio", 0.6, t1))
        conn.commit()

        # 1. by-heading: "intro" has 2 distinct domains (ML, NLP)
        bh = domains_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["distinct_domains"] == 2
        ok += 1

        # 2. "intro" has 2 domain assignments
        assert intro["domain_assignments"] == 2
        ok += 1

        # 3. "intro/details" has 1 domain (ML)
        details = [r for r in bh if r["heading_path"] == "intro/details"][0]
        assert details["distinct_domains"] == 1
        ok += 1

        # 4. by-depth: depth 1 has 4 domain assignments (intro=2, methods=2)
        bd = domains_by_heading_depth(conn)
        d1 = [r for r in bd if r["depth"] == 1][0]
        assert d1["domain_assignments"] == 4
        ok += 1

        # 5. depth 2 has 1 domain assignment (intro/details -> ML)
        d2 = [r for r in bd if r["depth"] == 2][0]
        assert d2["domain_assignments"] == 1
        ok += 1

        # 6. diversity: "intro" has ratio 2/2 = 1.0
        div = heading_domain_diversity(conn)
        intro_div = [r for r in div if r["heading_path"] == "intro"][0]
        assert intro_div["diversity_ratio"] == 1.0
        ok += 1

        # 7. "methods" has 2 distinct domains, 2 assignments, ratio 1.0
        meth_div = [r for r in div if r["heading_path"] == "methods"][0]
        assert meth_div["diversity_ratio"] == 1.0
        ok += 1

        # 8. "intro/details" not in diversity (only 1 assignment, below threshold)
        details_div = [r for r in div if r["heading_path"] == "intro/details"]
        assert len(details_div) == 0
        ok += 1

        # 9. summary: total_classified_chunks = 3 (c1, c2, c3)
        s = heading_domain_summary(conn)
        assert s["total_classified_chunks"] == 3
        ok += 1

        # 10. headings_with_domains = 3 (intro, intro/details, methods)
        assert s["headings_with_domains"] == 3
        ok += 1

        # 11. total_headings = 3 (intro, intro/details, methods -- c3 and c4 share "methods")
        assert s["total_headings"] == 3
        ok += 1

        # 12. max_classified_depth = 2 (intro/details)
        assert s["max_classified_depth"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["heading_domain_coverage"] == s["heading_domain_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = heading_domain_summary(conn)
        assert s["total_classified_chunks"] == 0
        assert s["headings_with_domains"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading domain correlation analysis")
    ap.add_argument("command", choices=["by-heading", "by-depth", "diversity", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_domain_correlation selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = domains_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No classified headings found.")
            else:
                print(f"{'heading_path':<30} {'domains':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['distinct_domains']:<8} {r['domain_assignments']:<12} {r['chunks_at_heading']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-depth":
        rows = domains_by_heading_depth(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No classified headings found.")
            else:
                print(f"{'depth':<8} {'domains':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['depth']:<8} {r['distinct_domains']:<8} {r['domain_assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "diversity":
        rows = heading_domain_diversity(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No headings with multiple domains found.")
            else:
                print(f"{'heading_path':<30} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['distinct_domains']:<10} {r['total_assignments']:<8} {r['chunk_count']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = heading_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
