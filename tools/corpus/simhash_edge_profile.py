#!/usr/bin/env python3
"""Simhash edge profile: structural similarity and claim edge patterns.

simhash_distribution.py measures hash-space density and collisions.
edge_density.py measures edge counts per chunk.
No tool joins simhash proximity with claim_edges to detect whether
structurally similar chunks share edge patterns, whether high-edge
chunks cluster in simhash space, or how edge types distribute across
simhash collision groups.

Usage:
    python tools/corpus/simhash_edge_profile.py by-collision [--db PATH] [--json]
    python tools/corpus/simhash_edge_profile.py edge-density [--db PATH] [--json]
    python tools/corpus/simhash_edge_profile.py type-by-group [--db PATH] [--json]
    python tools/corpus/simhash_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/simhash_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def edges_by_collision_group(conn) -> list[dict]:
    """Edge statistics for chunks sharing the same simhash (collision groups)."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT c.chunk_id) AS group_size,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT e.edge_type) AS edge_types
        FROM chunks c
        LEFT JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        WHERE c.simhash IS NOT NULL
        GROUP BY c.simhash
        HAVING COUNT(DISTINCT c.chunk_id) >= 2
        ORDER BY edge_count DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "group_size": r[1],
            "edge_count": r[2],
            "edge_types": r[3],
            "edges_per_chunk": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def simhash_edge_density(conn) -> list[dict]:
    """Per-chunk edge count with simhash, showing whether high-edge chunks cluster."""
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.simhash, c.source_id,
               COUNT(DISTINCT e.edge_id) AS edge_count
        FROM chunks c
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        WHERE c.simhash IS NOT NULL
        GROUP BY c.chunk_id
        ORDER BY edge_count DESC, c.chunk_id
        """
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "simhash": r[1],
            "source_id": r[2],
            "edge_count": r[3],
        }
        for r in rows
    ]


def edge_type_by_collision_group(conn) -> list[dict]:
    """Edge type distribution within simhash collision groups."""
    rows = conn.execute(
        """
        SELECT c.simhash, e.edge_type,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT c.chunk_id) AS chunks_involved
        FROM chunks c
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        WHERE c.simhash IS NOT NULL
          AND c.simhash IN (
              SELECT simhash FROM chunks
              WHERE simhash IS NOT NULL
              GROUP BY simhash HAVING COUNT(*) >= 2
          )
        GROUP BY c.simhash, e.edge_type
        ORDER BY c.simhash, edge_count DESC
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "edge_type": r[1],
            "edge_count": r[2],
            "chunks_involved": r[3],
        }
        for r in rows
    ]


