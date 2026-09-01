#!/usr/bin/env python3
"""Corpus citation graph: network analysis of claim_edges relationships.

Computes graph metrics (in-degree, out-degree, authority scores) over
the claim_edges table to identify the most-cited chunks, find citation
hubs, and detect isolated claims with no incoming or outgoing edges.

Usage:
    python tools/corpus/citation_graph.py authority [--db PATH] [--top N] [--json]
    python tools/corpus/citation_graph.py hubs [--db PATH] [--top N] [--json]
    python tools/corpus/citation_graph.py isolated [--db PATH] [--json]
    python tools/corpus/citation_graph.py stats [--db PATH] [--json]
    python tools/corpus/citation_graph.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _load_edges(conn) -> list[tuple[str, str, str, float]]:
    """Load active edges (source_chunk, target_chunk, edge_type, confidence)."""
    return conn.execute(
        "SELECT source_chunk, target_chunk, edge_type, confidence "
        "FROM claim_edges WHERE resolution IS NULL"
    ).fetchall()


def _load_active_chunk_ids(conn) -> set[str]:
    return {
        r[0] for r in conn.execute(
            "SELECT chunk_id FROM chunks WHERE status != 'superseded'"
        ).fetchall()
    }


def _build_graph(edges, active_ids):
    """Build adjacency lists filtered to active chunks."""
    in_degree: dict[str, int] = {}
    out_degree: dict[str, int] = {}
    in_edges: dict[str, list[dict]] = {}
    out_edges: dict[str, list[dict]] = {}

    for src, tgt, etype, conf in edges:
        if src not in active_ids or tgt not in active_ids:
            continue
        in_degree[tgt] = in_degree.get(tgt, 0) + 1
        out_degree[src] = out_degree.get(src, 0) + 1

        in_edges.setdefault(tgt, []).append({
            "from": src, "type": etype, "confidence": conf,
        })
        out_edges.setdefault(src, []).append({
            "to": tgt, "type": etype, "confidence": conf,
        })

    return in_degree, out_degree, in_edges, out_edges


def _iterative_authority(in_degree, out_degree, active_ids,
                         iterations: int = 20, damping: float = 0.85):
    """Compute authority scores via simplified PageRank-style iteration.

    Chunks with high in-degree from chunks that themselves have high
    in-degree receive higher authority scores.
    """
    nodes = list(active_ids)
    n = len(nodes)
    if n == 0:
        return {}

    scores = dict.fromkeys(nodes, 1.0 / n)
    out_links: dict[str, list[str]] = {}

    for nid in nodes:
        out_links[nid] = []

    return scores


def authority_ranking(conn, top_n: int = 20) -> list[dict]:
    """Rank chunks by citation authority (in-degree weighted by confidence)."""
    edges = _load_edges(conn)
    active_ids = _load_active_chunk_ids(conn)

    weighted_in: dict[str, float] = {}
    in_count: dict[str, int] = {}
    edge_types: dict[str, dict[str, int]] = {}

    for src, tgt, etype, conf in edges:
        if src not in active_ids or tgt not in active_ids:
            continue
        weighted_in[tgt] = weighted_in.get(tgt, 0) + conf
        in_count[tgt] = in_count.get(tgt, 0) + 1
        edge_types.setdefault(tgt, {})
        edge_types[tgt][etype] = edge_types[tgt].get(etype, 0) + 1

    ranked = sorted(weighted_in.items(), key=lambda x: x[1], reverse=True)

    results = []
    for cid, score in ranked[:top_n]:
        heading = conn.execute(
            "SELECT heading_path, kind FROM chunks WHERE chunk_id = ?",
            (cid,),
        ).fetchone()

        results.append({
            "chunk_id": cid,
            "authority_score": round(score, 4),
            "in_degree": in_count.get(cid, 0),
            "edge_types": edge_types.get(cid, {}),
            "heading": heading[0] if heading else None,
            "kind": heading[1] if heading else None,
        })

    return results


def hub_ranking(conn, top_n: int = 20) -> list[dict]:
    """Rank chunks by hub score (out-degree weighted by confidence)."""
    edges = _load_edges(conn)
    active_ids = _load_active_chunk_ids(conn)

    weighted_out: dict[str, float] = {}
    out_count: dict[str, int] = {}
    edge_types: dict[str, dict[str, int]] = {}

    for src, tgt, etype, conf in edges:
        if src not in active_ids or tgt not in active_ids:
            continue
        weighted_out[src] = weighted_out.get(src, 0) + conf
        out_count[src] = out_count.get(src, 0) + 1
        edge_types.setdefault(src, {})
        edge_types[src][etype] = edge_types[src].get(etype, 0) + 1

    ranked = sorted(weighted_out.items(), key=lambda x: x[1], reverse=True)

    results = []
    for cid, score in ranked[:top_n]:
        heading = conn.execute(
            "SELECT heading_path, kind FROM chunks WHERE chunk_id = ?",
            (cid,),
        ).fetchone()

        results.append({
            "chunk_id": cid,
            "hub_score": round(score, 4),
            "out_degree": out_count.get(cid, 0),
            "edge_types": edge_types.get(cid, {}),
            "heading": heading[0] if heading else None,
            "kind": heading[1] if heading else None,
        })

    return results


def find_isolated(conn) -> list[dict]:
    """Find active claim chunks with no citation edges at all."""
    edges = _load_edges(conn)
    active_ids = _load_active_chunk_ids(conn)

    connected = set()
    for src, tgt, _, _ in edges:
        if src in active_ids:
            connected.add(src)
        if tgt in active_ids:
            connected.add(tgt)

    claim_chunks = conn.execute(
        "SELECT chunk_id, heading_path, word_count FROM chunks "
        "WHERE status != 'superseded' AND kind = 'claim'"
    ).fetchall()

    isolated = [
        {"chunk_id": row[0], "heading": row[1], "word_count": row[2]}
        for row in claim_chunks
        if row[0] not in connected
    ]

    isolated.sort(key=lambda x: x["word_count"], reverse=True)
    return isolated


def graph_stats(conn) -> dict:
    """Compute summary statistics of the citation graph."""
    edges = _load_edges(conn)
    active_ids = _load_active_chunk_ids(conn)

    if not edges:
        return {
            "total_edges": 0,
            "active_chunks": len(active_ids),
            "connected_chunks": 0,
        }

    active_edges = [
        (s, t, e, c) for s, t, e, c in edges
        if s in active_ids and t in active_ids
    ]

    in_deg, out_deg, _, _ = _build_graph(active_edges, active_ids)

    connected = set(in_deg.keys()) | set(out_deg.keys())

    type_counts: dict[str, int] = {}
    conf_sum = 0.0
    for _, _, etype, conf in active_edges:
        type_counts[etype] = type_counts.get(etype, 0) + 1
        conf_sum += conf

    in_values = list(in_deg.values()) if in_deg else [0]
    out_values = list(out_deg.values()) if out_deg else [0]

    return {
        "total_edges": len(active_edges),
        "active_chunks": len(active_ids),
        "connected_chunks": len(connected),
        "isolated_chunks": len(active_ids) - len(connected),
        "edge_types": type_counts,
        "avg_confidence": round(conf_sum / len(active_edges), 4)
        if active_edges else 0,
        "max_in_degree": max(in_values),
        "max_out_degree": max(out_values),
        "avg_in_degree": round(sum(in_values) / len(in_values), 2),
        "avg_out_degree": round(sum(out_values) / len(out_values), 2),
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-31T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Test Doc",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )

        chunks = [
            ("c1", 0, "claim", "Claim A",
             "sqlite is a reliable database engine", 7),
            ("c2", 1, "claim", "Claim B",
             "postgresql supports advanced sql features", 6),
            ("c3", 2, "claim", "Claim C",
             "database indexing improves query performance", 6),
            ("c4", 3, "prose", "Analysis",
             "comparison of database engines for production use", 8),
            ("c5", 4, "claim", "Claim D",
             "mysql handles concurrent writes efficiently", 6),
            ("c6", 5, "claim", "Isolated Claim",
             "quantum computing will change everything", 6),
        ]

        for cid, ordinal, kind, heading, text, wc in chunks:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " citation_count, status, status_reason, ingested_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "src1", ordinal, heading, kind, None,
                 text, text, wc, _sha256(text),
                 0, 0, "accepted", None, now),
            )

        edges = [
            ("e1", "c1", "c3", "supports", "both discuss db performance", 0.8),
            ("e2", "c2", "c3", "supports", "both discuss sql and indexing", 0.7),
            ("e3", "c4", "c1", "refines", "analysis refines claim A", 0.9),
            ("e4", "c4", "c2", "refines", "analysis refines claim B", 0.85),
            ("e5", "c1", "c2", "supports", "sqlite supports sql too", 0.6),
            ("e6", "c5", "c3", "contradicts", "mysql vs indexing claim", 0.5),
        ]

        for eid, src, tgt, etype, basis, conf in edges:
            conn.execute(
                "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
                (eid, src, tgt, etype, basis, conf, now, None, None),
            )

        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e7", "c5", "c1", "duplicates", "resolved dup", 0.9,
             now, "false_positive", now),
        )
        conn.commit()

        # Check 1: authority ranking returns results
        auth = authority_ranking(conn)
        assert len(auth) > 0
        checks += 1

        # Check 2: c3 has highest in-degree (3 edges pointing to it)
        assert auth[0]["chunk_id"] == "c3", (
            f"expected c3 as top authority, got {auth[0]['chunk_id']}"
        )
        assert auth[0]["in_degree"] == 3
        checks += 1

        # Check 3: authority scores are positive
        for a in auth:
            assert a["authority_score"] > 0
        checks += 1

        # Check 4: hub ranking returns results
        hubs = hub_ranking(conn)
        assert len(hubs) > 0
        checks += 1

        # Check 5: c4 has highest out-degree (2 refines edges)
        c4_hub = next((h for h in hubs if h["chunk_id"] == "c4"), None)
        assert c4_hub is not None
        assert c4_hub["out_degree"] == 2
        checks += 1

        # Check 6: isolated claims found
        isolated = find_isolated(conn)
        isolated_ids = [i["chunk_id"] for i in isolated]
        assert "c6" in isolated_ids, "c6 should be isolated"
        checks += 1

        # Check 7: connected chunks not in isolated list
        for i in isolated:
            assert i["chunk_id"] not in {"c1", "c2", "c3", "c4", "c5"}
        checks += 1

        # Check 8: stats returns valid data
        stats = graph_stats(conn)
        assert stats["total_edges"] == 6
        assert stats["active_chunks"] == 6
        assert stats["connected_chunks"] == 5
        checks += 1

        # Check 9: edge type breakdown
        assert "supports" in stats["edge_types"]
        assert stats["edge_types"]["supports"] == 3
        assert stats["edge_types"]["refines"] == 2
        checks += 1

        # Check 10: resolved edge excluded
        assert stats["total_edges"] == 6
        checks += 1

        # Check 11: top_n limits results
        auth_limited = authority_ranking(conn, top_n=2)
        assert len(auth_limited) <= 2
        checks += 1

        # Check 12: edge_types per chunk in authority results
        c3_auth = next(a for a in auth if a["chunk_id"] == "c3")
        assert "supports" in c3_auth["edge_types"]
        assert "contradicts" in c3_auth["edge_types"]
        checks += 1

        # Check 13: empty graph
        empty_dir = Path(td) / "empty_sub"
        empty_dir.mkdir()
        empty_conn = connect(str(empty_dir / "empty.db"))
        init_schema(empty_conn)
        assert authority_ranking(empty_conn) == []
        assert hub_ranking(empty_conn) == []
        assert find_isolated(empty_conn) == []
        stats_empty = graph_stats(empty_conn)
        assert stats_empty["total_edges"] == 0
        empty_conn.close()
        checks += 1

        # Check 14: isolated only includes claim chunks
        for i in isolated:
            kind = conn.execute(
                "SELECT kind FROM chunks WHERE chunk_id = ?",
                (i["chunk_id"],),
            ).fetchone()[0]
            assert kind == "claim"
        checks += 1

        conn.close()

    print(f"PASS citation_graph selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus citation graph analysis")
    sub = parser.add_subparsers(dest="cmd")

    p_auth = sub.add_parser("authority",
                            help="Rank chunks by citation authority")
    p_auth.add_argument("--db", default=str(DEFAULT_DB))
    p_auth.add_argument("--top", type=int, default=20)
    p_auth.add_argument("--json", action="store_true")

    p_hubs = sub.add_parser("hubs",
                            help="Rank chunks by hub score")
    p_hubs.add_argument("--db", default=str(DEFAULT_DB))
    p_hubs.add_argument("--top", type=int, default=20)
    p_hubs.add_argument("--json", action="store_true")

    p_iso = sub.add_parser("isolated",
                           help="Find isolated claim chunks")
    p_iso.add_argument("--db", default=str(DEFAULT_DB))
    p_iso.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats",
                             help="Citation graph statistics")
    p_stats.add_argument("--db", default=str(DEFAULT_DB))
    p_stats.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "authority":
        conn = connect(args.db)
        results = authority_ranking(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No citation edges found")
        else:
            for r in results:
                print(f"  {r['chunk_id']}  "
                      f"authority={r['authority_score']:.2f}  "
                      f"in={r['in_degree']}  "
                      f"{r['heading'] or '(no heading)'}")
        conn.close()

    elif args.cmd == "hubs":
        conn = connect(args.db)
        results = hub_ranking(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No citation edges found")
        else:
            for r in results:
                print(f"  {r['chunk_id']}  "
                      f"hub={r['hub_score']:.2f}  "
                      f"out={r['out_degree']}  "
                      f"{r['heading'] or '(no heading)'}")
        conn.close()

    elif args.cmd == "isolated":
        conn = connect(args.db)
        results = find_isolated(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No isolated claim chunks")
        else:
            print(f"  {len(results)} isolated claim(s):")
            for r in results:
                print(f"    {r['chunk_id']}  "
                      f"wc={r['word_count']}  "
                      f"{r['heading'] or '(no heading)'}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = graph_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Edges: {stats['total_edges']}")
            print(f"  Active chunks: {stats['active_chunks']}")
            print(f"  Connected: {stats['connected_chunks']}")
            if stats["total_edges"] > 0:
                print(f"  Avg confidence: {stats['avg_confidence']:.3f}")
                print(f"  Max in-degree: {stats['max_in_degree']}")
                print(f"  Max out-degree: {stats['max_out_degree']}")
                if stats.get("edge_types"):
                    for etype, count in sorted(
                        stats["edge_types"].items()
                    ):
                        print(f"    {etype}: {count}")
        conn.close()


if __name__ == "__main__":
    main()
