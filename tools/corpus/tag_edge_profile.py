#!/usr/bin/env python3
"""Tag edge profile: how chunk tags distribute across claim edges.

tag_domain_profile.py profiles tags by semantic domains.
license_edge_profile.py profiles licenses by claim edges.
No tool cross-tabulates chunk_tags.tag with claim_edges to measure
which tags carry the most claim edges, or how edge types distribute
across tags.

Usage:
    python tools/corpus/tag_edge_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/tag_edge_profile.py by-type [--db PATH] [--json]
    python tools/corpus/tag_edge_profile.py concentration [--db PATH] [--json]
    python tools/corpus/tag_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/tag_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_tag(conn) -> list[dict]:
    """Edge statistics per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks_with_edges,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT e.edge_type) AS edge_types
        FROM chunk_tags ct
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY edge_count DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "tagged_chunks_with_edges": r[1],
            "edge_count": r[2],
            "edge_types": r[3],
            "edges_per_chunk": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def tags_by_edge_type(conn) -> list[dict]:
    """Tag distribution per edge type."""
    rows = conn.execute(
        """
        SELECT e.edge_type,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               COUNT(DISTINCT e.edge_id) AS edge_count
        FROM chunk_tags ct
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = ct.chunk_id
        GROUP BY e.edge_type
        ORDER BY edge_count DESC, e.edge_type
        """
    ).fetchall()
    return [
        {
            "edge_type": r[0],
            "distinct_tags": r[1],
            "tagged_chunks": r[2],
            "edge_count": r[3],
        }
        for r in rows
    ]


def tag_edge_concentration(conn) -> list[dict]:
    """Per-tag edge concentration ordered by edge type diversity."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks_with_edges,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT e.edge_type) AS edge_types
        FROM chunk_tags ct
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY edge_types DESC, edge_count DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "tagged_chunks_with_edges": r[1],
            "edge_count": r[2],
            "edge_types": r[3],
            "type_ratio": round(r[3] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def tag_edge_summary(conn) -> dict:
    """Aggregate tag-edge statistics."""
    total_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]

    tags_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT ct.tag)
        FROM chunk_tags ct
        WHERE ct.chunk_id IN (
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

    multi_type_tags = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT ct.tag
            FROM chunk_tags ct
            JOIN (
                SELECT source_chunk AS chunk_id, edge_type FROM claim_edges
                UNION ALL
                SELECT target_chunk AS chunk_id, edge_type FROM claim_edges
            ) e ON e.chunk_id = ct.chunk_id
            GROUP BY ct.tag
            HAVING COUNT(DISTINCT e.edge_type) > 1
        )
        """
    ).fetchone()[0]

    return {
        "total_tags": total_tags,
        "tags_with_edges": tags_with_edges,
        "tag_edge_rate": round(tags_with_edges / max(total_tags, 1), 4),
        "total_edges": total_edges,
        "total_edge_types": total_edge_types,
        "multi_type_tags": multi_type_tags,
        "multi_type_rate": round(multi_type_tags / max(tags_with_edges, 1), 4),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")

        t1 = "2026-01-01T00:00:00Z"
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        # c1: tags(python, ml); c2: tags(python); c3: tags(ml); c4: tags(web) no edges; c5: no tags
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "results", "claim", None, "t", "t", 35, "jkl", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3001, 0, "accepted", None, t1))

        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "python", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "web", 0.5, t1))

        # e1: c1->c2 supports, e2: c1->c3 contradicts, e3: c3->c2 refines
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c2", "refines", "text", 0.7, t1, None, None))
        conn.commit()

        # 1. by-tag: "python" has 2 tagged chunks with edges (c1, c2)
        bt = edges_by_tag(conn)
        python = [r for r in bt if r["tag"] == "python"][0]
        assert python["tagged_chunks_with_edges"] == 2
        ok += 1

        # 2. "python" has 3 edges (e1, e2, e3 via c1 and c2)
        assert python["edge_count"] == 3, f"expected 3, got {python['edge_count']}"
        ok += 1

        # 3. "ml" has 2 tagged chunks with edges (c1, c3)
        ml = [r for r in bt if r["tag"] == "ml"][0]
        assert ml["tagged_chunks_with_edges"] == 2
        ok += 1

        # 4. "web" not in results (c4 has no edges)
        web = [r for r in bt if r["tag"] == "web"]
        assert len(web) == 0
        ok += 1

        # 5. by-type: "supports" spans 2 tags (python, ml via c1)
        btype = tags_by_edge_type(conn)
        supports = [r for r in btype if r["edge_type"] == "supports"][0]
        assert supports["distinct_tags"] == 2
        ok += 1

        # 6. "contradicts" spans 2 tags (python+ml via c1, ml via c3)
        contradicts = [r for r in btype if r["edge_type"] == "contradicts"][0]
        assert contradicts["distinct_tags"] == 2
        ok += 1

        # 7. "refines" spans 2 tags (ml via c3, python via c2)
        refines = [r for r in btype if r["edge_type"] == "refines"][0]
        assert refines["distinct_tags"] == 2
        ok += 1

        # 8. concentration: python has 3 edge types
        conc = tag_edge_concentration(conn)
        c_python = [r for r in conc if r["tag"] == "python"][0]
        assert c_python["edge_types"] == 3
        ok += 1

        # 9. ml has 3 edge types
        c_ml = [r for r in conc if r["tag"] == "ml"][0]
        assert c_ml["edge_types"] == 3
        ok += 1

        # 10. summary: total_tags = 3 (python, ml, web)
        s = tag_edge_summary(conn)
        assert s["total_tags"] == 3
        ok += 1

        # 11. tags_with_edges = 2 (python, ml; web has no edges)
        assert s["tags_with_edges"] == 2
        ok += 1

        # 12. total_edges = 3
        assert s["total_edges"] == 3
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
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = tag_edge_summary(conn)
        assert s["total_tags"] == 0
        assert s["tags_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Tag edge profile analysis")
    ap.add_argument("command", choices=["by-tag", "by-type", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS tag_edge_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-tag":
        rows = edges_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag edge data found.")
            else:
                print(f"{'tag':<16} {'chunks':<8} {'edges':<8} {'types':<8} {'edges/chunk'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['tagged_chunks_with_edges']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {r['edges_per_chunk']:.4f}")
    elif args.command == "by-type":
        rows = tags_by_edge_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge type data found.")
            else:
                print(f"{'edge_type':<15} {'tags':<10} {'chunks':<8} {'edges'}")
                for r in rows:
                    print(f"{r['edge_type']:<15} {r['distinct_tags']:<10} {r['tagged_chunks']:<8} {r['edge_count']}")
    elif args.command == "concentration":
        rows = tag_edge_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag edge data found.")
            else:
                print(f"{'tag':<16} {'chunks':<8} {'edges':<8} {'types':<8} {'type_ratio'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['tagged_chunks_with_edges']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {r['type_ratio']:.4f}")
    elif args.command == "summary":
        s = tag_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
