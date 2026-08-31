#!/usr/bin/env python3
"""Tag edge correlation: how tags correlate with claim_edge density and types.

tag_citation_correlation.py correlates tags with citations.
domain_citation_profile.py correlates domains with citations.
No tool joins chunk_tags with claim_edges to measure which tags
appear on chunks with high edge connectivity, or which edge types
are most common for each tag.

Usage:
    python tools/corpus/tag_edge_correlation.py by-tag [--db PATH] [--json]
    python tools/corpus/tag_edge_correlation.py by-edge-type [--db PATH] [--json]
    python tools/corpus/tag_edge_correlation.py cross [--db PATH] [--json]
    python tools/corpus/tag_edge_correlation.py summary [--db PATH] [--json]
    python tools/corpus/tag_edge_correlation.py selftest
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


def edge_density_by_tag(conn) -> list[dict]:
    """Edge density per tag: edges touching tagged chunks."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               COUNT(DISTINCT e.edge_id) AS total_edges,
               ROUND(
                   COUNT(DISTINCT e.edge_id) * 1.0
                   / MAX(COUNT(DISTINCT ct.chunk_id), 1),
                   4
               ) AS edges_per_chunk
        FROM chunk_tags ct
        LEFT JOIN claim_edges e
          ON e.source_chunk = ct.chunk_id
          OR e.target_chunk = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY edges_per_chunk DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "tagged_chunks": r[1],
            "total_edges": r[2],
            "edges_per_chunk": r[3],
        }
        for r in rows
    ]


def tag_distribution_by_edge_type(conn) -> list[dict]:
    """Tag counts per edge type."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT e.edge_type,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT ct.chunk_id) AS tagged_endpoints
        FROM claim_edges e
        JOIN chunk_tags ct
          ON ct.chunk_id = e.source_chunk
          OR ct.chunk_id = e.target_chunk
        GROUP BY e.edge_type
        ORDER BY edge_count DESC, e.edge_type
        """
    ).fetchall()
    return [
        {
            "edge_type": r[0],
            "distinct_tags": r[1],
            "edge_count": r[2],
            "tagged_endpoints": r[3],
        }
        for r in rows
    ]


def tag_edge_cross(conn) -> list[dict]:
    """Full tag x edge_type cross-tabulation."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.tag, e.edge_type,
               COUNT(DISTINCT e.edge_id) AS count
        FROM chunk_tags ct
        JOIN claim_edges e
          ON e.source_chunk = ct.chunk_id
          OR e.target_chunk = ct.chunk_id
        GROUP BY ct.tag, e.edge_type
        ORDER BY ct.tag, count DESC
        """
    ).fetchall()
    return [
        {"tag": r[0], "edge_type": r[1], "count": r[2]}
        for r in rows
    ]


