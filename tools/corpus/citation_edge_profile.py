#!/usr/bin/env python3
"""Citation edge profile: how citation counts distribute across claim edges.

citation_tag_profile.py profiles citation buckets by chunk tags.
domain_edge_profile.py profiles domains by claim edges.
No tool cross-tabulates chunks.citation_count with claim_edges to measure
whether highly cited chunks carry more claim edges, or how edge types
distribute across citation buckets.

Usage:
    python tools/corpus/citation_edge_profile.py by-bucket [--db PATH] [--json]
    python tools/corpus/citation_edge_profile.py by-type [--db PATH] [--json]
    python tools/corpus/citation_edge_profile.py concentration [--db PATH] [--json]
    python tools/corpus/citation_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/citation_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _cite_bucket(n: int) -> str:
    if n == 0:
        return "0"
    if n <= 5:
        return "1-5"
    if n <= 20:
        return "6-20"
    return "21+"


def edges_by_citation_bucket(conn) -> list[dict]:
    """Edge statistics per citation bucket."""
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.citation_count,
               e.edge_id, e.edge_type
        FROM chunks c
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        """
    ).fetchall()
    buckets: dict[str, dict] = {}
    for chunk_id, cite_count, edge_id, edge_type in rows:
        b = _cite_bucket(cite_count)
        if b not in buckets:
            buckets[b] = {"chunks": set(), "edges": set(), "types": set()}
        buckets[b]["chunks"].add(chunk_id)
        buckets[b]["edges"].add(edge_id)
        buckets[b]["types"].add(edge_type)
    return sorted(
        [
            {
                "bucket": b,
                "chunks_with_edges": len(d["chunks"]),
                "edge_count": len(d["edges"]),
                "edge_types": len(d["types"]),
                "edges_per_chunk": round(len(d["edges"]) / max(len(d["chunks"]), 1), 4),
            }
            for b, d in buckets.items()
        ],
        key=lambda r: r["edge_count"],
        reverse=True,
    )


def citation_buckets_by_edge_type(conn) -> list[dict]:
    """Citation bucket distribution per edge type."""
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.citation_count,
               e.edge_id, e.edge_type
        FROM chunks c
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        """
    ).fetchall()
    types: dict[str, dict] = {}
    for chunk_id, cite_count, edge_id, edge_type in rows:
        b = _cite_bucket(cite_count)
        if edge_type not in types:
            types[edge_type] = {"buckets": set(), "chunks": set(), "edges": set()}
        types[edge_type]["buckets"].add(b)
        types[edge_type]["chunks"].add(chunk_id)
        types[edge_type]["edges"].add(edge_id)
    return sorted(
        [
            {
                "edge_type": t,
                "distinct_buckets": len(d["buckets"]),
                "chunks_involved": len(d["chunks"]),
                "edge_count": len(d["edges"]),
            }
            for t, d in types.items()
        ],
        key=lambda r: r["edge_count"],
        reverse=True,
    )


def citation_edge_concentration(conn) -> list[dict]:
    """Per-bucket edge concentration ordered by edges per chunk."""
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.citation_count,
               e.edge_id, e.edge_type
        FROM chunks c
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        """
    ).fetchall()
    buckets: dict[str, dict] = {}
    for chunk_id, cite_count, edge_id, edge_type in rows:
        b = _cite_bucket(cite_count)
        if b not in buckets:
            buckets[b] = {"chunks": set(), "edges": set(), "types": set(), "total_cites": 0, "cite_chunks": set()}
        buckets[b]["chunks"].add(chunk_id)
        buckets[b]["edges"].add(edge_id)
        buckets[b]["types"].add(edge_type)
        if chunk_id not in buckets[b]["cite_chunks"]:
            buckets[b]["total_cites"] += cite_count
            buckets[b]["cite_chunks"].add(chunk_id)
    return sorted(
        [
            {
                "bucket": b,
                "chunks_with_edges": len(d["chunks"]),
                "edge_count": len(d["edges"]),
                "edge_types": len(d["types"]),
                "edges_per_chunk": round(len(d["edges"]) / max(len(d["chunks"]), 1), 4),
                "total_citations": d["total_cites"],
            }
            for b, d in buckets.items()
        ],
        key=lambda r: r["edges_per_chunk"],
        reverse=True,
    )


