#!/usr/bin/env python3
"""Tag citation correlation: which tags predict high citation density.

tag_citation_yield.py correlates tags with citation count per chunk.
artifact_domain_distribution.py maps artifacts to domains.
No tool correlates tag presence with citation verification status and
citation density at a finer grain, measuring verified versus unverified
citation rates per tag.

Usage:
    python tools/corpus/tag_citation_correlation.py by-tag [--db PATH] [--json]
    python tools/corpus/tag_citation_correlation.py by-verified [--db PATH] [--json]
    python tools/corpus/tag_citation_correlation.py top-pairs [--db PATH] [--json]
    python tools/corpus/tag_citation_correlation.py summary [--db PATH] [--json]
    python tools/corpus/tag_citation_correlation.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

_CT_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_tags ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  tag TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  tagged_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, tag))"
)


def citation_density_by_tag(conn) -> list[dict]:
    """Citation density per tag: total, verified, unverified, rate."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               COUNT(DISTINCT ci.citation_id) AS total_citations,
               COUNT(DISTINCT CASE WHEN ci.verified = 1 THEN ci.citation_id END) AS verified,
               COUNT(DISTINCT CASE WHEN ci.verified = 0 THEN ci.citation_id END) AS unverified,
               ROUND(
                   COUNT(DISTINCT ci.citation_id) * 1.0
                   / MAX(COUNT(DISTINCT ct.chunk_id), 1),
                   4
               ) AS citations_per_chunk
        FROM chunk_tags ct
        LEFT JOIN citations ci ON ci.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY citations_per_chunk DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "tagged_chunks": r[1],
            "total_citations": r[2],
            "verified": r[3],
            "unverified": r[4],
            "citations_per_chunk": r[5],
        }
        for r in rows
    ]


def verification_rate_by_tag(conn) -> list[dict]:
    """Verification rate per tag among chunks that have citations."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT ci.citation_id) AS total_citations,
               COUNT(DISTINCT CASE WHEN ci.verified = 1 THEN ci.citation_id END) AS verified,
               ROUND(
                   COUNT(DISTINCT CASE WHEN ci.verified = 1 THEN ci.citation_id END) * 1.0
                   / MAX(COUNT(DISTINCT ci.citation_id), 1),
                   4
               ) AS verification_rate
        FROM chunk_tags ct
        JOIN citations ci ON ci.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY verification_rate DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "total_citations": r[1],
            "verified": r[2],
            "verification_rate": r[3],
        }
        for r in rows
    ]


def top_tag_citation_pairs(conn) -> list[dict]:
    """Tag-target_uri pairs with highest citation counts."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.tag, ci.target_uri,
               COUNT(*) AS pair_count,
               COUNT(CASE WHEN ci.verified = 1 THEN 1 END) AS verified
        FROM chunk_tags ct
        JOIN citations ci ON ci.chunk_id = ct.chunk_id
        GROUP BY ct.tag, ci.target_uri
        ORDER BY pair_count DESC, ct.tag
        LIMIT 50
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "target_uri": r[1],
            "pair_count": r[2],
            "verified": r[3],
        }
        for r in rows
    ]


