#!/usr/bin/env python3
"""Source enrichment completeness: how fully each source is enriched.

version_source_profile.py measures revision activity per source.
artifact_domain_distribution.py maps artifacts to domains.
No tool measures how completely each source has been enriched across
all enrichment tables (tags, domains, versions, artifacts, citations,
edges), or which sources have enrichment gaps.

Usage:
    python tools/corpus/source_enrichment_completeness.py by-source [--db PATH] [--json]
    python tools/corpus/source_enrichment_completeness.py by-kind [--db PATH] [--json]
    python tools/corpus/source_enrichment_completeness.py gaps [--db PATH] [--json]
    python tools/corpus/source_enrichment_completeness.py summary [--db PATH] [--json]
    python tools/corpus/source_enrichment_completeness.py selftest
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

_CD_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_domains ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  domain TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  classified_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, domain))"
)

_CV_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_versions ("
    "  version_id TEXT PRIMARY KEY,"
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  version_num INTEGER NOT NULL,"
    "  norm_sha256 TEXT NOT NULL,"
    "  word_count INTEGER NOT NULL,"
    "  snapshot_utc TEXT NOT NULL,"
    "  UNIQUE(chunk_id, version_num))"
)

_ENRICHMENT_TABLES = ["chunk_tags", "chunk_domains", "chunk_versions", "artifacts", "citations", "claim_edges"]


def _ensure_tables(conn):
    conn.execute(_CT_DDL)
    conn.execute(_CD_DDL)
    conn.execute(_CV_DDL)


def completeness_by_source(conn) -> list[dict]:
    """Enrichment completeness per source."""
    _ensure_tables(conn)
    rows = conn.execute(
        """
        SELECT s.source_id, s.title, s.kind,
               COUNT(DISTINCT c.chunk_id) AS total_chunks,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               COUNT(DISTINCT cd.chunk_id) AS classified_chunks,
               COUNT(DISTINCT cv.chunk_id) AS versioned_chunks,
               COUNT(DISTINCT a.chunk_id) AS artifact_chunks,
               COUNT(DISTINCT ci.chunk_id) AS cited_chunks,
               COUNT(DISTINCT CASE WHEN e_src.chunk_id IS NOT NULL
                                    OR e_tgt.chunk_id IS NOT NULL
                                   THEN COALESCE(e_src.chunk_id, e_tgt.chunk_id) END) AS edged_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM chunk_tags) ct ON ct.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM chunk_domains) cd ON cd.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM chunk_versions) cv ON cv.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM artifacts) a ON a.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM citations) ci ON ci.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT source_chunk AS chunk_id FROM claim_edges) e_src ON e_src.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT target_chunk AS chunk_id FROM claim_edges) e_tgt ON e_tgt.chunk_id = c.chunk_id
        GROUP BY s.source_id
        ORDER BY total_chunks DESC, s.source_id
        """
    ).fetchall()
    results = []
    for r in rows:
        total = r[3]
        enriched_counts = [r[4], r[5], r[6], r[7], r[8], r[9]]
        dimensions_hit = sum(1 for x in enriched_counts if x > 0)
        results.append({
            "source_id": r[0],
            "title": r[1],
            "kind": r[2],
            "total_chunks": total,
            "tagged_chunks": r[4],
            "classified_chunks": r[5],
            "versioned_chunks": r[6],
            "artifact_chunks": r[7],
            "cited_chunks": r[8],
            "edged_chunks": r[9],
            "dimensions_hit": dimensions_hit,
            "completeness_score": round(dimensions_hit / 6, 4),
        })
    return results


def completeness_by_kind(conn) -> list[dict]:
    """Enrichment completeness aggregated by source kind."""
    _ensure_tables(conn)
    rows = conn.execute(
        """
        SELECT s.kind,
               COUNT(DISTINCT s.source_id) AS source_count,
               COUNT(DISTINCT c.chunk_id) AS total_chunks,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               COUNT(DISTINCT cd.chunk_id) AS classified_chunks,
               COUNT(DISTINCT cv.chunk_id) AS versioned_chunks,
               COUNT(DISTINCT a.chunk_id) AS artifact_chunks,
               COUNT(DISTINCT ci.chunk_id) AS cited_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM chunk_tags) ct ON ct.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM chunk_domains) cd ON cd.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM chunk_versions) cv ON cv.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM artifacts) a ON a.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM citations) ci ON ci.chunk_id = c.chunk_id
        GROUP BY s.kind
        ORDER BY total_chunks DESC, s.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "source_count": r[1],
            "total_chunks": r[2],
            "tagged_chunks": r[3],
            "classified_chunks": r[4],
            "versioned_chunks": r[5],
            "artifact_chunks": r[6],
            "cited_chunks": r[7],
        }
        for r in rows
    ]


