#!/usr/bin/env python3
"""Status edge profile: how chunk status relates to claim edge patterns.

status_enrichment_profile.py profiles statuses by enrichment depth.
status_citation_profile.py profiles statuses by citation patterns.
No tool joins chunks.status with claim_edges to measure whether
accepted chunks produce more edges than quarantined ones, how edge
types distribute across statuses, or which edges cross status
boundaries.

Usage:
    python tools/corpus/status_edge_profile.py by-status [--db PATH] [--json]
    python tools/corpus/status_edge_profile.py by-type [--db PATH] [--json]
    python tools/corpus/status_edge_profile.py cross-status [--db PATH] [--json]
    python tools/corpus/status_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/status_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_status(conn) -> list[dict]:
    """Edge distribution per source chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(e.edge_id) AS total_edges,
               COUNT(DISTINCT e.edge_type) AS distinct_types,
               COUNT(DISTINCT c.chunk_id) AS source_chunks,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        GROUP BY c.status
        ORDER BY total_edges DESC, c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "total_edges": r[1],
            "distinct_types": r[2],
            "source_chunks": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def edge_types_by_status(conn) -> list[dict]:
    """Edge type distribution per source chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               e.edge_type,
               COUNT(e.edge_id) AS total,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        GROUP BY c.status, e.edge_type
        ORDER BY c.status, total DESC
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "edge_type": r[1],
            "total": r[2],
            "avg_confidence": r[3],
        }
        for r in rows
    ]


def cross_status_edges(conn) -> list[dict]:
    """Edges that cross chunk status boundaries."""
    rows = conn.execute(
        """
        SELECT sc.status AS source_status,
               tc.status AS target_status,
               e.edge_type,
               COUNT(e.edge_id) AS total,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks sc ON sc.chunk_id = e.source_chunk
        JOIN chunks tc ON tc.chunk_id = e.target_chunk
        WHERE sc.status IS NOT tc.status
        GROUP BY sc.status, tc.status, e.edge_type
        ORDER BY total DESC, sc.status, tc.status
        """
    ).fetchall()
    return [
        {
            "source_status": r[0],
            "target_status": r[1],
            "edge_type": r[2],
            "total": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def status_edge_summary(conn) -> dict:
    """Aggregate status-edge statistics."""
    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]

    statuses_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT c.status)
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        """
    ).fetchone()[0]

    total_statuses = conn.execute(
        "SELECT COUNT(DISTINCT status) FROM chunks"
    ).fetchone()[0]

    cross_status_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM claim_edges e
        JOIN chunks sc ON sc.chunk_id = e.source_chunk
        JOIN chunks tc ON tc.chunk_id = e.target_chunk
        WHERE sc.status IS NOT tc.status
        """
    ).fetchone()[0]

    avg_edges_per_status = conn.execute(
        """
        SELECT ROUND(AVG(edge_count), 4)
        FROM (
            SELECT c.status, COUNT(e.edge_id) AS edge_count
            FROM claim_edges e
            JOIN chunks c ON c.chunk_id = e.source_chunk
            GROUP BY c.status
        )
        """
    ).fetchone()[0]

    distinct_types = conn.execute(
        "SELECT COUNT(DISTINCT edge_type) FROM claim_edges"
    ).fetchone()[0]

    return {
        "total_edges": total_edges,
        "statuses_with_edges": statuses_with_edges,
        "total_statuses": total_statuses,
        "status_edge_coverage": round(statuses_with_edges / max(total_statuses, 1), 4),
        "cross_status_edges": cross_status_count,
        "cross_status_rate": round(cross_status_count / max(total_edges, 1), 4),
        "avg_edges_per_status": avg_edges_per_status or 0.0,
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

        # c1: accepted, c2: accepted, c3: quarantined, c4: rejected (no edges)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 15, "ghi", 3000, 0, "quarantined", "low quality", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 25, "jkl", 4000, 0, "rejected", "duplicate", t1))

        # Edges: accepted->accepted (supports), accepted->quarantined (contradicts),
        #        quarantined->accepted (supports), accepted->accepted (refines)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "sim", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "manual", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "supports", "sim", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c2", "c1", "refines", "sim", 0.6, t1, None, None))
        conn.commit()

        # 1. by-status: "accepted" has 3 edges as source (e1, e2, e4)
        bs = edges_by_status(conn)
        accepted = [r for r in bs if r["status"] == "accepted"][0]
        assert accepted["total_edges"] == 3
        ok += 1

        # 2. "quarantined" has 1 edge as source (e3)
        quarantined = [r for r in bs if r["status"] == "quarantined"][0]
        assert quarantined["total_edges"] == 1
        ok += 1

        # 3. "rejected" not in results (no edges)
        rejected = [r for r in bs if r["status"] == "rejected"]
        assert len(rejected) == 0
        ok += 1

        # 4. edge_types_by_status: accepted has "supports" with 1
        et = edge_types_by_status(conn)
        acc_sup = [r for r in et if r["status"] == "accepted" and r["edge_type"] == "supports"]
        assert len(acc_sup) == 1 and acc_sup[0]["total"] == 1
        ok += 1

        # 5. accepted has "contradicts" with 1
        acc_con = [r for r in et if r["status"] == "accepted" and r["edge_type"] == "contradicts"]
        assert len(acc_con) == 1 and acc_con[0]["total"] == 1
        ok += 1

        # 6. accepted has "refines" with 1
        acc_ref = [r for r in et if r["status"] == "accepted" and r["edge_type"] == "refines"]
        assert len(acc_ref) == 1 and acc_ref[0]["total"] == 1
        ok += 1

        # 7. cross-status: accepted->quarantined (contradicts) = 1
        cs = cross_status_edges(conn)
        a2q = [r for r in cs if r["source_status"] == "accepted" and r["target_status"] == "quarantined"]
        assert len(a2q) == 1 and a2q[0]["total"] == 1
        ok += 1

        # 8. cross-status: quarantined->accepted (supports) = 1
        q2a = [r for r in cs if r["source_status"] == "quarantined" and r["target_status"] == "accepted"]
        assert len(q2a) == 1 and q2a[0]["total"] == 1
        ok += 1

        # 9. total cross-status edges = 2
        total_cross = sum(r["total"] for r in cs)
        assert total_cross == 2
        ok += 1

        # 10. summary: total_edges = 4
        s = status_edge_summary(conn)
        assert s["total_edges"] == 4
        ok += 1

        # 11. statuses_with_edges = 2 (accepted, quarantined)
        assert s["statuses_with_edges"] == 2
        ok += 1

        # 12. cross_status_edges = 2
        assert s["cross_status_edges"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cross_status_rate"] == s["cross_status_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = status_edge_summary(conn)
        assert s["total_edges"] == 0
        assert s["statuses_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Status edge profile analysis")
    ap.add_argument("command", choices=["by-status", "by-type", "cross-status", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS status_edge_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-status":
        rows = edges_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status edge data found.")
            else:
                print(f"{'status':<14} {'edges':<8} {'types':<8} {'chunks':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['total_edges']:<8} {r['distinct_types']:<8} {r['source_chunks']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "by-type":
        rows = edge_types_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status edge type data found.")
            else:
                print(f"{'status':<14} {'edge_type':<14} {'total':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['edge_type']:<14} {r['total']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "cross-status":
        rows = cross_status_edges(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cross-status edges found.")
            else:
                print(f"{'source':<14} {'target':<14} {'edge_type':<14} {'total':<8} {'avg_conf'}")
                for r in rows:
                    print(f"{r['source_status']:<14} {r['target_status']:<14} {r['edge_type']:<14} {r['total']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "summary":
        s = status_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
