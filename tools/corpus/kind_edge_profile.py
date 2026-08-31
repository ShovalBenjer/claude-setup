#!/usr/bin/env python3
"""Kind edge profile: how chunk kinds relate to claim edge patterns.

chunk_kind_profile.py profiles kinds per source.
kind_citation_profile.py profiles kinds by citation patterns.
No tool joins chunks.kind with claim_edges to measure which chunk
kinds produce the most edges, how edge types distribute across kinds,
or which edges cross kind boundaries.

Usage:
    python tools/corpus/kind_edge_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/kind_edge_profile.py by-type [--db PATH] [--json]
    python tools/corpus/kind_edge_profile.py cross-kind [--db PATH] [--json]
    python tools/corpus/kind_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/kind_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_kind(conn) -> list[dict]:
    """Edge distribution per source chunk kind."""
    rows = conn.execute(
        """
        SELECT c.kind,
               COUNT(e.edge_id) AS total_edges,
               COUNT(DISTINCT e.edge_type) AS distinct_types,
               COUNT(DISTINCT c.chunk_id) AS source_chunks,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        GROUP BY c.kind
        ORDER BY total_edges DESC, c.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "total_edges": r[1],
            "distinct_types": r[2],
            "source_chunks": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def edge_types_by_kind(conn) -> list[dict]:
    """Edge type distribution per source chunk kind."""
    rows = conn.execute(
        """
        SELECT c.kind,
               e.edge_type,
               COUNT(e.edge_id) AS total,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        GROUP BY c.kind, e.edge_type
        ORDER BY c.kind, total DESC
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "edge_type": r[1],
            "total": r[2],
            "avg_confidence": r[3],
        }
        for r in rows
    ]


def cross_kind_edges(conn) -> list[dict]:
    """Edges that cross chunk kind boundaries."""
    rows = conn.execute(
        """
        SELECT sc.kind AS source_kind,
               tc.kind AS target_kind,
               e.edge_type,
               COUNT(e.edge_id) AS total,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks sc ON sc.chunk_id = e.source_chunk
        JOIN chunks tc ON tc.chunk_id = e.target_chunk
        WHERE sc.kind IS NOT tc.kind
        GROUP BY sc.kind, tc.kind, e.edge_type
        ORDER BY total DESC, sc.kind, tc.kind
        """
    ).fetchall()
    return [
        {
            "source_kind": r[0],
            "target_kind": r[1],
            "edge_type": r[2],
            "total": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def kind_edge_summary(conn) -> dict:
    """Aggregate kind-edge statistics."""
    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]

    kinds_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT c.kind)
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        """
    ).fetchone()[0]

    total_kinds = conn.execute(
        "SELECT COUNT(DISTINCT kind) FROM chunks"
    ).fetchone()[0]

    cross_kind_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM claim_edges e
        JOIN chunks sc ON sc.chunk_id = e.source_chunk
        JOIN chunks tc ON tc.chunk_id = e.target_chunk
        WHERE sc.kind IS NOT tc.kind
        """
    ).fetchone()[0]

    avg_edges_per_kind = conn.execute(
        """
        SELECT ROUND(AVG(edge_count), 4)
        FROM (
            SELECT c.kind, COUNT(e.edge_id) AS edge_count
            FROM claim_edges e
            JOIN chunks c ON c.chunk_id = e.source_chunk
            GROUP BY c.kind
        )
        """
    ).fetchone()[0]

    distinct_types = conn.execute(
        "SELECT COUNT(DISTINCT edge_type) FROM claim_edges"
    ).fetchone()[0]

    return {
        "total_edges": total_edges,
        "kinds_with_edges": kinds_with_edges,
        "total_kinds": total_kinds,
        "kind_edge_coverage": round(kinds_with_edges / max(total_kinds, 1), 4),
        "cross_kind_edges": cross_kind_count,
        "cross_kind_rate": round(cross_kind_count / max(total_edges, 1), 4),
        "avg_edges_per_kind": avg_edges_per_kind or 0.0,
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

        # c1: claim, c2: claim, c3: code, c4: prose (no edges)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "code", None, "t", "t", 15, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "prose", None, "t", "t", 25, "jkl", 4000, 0, "accepted", None, t1))

        # Edges: claim->claim (supports), claim->code (contradicts),
        #        code->claim (supports), claim->claim (refines)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "sim", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "manual", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "supports", "sim", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c2", "c1", "refines", "sim", 0.6, t1, None, None))
        conn.commit()

        # 1. by-kind: "claim" has 3 edges as source (e1, e2, e4)
        bk = edges_by_kind(conn)
        claim = [r for r in bk if r["kind"] == "claim"][0]
        assert claim["total_edges"] == 3
        ok += 1

        # 2. "code" has 1 edge as source (e3)
        code = [r for r in bk if r["kind"] == "code"][0]
        assert code["total_edges"] == 1
        ok += 1

        # 3. "prose" not in results (no edges)
        prose = [r for r in bk if r["kind"] == "prose"]
        assert len(prose) == 0
        ok += 1

        # 4. edge_types_by_kind: claim has "supports" with 1
        et = edge_types_by_kind(conn)
        claim_sup = [r for r in et if r["kind"] == "claim" and r["edge_type"] == "supports"]
        assert len(claim_sup) == 1 and claim_sup[0]["total"] == 1
        ok += 1

        # 5. claim has "contradicts" with 1
        claim_con = [r for r in et if r["kind"] == "claim" and r["edge_type"] == "contradicts"]
        assert len(claim_con) == 1 and claim_con[0]["total"] == 1
        ok += 1

        # 6. claim has "refines" with 1
        claim_ref = [r for r in et if r["kind"] == "claim" and r["edge_type"] == "refines"]
        assert len(claim_ref) == 1 and claim_ref[0]["total"] == 1
        ok += 1

        # 7. cross-kind: claim->code (contradicts) = 1
        ck = cross_kind_edges(conn)
        c2c = [r for r in ck if r["source_kind"] == "claim" and r["target_kind"] == "code"]
        assert len(c2c) == 1 and c2c[0]["total"] == 1
        ok += 1

        # 8. cross-kind: code->claim (supports) = 1
        c2cl = [r for r in ck if r["source_kind"] == "code" and r["target_kind"] == "claim"]
        assert len(c2cl) == 1 and c2cl[0]["total"] == 1
        ok += 1

        # 9. total cross-kind edges = 2 (e2: claim->code, e3: code->claim)
        total_cross = sum(r["total"] for r in ck)
        assert total_cross == 2
        ok += 1

        # 10. summary: total_edges = 4
        s = kind_edge_summary(conn)
        assert s["total_edges"] == 4
        ok += 1

        # 11. kinds_with_edges = 2 (claim, code)
        assert s["kinds_with_edges"] == 2
        ok += 1

        # 12. cross_kind_edges = 2
        assert s["cross_kind_edges"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cross_kind_rate"] == s["cross_kind_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = kind_edge_summary(conn)
        assert s["total_edges"] == 0
        assert s["kinds_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Kind edge profile analysis")
    ap.add_argument("command", choices=["by-kind", "by-type", "cross-kind", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS kind_edge_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-kind":
        rows = edges_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind edge data found.")
            else:
                print(f"{'kind':<12} {'edges':<8} {'types':<8} {'chunks':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['kind']:<12} {r['total_edges']:<8} {r['distinct_types']:<8} {r['source_chunks']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "by-type":
        rows = edge_types_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind edge type data found.")
            else:
                print(f"{'kind':<12} {'edge_type':<14} {'total':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['kind']:<12} {r['edge_type']:<14} {r['total']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "cross-kind":
        rows = cross_kind_edges(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cross-kind edges found.")
            else:
                print(f"{'source_kind':<14} {'target_kind':<14} {'edge_type':<14} {'total':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['source_kind']:<14} {r['target_kind']:<14} {r['edge_type']:<14} {r['total']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "summary":
        s = kind_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
