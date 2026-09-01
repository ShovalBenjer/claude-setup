#!/usr/bin/env python3
"""Liveness edge profile: how source liveness relates to claim edges.

liveness_cross_analysis.py cross-tabulates liveness against kind,
publisher, and license. liveness_citation_profile.py correlates
liveness with citations. No tool joins sources.liveness with
claim_edges to measure whether live sources produce more edges than
stale ones, how edge types distribute across liveness states, or
which edges cross liveness boundaries.

Usage:
    python tools/corpus/liveness_edge_profile.py by-liveness [--db PATH] [--json]
    python tools/corpus/liveness_edge_profile.py by-type [--db PATH] [--json]
    python tools/corpus/liveness_edge_profile.py cross-liveness [--db PATH] [--json]
    python tools/corpus/liveness_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/liveness_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_liveness(conn) -> list[dict]:
    """Edge distribution per source liveness state."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               COUNT(e.edge_id) AS total_edges,
               COUNT(DISTINCT e.edge_type) AS distinct_types,
               COUNT(DISTINCT c.chunk_id) AS source_chunks,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.liveness
        ORDER BY total_edges DESC, s.liveness
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "total_edges": r[1],
            "distinct_types": r[2],
            "source_chunks": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def edge_types_by_liveness(conn) -> list[dict]:
    """Edge type distribution per source liveness state."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               e.edge_type,
               COUNT(e.edge_id) AS total,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.liveness, e.edge_type
        ORDER BY s.liveness, total DESC
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "edge_type": r[1],
            "total": r[2],
            "avg_confidence": r[3],
        }
        for r in rows
    ]


def cross_liveness_edges(conn) -> list[dict]:
    """Edges that cross source liveness boundaries."""
    rows = conn.execute(
        """
        SELECT ss.liveness AS source_liveness,
               ts.liveness AS target_liveness,
               e.edge_type,
               COUNT(e.edge_id) AS total,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks sc ON sc.chunk_id = e.source_chunk
        JOIN chunks tc ON tc.chunk_id = e.target_chunk
        JOIN sources ss ON ss.source_id = sc.source_id
        JOIN sources ts ON ts.source_id = tc.source_id
        WHERE ss.liveness IS NOT ts.liveness
        GROUP BY ss.liveness, ts.liveness, e.edge_type
        ORDER BY total DESC, ss.liveness, ts.liveness
        """
    ).fetchall()
    return [
        {
            "source_liveness": r[0],
            "target_liveness": r[1],
            "edge_type": r[2],
            "total": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def liveness_edge_summary(conn) -> dict:
    """Aggregate liveness-edge statistics."""
    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]

    states_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT s.liveness)
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        """
    ).fetchone()[0]

    total_states = conn.execute(
        "SELECT COUNT(DISTINCT liveness) FROM sources"
    ).fetchone()[0]

    cross_liveness_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM claim_edges e
        JOIN chunks sc ON sc.chunk_id = e.source_chunk
        JOIN chunks tc ON tc.chunk_id = e.target_chunk
        JOIN sources ss ON ss.source_id = sc.source_id
        JOIN sources ts ON ts.source_id = tc.source_id
        WHERE ss.liveness IS NOT ts.liveness
        """
    ).fetchone()[0]

    avg_edges_per_state = conn.execute(
        """
        SELECT ROUND(AVG(edge_count), 4)
        FROM (
            SELECT s.liveness, COUNT(e.edge_id) AS edge_count
            FROM claim_edges e
            JOIN chunks c ON c.chunk_id = e.source_chunk
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY s.liveness
        )
        """
    ).fetchone()[0]

    distinct_types = conn.execute(
        "SELECT COUNT(DISTINCT edge_type) FROM claim_edges"
    ).fetchone()[0]

    return {
        "total_edges": total_edges,
        "liveness_states_with_edges": states_with_edges,
        "total_liveness_states": total_states,
        "liveness_edge_coverage": round(states_with_edges / max(total_states, 1), 4),
        "cross_liveness_edges": cross_liveness_count,
        "cross_liveness_rate": round(cross_liveness_count / max(total_edges, 1), 4),
        "avg_edges_per_state": avg_edges_per_state or 0.0,
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "stale", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "archived", "ghi", 150, None),
        )

        # c1: live, c2: live, c3: stale, c4: archived (no edges)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "methods", "claim", None, "t", "t", 15, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "methods", "claim", None, "t", "t", 25, "jkl", 4000, 0, "accepted", None, t1))

        # Edges: live->live (supports), live->stale (contradicts),
        #        stale->live (supports), live->live (refines)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "sim", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "manual", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "supports", "sim", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c2", "c1", "refines", "sim", 0.6, t1, None, None))
        conn.commit()

        # 1. by-liveness: "live" has 3 edges as source (e1, e2, e4)
        bl = edges_by_liveness(conn)
        live = [r for r in bl if r["liveness"] == "live"][0]
        assert live["total_edges"] == 3
        ok += 1

        # 2. "stale" has 1 edge as source (e3)
        stale = [r for r in bl if r["liveness"] == "stale"][0]
        assert stale["total_edges"] == 1
        ok += 1

        # 3. "archived" not in results (no edges)
        archived = [r for r in bl if r["liveness"] == "archived"]
        assert len(archived) == 0
        ok += 1

        # 4. edge_types_by_liveness: live has "supports" with 1
        et = edge_types_by_liveness(conn)
        live_sup = [r for r in et if r["liveness"] == "live" and r["edge_type"] == "supports"]
        assert len(live_sup) == 1 and live_sup[0]["total"] == 1
        ok += 1

        # 5. live has "contradicts" with 1
        live_con = [r for r in et if r["liveness"] == "live" and r["edge_type"] == "contradicts"]
        assert len(live_con) == 1 and live_con[0]["total"] == 1
        ok += 1

        # 6. live has "refines" with 1
        live_ref = [r for r in et if r["liveness"] == "live" and r["edge_type"] == "refines"]
        assert len(live_ref) == 1 and live_ref[0]["total"] == 1
        ok += 1

        # 7. cross-liveness: live->stale (contradicts) = 1
        cl = cross_liveness_edges(conn)
        l2s = [r for r in cl if r["source_liveness"] == "live" and r["target_liveness"] == "stale"]
        assert len(l2s) == 1 and l2s[0]["total"] == 1
        ok += 1

        # 8. cross-liveness: stale->live (supports) = 1
        s2l = [r for r in cl if r["source_liveness"] == "stale" and r["target_liveness"] == "live"]
        assert len(s2l) == 1 and s2l[0]["total"] == 1
        ok += 1

        # 9. total cross-liveness edges = 2
        total_cross = sum(r["total"] for r in cl)
        assert total_cross == 2
        ok += 1

        # 10. summary: total_edges = 4
        s = liveness_edge_summary(conn)
        assert s["total_edges"] == 4
        ok += 1

        # 11. liveness_states_with_edges = 2 (live, stale)
        assert s["liveness_states_with_edges"] == 2
        ok += 1

        # 12. cross_liveness_edges = 2
        assert s["cross_liveness_edges"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cross_liveness_rate"] == s["cross_liveness_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = liveness_edge_summary(conn)
        assert s["total_edges"] == 0
        assert s["liveness_states_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Liveness edge profile analysis")
    ap.add_argument("command", choices=["by-liveness", "by-type", "cross-liveness", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS liveness_edge_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-liveness":
        rows = edges_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness edge data found.")
            else:
                print(f"{'liveness':<12} {'edges':<8} {'types':<8} {'chunks':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['liveness']:<12} {r['total_edges']:<8} {r['distinct_types']:<8} {r['source_chunks']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "by-type":
        rows = edge_types_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness edge type data found.")
            else:
                print(f"{'liveness':<12} {'edge_type':<14} {'total':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['liveness']:<12} {r['edge_type']:<14} {r['total']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "cross-liveness":
        rows = cross_liveness_edges(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cross-liveness edges found.")
            else:
                print(f"{'source':<12} {'target':<12} {'edge_type':<14} {'total':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['source_liveness']:<12} {r['target_liveness']:<12} {r['edge_type']:<14} {r['total']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "summary":
        s = liveness_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
