#!/usr/bin/env python3
"""Heading domain profile: how heading paths distribute across semantic domains.

heading_tag_profile.py profiles headings by chunk tags.
heading_license_profile.py profiles headings by source license.
No tool cross-tabulates chunks.heading_path with chunk_domains.domain to
measure which semantic domains appear under which document sections, or how
domain classifications distribute across heading paths.

Usage:
    python tools/corpus/heading_domain_profile.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_domain_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/heading_domain_profile.py concentration [--db PATH] [--json]
    python tools/corpus/heading_domain_profile.py summary [--db PATH] [--json]
    python tools/corpus/heading_domain_profile.py selftest
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
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               COUNT(cd.domain) AS domain_assignments,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        ORDER BY classified_chunks DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_domains": r[1],
            "classified_chunks": r[2],
            "domain_assignments": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def headings_by_domain(conn) -> list[dict]:
    """Heading distribution per semantic domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT c.heading_path) AS distinct_headings,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               COUNT(cd.domain) AS domain_assignments,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY cd.domain
        ORDER BY classified_chunks DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_headings": r[1],
            "classified_chunks": r[2],
            "domain_assignments": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def heading_domain_concentration(conn) -> list[dict]:
    """Per-heading domain concentration ordered by domain diversity."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               COUNT(cd.domain) AS domain_assignments,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        ORDER BY distinct_domains DESC, classified_chunks DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_domains": r[1],
            "classified_chunks": r[2],
            "domain_assignments": r[3],
            "avg_score": r[4],
            "domain_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def heading_domain_summary(conn) -> dict:
    """Aggregate heading-domain statistics."""
    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT c.heading_path) FROM chunks c JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id"
    ).fetchone()[0]

    total_classified_chunks = conn.execute(
        "SELECT COUNT(DISTINCT c.chunk_id) FROM chunks c JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id"
    ).fetchone()[0]

    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT cd.domain) FROM chunk_domains cd"
    ).fetchone()[0]

    multi_domain_headings = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.heading_path
            FROM chunks c
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY c.heading_path
            HAVING COUNT(DISTINCT cd.domain) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.heading_path, cd.domain
            FROM chunks c
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY c.heading_path, cd.domain
        )
        """
    ).fetchone()[0]

    return {
        "total_headings": total_headings,
        "total_classified_chunks": total_classified_chunks,
        "total_domains": total_domains,
        "multi_domain_headings": multi_domain_headings,
        "multi_domain_rate": round(multi_domain_headings / max(total_headings, 1), 4),
        "distinct_heading_domain_pairs": distinct_pairs,
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
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        # intro: c1 (nlp, ml), c2 (nlp); methods: c3 (ml); results: c4 (web); c5 unclassified
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "results", "claim", None, "t", "t", 35, "jkl", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3001, 0, "accepted", None, t1))

        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "nlp", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "nlp", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "web", 0.5, t1))
        conn.commit()

        # 1. by-heading: intro has 2 distinct domains (nlp, ml)
        bh = domains_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["distinct_domains"] == 2
        ok += 1

        # 2. methods has 1 distinct domain (ml)
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["distinct_domains"] == 1
        ok += 1

        # 3. results has 1 distinct domain (web)
        results = [r for r in bh if r["heading_path"] == "results"][0]
        assert results["distinct_domains"] == 1
        ok += 1

        # 4. by-domain: "nlp" spans 1 heading (intro)
        bd = headings_by_domain(conn)
        nlp = [r for r in bd if r["domain"] == "nlp"][0]
        assert nlp["distinct_headings"] == 1
        ok += 1

        # 5. "ml" spans 2 headings (intro, methods)
        ml = [r for r in bd if r["domain"] == "ml"][0]
        assert ml["distinct_headings"] == 2
        ok += 1

        # 6. "nlp" has 2 classified chunks (c1, c2)
        assert nlp["classified_chunks"] == 2
        ok += 1

        # 7. concentration: intro domain_ratio = 2/2 = 1.0
        conc = heading_domain_concentration(conn)
        c_intro = [r for r in conc if r["heading_path"] == "intro"][0]
        assert c_intro["domain_ratio"] == 1.0
        ok += 1

        # 8. methods domain_ratio = 1/1 = 1.0
        c_methods = [r for r in conc if r["heading_path"] == "methods"][0]
        assert c_methods["domain_ratio"] == 1.0
        ok += 1

        # 9. results classified_chunks = 1
        c_results = [r for r in conc if r["heading_path"] == "results"][0]
        assert c_results["classified_chunks"] == 1
        ok += 1

        # 10. summary: total_headings = 3
        s = heading_domain_summary(conn)
        assert s["total_headings"] == 3
        ok += 1

        # 11. multi_domain_headings = 1 (intro has nlp + ml)
        assert s["multi_domain_headings"] == 1
        ok += 1

        # 12. total_domains = 3 (nlp, ml, web)
        assert s["total_domains"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_domain_rate"] == s["multi_domain_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = heading_domain_summary(conn)
        assert s["total_headings"] == 0
        assert s["total_classified_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading domain profile analysis")
    ap.add_argument("command", choices=["by-heading", "by-domain", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_domain_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = domains_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading domain data found.")
            else:
                print(f"{'heading':<20} {'domains':<10} {'chunks':<8} {'assignments':<14} {'avg_score'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['distinct_domains']:<10} {r['classified_chunks']:<8} {r['domain_assignments']:<14} {r['avg_score']:.4f}")
    elif args.command == "by-domain":
        rows = headings_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain heading data found.")
            else:
                print(f"{'domain':<16} {'headings':<10} {'chunks':<8} {'assignments':<14} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<16} {r['distinct_headings']:<10} {r['classified_chunks']:<8} {r['domain_assignments']:<14} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = heading_domain_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading domain data found.")
            else:
                print(f"{'heading':<20} {'domains':<10} {'chunks':<8} {'assignments':<14} {'avg_score':<12} {'ratio'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['distinct_domains']:<10} {r['classified_chunks']:<8} {r['domain_assignments']:<14} {r['avg_score']:<12.4f} {r['domain_ratio']:.4f}")
    elif args.command == "summary":
        s = heading_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
