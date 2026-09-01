#!/usr/bin/env python3
"""FTS citation reachability: how well full-text search covers cited content.

tag_citation_correlation.py correlates tags with citations.
domain_citation_profile.py correlates domains with citations.
No tool measures how many cited chunks are searchable through the
FTS index, which citation tags produce the highest-ranked FTS hits,
or how citation density correlates with FTS word count.

Usage:
    python tools/corpus/fts_citation_reachability.py by-tag [--db PATH] [--json]
    python tools/corpus/fts_citation_reachability.py density [--db PATH] [--json]
    python tools/corpus/fts_citation_reachability.py coverage [--db PATH] [--json]
    python tools/corpus/fts_citation_reachability.py summary [--db PATH] [--json]
    python tools/corpus/fts_citation_reachability.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def citation_fts_by_tag(conn) -> list[dict]:
    """Citation FTS statistics grouped by citation tag."""
    rows = conn.execute(
        """
        SELECT ci.tag,
               COUNT(DISTINCT ci.chunk_id) AS cited_chunks,
               COUNT(ci.citation_id) AS citation_count,
               COUNT(CASE WHEN ci.verified = 1 THEN 1 END) AS verified,
               ROUND(AVG(c.word_count), 2) AS avg_chunk_words,
               SUM(c.word_count) AS total_chunk_words
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY ci.tag
        ORDER BY citation_count DESC, ci.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "cited_chunks": r[1],
            "citation_count": r[2],
            "verified": r[3],
            "avg_chunk_words": r[4],
            "total_chunk_words": r[5],
        }
        for r in rows
    ]


def citation_fts_density(conn) -> list[dict]:
    """Citation density relative to FTS word count per source."""
    rows = conn.execute(
        """
        SELECT cw.source_id, s.title,
               cw.total_chunks,
               cw.total_words,
               COALESCE(cc.cited_chunks, 0) AS cited_chunks,
               COALESCE(cc.citation_count, 0) AS citation_count,
               ROUND(
                   COALESCE(cc.citation_count, 0) * 1.0
                   / MAX(cw.total_words, 1) * 1000,
                   4
               ) AS citations_per_1k_words
        FROM (
            SELECT source_id, COUNT(*) AS total_chunks, SUM(word_count) AS total_words
            FROM chunks GROUP BY source_id
        ) cw
        JOIN sources s ON s.source_id = cw.source_id
        LEFT JOIN (
            SELECT c.source_id,
                   COUNT(DISTINCT ci.chunk_id) AS cited_chunks,
                   COUNT(ci.citation_id) AS citation_count
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            GROUP BY c.source_id
        ) cc ON cc.source_id = cw.source_id
        ORDER BY citations_per_1k_words DESC, cw.source_id
        """
    ).fetchall()
    return [
        {
            "source_id": r[0],
            "title": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
            "cited_chunks": r[4],
            "citation_count": r[5],
            "citations_per_1k_words": r[6],
        }
        for r in rows
    ]