def correlation_summary(conn) -> dict:
    """Aggregate tag-citation correlation statistics."""
    conn.execute(_CT_DDL)
    distinct_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]
    tagged_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_tags"
    ).fetchone()[0]
    tagged_with_citations = conn.execute(
        """
        SELECT COUNT(DISTINCT ct.chunk_id)
        FROM chunk_tags ct
        JOIN citations ci ON ci.chunk_id = ct.chunk_id
        """
    ).fetchone()[0]
    tagged_without_citations = tagged_chunks - tagged_with_citations
    citation_coverage_rate = round(tagged_with_citations / max(tagged_chunks, 1), 4)

    total_citations_on_tagged = conn.execute(
        """
        SELECT COUNT(DISTINCT ci.citation_id)
        FROM chunk_tags ct
        JOIN citations ci ON ci.chunk_id = ct.chunk_id
        """
    ).fetchone()[0]
    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]
    tagged_citation_share = round(
        total_citations_on_tagged / max(total_citations, 1), 4
    )

    by_tag = citation_density_by_tag(conn)
    highest_density_tag = by_tag[0]["tag"] if by_tag and by_tag[0]["total_citations"] > 0 else None
    lowest_density_tag = None
    for r in reversed(by_tag):
        if r["total_citations"] > 0:
            lowest_density_tag = r["tag"]
            break

    return {
        "distinct_tags": distinct_tags,
        "tagged_chunks": tagged_chunks,
        "tagged_with_citations": tagged_with_citations,
        "tagged_without_citations": tagged_without_citations,
        "citation_coverage_rate": citation_coverage_rate,
        "total_citations_on_tagged": total_citations_on_tagged,
        "tagged_citation_share": tagged_citation_share,
        "highest_density_tag": highest_density_tag,
        "lowest_density_tag": lowest_density_tag,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute(_CT_DDL)

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

        # Tags: c1 has "python"+"ml", c2 has "python", c3 has "ml", c4 has "web" (no citations)
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "python", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "web", 0.5, t1))

        # Citations: c1 has 2 (1 verified, 1 not), c2 has 1 verified, c3 has 1 unverified, c5 has 1 (untagged)
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

        # 1. citation_density_by_tag: python has 3 citations across 2 chunks
        bd = citation_density_by_tag(conn)
        py_row = [r for r in bd if r["tag"] == "python"][0]
        assert py_row["total_citations"] == 3, f"python citations {py_row['total_citations']}"
        assert py_row["tagged_chunks"] == 2
        ok += 1

        # 2. ml has 3 citations across 2 chunks (c1 has 2, c3 has 1)
        ml_row = [r for r in bd if r["tag"] == "ml"][0]
        assert ml_row["total_citations"] == 3, f"ml citations {ml_row['total_citations']}"
        ok += 1

        # 3. web has 0 citations
        web_row = [r for r in bd if r["tag"] == "web"][0]
        assert web_row["total_citations"] == 0
        ok += 1

        # 4. python verified count is 2 (ci1 + ci3)
        assert py_row["verified"] == 2, f"python verified {py_row['verified']}"
        ok += 1

        # 5. ml verified count is 1 (ci1 from c1)
        assert ml_row["verified"] == 1, f"ml verified {ml_row['verified']}"
        ok += 1

        # 6. verification_rate_by_tag: python rate = 2/3
        vr = verification_rate_by_tag(conn)
        py_vr = [r for r in vr if r["tag"] == "python"][0]
        assert py_vr["verification_rate"] == round(2 / 3, 4), f"python vr {py_vr['verification_rate']}"
        ok += 1

        # 7. web not in verification_rate (no citations to join)
        vr_tags = {r["tag"] for r in vr}
        assert "web" not in vr_tags
        ok += 1

        # 8. top_tag_citation_pairs returns entries
        tp = top_tag_citation_pairs(conn)
        assert len(tp) >= 1
        ok += 1

        # 9. summary: tagged_with_citations is 3 (c1, c2, c3)
        s = correlation_summary(conn)
        assert s["tagged_with_citations"] == 3, f"tagged_with_citations {s['tagged_with_citations']}"
        ok += 1

        # 10. tagged_without_citations is 1 (c4)
        assert s["tagged_without_citations"] == 1
        ok += 1

        # 11. total_citations_on_tagged is 4 (ci1-ci4, not ci5 which is on untagged c5)
        assert s["total_citations_on_tagged"] == 4, f"on_tagged {s['total_citations_on_tagged']}"
        ok += 1

        # 12. tagged_citation_share = 4/5
        assert s["tagged_citation_share"] == round(4 / 5, 4)
        ok += 1

        # 13. JSON serialisation round-trips
        j = json.loads(json.dumps(s))
        assert j["citation_coverage_rate"] == s["citation_coverage_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = correlation_summary(conn)
        assert s["distinct_tags"] == 0
        assert s["tagged_with_citations"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Tag citation correlation analysis")
    ap.add_argument("command", choices=["by-tag", "by-verified", "top-pairs", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS tag_citation_correlation selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-tag":
        rows = citation_density_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tagged chunks found.")
            else:
                print(f"{'tag':<16} {'chunks':<8} {'citations':<10} {'verified':<10} {'cit/chunk'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['tagged_chunks']:<8} {r['total_citations']:<10} {r['verified']:<10} {r['citations_per_chunk']:.4f}")
    elif args.command == "by-verified":
        rows = verification_rate_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'tag':<16} {'citations':<10} {'verified':<10} {'ver_rate'}")
            for r in rows:
                print(f"{r['tag']:<16} {r['total_citations']:<10} {r['verified']:<10} {r['verification_rate']:.4f}")
    elif args.command == "top-pairs":
        rows = top_tag_citation_pairs(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'tag':<16} {'target_uri':<30} {'count':<8} {'verified'}")
            for r in rows:
                print(f"{r['tag']:<16} {r['target_uri']:<30} {r['pair_count']:<8} {r['verified']}")
    elif args.command == "summary":
        s = correlation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