def tag_edge_summary(conn) -> dict:
    """Aggregate tag-edge correlation statistics."""
    conn.execute(_CT_DDL)
    distinct_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]
    tagged_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_tags"
    ).fetchone()[0]
    tagged_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT ct.chunk_id)
        FROM chunk_tags ct
        JOIN claim_edges e
          ON e.source_chunk = ct.chunk_id
          OR e.target_chunk = ct.chunk_id
        """
    ).fetchone()[0]
    tagged_without = tagged_chunks - tagged_with_edges
    edge_coverage = round(tagged_with_edges / max(tagged_chunks, 1), 4)

    edges_on_tagged = conn.execute(
        """
        SELECT COUNT(DISTINCT e.edge_id)
        FROM chunk_tags ct
        JOIN claim_edges e
          ON e.source_chunk = ct.chunk_id
          OR e.target_chunk = ct.chunk_id
        """
    ).fetchone()[0]
    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]
    tagged_edge_share = round(edges_on_tagged / max(total_edges, 1), 4)

    by_tag = edge_density_by_tag(conn)
    densest = by_tag[0]["tag"] if by_tag and by_tag[0]["total_edges"] > 0 else None

    return {
        "distinct_tags": distinct_tags,
        "tagged_chunks": tagged_chunks,
        "tagged_with_edges": tagged_with_edges,
        "tagged_without_edges": tagged_without,
        "edge_coverage_rate": edge_coverage,
        "edges_on_tagged": edges_on_tagged,
        "tagged_edge_share": tagged_edge_share,
        "densest_tag": densest,
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

        # tags: c1 python+ml, c2 python, c3 ml, c4 web (no edges)
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "python", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "web", 0.5, t1))

        # edges: c1->c2 supports, c1->c3 contradicts, c5->c3 refines (c5 untagged)
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text match", 0.9, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "semantic", 0.8, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c5", "c3", "refines", "detail", 0.7, t1, None, None),
        )
        conn.commit()

        # 1. python has 2 edges (e1 via c1+c2, e2 via c1)
        bd = edge_density_by_tag(conn)
        py_row = [r for r in bd if r["tag"] == "python"][0]
        assert py_row["total_edges"] == 2, f"python edges {py_row['total_edges']}"
        ok += 1

        # 2. ml has 3 edges (e1+e2 via c1, e2+e3 via c3, deduplicated = e1,e2,e3)
        ml_row = [r for r in bd if r["tag"] == "ml"][0]
        assert ml_row["total_edges"] == 3, f"ml edges {ml_row['total_edges']}"
        ok += 1

        # 3. web has 0 edges
        web_row = [r for r in bd if r["tag"] == "web"][0]
        assert web_row["total_edges"] == 0
        ok += 1

        # 4. tag_distribution_by_edge_type: supports has tags
        bt = tag_distribution_by_edge_type(conn)
        sup_row = [r for r in bt if r["edge_type"] == "supports"][0]
        assert sup_row["edge_count"] == 1
        ok += 1

        # 5. contradicts has tags
        con_row = [r for r in bt if r["edge_type"] == "contradicts"][0]
        assert con_row["edge_count"] == 1
        ok += 1

        # 6. refines has 1 tagged endpoint (c3)
        ref_row = [r for r in bt if r["edge_type"] == "refines"][0]
        assert ref_row["tagged_endpoints"] >= 1
        ok += 1

        # 7. cross-tabulation has entries
        cr = tag_edge_cross(conn)
        assert len(cr) >= 1
        ok += 1

        # 8. python/supports in cross
        py_sup = [r for r in cr if r["tag"] == "python" and r["edge_type"] == "supports"]
        assert len(py_sup) == 1 and py_sup[0]["count"] == 1
        ok += 1

        # 9. summary: tagged_with_edges is 3 (c1, c2, c3)
        s = tag_edge_summary(conn)
        assert s["tagged_with_edges"] == 3
        ok += 1

        # 10. tagged_without_edges is 1 (c4)
        assert s["tagged_without_edges"] == 1
        ok += 1

        # 11. edges_on_tagged is 3 (all edges touch at least one tagged chunk)
        assert s["edges_on_tagged"] == 3
        ok += 1

        # 12. tagged_edge_share is 1.0
        assert s["tagged_edge_share"] == 1.0
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["edge_coverage_rate"] == s["edge_coverage_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = tag_edge_summary(conn)
        assert s["distinct_tags"] == 0
        assert s["tagged_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Tag edge correlation analysis")
    ap.add_argument("command", choices=["by-tag", "by-edge-type", "cross", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS tag_edge_correlation selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-tag":
        rows = edge_density_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tagged chunks found.")
            else:
                print(f"{'tag':<16} {'chunks':<8} {'edges':<8} {'edges/chunk'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['tagged_chunks']:<8} {r['total_edges']:<8} {r['edges_per_chunk']:.4f}")
    elif args.command == "by-edge-type":
        rows = tag_distribution_by_edge_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'edge_type':<16} {'tags':<8} {'edges':<8} {'tagged_endpoints'}")
            for r in rows:
                print(f"{r['edge_type']:<16} {r['distinct_tags']:<8} {r['edge_count']:<8} {r['tagged_endpoints']}")
    elif args.command == "cross":
        rows = tag_edge_cross(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'tag':<16} {'edge_type':<16} {'count'}")
            for r in rows:
                print(f"{r['tag']:<16} {r['edge_type']:<16} {r['count']}")
    elif args.command == "summary":
        s = tag_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