def citation_fts_coverage(conn) -> list[dict]:
    """Per-chunk citation and FTS statistics for cited chunks."""
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.source_id, c.word_count, c.status,
               COUNT(ci.citation_id) AS citation_count,
               COUNT(CASE WHEN ci.verified = 1 THEN 1 END) AS verified
        FROM chunks c
        JOIN citations ci ON ci.chunk_id = c.chunk_id
        GROUP BY c.chunk_id
        ORDER BY citation_count DESC, c.chunk_id
        """
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "source_id": r[1],
            "word_count": r[2],
            "status": r[3],
            "citation_count": r[4],
            "verified": r[5],
            "searchable": r[3] == "accepted",
        }
        for r in rows
    ]


def fts_citation_summary(conn) -> dict:
    """Aggregate FTS citation reachability statistics."""
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    accepted_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'accepted'"
    ).fetchone()[0]
    total_words = conn.execute("SELECT COALESCE(SUM(word_count), 0) FROM chunks").fetchone()[0]

    total_citations = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]
    cited_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM citations"
    ).fetchone()[0]
    verified_citations = conn.execute(
        "SELECT COUNT(*) FROM citations WHERE verified = 1"
    ).fetchone()[0]

    cited_accepted = conn.execute(
        """
        SELECT COUNT(DISTINCT ci.chunk_id)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        WHERE c.status = 'accepted'
        """
    ).fetchone()[0]

    uncited_accepted = accepted_chunks - cited_accepted
    citation_coverage = round(cited_accepted / max(accepted_chunks, 1), 4)

    citations_per_1k = round(
        total_citations / max(total_words, 1) * 1000, 4
    )

    return {
        "total_chunks": total_chunks,
        "accepted_chunks": accepted_chunks,
        "total_words": total_words,
        "total_citations": total_citations,
        "cited_chunks": cited_chunks,
        "cited_accepted_chunks": cited_accepted,
        "uncited_accepted_chunks": uncited_accepted,
        "citation_coverage_rate": citation_coverage,
        "verified_citations": verified_citations,
        "citations_per_1k_words": citations_per_1k,
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
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None),
        )

        # s1: c1 (20 words, accepted), c2 (30 words, accepted), c3 (10 words, quarantined)
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "h", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "h", "claim", None, "t", "t", 30, "abc", 2000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "h", "claim", None, "t", "t", 10, "abc", 3000, 0, "quarantined", None, t1),
        )
        # s2: c4 (50 words, accepted)
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s2", 1, "h", "claim", None, "t", "t", 50, "abc", 4000, 0, "accepted", None, t1),
        )

        # Citations: c1 has 2 url citations, c2 has 1 doi (verified), c3 has 1 url, c4 has none
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit1", "c1", "u://ref1", None, "url", None, 0, None),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit2", "c1", "u://ref2", None, "url", None, 0, None),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit3", "c2", "u://ref3", None, "doi", None, 1, t1),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit4", "c3", "u://ref4", None, "url", None, 0, None),
        )
        conn.commit()

        # 1. by-tag url: 2 cited chunks (c1, c3), 3 citations
        bt = citation_fts_by_tag(conn)
        url_row = [r for r in bt if r["tag"] == "url"][0]
        assert url_row["citation_count"] == 3
        ok += 1

        # 2. url cited_chunks is 2
        assert url_row["cited_chunks"] == 2
        ok += 1

        # 3. doi: 1 citation, 1 verified
        doi_row = [r for r in bt if r["tag"] == "doi"][0]
        assert doi_row["verified"] == 1
        ok += 1

        # 4. density: s1 has citations, s2 has none
        dens = citation_fts_density(conn)
        s1_row = [r for r in dens if r["source_id"] == "s1"][0]
        assert s1_row["citation_count"] == 4
        ok += 1

        # 5. s2 has 0 citations
        s2_row = [r for r in dens if r["source_id"] == "s2"][0]
        assert s2_row["citation_count"] == 0
        ok += 1

        # 6. s1 total_words is 60 (20+30+10)
        assert s1_row["total_words"] == 60
        ok += 1

        # 7. coverage: 3 cited chunks (c1, c2, c3)
        cov = citation_fts_coverage(conn)
        assert len(cov) == 3
        ok += 1

        # 8. c1 has 2 citations
        c1_row = [r for r in cov if r["chunk_id"] == "c1"][0]
        assert c1_row["citation_count"] == 2
        ok += 1

        # 9. c3 is not searchable (quarantined)
        c3_row = [r for r in cov if r["chunk_id"] == "c3"][0]
        assert c3_row["searchable"] is False
        ok += 1

        # 10. summary: cited_accepted is 2 (c1, c2)
        s = fts_citation_summary(conn)
        assert s["cited_accepted_chunks"] == 2
        ok += 1

        # 11. uncited_accepted is 1 (c4)
        assert s["uncited_accepted_chunks"] == 1
        ok += 1

        # 12. citation_coverage_rate = 2/3
        assert s["citation_coverage_rate"] == round(2 / 3, 4)
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["citations_per_1k_words"] == s["citations_per_1k_words"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = fts_citation_summary(conn)
        assert s["total_chunks"] == 0
        assert s["cited_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="FTS citation reachability analysis")
    ap.add_argument("command", choices=["by-tag", "density", "coverage", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS fts_citation_reachability selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-tag":
        rows = citation_fts_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No citations found.")
            else:
                print(f"{'tag':<16} {'chunks':<8} {'citations':<10} {'verified':<10} {'avg_words':<10} {'total_words'}")
                for r in rows:
                    t = r["tag"] if r["tag"] is not None else "(none)"
                    print(f"{t:<16} {r['cited_chunks']:<8} {r['citation_count']:<10} {r['verified']:<10} {r['avg_chunk_words']:<10.2f} {r['total_chunk_words']}")
    elif args.command == "density":
        rows = citation_fts_density(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No sources found.")
            else:
                print(f"{'source_id':<14} {'title':<20} {'chunks':<8} {'words':<8} {'cited':<7} {'citations':<10} {'per_1k_words'}")
                for r in rows:
                    print(f"{r['source_id']:<14} {r['title']:<20} {r['total_chunks']:<8} {r['total_words']:<8} {r['cited_chunks']:<7} {r['citation_count']:<10} {r['citations_per_1k_words']:.4f}")
    elif args.command == "coverage":
        rows = citation_fts_coverage(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cited chunks found.")
            else:
                print(f"{'chunk_id':<12} {'source_id':<14} {'words':<8} {'status':<12} {'citations':<10} {'verified':<10} {'searchable'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['source_id']:<14} {r['word_count']:<8} {r['status']:<12} {r['citation_count']:<10} {r['verified']:<10} {r['searchable']}")
    elif args.command == "summary":
        s = fts_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
