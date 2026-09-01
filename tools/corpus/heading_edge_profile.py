#!/usr/bin/env python3
"""Heading edge profile: how heading paths distribute across claim edges.

heading_citation_profile.py profiles headings by citation counts.
simhash_edge_profile.py profiles simhash collision groups by claim edges.
No tool cross-tabulates chunks.heading_path with claim_edges to measure
which document sections carry the most claim edges, or how edge types
distribute across heading paths.

Usage:
    python tools/corpus/heading_edge_profile.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_edge_profile.py by-type [--db PATH] [--json]
    python tools/corpus/heading_edge_profile.py concentration [--db PATH] [--json]
    python tools/corpus/heading_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/heading_edge_profile.py selftest
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
    """Edge statistics per heading path."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT c.chunk_id) AS chunks_with_edges,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT e.edge_type) AS edge_types
        FROM chunks c
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        ORDER BY edge_count DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "chunks_with_edges": r[1],
            "edge_count": r[2],
            "edge_types": r[3],
            "edges_per_chunk": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def headings_by_edge_type(conn) -> list[dict]:
    """Heading distribution per edge type."""
    rows = conn.execute(
        """
        SELECT e.edge_type,
               COUNT(DISTINCT c.heading_path) AS distinct_headings,
               COUNT(DISTINCT c.chunk_id) AS chunks_involved,
               COUNT(DISTINCT e.edge_id) AS edge_count
        FROM chunks c
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        GROUP BY e.edge_type
        ORDER BY edge_count DESC, e.edge_type
        """
    ).fetchall()
    return [
        {
            "edge_type": r[0],
            "distinct_headings": r[1],
            "chunks_involved": r[2],
            "edge_count": r[3],
        }
        for r in rows
    ]


def heading_edge_concentration(conn) -> list[dict]:
    """Per-heading edge concentration ordered by edge type diversity."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT c.chunk_id) AS chunks_with_edges,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT e.edge_type) AS edge_types
        FROM chunks c
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        ORDER BY edge_types DESC, edge_count DESC, c.heading_path
        """
    ).fetchall()
    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks"
    ).fetchone()[0]
    return [
        {
            "heading_path": r[0],
            "chunks_with_edges": r[1],
            "edge_count": r[2],
            "edge_types": r[3],
            "type_ratio": round(r[3] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def heading_edge_summary(conn) -> dict:
    """Aggregate heading-edge statistics."""
    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks"
    ).fetchone()[0]

    headings_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT c.heading_path)
        FROM chunks c
        WHERE c.chunk_id IN (
            SELECT source_chunk FROM claim_edges
            UNION
            SELECT target_chunk FROM claim_edges
        )
        """
    ).fetchone()[0]

    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]

    total_edge_types = conn.execute(
        "SELECT COUNT(DISTINCT edge_type) FROM claim_edges"
    ).fetchone()[0]

    multi_type_headings = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.heading_path
            FROM chunks c
            JOIN (
                SELECT source_chunk AS chunk_id, edge_type FROM claim_edges
                UNION ALL
                SELECT target_chunk AS chunk_id, edge_type FROM claim_edges
            ) e ON e.chunk_id = c.chunk_id
            GROUP BY c.heading_path
            HAVING COUNT(DISTINCT e.edge_type) > 1
        )
        """
    ).fetchone()[0]

    return {
        "total_headings": total_headings,
        "headings_with_edges": headings_with_edges,
        "heading_edge_rate": round(headings_with_edges / max(total_headings, 1), 4),
        "total_edges": total_edges,
        "total_edge_types": total_edge_types,
        "multi_type_headings": multi_type_headings,
        "multi_type_rate": round(multi_type_headings / max(headings_with_edges, 1), 4),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        # intro: c1, c2; methods: c3, c4; results: c5 (no edges)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 35, "jkl", 2001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3000, 0, "accepted", None, t1))

        # e1: c1->c2 supports (within intro), e2: c1->c3 contradicts (cross heading)
        # e3: c3->c4 supports (within methods), e4: c3->c2 refines (cross heading)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "supports", "text", 0.85, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c3", "c2", "refines", "text", 0.7, t1, None, None))
        conn.commit()

        # 1. by-heading: intro has 2 chunks with edges (c1, c2)
        bh = edges_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["chunks_with_edges"] == 2
        ok += 1

        # 2. intro has 3 distinct edges (e1, e2, e4)
        assert intro["edge_count"] == 3, f"expected 3, got {intro['edge_count']}"
        ok += 1

        # 3. methods has 3 distinct edges (e2, e3, e4)
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["edge_count"] == 3, f"expected 3, got {methods['edge_count']}"
        ok += 1

        # 4. results has no edges (c5 not in any edge)
        results = [r for r in bh if r["heading_path"] == "results"]
        assert len(results) == 0
        ok += 1

        # 5. by-type: "supports" spans 2 headings (intro, methods)
        bt = headings_by_edge_type(conn)
        supports = [r for r in bt if r["edge_type"] == "supports"][0]
        assert supports["distinct_headings"] == 2
        ok += 1

        # 6. "contradicts" spans 2 headings (intro, methods)
        contradicts = [r for r in bt if r["edge_type"] == "contradicts"][0]
        assert contradicts["distinct_headings"] == 2
        ok += 1

        # 7. "refines" has 2 chunks involved (c3, c2)
        refines = [r for r in bt if r["edge_type"] == "refines"][0]
        assert refines["chunks_involved"] == 2
        ok += 1

        # 8. concentration: intro has 3 edge types (supports, contradicts, refines)
        conc = heading_edge_concentration(conn)
        c_intro = [r for r in conc if r["heading_path"] == "intro"][0]
        assert c_intro["edge_types"] == 3
        ok += 1

        # 9. methods has 3 edge types (supports, contradicts, refines)
        c_methods = [r for r in conc if r["heading_path"] == "methods"][0]
        assert c_methods["edge_types"] == 3
        ok += 1

        # 10. summary: total_headings = 3
        s = heading_edge_summary(conn)
        assert s["total_headings"] == 3
        ok += 1

        # 11. headings_with_edges = 2 (intro, methods; results has no edges)
        assert s["headings_with_edges"] == 2
        ok += 1

        # 12. total_edges = 4
        assert s["total_edges"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_type_rate"] == s["multi_type_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = heading_edge_summary(conn)
        assert s["total_headings"] == 0
        assert s["headings_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading edge profile analysis")
    ap.add_argument("command", choices=["by-heading", "by-type", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_edge_profile selftest ({ok} checks)")
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
                print(f"{'heading':<20} {'chunks':<8} {'edges':<8} {'types':<8} {'edges/chunk'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['chunks_with_edges']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {r['edges_per_chunk']:.4f}")
    elif args.command == "by-type":
        rows = headings_by_edge_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge type data found.")
            else:
                print(f"{'edge_type':<15} {'headings':<10} {'chunks':<8} {'edges'}")
                for r in rows:
                    print(f"{r['edge_type']:<15} {r['distinct_headings']:<10} {r['chunks_involved']:<8} {r['edge_count']}")
    elif args.command == "concentration":
        rows = heading_edge_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading edge data found.")
            else:
                print(f"{'heading':<20} {'chunks':<8} {'edges':<8} {'types':<8} {'type_ratio'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['chunks_with_edges']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {r['type_ratio']:.4f}")
    elif args.command == "summary":
        s = heading_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
