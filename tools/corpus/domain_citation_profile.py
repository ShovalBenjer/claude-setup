#!/usr/bin/env python3
"""Domain citation profile: citation density and quality per knowledge domain.

tag_citation_correlation.py correlates tags with citations.
artifact_domain_distribution.py maps artifacts to domains.
No tool joins chunk_domains with citations to measure how well
each knowledge domain is externally referenced, or which domains
have the highest and lowest verification rates.

Usage:
    python tools/corpus/domain_citation_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/domain_citation_profile.py by-verified [--db PATH] [--json]
    python tools/corpus/domain_citation_profile.py top-uris [--db PATH] [--json]
    python tools/corpus/domain_citation_profile.py summary [--db PATH] [--json]
    python tools/corpus/domain_citation_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

_CD_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_domains ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  domain TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  classified_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, domain))"
)


def citation_density_by_domain(conn) -> list[dict]:
    """Citation density per domain."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT cd.chunk_id) AS classified_chunks,
               COUNT(DISTINCT ci.citation_id) AS total_citations,
               COUNT(DISTINCT CASE WHEN ci.verified = 1 THEN ci.citation_id END) AS verified,
               COUNT(DISTINCT CASE WHEN ci.verified = 0 THEN ci.citation_id END) AS unverified,
               ROUND(
                   COUNT(DISTINCT ci.citation_id) * 1.0
                   / MAX(COUNT(DISTINCT cd.chunk_id), 1),
                   4
               ) AS citations_per_chunk
        FROM chunk_domains cd
        LEFT JOIN citations ci ON ci.chunk_id = cd.chunk_id
        GROUP BY cd.domain
        ORDER BY citations_per_chunk DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "classified_chunks": r[1],
            "total_citations": r[2],
            "verified": r[3],
            "unverified": r[4],
            "citations_per_chunk": r[5],
        }
        for r in rows
    ]


def verification_by_domain(conn) -> list[dict]:
    """Verification rate per domain among chunks with citations."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT ci.citation_id) AS total_citations,
               COUNT(DISTINCT CASE WHEN ci.verified = 1 THEN ci.citation_id END) AS verified,
               ROUND(
                   COUNT(DISTINCT CASE WHEN ci.verified = 1 THEN ci.citation_id END) * 1.0
                   / MAX(COUNT(DISTINCT ci.citation_id), 1),
                   4
               ) AS verification_rate
        FROM chunk_domains cd
        JOIN citations ci ON ci.chunk_id = cd.chunk_id
        GROUP BY cd.domain
        ORDER BY verification_rate DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "total_citations": r[1],
            "verified": r[2],
            "verification_rate": r[3],
        }
        for r in rows
    ]


def top_domain_uris(conn) -> list[dict]:
    """Domain-target_uri pairs with highest citation counts."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT cd.domain, ci.target_uri,
               COUNT(*) AS pair_count,
               COUNT(CASE WHEN ci.verified = 1 THEN 1 END) AS verified
        FROM chunk_domains cd
        JOIN citations ci ON ci.chunk_id = cd.chunk_id
        GROUP BY cd.domain, ci.target_uri
        ORDER BY pair_count DESC, cd.domain
        LIMIT 50
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "target_uri": r[1],
            "pair_count": r[2],
            "verified": r[3],
        }
        for r in rows
    ]