def enrichment_gaps(conn) -> list[dict]:
    """Sources missing one or more enrichment dimensions."""
    by_source = completeness_by_source(conn)
    return [r for r in by_source if r["dimensions_hit"] < 6]


def enrichment_summary(conn) -> dict:
    """Aggregate enrichment completeness statistics."""
    _ensure_tables(conn)
    total_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    tagged = conn.execute("SELECT COUNT(DISTINCT chunk_id) FROM chunk_tags").fetchone()[0]
    classified = conn.execute("SELECT COUNT(DISTINCT chunk_id) FROM chunk_domains").fetchone()[0]
    versioned = conn.execute("SELECT COUNT(DISTINCT chunk_id) FROM chunk_versions").fetchone()[0]
    with_artifacts = conn.execute("SELECT COUNT(DISTINCT chunk_id) FROM artifacts").fetchone()[0]
    with_citations = conn.execute("SELECT COUNT(DISTINCT chunk_id) FROM citations").fetchone()[0]
    with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT chunk_id) FROM (
            SELECT source_chunk AS chunk_id FROM claim_edges
            UNION
            SELECT target_chunk AS chunk_id FROM claim_edges
        )
        """
    ).fetchone()[0]

    by_source = completeness_by_source(conn)
    fully_enriched = sum(1 for r in by_source if r["dimensions_hit"] == 6)
    avg_score = round(
        sum(r["completeness_score"] for r in by_source) / max(len(by_source), 1), 4
    )

    return {
        "total_sources": total_sources,
        "total_chunks": total_chunks,
        "tagged_chunks": tagged,
        "classified_chunks": classified,
        "versioned_chunks": versioned,
        "artifact_chunks": with_artifacts,
        "cited_chunks": with_citations,
        "edged_chunks": with_edges,
        "fully_enriched_sources": fully_enriched,
        "average_completeness_score": avg_score,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        _ensure_tables(conn)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "Full Source", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "Partial Source", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "repo", "Empty Source", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 50, None),
        )

        for i, (cid, sid) in enumerate([
            ("c1", "s1"), ("c2", "s1"),
            ("c3", "s2"), ("c4", "s2"),
            ("c5", "s3"),
        ], 1):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t1),
            )

        # s1 fully enriched: tags, domains, versions, artifacts, citations, edges
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v1", "c1", 1, "sha1", 10, t1))
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a1", "c1", "library", "requests", "2.31", None, 1, None),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit1", "c1", "u://ref1", None, None, None, 0, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None),
        )

        # s2 partial: only tags and citations
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "web", 0.7, t1))
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit2", "c3", "u://ref2", None, None, None, 0, None),
        )

        # s3: no enrichment at all
        conn.commit()

        # 1. s1 has 6 dimensions hit
        bs = completeness_by_source(conn)
        s1_row = [r for r in bs if r["source_id"] == "s1"][0]
        assert s1_row["dimensions_hit"] == 6, f"s1 dims {s1_row['dimensions_hit']}"
        ok += 1

        # 2. s1 completeness_score is 1.0
        assert s1_row["completeness_score"] == 1.0
        ok += 1

        # 3. s2 has 2 dimensions (tags + citations)
        s2_row = [r for r in bs if r["source_id"] == "s2"][0]
        assert s2_row["dimensions_hit"] == 2
        ok += 1

        # 4. s3 has 0 dimensions
        s3_row = [r for r in bs if r["source_id"] == "s3"][0]
        assert s3_row["dimensions_hit"] == 0
        ok += 1

        # 5. s1 tagged_chunks is 1
        assert s1_row["tagged_chunks"] == 1
        ok += 1

        # 6. s1 edged_chunks is 2 (c1 source, c2 target)
        assert s1_row["edged_chunks"] == 2
        ok += 1

        # 7. by-kind: local_md has 4 chunks
        bk = completeness_by_kind(conn)
        lm_row = [r for r in bk if r["kind"] == "local_md"][0]
        assert lm_row["total_chunks"] == 4
        ok += 1

        # 8. by-kind: repo has 0 tagged
        repo_row = [r for r in bk if r["kind"] == "repo"][0]
        assert repo_row["tagged_chunks"] == 0
        ok += 1

        # 9. gaps: s2 and s3 have gaps
        gaps = enrichment_gaps(conn)
        gap_ids = {r["source_id"] for r in gaps}
        assert gap_ids == {"s2", "s3"}
        ok += 1

        # 10. gaps excludes s1
        assert "s1" not in gap_ids
        ok += 1

        # 11. summary: fully_enriched_sources is 1
        s = enrichment_summary(conn)
        assert s["fully_enriched_sources"] == 1
        ok += 1

        # 12. summary: total_sources is 3
        assert s["total_sources"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["average_completeness_score"] == s["average_completeness_score"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = enrichment_summary(conn)
        assert s["total_sources"] == 0
        assert s["fully_enriched_sources"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Source enrichment completeness analysis")
    ap.add_argument("command", choices=["by-source", "by-kind", "gaps", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS source_enrichment_completeness selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-source":
        rows = completeness_by_source(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No sources found.")
            else:
                print(f"{'source_id':<14} {'kind':<12} {'chunks':<7} {'tagged':<7} {'classif':<8} {'versnd':<7} {'artfct':<7} {'cited':<6} {'edged':<6} {'dims':<5} {'score'}")
                for r in rows:
                    print(f"{r['source_id']:<14} {r['kind']:<12} {r['total_chunks']:<7} {r['tagged_chunks']:<7} {r['classified_chunks']:<8} {r['versioned_chunks']:<7} {r['artifact_chunks']:<7} {r['cited_chunks']:<6} {r['edged_chunks']:<6} {r['dimensions_hit']:<5} {r['completeness_score']:.4f}")
    elif args.command == "by-kind":
        rows = completeness_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'kind':<16} {'sources':<10} {'chunks':<8} {'tagged':<8} {'classif':<8} {'versnd':<8} {'artfct':<8} {'cited'}")
            for r in rows:
                print(f"{r['kind']:<16} {r['source_count']:<10} {r['total_chunks']:<8} {r['tagged_chunks']:<8} {r['classified_chunks']:<8} {r['versioned_chunks']:<8} {r['artifact_chunks']:<8} {r['cited_chunks']}")
    elif args.command == "gaps":
        rows = enrichment_gaps(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("All sources fully enriched.")
            else:
                print(f"{'source_id':<14} {'kind':<12} {'dims':<5} {'score':<8} {'missing'}")
                for r in rows:
                    missing = []
                    if r["tagged_chunks"] == 0:
                        missing.append("tags")
                    if r["classified_chunks"] == 0:
                        missing.append("domains")
                    if r["versioned_chunks"] == 0:
                        missing.append("versions")
                    if r["artifact_chunks"] == 0:
                        missing.append("artifacts")
                    if r["cited_chunks"] == 0:
                        missing.append("citations")
                    if r["edged_chunks"] == 0:
                        missing.append("edges")
                    print(f"{r['source_id']:<14} {r['kind']:<12} {r['dimensions_hit']:<5} {r['completeness_score']:<8.4f} {', '.join(missing)}")
    elif args.command == "summary":
        s = enrichment_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
