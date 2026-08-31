#!/usr/bin/env python3
"""Publisher citation profile: which publishers produce the most cited content.

publisher_tag_profile.py profiles publishers by tag vocabulary.
publisher_domain_profile.py profiles publishers by semantic domain.
No tool joins sources.publisher with citations to measure which
publishers attract the most citations, how verification rates vary
by publisher, or which publishers are exclusive citation sources.

Usage:
    python tools/corpus/publisher_citation_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/publisher_citation_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/publisher_citation_profile.py verification [--db PATH] [--json]
    python tools/corpus/publisher_citation_profile.py summary [--db PATH] [--json]
    python tools/corpus/publisher_citation_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def citations_by_publisher(conn) -> list[dict]:
    """Citation distribution per publisher."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(ci.citation_id) AS total_citations,
               COUNT(DISTINCT ci.chunk_id) AS citing_chunks,
               SUM(ci.verified) AS verified_citations,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN citations ci ON ci.chunk_id = c.chunk_id
        GROUP BY s.publisher
        ORDER BY total_citations DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "total_citations": r[1],
            "citing_chunks": r[2],
            "verified_citations": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[3] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def citation_tags_by_publisher(conn) -> list[dict]:
    """Citation tag distribution per publisher."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COALESCE(ci.tag, '(none)') AS citation_tag,
               COUNT(ci.citation_id) AS tag_count
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN citations ci ON ci.chunk_id = c.chunk_id
        GROUP BY s.publisher, citation_tag
        ORDER BY tag_count DESC, s.publisher, citation_tag
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "citation_tag": r[1],
            "count": r[2],
        }
        for r in rows
    ]


def publisher_verification_profile(conn) -> list[dict]:
    """Verification rate per publisher, filtered to publishers with citations."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified,
               SUM(CASE WHEN ci.verified = 0 THEN 1 ELSE 0 END) AS unverified,
               COUNT(DISTINCT c.chunk_id) AS citing_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN citations ci ON ci.chunk_id = c.chunk_id
        GROUP BY s.publisher
        HAVING COUNT(ci.citation_id) >= 1
        ORDER BY CAST(SUM(ci.verified) AS REAL) / COUNT(ci.citation_id) DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "total": r[1],
            "verified": r[2],
            "unverified": r[3],
            "citing_chunks": r[4],
            "verification_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def publisher_citation_summary(conn) -> dict:
    """Aggregate publisher-citation statistics."""
    total_publishers = conn.execute(
        "SELECT COUNT(DISTINCT publisher) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    publishers_with_citations = conn.execute(
        """
        SELECT COUNT(DISTINCT s.publisher)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN citations ci ON ci.chunk_id = c.chunk_id
        WHERE s.publisher IS NOT NULL
        """
    ).fetchone()[0]

    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]

    total_verified = conn.execute(
        "SELECT SUM(verified) FROM citations"
    ).fetchone()[0] or 0

    avg_citations_per_publisher = conn.execute(
        """
        SELECT ROUND(AVG(cite_count), 4)
        FROM (
            SELECT s.publisher, COUNT(ci.citation_id) AS cite_count
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            JOIN citations ci ON ci.chunk_id = c.chunk_id
            WHERE s.publisher IS NOT NULL
            GROUP BY s.publisher
        )
        """
    ).fetchone()[0]

    single_publisher_targets = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ci.target_uri
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            WHERE s.publisher IS NOT NULL
            GROUP BY ci.target_uri
            HAVING COUNT(DISTINCT s.publisher) = 1
        )
        """
    ).fetchone()[0]

    total_distinct_targets = conn.execute(
        """
        SELECT COUNT(DISTINCT ci.target_uri)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        WHERE s.publisher IS NOT NULL
        """
    ).fetchone()[0]

    return {
        "total_publishers": total_publishers,
        "publishers_with_citations": publishers_with_citations,
        "publisher_citation_coverage": round(publishers_with_citations / max(total_publishers, 1), 4),
        "total_citations": total_citations,
        "total_verified": total_verified,
        "overall_verification_rate": round(total_verified / max(total_citations, 1), 4),
        "avg_citations_per_publisher": avg_citations_per_publisher or 0.0,
        "single_publisher_targets": single_publisher_targets,
        "single_publisher_target_rate": round(single_publisher_targets / max(total_distinct_targets, 1), 4),
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
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "abc", 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None),
        )

        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 25, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "intro", "claim", None, "t", "t", 15, "jkl", 4000, 0, "accepted", None, t1))

        # Citations: acme has 3 (2 verified), globex has 2 (1 verified), null pub has 1 (0 verified)
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci1", "c1", "http://example.com/a", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci2", "c1", "http://example.com/b", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci3", "c2", "http://example.com/c", None, "note", None, 0, None))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci4", "c3", "http://example.com/a", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci5", "c3", "http://example.com/d", None, None, None, 0, None))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci6", "c4", "http://example.com/e", None, "ref", None, 0, None))
        conn.commit()

        # 1. by-publisher: acme has 3 citations
        bp = citations_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["total_citations"] == 3
        ok += 1

        # 2. acme has 2 verified citations
        assert acme["verified_citations"] == 2
        ok += 1

        # 3. globex has 2 citations
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["total_citations"] == 2
        ok += 1

        # 4. globex has 1 verified
        assert globex["verified_citations"] == 1
        ok += 1

        # 5. acme verification rate = 2/3
        assert acme["verification_rate"] == round(2 / 3, 4)
        ok += 1

        # 6. by-tag: acme "ref" tag has 2 citations
        bt = citation_tags_by_publisher(conn)
        acme_ref = [r for r in bt if r["publisher"] == "acme" and r["citation_tag"] == "ref"][0]
        assert acme_ref["count"] == 2
        ok += 1

        # 7. acme "note" tag has 1 citation
        acme_note = [r for r in bt if r["publisher"] == "acme" and r["citation_tag"] == "note"][0]
        assert acme_note["count"] == 1
        ok += 1

        # 8. verification profile: acme has 1 unverified
        vp = publisher_verification_profile(conn)
        acme_vp = [r for r in vp if r["publisher"] == "acme"][0]
        assert acme_vp["unverified"] == 1
        ok += 1

        # 9. globex has 1 unverified
        globex_vp = [r for r in vp if r["publisher"] == "globex"][0]
        assert globex_vp["unverified"] == 1
        ok += 1

        # 10. summary: publishers_with_citations = 2 (acme, globex; null excluded)
        s = publisher_citation_summary(conn)
        assert s["publishers_with_citations"] == 2
        ok += 1

        # 11. total_citations = 6
        assert s["total_citations"] == 6
        ok += 1

        # 12. total_verified = 3
        assert s["total_verified"] == 3
        ok += 1

        # 13. single_publisher_targets: b (acme), c (acme), d (globex), but a is shared
        # b -> acme only, c -> acme only, d -> globex only = 3 single-publisher targets
        assert s["single_publisher_targets"] == 3, f"expected 3, got {s['single_publisher_targets']}"
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = publisher_citation_summary(conn)
        assert s["publishers_with_citations"] == 0
        assert s["total_citations"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Publisher citation profile analysis")
    ap.add_argument("command", choices=["by-publisher", "by-tag", "verification", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS publisher_citation_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-publisher":
        rows = citations_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher citation data found.")
            else:
                print(f"{'publisher':<20} {'citations':<10} {'chunks':<8} {'verified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['total_citations']:<10} {r['citing_chunks']:<8} {r['verified_citations']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "by-tag":
        rows = citation_tags_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher citation tag data found.")
            else:
                print(f"{'publisher':<20} {'tag':<15} {'count'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['citation_tag']:<15} {r['count']}")
    elif args.command == "verification":
        rows = publisher_verification_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publishers with citations found.")
            else:
                print(f"{'publisher':<20} {'total':<8} {'verified':<10} {'unverified':<10} {'rate'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['total']:<8} {r['verified']:<10} {r['unverified']:<10} {r['verification_rate']:.4f}")
    elif args.command == "summary":
        s = publisher_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