def citation_edge_summary(conn) -> dict:
    """Aggregate citation-edge statistics."""
    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    chunks_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT chunk_id) FROM (
            SELECT source_chunk AS chunk_id FROM claim_edges
            UNION
            SELECT target_chunk AS chunk_id FROM claim_edges
        )
        """
    ).fetchone()[0]

    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]

    cited_chunks_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT c.chunk_id)
        FROM chunks c
        WHERE c.citation_count > 0
          AND c.chunk_id IN (
              SELECT source_chunk FROM claim_edges
              UNION
              SELECT target_chunk FROM claim_edges
          )
        """
    ).fetchone()[0]

    cited_chunks_total = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE citation_count > 0"
    ).fetchone()[0]

    total_citations = conn.execute(
        "SELECT COALESCE(SUM(citation_count), 0) FROM chunks"
    ).fetchone()[0]

    return {
        "total_chunks": total_chunks,
        "chunks_with_edges": chunks_with_edges,
        "total_edges": total_edges,
        "cited_chunks_with_edges": cited_chunks_with_edges,
        "cited_chunks_total": cited_chunks_total,
        "cited_edge_rate": round(cited_chunks_with_edges / max(cited_chunks_total, 1), 4),
        "total_citations": total_citations,
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

        # c1 cite=0, c2 cite=3 (bucket 1-5), c3 cite=15 (bucket 6-20), c4 cite=25 (bucket 21+), c5 cite=0 (no edges)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1001, 3, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 15, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "results", "claim", None, "t", "t", 35, "jkl", 3000, 25, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3001, 0, "accepted", None, t1))

        # e1: c1->c2 supports, e2: c2->c3 contradicts, e3: c3->c4 refines
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "contradicts", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "refines", "text", 0.7, t1, None, None))
        conn.commit()

        # 1. by-bucket: bucket "0" has 1 chunk (c1)
        bb = edges_by_citation_bucket(conn)
        b0 = [r for r in bb if r["bucket"] == "0"][0]
        assert b0["chunks_with_edges"] == 1
        ok += 1

        # 2. bucket "1-5" has 1 chunk (c2), 2 edges (e1, e2)
        b15 = [r for r in bb if r["bucket"] == "1-5"][0]
        assert b15["edge_count"] == 2
        ok += 1

        # 3. bucket "6-20" has 1 chunk (c3), 2 edges (e2, e3)
        b620 = [r for r in bb if r["bucket"] == "6-20"][0]
        assert b620["edge_count"] == 2
        ok += 1

        # 4. bucket "21+" has 1 chunk (c4), 1 edge (e3)
        b21 = [r for r in bb if r["bucket"] == "21+"][0]
        assert b21["edge_count"] == 1
        ok += 1

        # 5. by-type: "supports" spans 2 buckets (0, 1-5)
        bt = citation_buckets_by_edge_type(conn)
        supports = [r for r in bt if r["edge_type"] == "supports"][0]
        assert supports["distinct_buckets"] == 2
        ok += 1

        # 6. "contradicts" spans 2 buckets (1-5, 6-20)
        contradicts = [r for r in bt if r["edge_type"] == "contradicts"][0]
        assert contradicts["distinct_buckets"] == 2
        ok += 1

        # 7. "refines" spans 2 buckets (6-20, 21+)
        refines = [r for r in bt if r["edge_type"] == "refines"][0]
        assert refines["distinct_buckets"] == 2
        ok += 1

        # 8. concentration: all buckets have edges_per_chunk >= 1
        conc = citation_edge_concentration(conn)
        for r in conc:
            assert r["edges_per_chunk"] >= 1.0
        ok += 1

        # 9. bucket "1-5" has 2 edges per 1 chunk = 2.0
        c_15 = [r for r in conc if r["bucket"] == "1-5"][0]
        assert c_15["edges_per_chunk"] == 2.0
        ok += 1

        # 10. summary: total_chunks = 5
        s = citation_edge_summary(conn)
        assert s["total_chunks"] == 5
        ok += 1

        # 11. chunks_with_edges = 4 (c1, c2, c3, c4)
        assert s["chunks_with_edges"] == 4
        ok += 1

        # 12. cited_chunks_with_edges = 3 (c2, c3, c4 have citations > 0 and edges)
        assert s["cited_chunks_with_edges"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cited_edge_rate"] == s["cited_edge_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = citation_edge_summary(conn)
        assert s["total_chunks"] == 0
        assert s["chunks_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Citation edge profile analysis")
    ap.add_argument("command", choices=["by-bucket", "by-type", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS citation_edge_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-bucket":
        rows = edges_by_citation_bucket(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No citation edge data found.")
            else:
                print(f"{'bucket':<10} {'chunks':<8} {'edges':<8} {'types':<8} {'edges/chunk'}")
                for r in rows:
                    print(f"{r['bucket']:<10} {r['chunks_with_edges']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {r['edges_per_chunk']:.4f}")
    elif args.command == "by-type":
        rows = citation_buckets_by_edge_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge type data found.")
            else:
                print(f"{'edge_type':<15} {'buckets':<10} {'chunks':<8} {'edges'}")
                for r in rows:
                    print(f"{r['edge_type']:<15} {r['distinct_buckets']:<10} {r['chunks_involved']:<8} {r['edge_count']}")
    elif args.command == "concentration":
        rows = citation_edge_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No citation edge data found.")
            else:
                print(f"{'bucket':<10} {'chunks':<8} {'edges':<8} {'types':<8} {'edges/chunk':<12} {'citations'}")
                for r in rows:
                    print(f"{r['bucket']:<10} {r['chunks_with_edges']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {r['edges_per_chunk']:<12.4f} {r['total_citations']}")
    elif args.command == "summary":
        s = citation_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
