#!/usr/bin/env python3
"""Version claim edge cascade: how chunk revisions relate to claim edges.

version_source_profile.py measures revision activity per source.
fts_edge_reachability.py measures edge density relative to word count.
No tool measures whether heavily-revised chunks attract more edges,
how edge types distribute across version depths, or whether edges
connect chunks at similar or different revision counts.

Usage:
    python tools/corpus/version_claim_edge_cascade.py by-depth [--db PATH] [--json]
    python tools/corpus/version_claim_edge_cascade.py edge-type-depth [--db PATH] [--json]
    python tools/corpus/version_claim_edge_cascade.py depth-pairs [--db PATH] [--json]
    python tools/corpus/version_claim_edge_cascade.py summary [--db PATH] [--json]
    python tools/corpus/version_claim_edge_cascade.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_version_depth(conn) -> list[dict]:
    """Edge counts grouped by source chunk version depth."""
    rows = conn.execute(
        """
        SELECT COALESCE(vd.version_depth, 0) AS version_depth,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT e.source_chunk) AS source_chunks
        FROM claim_edges e
        LEFT JOIN (
            SELECT chunk_id, MAX(version_num) AS version_depth
            FROM chunk_versions
            GROUP BY chunk_id
        ) vd ON vd.chunk_id = e.source_chunk
        GROUP BY version_depth
        ORDER BY version_depth
        """
    ).fetchall()
    return [
        {
            "version_depth": r[0],
            "edge_count": r[1],
            "source_chunks": r[2],
        }
        for r in rows
    ]


def edge_type_by_depth(conn) -> list[dict]:
    """Edge type distribution across source chunk version depths."""
    rows = conn.execute(
        """
        SELECT e.edge_type,
               COALESCE(vd.version_depth, 0) AS version_depth,
               COUNT(e.edge_id) AS edge_count,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        LEFT JOIN (
            SELECT chunk_id, MAX(version_num) AS version_depth
            FROM chunk_versions
            GROUP BY chunk_id
        ) vd ON vd.chunk_id = e.source_chunk
        GROUP BY e.edge_type, version_depth
        ORDER BY e.edge_type, version_depth
        """
    ).fetchall()
    return [
        {
            "edge_type": r[0],
            "version_depth": r[1],
            "edge_count": r[2],
            "avg_confidence": r[3],
        }
        for r in rows
    ]


def version_depth_pairs(conn) -> list[dict]:
    """Edge counts by source-target version depth pairs."""
    rows = conn.execute(
        """
        SELECT COALESCE(vs.version_depth, 0) AS source_depth,
               COALESCE(vt.version_depth, 0) AS target_depth,
               COUNT(e.edge_id) AS edge_count,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        LEFT JOIN (
            SELECT chunk_id, MAX(version_num) AS version_depth
            FROM chunk_versions
            GROUP BY chunk_id
        ) vs ON vs.chunk_id = e.source_chunk
        LEFT JOIN (
            SELECT chunk_id, MAX(version_num) AS version_depth
            FROM chunk_versions
            GROUP BY chunk_id
        ) vt ON vt.chunk_id = e.target_chunk
        GROUP BY source_depth, target_depth
        ORDER BY edge_count DESC, source_depth, target_depth
        """
    ).fetchall()
    return [
        {
            "source_depth": r[0],
            "target_depth": r[1],
            "edge_count": r[2],
            "avg_confidence": r[3],
            "same_depth": r[0] == r[1],
        }
        for r in rows
    ]


def version_edge_summary(conn) -> dict:
    """Aggregate version-edge cascade statistics."""
    total_edges = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]

    edges_from_versioned = conn.execute(
        """
        SELECT COUNT(DISTINCT e.edge_id)
        FROM claim_edges e
        JOIN chunk_versions v ON v.chunk_id = e.source_chunk
        """
    ).fetchone()[0]

    edges_from_unversioned = total_edges - edges_from_versioned

    edges_to_versioned = conn.execute(
        """
        SELECT COUNT(DISTINCT e.edge_id)
        FROM claim_edges e
        JOIN chunk_versions v ON v.chunk_id = e.target_chunk
        """
    ).fetchone()[0]

    both_versioned = conn.execute(
        """
        SELECT COUNT(DISTINCT e.edge_id)
        FROM claim_edges e
        JOIN chunk_versions vs ON vs.chunk_id = e.source_chunk
        JOIN chunk_versions vt ON vt.chunk_id = e.target_chunk
        """
    ).fetchone()[0]

    max_depth = conn.execute(
        "SELECT COALESCE(MAX(version_num), 0) FROM chunk_versions"
    ).fetchone()[0]

    avg_source_depth = conn.execute(
        """
        SELECT ROUND(AVG(COALESCE(vd.version_depth, 0)), 4)
        FROM claim_edges e
        LEFT JOIN (
            SELECT chunk_id, MAX(version_num) AS version_depth
            FROM chunk_versions GROUP BY chunk_id
        ) vd ON vd.chunk_id = e.source_chunk
        """
    ).fetchone()[0]

    return {
        "total_edges": total_edges,
        "edges_from_versioned": edges_from_versioned,
        "edges_from_unversioned": edges_from_unversioned,
        "edges_to_versioned": edges_to_versioned,
        "both_versioned": both_versioned,
        "max_version_depth": max_depth,
        "avg_source_version_depth": avg_source_depth or 0.0,
        "versioned_source_rate": round(
            edges_from_versioned / max(total_edges, 1), 4
        ),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_versions (version_id TEXT PRIMARY KEY, chunk_id TEXT NOT NULL, version_num INTEGER NOT NULL, norm_sha256 TEXT NOT NULL, word_count INTEGER NOT NULL, snapshot_utc TEXT NOT NULL, UNIQUE(chunk_id, version_num))")

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1 (3 versions), c2 (1 version), c3 (no versions), c4 (2 versions)
        for cid, wc in [("c1", 20), ("c2", 30), ("c3", 10), ("c4", 40)]:
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "s1", int(cid[1]), "h", "claim", None, "t", "t", wc, "abc", 1000, 0, "accepted", None, t1),
            )

        # Versions: c1 has 3, c2 has 1, c4 has 2
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v1", "c1", 1, "h1", 15, t1))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v2", "c1", 2, "h2", 18, t1))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v3", "c1", 3, "h3", 20, t1))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v4", "c2", 1, "h4", 30, t1))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v5", "c4", 1, "h5", 35, t1))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v6", "c4", 2, "h6", 40, t1))

        # Edges: c1->c2 supports, c1->c3 contradicts, c3->c4 supports, c4->c2 refines
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "semantic", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "supports", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c4", "c2", "refines", "text", 0.85, t1, None, None))
        conn.commit()

        # 1. by-depth: depth 0 (c3 as source) has 1 edge (e3)
        bd = edges_by_version_depth(conn)
        d0 = [r for r in bd if r["version_depth"] == 0][0]
        assert d0["edge_count"] == 1
        ok += 1

        # 2. depth 2 (c4, max version_num=2) has 1 edge (e4)
        d2 = [r for r in bd if r["version_depth"] == 2][0]
        assert d2["edge_count"] == 1
        ok += 1

        # 3. depth 3 (c1, max version_num=3) has 2 edges (e1, e2)
        d3 = [r for r in bd if r["version_depth"] == 3][0]
        assert d3["edge_count"] == 2
        ok += 1

        # 4. edge-type-depth: supports at depth 3 has 1 edge
        etd = edge_type_by_depth(conn)
        sup_d3 = [r for r in etd if r["edge_type"] == "supports" and r["version_depth"] == 3]
        assert len(sup_d3) == 1
        assert sup_d3[0]["edge_count"] == 1
        ok += 1

        # 5. contradicts at depth 3 has 1 edge
        con_d3 = [r for r in etd if r["edge_type"] == "contradicts" and r["version_depth"] == 3]
        assert len(con_d3) == 1
        assert con_d3[0]["edge_count"] == 1
        ok += 1

        # 6. depth-pairs: (3,1) from c1->c2, 1 edge
        dp = version_depth_pairs(conn)
        p31 = [r for r in dp if r["source_depth"] == 3 and r["target_depth"] == 1][0]
        assert p31["edge_count"] == 1
        ok += 1

        # 7. (3,0) from c1->c3, 1 edge, same_depth=False
        p30 = [r for r in dp if r["source_depth"] == 3 and r["target_depth"] == 0][0]
        assert p30["edge_count"] == 1
        assert p30["same_depth"] is False
        ok += 1

        # 8. (0,2) from c3->c4, 1 edge
        p02 = [r for r in dp if r["source_depth"] == 0 and r["target_depth"] == 2][0]
        assert p02["edge_count"] == 1
        ok += 1

        # 9. summary: total_edges = 4
        s = version_edge_summary(conn)
        assert s["total_edges"] == 4
        ok += 1

        # 10. edges_from_versioned = 3 (e1, e2 from c1; e4 from c4)
        assert s["edges_from_versioned"] == 3
        ok += 1

        # 11. edges_from_unversioned = 1 (e3 from c3)
        assert s["edges_from_unversioned"] == 1
        ok += 1

        # 12. both_versioned = 2 (e1: c1->c2, e4: c4->c2)
        assert s["both_versioned"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["versioned_source_rate"] == s["versioned_source_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_versions (version_id TEXT PRIMARY KEY, chunk_id TEXT NOT NULL, version_num INTEGER NOT NULL, norm_sha256 TEXT NOT NULL, word_count INTEGER NOT NULL, snapshot_utc TEXT NOT NULL, UNIQUE(chunk_id, version_num))")
        s = version_edge_summary(conn)
        assert s["total_edges"] == 0
        assert s["edges_from_versioned"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Version claim edge cascade analysis")
    ap.add_argument("command", choices=["by-depth", "edge-type-depth", "depth-pairs", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS version_claim_edge_cascade selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-depth":
        rows = edges_by_version_depth(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edges found.")
            else:
                print(f"{'depth':<8} {'edges':<8} {'src_chunks'}")
                for r in rows:
                    print(f"{r['version_depth']:<8} {r['edge_count']:<8} {r['source_chunks']}")
    elif args.command == "edge-type-depth":
        rows = edge_type_by_depth(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edges found.")
            else:
                print(f"{'edge_type':<16} {'depth':<8} {'edges':<8} {'avg_conf'}")
                for r in rows:
                    conf = f"{r['avg_confidence']:.4f}" if r["avg_confidence"] is not None else "n/a"
                    print(f"{r['edge_type']:<16} {r['version_depth']:<8} {r['edge_count']:<8} {conf}")
    elif args.command == "depth-pairs":
        rows = version_depth_pairs(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edges found.")
            else:
                print(f"{'src_depth':<12} {'tgt_depth':<12} {'edges':<8} {'avg_conf':<10} {'same_depth'}")
                for r in rows:
                    conf = f"{r['avg_confidence']:.4f}" if r["avg_confidence"] is not None else "n/a"
                    print(f"{r['source_depth']:<12} {r['target_depth']:<12} {r['edge_count']:<8} {conf:<10} {r['same_depth']}")
    elif args.command == "summary":
        s = version_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