def domain_citation_summary(conn) -> dict:
    """Aggregate domain-citation profile statistics."""
    conn.execute(_CD_DDL)
    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]
    classified_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_domains"
    ).fetchone()[0]
    classified_with_citations = conn.execute(
        """
        SELECT COUNT(DISTINCT cd.chunk_id)
        FROM chunk_domains cd
        JOIN citations ci ON ci.chunk_id = cd.chunk_id
        """
    ).fetchone()[0]
    classified_without = classified_chunks - classified_with_citations
    citation_coverage = round(classified_with_citations / max(classified_chunks, 1), 4)

    citations_on_classified = conn.execute(
        """
        SELECT COUNT(DISTINCT ci.citation_id)
        FROM chunk_domains cd
        JOIN citations ci ON ci.chunk_id = cd.chunk_id
        """
    ).fetchone()[0]
    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]
    classified_share = round(citations_on_classified / max(total_citations, 1), 4)

    by_domain = citation_density_by_domain(conn)
    densest = by_domain[0]["domain"] if by_domain and by_domain[0]["total_citations"] > 0 else None
    sparsest = None
    for r in reversed(by_domain):
        if r["total_citations"] > 0:
            sparsest = r["domain"]
            break

    return {
        "total_domains": total_domains,
        "classified_chunks": classified_chunks,
        "classified_with_citations": classified_with_citations,
        "classified_without_citations": classified_without,
        "citation_coverage_rate": citation_coverage,
        "citations_on_classified": citations_on_classified,
        "classified_citation_share": classified_share,
        "densest_domain": densest,
        "sparsest_domain": sparsest,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute(_CD_DDL)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        for i in range(1, 6):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"c{i}", "s1", i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t1),
            )

        # domains: c1 in ml+web, c2 in devops, c3 in ml, c4 in security (no citations)
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "web", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "devops", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "security", 0.6, t1))

        # citations: c1 has 2 (1 verified), c2 has 1 verified, c3 has 1 unverified, c5 unclassified
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci1", "c1", "http://a.com", None, "url", None, 1, t1),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci2", "c1", "http://b.com", None, "doi", None, 0, None),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci3", "c2", "http://c.com", None, "url", None, 1, t1),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci4", "c3", "http://d.com", None, "doi", None, 0, None),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci5", "c5", "http://e.com", None, "url", None, 1, t1),
        )
        conn.commit()

        # 1. ml has 3 citations (ci1, ci2 from c1 + ci4 from c3)
        bd = citation_density_by_domain(conn)
        ml_row = [r for r in bd if r["domain"] == "ml"][0]
        assert ml_row["total_citations"] == 3, f"ml citations {ml_row['total_citations']}"
        ok += 1

        # 2. web has 2 citations (ci1, ci2 from c1)
        web_row = [r for r in bd if r["domain"] == "web"][0]
        assert web_row["total_citations"] == 2
        ok += 1

        # 3. devops has 1 citation
        devops_row = [r for r in bd if r["domain"] == "devops"][0]
        assert devops_row["total_citations"] == 1
        ok += 1

        # 4. security has 0 citations
        sec_row = [r for r in bd if r["domain"] == "security"][0]
        assert sec_row["total_citations"] == 0
        ok += 1

        # 5. ml verified is 1 (ci1)
        assert ml_row["verified"] == 1
        ok += 1

        # 6. verification_by_domain: devops rate = 1.0
        vr = verification_by_domain(conn)
        devops_vr = [r for r in vr if r["domain"] == "devops"][0]
        assert devops_vr["verification_rate"] == 1.0
        ok += 1

        # 7. security not in verification (no citations)
        vr_domains = {r["domain"] for r in vr}
        assert "security" not in vr_domains
        ok += 1

        # 8. top_domain_uris returns entries
        tu = top_domain_uris(conn)
        assert len(tu) >= 1
        ok += 1

        # 9. summary classified_with_citations is 3 (c1, c2, c3)
        s = domain_citation_summary(conn)
        assert s["classified_with_citations"] == 3
        ok += 1

        # 10. classified_without is 1 (c4)
        assert s["classified_without_citations"] == 1
        ok += 1

        # 11. citations_on_classified is 4 (ci5 on unclassified c5)
        assert s["citations_on_classified"] == 4
        ok += 1

        # 12. total_domains is 4
        assert s["total_domains"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["citation_coverage_rate"] == s["citation_coverage_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = domain_citation_summary(conn)
        assert s["total_domains"] == 0
        assert s["classified_with_citations"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Domain citation profile analysis")
    ap.add_argument("command", choices=["by-domain", "by-verified", "top-uris", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS domain_citation_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-domain":
        rows = citation_density_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No classified chunks found.")
            else:
                print(f"{'domain':<16} {'chunks':<8} {'citations':<10} {'verified':<10} {'cit/chunk'}")
                for r in rows:
                    print(f"{r['domain']:<16} {r['classified_chunks']:<8} {r['total_citations']:<10} {r['verified']:<10} {r['citations_per_chunk']:.4f}")
    elif args.command == "by-verified":
        rows = verification_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'domain':<16} {'citations':<10} {'verified':<10} {'ver_rate'}")
            for r in rows:
                print(f"{r['domain']:<16} {r['total_citations']:<10} {r['verified']:<10} {r['verification_rate']:.4f}")
    elif args.command == "top-uris":
        rows = top_domain_uris(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'domain':<16} {'target_uri':<30} {'count':<8} {'verified'}")
            for r in rows:
                print(f"{r['domain']:<16} {r['target_uri']:<30} {r['pair_count']:<8} {r['verified']}")
    elif args.command == "summary":
        s = domain_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
