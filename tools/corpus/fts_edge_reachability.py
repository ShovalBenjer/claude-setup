#!/usr/bin/env python3
"""FTS edge reachability: how claim edges relate to FTS content.

tag_edge_correlation.py correlates tags with claim_edges.
domain_edge_depth.py correlates domains with claim_edges.
No tool measures how claim edge density relates to FTS word count,
which edge types connect the most searchable content, or which
sources have the highest edge-to-word ratios.

Usage:
    python tools/corpus/fts_edge_reachability.py by-type [--db PATH] [--json]
    python tools/corpus/fts_edge_reachability.py density [--db PATH] [--json]
    python tools/corpus/fts_edge_reachability.py coverage [--db PATH] [--json]
    python tools/corpus/fts_edge_reachability.py summary [--db PATH] [--json]
    python tools/corpus/fts_edge_reachability.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edge_fts_by_type(conn) -> list[dict]:
    """Edge FTS statistics grouped by edge type."""
    rows = conn.execute(
        """
        SELECT e.edge_type,
               COUNT(e.edge_id) AS edge_count,
               COUNT(DISTINCT e.source_chunk) AS source_chunks,
               COUNT(DISTINCT e.target_chunk) AS target_chunks,
               ROUND(AVG(c.word_count), 2) AS avg_source_words
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        GROUP BY e.edge_type
        ORDER BY edge_count DESC, e.edge_type
        """
    ).fetchall()
    return [
        {
            "edge_type": r[0],
            "edge_count": r[1],
            "source_chunks": r[2],
            "target_chunks": r[3],
            "avg_source_words": r[4],
        }
        for r in rows
    ]


def edge_fts_density(conn) -> list[dict]:
    """Edge density per source relative to FTS word count."""
    rows = conn.execute(
        """
        SELECT cw.source_id, s.title,
               cw.total_chunks,
               cw.total_words,
               COALESCE(ec.edge_count, 0) AS edge_count,
               COALESCE(ec.edged_chunks, 0) AS edged_chunks,
               ROUND(
                   COALESCE(ec.edge_count, 0) * 1.0
                   / MAX(cw.total_words, 1) * 1000,
                   4
               ) AS edges_per_1k_words
        FROM (
            SELECT source_id, COUNT(*) AS total_chunks, SUM(word_count) AS total_words
            FROM chunks GROUP BY source_id
        ) cw
        JOIN sources s ON s.source_id = cw.source_id
        LEFT JOIN (
            SELECT source_id, COUNT(DISTINCT edge_id) AS edge_count, COUNT(DISTINCT chunk_id) AS edged_chunks
            FROM (
                SELECT c.source_id, e.edge_id, c.chunk_id
                FROM claim_edges e
                JOIN chunks c ON c.chunk_id = e.source_chunk
                UNION
                SELECT c.source_id, e.edge_id, c.chunk_id
                FROM claim_edges e
                JOIN chunks c ON c.chunk_id = e.target_chunk
            )
            GROUP BY source_id
        ) ec ON ec.source_id = cw.source_id
        ORDER BY edges_per_1k_words DESC, cw.source_id
        """
    ).fetchall()
    return [
        {
            "source_id": r[0],
            "title": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
            "edge_count": r[4],
            "edged_chunks": r[5],
            "edges_per_1k_words": r[6],
        }
        for r in rows
    ]


def edge_fts_coverage(conn) -> list[dict]:
    """Per-chunk edge and FTS statistics for edged chunks."""
    rows = conn.execute(
        """
        SELECT chunk_id, source_id, word_count, status,
               edge_count, as_source, as_target
        FROM (
            SELECT c.chunk_id, c.source_id, c.word_count, c.status,
                   COUNT(DISTINCT e_id) AS edge_count,
                   COUNT(DISTINCT src_id) AS as_source,
                   COUNT(DISTINCT tgt_id) AS as_target
            FROM chunks c
            LEFT JOIN (
                SELECT source_chunk AS chunk_id, edge_id AS e_id, edge_id AS src_id, NULL AS tgt_id
                FROM claim_edges
                UNION ALL
                SELECT target_chunk, edge_id, NULL, edge_id
                FROM claim_edges
            ) edges ON edges.chunk_id = c.chunk_id
            WHERE edges.e_id IS NOT NULL
            GROUP BY c.chunk_id
        )
        ORDER BY edge_count DESC, chunk_id
        """
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "source_id": r[1],
            "word_count": r[2],
            "status": r[3],
            "edge_count": r[4],
            "as_source": r[5],
            "as_target": r[6],
            "searchable": r[3] == "accepted",
        }
        for r in rows
    ]


def fts_edge_summary(conn) -> dict:
    """Aggregate FTS edge reachability statistics."""
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    accepted_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'accepted'"
    ).fetchone()[0]
    total_words = conn.execute("SELECT COALESCE(SUM(word_count), 0) FROM chunks").fetchone()[0]

    total_edges = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]

    edged_chunk_ids = conn.execute(
        """
        SELECT DISTINCT chunk_id FROM (
            SELECT source_chunk AS chunk_id FROM claim_edges
            UNION
            SELECT target_chunk FROM claim_edges
        )
        """
    ).fetchall()
    edged_chunks = len(edged_chunk_ids)

    edged_accepted = conn.execute(
        """
        SELECT COUNT(DISTINCT c.chunk_id)
        FROM chunks c
        WHERE c.status = 'accepted'
          AND c.chunk_id IN (
              SELECT source_chunk FROM claim_edges
              UNION
              SELECT target_chunk FROM claim_edges
          )
        """
    ).fetchone()[0]

    unedged_accepted = accepted_chunks - edged_accepted
    edge_coverage = round(edged_accepted / max(accepted_chunks, 1), 4)
    edges_per_1k = round(total_edges / max(total_words, 1) * 1000, 4)

    return {
        "total_chunks": total_chunks,
        "accepted_chunks": accepted_chunks,
        "total_words": total_words,
        "total_edges": total_edges,
        "edged_chunks": edged_chunks,
        "edged_accepted_chunks": edged_accepted,
        "unedged_accepted_chunks": unedged_accepted,
        "edge_coverage_rate": edge_coverage,
        "edges_per_1k_words": edges_per_1k,
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

        # s1: c1 (20w accepted), c2 (30w accepted), c3 (10w quarantined)
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
        # s2: c4 (50w accepted)
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s2", 1, "h", "claim", None, "t", "t", 50, "abc", 4000, 0, "accepted", None, t1),
        )

        # edges: c1->c2 supports, c1->c3 contradicts
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "semantic", 0.8, t1, None, None),
        )
        conn.commit()

        # 1. by-type: supports has 1 edge
        bt = edge_fts_by_type(conn)
        sup_row = [r for r in bt if r["edge_type"] == "supports"][0]
        assert sup_row["edge_count"] == 1
        ok += 1

        # 2. contradicts has 1 edge
        con_row = [r for r in bt if r["edge_type"] == "contradicts"][0]
        assert con_row["edge_count"] == 1
        ok += 1

        # 3. supports avg_source_words is 20 (c1)
        assert sup_row["avg_source_words"] == 20.0
        ok += 1

        # 4. density: s1 has 2 edges
        dens = edge_fts_density(conn)
        s1_row = [r for r in dens if r["source_id"] == "s1"][0]
        assert s1_row["edge_count"] == 2
        ok += 1

        # 5. s1 total_words is 60
        assert s1_row["total_words"] == 60
        ok += 1

        # 6. s2 has 0 edges
        s2_row = [r for r in dens if r["source_id"] == "s2"][0]
        assert s2_row["edge_count"] == 0
        ok += 1

        # 7. coverage: 3 edged chunks (c1 source, c2 target, c3 target)
        cov = edge_fts_coverage(conn)
        assert len(cov) == 3
        ok += 1

        # 8. c1 has 2 edges (as source for both)
        c1_row = [r for r in cov if r["chunk_id"] == "c1"][0]
        assert c1_row["edge_count"] == 2
        ok += 1

        # 9. c3 is not searchable (quarantined)
        c3_row = [r for r in cov if r["chunk_id"] == "c3"][0]
        assert c3_row["searchable"] is False
        ok += 1

        # 10. summary: edged_accepted is 2 (c1, c2)
        s = fts_edge_summary(conn)
        assert s["edged_accepted_chunks"] == 2
        ok += 1

        # 11. unedged_accepted is 1 (c4)
        assert s["unedged_accepted_chunks"] == 1
        ok += 1

        # 12. edge_coverage_rate = 2/3
        assert s["edge_coverage_rate"] == round(2 / 3, 4)
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["edges_per_1k_words"] == s["edges_per_1k_words"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = fts_edge_summary(conn)
        assert s["total_chunks"] == 0
        assert s["edged_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="FTS edge reachability analysis")
    ap.add_argument("command", choices=["by-type", "density", "coverage", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS fts_edge_reachability selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-type":
        rows = edge_fts_by_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edges found.")
            else:
                print(f"{'edge_type':<16} {'edges':<8} {'src_chunks':<12} {'tgt_chunks':<12} {'avg_src_words'}")
                for r in rows:
                    print(f"{r['edge_type']:<16} {r['edge_count']:<8} {r['source_chunks']:<12} {r['target_chunks']:<12} {r['avg_source_words']:.2f}")
    elif args.command == "density":
        rows = edge_fts_density(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No sources found.")
            else:
                print(f"{'source_id':<14} {'title':<20} {'chunks':<8} {'words':<8} {'edges':<8} {'edged':<7} {'per_1k_words'}")
                for r in rows:
                    print(f"{r['source_id']:<14} {r['title']:<20} {r['total_chunks']:<8} {r['total_words']:<8} {r['edge_count']:<8} {r['edged_chunks']:<7} {r['edges_per_1k_words']:.4f}")
    elif args.command == "coverage":
        rows = edge_fts_coverage(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edged chunks found.")
            else:
                print(f"{'chunk_id':<12} {'source_id':<14} {'words':<8} {'status':<12} {'edges':<8} {'as_src':<8} {'as_tgt':<8} {'searchable'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['source_id']:<14} {r['word_count']:<8} {r['status']:<12} {r['edge_count']:<8} {r['as_source']:<8} {r['as_target']:<8} {r['searchable']}")
    elif args.command == "summary":
        s = fts_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