def simhash_edge_summary(conn) -> dict:
    """Aggregate simhash-edge statistics."""
    total_with_simhash = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE simhash IS NOT NULL"
    ).fetchone()[0]

    total_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT chunk_id) FROM (
            SELECT source_chunk AS chunk_id FROM claim_edges
            UNION
            SELECT target_chunk AS chunk_id FROM claim_edges
        )
        """
    ).fetchone()[0]

    both = conn.execute(
        """
        SELECT COUNT(DISTINCT c.chunk_id)
        FROM chunks c
        WHERE c.simhash IS NOT NULL
          AND c.chunk_id IN (
              SELECT source_chunk FROM claim_edges
              UNION
              SELECT target_chunk FROM claim_edges
          )
        """
    ).fetchone()[0]

    collision_groups = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT simhash FROM chunks
            WHERE simhash IS NOT NULL
            GROUP BY simhash HAVING COUNT(*) >= 2
        )
        """
    ).fetchone()[0]

    collision_chunks_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT c.chunk_id)
        FROM chunks c
        WHERE c.simhash IS NOT NULL
          AND c.simhash IN (
              SELECT simhash FROM chunks
              WHERE simhash IS NOT NULL
              GROUP BY simhash HAVING COUNT(*) >= 2
          )
          AND c.chunk_id IN (
              SELECT source_chunk FROM claim_edges
              UNION
              SELECT target_chunk FROM claim_edges
          )
        """
    ).fetchone()[0]

    collision_chunks_total = conn.execute(
        """
        SELECT COUNT(*)
        FROM chunks c
        WHERE c.simhash IS NOT NULL
          AND c.simhash IN (
              SELECT simhash FROM chunks
              WHERE simhash IS NOT NULL
              GROUP BY simhash HAVING COUNT(*) >= 2
          )
        """
    ).fetchone()[0]

    return {
        "total_with_simhash": total_with_simhash,
        "total_with_edges": total_with_edges,
        "simhash_and_edges": both,
        "simhash_edge_rate": round(both / max(total_with_simhash, 1), 4),
        "collision_groups": collision_groups,
        "collision_chunks_total": collision_chunks_total,
        "collision_chunks_with_edges": collision_chunks_with_edges,
        "collision_edge_rate": round(collision_chunks_with_edges / max(collision_chunks_total, 1), 4),
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

        # c1,c2 share simhash 1000; c3,c4 share simhash 2000; c5 unique simhash 3000; c6 unique 4000 (no edges)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 25, "def", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "results", "claim", None, "t", "t", 30, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "discuss", "claim", None, "t", "t", 35, "jkl", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "concl", "claim", None, "t", "t", 15, "mno", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "s1", 6, "appendix", "claim", None, "t", "t", 10, "pqr", 4000, 0, "accepted", None, t1))

        # Edges: e1 c1->c2 (same simhash group), e2 c1->c3 (cross group), e3 c3->c4 (same group), e4 c5->c3
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "supports", "text", 0.85, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c5", "c3", "refines", "text", 0.7, t1, None, None))
        conn.commit()

        # 1. by-collision: simhash 1000 group has 2 chunks
        bcg = edges_by_collision_group(conn)
        g1000 = [r for r in bcg if r["simhash"] == 1000][0]
        assert g1000["group_size"] == 2
        ok += 1

        # 2. simhash 1000 group: c1 participates in e1,e2; c2 in e1 -> 2 distinct edges
        assert g1000["edge_count"] == 2, f"expected 2, got {g1000['edge_count']}"
        ok += 1

        # 3. simhash 2000 group: c3 in e2,e3,e4; c4 in e3 -> 3 distinct edges
        g2000 = [r for r in bcg if r["simhash"] == 2000][0]
        assert g2000["edge_count"] == 3, f"expected 3, got {g2000['edge_count']}"
        ok += 1

        # 4. edge-density: c1 has 2 edges (e1, e2), c3 has 3 edges (e2, e3, e4)
        ed = simhash_edge_density(conn)
        c1_ed = [r for r in ed if r["chunk_id"] == "c1"][0]
        assert c1_ed["edge_count"] == 2
        ok += 1

        # 5. c3 has 3 edges
        c3_ed = [r for r in ed if r["chunk_id"] == "c3"][0]
        assert c3_ed["edge_count"] == 3
        ok += 1

        # 6. c6 (no edges) not in edge-density results
        c6_ed = [r for r in ed if r["chunk_id"] == "c6"]
        assert len(c6_ed) == 0
        ok += 1

        # 7. type-by-group: simhash 1000 has supports (e1) and contradicts (e2)
        tbg = edge_type_by_collision_group(conn)
        g1000_types = [r for r in tbg if r["simhash"] == 1000]
        g1000_type_set = {r["edge_type"] for r in g1000_types}
        assert "supports" in g1000_type_set
        ok += 1

        # 8. simhash 1000 also has contradicts
        assert "contradicts" in g1000_type_set
        ok += 1

        # 9. simhash 2000 has supports, contradicts, refines
        g2000_types = [r for r in tbg if r["simhash"] == 2000]
        g2000_type_set = {r["edge_type"] for r in g2000_types}
        assert len(g2000_type_set) == 3
        ok += 1

        # 10. summary: total_with_simhash = 6
        s = simhash_edge_summary(conn)
        assert s["total_with_simhash"] == 6
        ok += 1

        # 11. collision_groups = 2 (simhash 1000 and 2000)
        assert s["collision_groups"] == 2
        ok += 1

        # 12. collision_chunks_total = 4 (c1,c2,c3,c4)
        assert s["collision_chunks_total"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["simhash_edge_rate"] == s["simhash_edge_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = simhash_edge_summary(conn)
        assert s["total_with_simhash"] == 0
        assert s["collision_groups"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Simhash edge profile analysis")
    ap.add_argument("command", choices=["by-collision", "edge-density", "type-by-group", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS simhash_edge_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-collision":
        rows = edges_by_collision_group(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<12} {'size':<6} {'edges':<8} {'types':<8} {'edges/chunk'}")
                for r in rows:
                    print(f"{r['simhash']:<12} {r['group_size']:<6} {r['edge_count']:<8} {r['edge_types']:<8} {r['edges_per_chunk']:.4f}")
    elif args.command == "edge-density":
        rows = simhash_edge_density(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No chunks with both simhash and edges found.")
            else:
                print(f"{'chunk_id':<12} {'simhash':<12} {'source':<10} {'edges'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['simhash']:<12} {r['source_id']:<10} {r['edge_count']}")
    elif args.command == "type-by-group":
        rows = edge_type_by_collision_group(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge types in collision groups found.")
            else:
                print(f"{'simhash':<12} {'edge_type':<15} {'edges':<8} {'chunks'}")
                for r in rows:
                    print(f"{r['simhash']:<12} {r['edge_type']:<15} {r['edge_count']:<8} {r['chunks_involved']}")
    elif args.command == "summary":
        s = simhash_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
