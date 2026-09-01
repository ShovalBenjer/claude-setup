#!/usr/bin/env python3
"""License domain profile: which license types correlate with which domains.

license_tag_profile.py profiles licenses by tag vocabulary.
license_edge_analysis.py profiles licenses by edge patterns.
No tool joins sources.license_spdx with chunk_domains to measure
which license categories concentrate which knowledge domains,
whether permissive licenses attract broader domain coverage, or
how domain scores vary by license.

Usage:
    python tools/corpus/license_domain_profile.py by-license [--db PATH] [--json]
    python tools/corpus/license_domain_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/license_domain_profile.py diversity [--db PATH] [--json]
    python tools/corpus/license_domain_profile.py summary [--db PATH] [--json]
    python tools/corpus/license_domain_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def domains_by_license(conn) -> list[dict]:
    """Domain distribution per license type."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS domain_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY s.license_spdx
        ORDER BY domain_assignments DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "distinct_domains": r[1],
            "domain_assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def licenses_by_domain(conn) -> list[dict]:
    """License distribution per domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT s.license_spdx) AS distinct_licenses,
               COUNT(cd.domain) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunk_domains cd
        JOIN chunks c ON c.chunk_id = cd.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY cd.domain
        ORDER BY distinct_licenses DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_licenses": r[1],
            "assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def license_domain_diversity(conn) -> list[dict]:
    """Per-license domain diversity: ratio of distinct domains to assignments."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY s.license_spdx
        HAVING COUNT(cd.domain) >= 2
        ORDER BY CAST(COUNT(DISTINCT cd.domain) AS REAL) / COUNT(cd.domain), s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "distinct_domains": r[1],
            "total_assignments": r[2],
            "classified_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def license_domain_summary(conn) -> dict:
    """Aggregate license-domain statistics."""
    total_licenses = conn.execute(
        "SELECT COUNT(DISTINCT license_spdx) FROM sources"
    ).fetchone()[0]

    licenses_with_domains = conn.execute(
        """
        SELECT COUNT(DISTINCT s.license_spdx)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]

    total_assignments = conn.execute(
        "SELECT COUNT(*) FROM chunk_domains"
    ).fetchone()[0]

    avg_domains_per_license = conn.execute(
        """
        SELECT ROUND(AVG(dom_count), 4)
        FROM (
            SELECT s.license_spdx, COUNT(DISTINCT cd.domain) AS dom_count
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY s.license_spdx
        )
        """
    ).fetchone()[0]

    single_license_domains = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT cd.domain
            FROM chunk_domains cd
            JOIN chunks c ON c.chunk_id = cd.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY cd.domain
            HAVING COUNT(DISTINCT s.license_spdx) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_licenses": total_licenses,
        "licenses_with_domains": licenses_with_domains,
        "license_domain_coverage": round(licenses_with_domains / max(total_licenses, 1), 4),
        "total_distinct_domains": total_domains,
        "total_domain_assignments": total_assignments,
        "avg_domains_per_license": avg_domains_per_license or 0.0,
        "single_license_domains": single_license_domains,
        "single_license_domain_rate": round(single_license_domains / max(total_domains, 1), 4),
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "Apache-2.0", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "CC-BY-4.0", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None),
        )

        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 25, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "intro", "claim", None, "t", "t", 15, "jkl", 4000, 0, "accepted", None, t1))

        # Domains: MIT gets ML+NLP+stats, Apache gets ML+bio, CC-BY gets NLP
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ML", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "NLP", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "stats", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ML", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "bio", 0.6, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "NLP", 0.75, t1))
        conn.commit()

        # 1. by-license: MIT has 3 distinct domains
        bl = domains_by_license(conn)
        mit = [r for r in bl if r["license_spdx"] == "MIT"][0]
        assert mit["distinct_domains"] == 3
        ok += 1

        # 2. MIT has 3 domain assignments
        assert mit["domain_assignments"] == 3
        ok += 1

        # 3. Apache has 2 distinct domains
        apache = [r for r in bl if r["license_spdx"] == "Apache-2.0"][0]
        assert apache["distinct_domains"] == 2
        ok += 1

        # 4. CC-BY has 1 domain
        ccby = [r for r in bl if r["license_spdx"] == "CC-BY-4.0"][0]
        assert ccby["distinct_domains"] == 1
        ok += 1

        # 5. by-domain: "ML" spans 2 licenses (MIT, Apache)
        bd = licenses_by_domain(conn)
        ml = [r for r in bd if r["domain"] == "ML"][0]
        assert ml["distinct_licenses"] == 2
        ok += 1

        # 6. "NLP" spans 2 licenses (MIT, CC-BY)
        nlp = [r for r in bd if r["domain"] == "NLP"][0]
        assert nlp["distinct_licenses"] == 2
        ok += 1

        # 7. "bio" spans 1 license (Apache only)
        bio = [r for r in bd if r["domain"] == "bio"][0]
        assert bio["distinct_licenses"] == 1
        ok += 1

        # 8. diversity: MIT has 3/3=1.0
        div = license_domain_diversity(conn)
        mit_div = [r for r in div if r["license_spdx"] == "MIT"][0]
        assert mit_div["diversity_ratio"] == 1.0
        ok += 1

        # 9. Apache has 2/2=1.0
        apache_div = [r for r in div if r["license_spdx"] == "Apache-2.0"][0]
        assert apache_div["diversity_ratio"] == 1.0
        ok += 1

        # 10. CC-BY not in diversity (only 1 assignment)
        ccby_div = [r for r in div if r["license_spdx"] == "CC-BY-4.0"]
        assert len(ccby_div) == 0
        ok += 1

        # 11. summary: licenses_with_domains = 3
        s = license_domain_summary(conn)
        assert s["licenses_with_domains"] == 3
        ok += 1

        # 12. total_distinct_domains = 4
        assert s["total_distinct_domains"] == 4
        ok += 1

        # 13. single_license_domains: stats (MIT only), bio (Apache only) = 2
        assert s["single_license_domains"] == 2, f"expected 2, got {s['single_license_domains']}"
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = license_domain_summary(conn)
        assert s["licenses_with_domains"] == 0
        assert s["total_distinct_domains"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="License domain profile analysis")
    ap.add_argument("command", choices=["by-license", "by-domain", "diversity", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS license_domain_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-license":
        rows = domains_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license domain data found.")
            else:
                print(f"{'license':<20} {'domains':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['license_spdx']:<20} {r['distinct_domains']:<8} {r['domain_assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-domain":
        rows = licenses_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain license data found.")
            else:
                print(f"{'domain':<20} {'licenses':<10} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<20} {r['distinct_licenses']:<10} {r['assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "diversity":
        rows = license_domain_diversity(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No licenses with multiple domains found.")
            else:
                print(f"{'license':<20} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    print(f"{r['license_spdx']:<20} {r['distinct_domains']:<10} {r['total_assignments']:<8} {r['classified_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = license_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
