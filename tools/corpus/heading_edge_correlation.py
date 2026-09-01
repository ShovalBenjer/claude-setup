#!/usr/bin/env python3
"""Heading edge correlation: how heading paths relate to claim edges.

heading_tag_correlation.py measures heading paths against chunk tags.
heading_domain_correlation.py measures heading paths against domains.
No tool measures which heading paths concentrate which claim edge
types, whether deeper headings produce more contradictions or
supports, or how edge density varies across heading structures.

Usage:
    python tools/corpus/heading_edge_correlation.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_edge_correlation.py by-depth [--db PATH] [--json]
    python tools/corpus/heading_edge_correlation.py diversity [--db PATH] [--json]
    python tools/corpus/heading_edge_correlation.py summary [--db PATH] [--json]
    python tools/corpus/heading_edge_correlation.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_heading(conn) -> list[dict]:
    """Edge distribution per heading path (source chunk heading)."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(e.edge_id) AS total_edges,
               COUNT(DISTINCT e.edge_type) AS distinct_types,
               COUNT(DISTINCT c.chunk_id) AS source_chunks,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        GROUP BY c.heading_path
        ORDER BY total_edges DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "total_edges": r[1],
            "distinct_types": r[2],
            "source_chunks": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def edges_by_heading_depth(conn) -> list[dict]:
    """Edge statistics grouped by heading depth (separator count + 1)."""
    rows = conn.execute(
        """
        SELECT depth,
               COUNT(*) AS total_edges,
               COUNT(DISTINCT edge_type) AS distinct_types,
               COUNT(DISTINCT chunk_id) AS source_chunks,
               ROUND(AVG(confidence), 4) AS avg_confidence
        FROM (
            SELECT e.edge_id, e.edge_type, e.confidence, c.chunk_id,
                   LENGTH(c.heading_path) - LENGTH(REPLACE(c.heading_path, '/', '')) + 1 AS depth
            FROM claim_edges e
            JOIN chunks c ON c.chunk_id = e.source_chunk
            WHERE c.heading_path IS NOT NULL
        )
        GROUP BY depth
        ORDER BY depth
        """
    ).fetchall()
    return [
        {
            "depth": r[0],
            "total_edges": r[1],
            "distinct_types": r[2],
            "source_chunks": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def heading_edge_type_diversity(conn) -> list[dict]:
    """Per-heading edge type diversity: ratio of distinct types to total edges."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT e.edge_type) AS distinct_types,
               COUNT(e.edge_id) AS total_edges,
               COUNT(DISTINCT c.chunk_id) AS source_chunks
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        GROUP BY c.heading_path
        HAVING COUNT(e.edge_id) >= 2
        ORDER BY CAST(COUNT(DISTINCT e.edge_type) AS REAL) / COUNT(e.edge_id), c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_types": r[1],
            "total_edges": r[2],
            "source_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def heading_edge_summary(conn) -> dict:
    """Aggregate heading-edge correlation statistics."""
    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]

    headings_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT c.heading_path)
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        """
    ).fetchone()[0]

    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks WHERE heading_path IS NOT NULL"
    ).fetchone()[0]

    max_depth_row = conn.execute(
        """
        SELECT MAX(LENGTH(c.heading_path) - LENGTH(REPLACE(c.heading_path, '/', '')) + 1)
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        WHERE c.heading_path IS NOT NULL
        """
    ).fetchone()
    max_edge_depth = max_depth_row[0] if max_depth_row[0] is not None else 0

    avg_edges_per_heading = conn.execute(
        """
        SELECT ROUND(AVG(edge_count), 4)
        FROM (
            SELECT c.heading_path, COUNT(e.edge_id) AS edge_count
            FROM claim_edges e
            JOIN chunks c ON c.chunk_id = e.source_chunk
            GROUP BY c.heading_path
        )
        """
    ).fetchone()[0]

    distinct_types = conn.execute(
        "SELECT COUNT(DISTINCT edge_type) FROM claim_edges"
    ).fetchone()[0]

    return {
        "total_edges": total_edges,
        "headings_with_edges": headings_with_edges,
        "total_headings": total_headings,
        "heading_edge_coverage": round(headings_with_edges / max(total_headings, 1), 4),
        "max_edge_depth": max_edge_depth,
        "avg_edges_per_heading": avg_edges_per_heading or 0.0,
        "distinct_edge_types": distinct_types,
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

        # c1: "intro", c2: "intro/details", c3: "methods", c4: "methods" (no edges)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro/details", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 15, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 25, "jkl", 4000, 0, "accepted", None, t1))

        # Edges: intro->methods (supports), intro->intro/details (refines),
        #        intro/details->methods (contradicts), methods->intro (supports)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c3", "supports", "sim", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c2", "refines", "manual", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c2", "c3", "contradicts", "sim", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c3", "c1", "supports", "sim", 0.6, t1, None, None))
        conn.commit()

        # 1. by-heading: "intro" has 2 edges as source (e1, e2)
        bh = edges_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["total_edges"] == 2
        ok += 1

        # 2. "intro" has 2 distinct types (supports, refines)
        assert intro["distinct_types"] == 2
        ok += 1

        # 3. "intro/details" has 1 edge (e3)
        details = [r for r in bh if r["heading_path"] == "intro/details"][0]
        assert details["total_edges"] == 1
        ok += 1

        # 4. "methods" has 1 edge as source (e4)
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["total_edges"] == 1
        ok += 1

        # 5. by-depth: depth 1 has 3 edges (intro=2, methods=1)
        bd = edges_by_heading_depth(conn)
        d1 = [r for r in bd if r["depth"] == 1][0]
        assert d1["total_edges"] == 3
        ok += 1

        # 6. depth 2 has 1 edge (intro/details=1)
        d2 = [r for r in bd if r["depth"] == 2][0]
        assert d2["total_edges"] == 1
        ok += 1

        # 7. diversity: "intro" has 2/2 = 1.0
        div = heading_edge_type_diversity(conn)
        intro_div = [r for r in div if r["heading_path"] == "intro"][0]
        assert intro_div["diversity_ratio"] == 1.0
        ok += 1

        # 8. "intro/details" not in diversity (only 1 edge)
        details_div = [r for r in div if r["heading_path"] == "intro/details"]
        assert len(details_div) == 0
        ok += 1

        # 9. "methods" not in diversity (only 1 edge)
        methods_div = [r for r in div if r["heading_path"] == "methods"]
        assert len(methods_div) == 0
        ok += 1

        # 10. summary: total_edges = 4
        s = heading_edge_summary(conn)
        assert s["total_edges"] == 4
        ok += 1

        # 11. headings_with_edges = 3 (intro, intro/details, methods)
        assert s["headings_with_edges"] == 3
        ok += 1

        # 12. max_edge_depth = 2 (intro/details)
        assert s["max_edge_depth"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["heading_edge_coverage"] == s["heading_edge_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = heading_edge_summary(conn)
        assert s["total_edges"] == 0
        assert s["headings_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading edge correlation analysis")
    ap.add_argument("command", choices=["by-heading", "by-depth", "diversity", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_edge_correlation selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = edges_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading edge data found.")
            else:
                print(f"{'heading_path':<30} {'edges':<8} {'types':<8} {'chunks':<8} {'avg_conf'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['total_edges']:<8} {r['distinct_types']:<8} {r['source_chunks']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "by-depth":
        rows = edges_by_heading_depth(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading edge data found.")
            else:
                print(f"{'depth':<8} {'edges':<8} {'types':<8} {'chunks':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['depth']:<8} {r['total_edges']:<8} {r['distinct_types']:<8} {r['source_chunks']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "diversity":
        rows = heading_edge_type_diversity(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No headings with multiple edge types found.")
            else:
                print(f"{'heading_path':<30} {'types':<8} {'edges':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['distinct_types']:<8} {r['total_edges']:<8} {r['source_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = heading_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
