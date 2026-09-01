#!/usr/bin/env python3
"""Publisher edge profile: which publishers produce which claim edge types.

publisher_tag_profile.py profiles publishers by tag vocabulary.
publisher_citation_profile.py profiles publishers by citation patterns.
No tool joins sources.publisher with claim_edges to measure which
publishers produce the most claim edges, how edge types distribute
across publishers, or which publishers are exclusive edge sources.

Usage:
    python tools/corpus/publisher_edge_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/publisher_edge_profile.py by-type [--db PATH] [--json]
    python tools/corpus/publisher_edge_profile.py cross-publisher [--db PATH] [--json]
    python tools/corpus/publisher_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/publisher_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_publisher(conn) -> list[dict]:
    """Edge distribution per publisher (counting edges where the publisher is source or target)."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT e.edge_id) AS total_edges,
               COUNT(DISTINCT e.source_chunk) AS source_chunks,
               COUNT(DISTINCT e.target_chunk) AS target_chunks,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.publisher
        ORDER BY total_edges DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "total_edges": r[1],
            "source_chunks": r[2],
            "target_chunks": r[3],
            "avg_confidence": r[4],
        }
        for r in rows
    ]


def edge_types_by_publisher(conn) -> list[dict]:
    """Edge type distribution per publisher."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               e.edge_type,
               COUNT(e.edge_id) AS edge_count,
               ROUND(AVG(e.confidence), 4) AS avg_confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.publisher, e.edge_type
        ORDER BY edge_count DESC, s.publisher, e.edge_type
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "edge_type": r[1],
            "edge_count": r[2],
            "avg_confidence": r[3],
        }
        for r in rows
    ]


def cross_publisher_edges(conn) -> list[dict]:
    """Edges that cross publisher boundaries (source and target from different publishers)."""
    rows = conn.execute(
        """
        SELECT s_src.publisher AS source_publisher,
               s_tgt.publisher AS target_publisher,
               e.edge_type,
               COUNT(e.edge_id) AS edge_count
        FROM claim_edges e
        JOIN chunks c_src ON c_src.chunk_id = e.source_chunk
        JOIN sources s_src ON s_src.source_id = c_src.source_id
        JOIN chunks c_tgt ON c_tgt.chunk_id = e.target_chunk
        JOIN sources s_tgt ON s_tgt.source_id = c_tgt.source_id
        WHERE s_src.publisher IS NOT s_tgt.publisher
        GROUP BY s_src.publisher, s_tgt.publisher, e.edge_type
        ORDER BY edge_count DESC, source_publisher, target_publisher
        """
    ).fetchall()
    return [
        {
            "source_publisher": r[0],
            "target_publisher": r[1],
            "edge_type": r[2],
            "edge_count": r[3],
        }
        for r in rows
    ]


def publisher_edge_summary(conn) -> dict:
    """Aggregate publisher-edge statistics."""
    total_publishers = conn.execute(
        "SELECT COUNT(DISTINCT publisher) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    publishers_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT s.publisher)
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        WHERE s.publisher IS NOT NULL
        """
    ).fetchone()[0]

    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]

    cross_pub_edges = conn.execute(
        """
        SELECT COUNT(*)
        FROM claim_edges e
        JOIN chunks c_src ON c_src.chunk_id = e.source_chunk
        JOIN sources s_src ON s_src.source_id = c_src.source_id
        JOIN chunks c_tgt ON c_tgt.chunk_id = e.target_chunk
        JOIN sources s_tgt ON s_tgt.source_id = c_tgt.source_id
        WHERE s_src.publisher IS NOT s_tgt.publisher
        """
    ).fetchone()[0]

    avg_edges_per_publisher = conn.execute(
        """
        SELECT ROUND(AVG(edge_count), 4)
        FROM (
            SELECT s.publisher, COUNT(e.edge_id) AS edge_count
            FROM claim_edges e
            JOIN chunks c ON c.chunk_id = e.source_chunk
            JOIN sources s ON s.source_id = c.source_id
            WHERE s.publisher IS NOT NULL
            GROUP BY s.publisher
        )
        """
    ).fetchone()[0]

    distinct_edge_types = conn.execute(
        "SELECT COUNT(DISTINCT edge_type) FROM claim_edges"
    ).fetchone()[0]

    return {
        "total_publishers": total_publishers,
        "publishers_with_edges": publishers_with_edges,
        "publisher_edge_coverage": round(publishers_with_edges / max(total_publishers, 1), 4),
        "total_edges": total_edges,
        "cross_publisher_edges": cross_pub_edges,
        "cross_publisher_rate": round(cross_pub_edges / max(total_edges, 1), 4),
        "avg_edges_per_publisher": avg_edges_per_publisher or 0.0,
        "distinct_edge_types": distinct_edge_types,
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
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "abc", 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None),
        )

        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 25, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "intro", "claim", None, "t", "t", 15, "jkl", 4000, 0, "accepted", None, t1))

        # Edges: acme->acme (supports), acme->globex (contradicts), globex->acme (supports)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "sim", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "contradicts", "manual", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "supports", "sim", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c4", "c1", "duplicates", "sim", 0.6, t1, None, None))
        conn.commit()

        # 1. by-publisher: acme has 2 edges as source (e1, e2)
        bp = edges_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["total_edges"] == 2
        ok += 1

        # 2. globex has 1 edge as source (e3)
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["total_edges"] == 1
        ok += 1

        # 3. null publisher has 1 edge as source (e4)
        null_pub = [r for r in bp if r["publisher"] is None][0]
        assert null_pub["total_edges"] == 1
        ok += 1

        # 4. by-type: acme "supports" has 1 edge
        bt = edge_types_by_publisher(conn)
        acme_supports = [r for r in bt if r["publisher"] == "acme" and r["edge_type"] == "supports"][0]
        assert acme_supports["edge_count"] == 1
        ok += 1

        # 5. acme "contradicts" has 1 edge
        acme_contradicts = [r for r in bt if r["publisher"] == "acme" and r["edge_type"] == "contradicts"][0]
        assert acme_contradicts["edge_count"] == 1
        ok += 1

        # 6. cross-publisher: acme->globex contradicts = 1
        cp = cross_publisher_edges(conn)
        a2g = [r for r in cp if r["source_publisher"] == "acme" and r["target_publisher"] == "globex"]
        assert len(a2g) == 1
        assert a2g[0]["edge_count"] == 1
        ok += 1

        # 7. cross-publisher: globex->acme supports = 1
        g2a = [r for r in cp if r["source_publisher"] == "globex" and r["target_publisher"] == "acme"]
        assert len(g2a) == 1
        assert g2a[0]["edge_count"] == 1
        ok += 1

        # 8. null->acme is also cross-publisher
        n2a = [r for r in cp if r["source_publisher"] is None and r["target_publisher"] == "acme"]
        assert len(n2a) == 1
        ok += 1

        # 9. summary: publishers_with_edges = 2 (acme, globex; null excluded)
        s = publisher_edge_summary(conn)
        assert s["publishers_with_edges"] == 2
        ok += 1

        # 10. total_edges = 4
        assert s["total_edges"] == 4
        ok += 1

        # 11. cross_publisher_edges = 3 (e2: acme->globex, e3: globex->acme, e4: null->acme)
        assert s["cross_publisher_edges"] == 3, f"expected 3, got {s['cross_publisher_edges']}"
        ok += 1

        # 12. distinct_edge_types = 3 (supports, contradicts, duplicates)
        assert s["distinct_edge_types"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["publisher_edge_coverage"] == s["publisher_edge_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = publisher_edge_summary(conn)
        assert s["publishers_with_edges"] == 0
        assert s["total_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Publisher edge profile analysis")
    ap.add_argument("command", choices=["by-publisher", "by-type", "cross-publisher", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS publisher_edge_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-publisher":
        rows = edges_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher edge data found.")
            else:
                print(f"{'publisher':<20} {'edges':<8} {'src_chunks':<12} {'tgt_chunks':<12} {'avg_conf'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['total_edges']:<8} {r['source_chunks']:<12} {r['target_chunks']:<12} {r['avg_confidence']:.4f}")
    elif args.command == "by-type":
        rows = edge_types_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher edge type data found.")
            else:
                print(f"{'publisher':<20} {'edge_type':<15} {'count':<8} {'avg_conf'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['edge_type']:<15} {r['edge_count']:<8} {r['avg_confidence']:.4f}")
    elif args.command == "cross-publisher":
        rows = cross_publisher_edges(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cross-publisher edges found.")
            else:
                print(f"{'source':<20} {'target':<20} {'type':<15} {'count'}")
                for r in rows:
                    sp = r["source_publisher"] or "(none)"
                    tp = r["target_publisher"] or "(none)"
                    print(f"{sp:<20} {tp:<20} {r['edge_type']:<15} {r['edge_count']}")
    elif args.command == "summary":
        s = publisher_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
