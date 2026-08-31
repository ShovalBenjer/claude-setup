#!/usr/bin/env python3
"""License citation profile: how license types relate to citation patterns.

license_tag_profile.py profiles licenses by tag vocabulary.
license_domain_profile.py profiles licenses by semantic domain.
license_edge_analysis.py profiles licenses by claim edges.
No tool joins sources.license_spdx with citations to measure which
license types concentrate citations, how verification rates vary
across licenses, or how citation target diversity differs by license.

Usage:
    python tools/corpus/license_citation_profile.py by-license [--db PATH] [--json]
    python tools/corpus/license_citation_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/license_citation_profile.py verification [--db PATH] [--json]
    python tools/corpus/license_citation_profile.py summary [--db PATH] [--json]
    python tools/corpus/license_citation_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def citations_by_license(conn) -> list[dict]:
    """Citation distribution per license type."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(ci.citation_id) AS total_citations,
               COUNT(DISTINCT c.chunk_id) AS citing_chunks,
               SUM(ci.verified) AS verified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.license_spdx
        ORDER BY total_citations DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "total_citations": r[1],
            "citing_chunks": r[2],
            "verified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[3] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def citation_tags_by_license(conn) -> list[dict]:
    """Citation tag distribution per license type."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               ci.tag,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.license_spdx, ci.tag
        ORDER BY s.license_spdx, total DESC
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "tag": r[1],
            "total": r[2],
            "verified": r[3],
        }
        for r in rows
    ]


def license_verification_profile(conn) -> list[dict]:
    """Verification rate per license, filtered to licenses with at least 2 citations."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified,
               SUM(CASE WHEN ci.verified = 0 THEN 1 ELSE 0 END) AS unverified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.license_spdx
        HAVING COUNT(ci.citation_id) >= 2
        ORDER BY CAST(SUM(ci.verified) AS REAL) / COUNT(ci.citation_id) DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "total": r[1],
            "verified": r[2],
            "unverified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def license_citation_summary(conn) -> dict:
    """Aggregate license-citation statistics."""
    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]

    total_verified = conn.execute(
        "SELECT SUM(verified) FROM citations"
    ).fetchone()[0] or 0

    licenses_with_citations = conn.execute(
        """
        SELECT COUNT(DISTINCT s.license_spdx)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        """
    ).fetchone()[0]

    total_licenses = conn.execute(
        "SELECT COUNT(DISTINCT license_spdx) FROM sources"
    ).fetchone()[0]

    avg_citations_per_license = conn.execute(
        """
        SELECT ROUND(AVG(cite_count), 4)
        FROM (
            SELECT s.license_spdx, COUNT(ci.citation_id) AS cite_count
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY s.license_spdx
        )
        """
    ).fetchone()[0]

    distinct_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT ci.tag)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        WHERE ci.tag IS NOT NULL
        """
    ).fetchone()[0]

    return {
        "total_citations": total_citations,
        "total_verified": total_verified,
        "overall_verification_rate": round(total_verified / max(total_citations, 1), 4),
        "licenses_with_citations": licenses_with_citations,
        "total_licenses": total_licenses,
        "license_citation_coverage": round(licenses_with_citations / max(total_licenses, 1), 4),
        "avg_citations_per_license": avg_citations_per_license or 0.0,
        "distinct_citation_tags": distinct_tags,
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "Apache-2.0", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "CC-BY-4.0", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None),
        )

        # c1: MIT, c2: MIT, c3: Apache-2.0, c4: CC-BY-4.0 (no citations)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "methods", "claim", None, "t", "t", 15, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "methods", "claim", None, "t", "t", 25, "jkl", 4000, 0, "accepted", None, t1))

        # Citations: MIT c1 has 3 (2 verified, tags: ref, ref, note),
        # MIT c2 has 1 (1 verified, tag: ref), Apache c3 has 2 (0 verified, tags: ref, None)
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci1", "c1", "http://example.com/a", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci2", "c1", "http://example.com/b", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci3", "c1", "http://example.com/c", None, "note", None, 0, None))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci4", "c2", "http://example.com/a", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci5", "c3", "http://example.com/d", None, "ref", None, 0, None))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci6", "c3", "http://example.com/e", None, None, None, 0, None))
        conn.commit()

        # 1. by-license: MIT has 4 citations (c1=3, c2=1)
        bl = citations_by_license(conn)
        mit = [r for r in bl if r["license_spdx"] == "MIT"][0]
        assert mit["total_citations"] == 4
        ok += 1

        # 2. MIT has 3 verified
        assert mit["verified"] == 3
        ok += 1

        # 3. Apache-2.0 has 2 citations
        apache = [r for r in bl if r["license_spdx"] == "Apache-2.0"][0]
        assert apache["total_citations"] == 2
        ok += 1

        # 4. CC-BY-4.0 not in results (no citations)
        ccby = [r for r in bl if r["license_spdx"] == "CC-BY-4.0"]
        assert len(ccby) == 0
        ok += 1

        # 5. citation_tags_by_license: MIT has "ref" with 3
        ct = citation_tags_by_license(conn)
        mit_ref = [r for r in ct if r["license_spdx"] == "MIT" and r["tag"] == "ref"]
        assert len(mit_ref) == 1 and mit_ref[0]["total"] == 3
        ok += 1

        # 6. MIT has "note" with 1
        mit_note = [r for r in ct if r["license_spdx"] == "MIT" and r["tag"] == "note"]
        assert len(mit_note) == 1 and mit_note[0]["total"] == 1
        ok += 1

        # 7. Apache has None tag with 1
        apache_none = [r for r in ct if r["license_spdx"] == "Apache-2.0" and r["tag"] is None]
        assert len(apache_none) == 1 and apache_none[0]["total"] == 1
        ok += 1

        # 8. verification: MIT rate = 3/4 = 0.75
        vp = license_verification_profile(conn)
        mit_vp = [r for r in vp if r["license_spdx"] == "MIT"][0]
        assert mit_vp["verification_rate"] == 0.75
        ok += 1

        # 9. Apache rate = 0/2 = 0.0
        apache_vp = [r for r in vp if r["license_spdx"] == "Apache-2.0"][0]
        assert apache_vp["verification_rate"] == 0.0
        ok += 1

        # 10. CC-BY-4.0 not in verification (no citations)
        ccby_vp = [r for r in vp if r["license_spdx"] == "CC-BY-4.0"]
        assert len(ccby_vp) == 0
        ok += 1

        # 11. summary: total_citations = 6
        s = license_citation_summary(conn)
        assert s["total_citations"] == 6
        ok += 1

        # 12. licenses_with_citations = 2 (MIT, Apache-2.0)
        assert s["licenses_with_citations"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["license_citation_coverage"] == s["license_citation_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = license_citation_summary(conn)
        assert s["total_citations"] == 0
        assert s["licenses_with_citations"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="License citation profile analysis")
    ap.add_argument("command", choices=["by-license", "by-tag", "verification", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS license_citation_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-license":
        rows = citations_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license citation data found.")
            else:
                print(f"{'license':<16} {'citations':<10} {'chunks':<8} {'verified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['license_spdx']:<16} {r['total_citations']:<10} {r['citing_chunks']:<8} {r['verified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "by-tag":
        rows = citation_tags_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license citation tag data found.")
            else:
                print(f"{'license':<16} {'tag':<12} {'total':<8} {'verified'}")
                for r in rows:
                    tag = r["tag"] or "(none)"
                    print(f"{r['license_spdx']:<16} {tag:<12} {r['total']:<8} {r['verified']}")
    elif args.command == "verification":
        rows = license_verification_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No licenses with multiple citations found.")
            else:
                print(f"{'license':<16} {'total':<8} {'verified':<10} {'unverified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['license_spdx']:<16} {r['total']:<8} {r['verified']:<10} {r['unverified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "summary":
        s = license_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
