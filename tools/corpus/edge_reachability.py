#!/usr/bin/env python3
"""Edge reachability: multi-hop path analysis in the claim_edges graph.

citation_graph.py computes degree and authority scores.  claim_network.py
computes connected components and bridges.  No tool computes multi-hop
paths between chunks or the diameter of the claim graph.  Understanding
how many hops separate two chunks, or what the longest shortest-path is,
required manual BFS traversal.

Usage:
    python tools/corpus/edge_reachability.py diameter [--db PATH] [--json]
    python tools/corpus/edge_reachability.py path <src> <tgt> [--db PATH] [--json]
    python tools/corpus/edge_reachability.py hop-distribution [--db PATH] [--json]
    python tools/corpus/edge_reachability.py summary [--db PATH] [--json]
    python tools/corpus/edge_reachability.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _build_adjacency(conn) -> dict[str, set[str]]:
    """Build undirected adjacency list from claim_edges."""
    rows = conn.execute(
        "SELECT source_chunk, target_chunk FROM claim_edges"
    ).fetchall()

    adj: dict[str, set[str]] = {}
    for src, tgt in rows:
        if src not in adj:
            adj[src] = set()
        if tgt not in adj:
            adj[tgt] = set()
        adj[src].add(tgt)
        adj[tgt].add(src)

    return adj


def _bfs_distances(adj: dict[str, set[str]],
                   start: str) -> dict[str, int]:
    """BFS from start, returning distances to all reachable nodes."""
    dist: dict[str, int] = {start: 0}
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in adj.get(node, set()):
            if neighbor not in dist:
                dist[neighbor] = dist[node] + 1
                queue.append(neighbor)
    return dist


def _bfs_path(adj: dict[str, set[str]],
              start: str, end: str) -> list[str] | None:
    """BFS shortest path from start to end."""
    if start == end:
        return [start]
    if start not in adj:
        return None

    parent: dict[str, str | None] = {start: None}
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in adj.get(node, set()):
            if neighbor not in parent:
                parent[neighbor] = node
                if neighbor == end:
                    path = []
                    cur: str | None = end
                    while cur is not None:
                        path.append(cur)
                        cur = parent[cur]
                    return list(reversed(path))
                queue.append(neighbor)
    return None


def graph_diameter(conn) -> dict:
    """Compute diameter (longest shortest-path) of the claim graph."""
    adj = _build_adjacency(conn)
    if not adj:
        return {
            "diameter": 0,
            "endpoint_a": None,
            "endpoint_b": None,
            "node_count": 0,
        }

    max_dist = 0
    ep_a = ep_b = None

    for node in adj:
        distances = _bfs_distances(adj, node)
        for target, d in distances.items():
            if d > max_dist:
                max_dist = d
                ep_a = node
                ep_b = target

    return {
        "diameter": max_dist,
        "endpoint_a": ep_a,
        "endpoint_b": ep_b,
        "node_count": len(adj),
    }


def shortest_path(conn, src: str, tgt: str) -> dict:
    """Shortest path between two chunks."""
    adj = _build_adjacency(conn)
    path = _bfs_path(adj, src, tgt)

    return {
        "source": src,
        "target": tgt,
        "reachable": path is not None,
        "hops": len(path) - 1 if path else None,
        "path": path,
    }


def hop_distribution(conn) -> list[dict]:
    """Distribution of pairwise shortest-path distances."""
    adj = _build_adjacency(conn)
    if not adj:
        return []

    counts: dict[int, int] = {}
    seen_pairs: set[tuple[str, str]] = set()

    for node in adj:
        distances = _bfs_distances(adj, node)
        for target, d in distances.items():
            if d == 0:
                continue
            pair = (min(node, target), max(node, target))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                counts[d] = counts.get(d, 0) + 1

    total = sum(counts.values())
    results = []
    for hops in sorted(counts):
        results.append({
            "hops": hops,
            "pair_count": counts[hops],
            "rate": round(counts[hops] / total, 4) if total > 0 else 0.0,
        })

    return results


def reachability_summary(conn) -> dict:
    """Aggregate reachability statistics."""
    adj = _build_adjacency(conn)
    if not adj:
        return {
            "nodes_in_graph": 0,
            "total_edges": 0,
            "connected_components": 0,
            "diameter": 0,
            "mean_hops": 0.0,
            "reachable_pairs": 0,
            "unreachable_pairs": 0,
        }

    total_edges = conn.execute(
        "SELECT count(*) FROM claim_edges"
    ).fetchone()[0]

    components: list[set[str]] = []
    visited: set[str] = set()
    for node in adj:
        if node not in visited:
            comp: set[str] = set()
            queue: deque[str] = deque([node])
            while queue:
                n = queue.popleft()
                if n in comp:
                    continue
                comp.add(n)
                visited.add(n)
                for nb in adj.get(n, set()):
                    if nb not in comp:
                        queue.append(nb)
            components.append(comp)

    diam_result = graph_diameter(conn)
    hop_dist = hop_distribution(conn)

    reachable = sum(h["pair_count"] for h in hop_dist)
    total_nodes = len(adj)
    total_possible = total_nodes * (total_nodes - 1) // 2
    unreachable = total_possible - reachable

    mean_hops = 0.0
    if reachable > 0:
        total_hops = sum(
            h["hops"] * h["pair_count"] for h in hop_dist
        )
        mean_hops = round(total_hops / reachable, 2)

    return {
        "nodes_in_graph": total_nodes,
        "total_edges": total_edges,
        "connected_components": len(components),
        "diameter": diam_result["diameter"],
        "mean_hops": mean_hops,
        "reachable_pairs": reachable,
        "unreachable_pairs": unreachable,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(6):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"c{i+1}", "s1", i, f"/h/c{i+1}", "claim", "en",
                 f"text c{i+1}", f"text c{i+1}", 10,
                 f"sha_c{i+1}", 0, 0, "accepted", now),
            )

        # Graph: c1--c2--c3--c4 (linear chain, diameter=3)
        #        c5--c6 (separate component)
        edges = [
            ("e1", "c1", "c2", "supports", "text", 0.9, now),
            ("e2", "c2", "c3", "supports", "text", 0.85, now),
            ("e3", "c3", "c4", "refines", "version", 0.7, now),
            ("e4", "c5", "c6", "duplicates", "simhash", 0.95, now),
        ]
        for e in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)", e,
            )

        conn.commit()

        # 1: diameter is 3 (c1 to c4)
        diam = graph_diameter(conn)
        assert diam["diameter"] == 3
        assert diam["node_count"] == 6
        checks += 1

        # 2: shortest path c1->c4 is 3 hops
        sp = shortest_path(conn, "c1", "c4")
        assert sp["reachable"] is True
        assert sp["hops"] == 3
        assert len(sp["path"]) == 4
        checks += 1

        # 3: path c1->c4 goes through c2,c3
        assert sp["path"][0] == "c1"
        assert sp["path"][-1] == "c4"
        checks += 1

        # 4: c1->c2 is 1 hop
        sp12 = shortest_path(conn, "c1", "c2")
        assert sp12["hops"] == 1
        checks += 1

        # 5: c1->c5 is unreachable (different component)
        sp15 = shortest_path(conn, "c1", "c5")
        assert sp15["reachable"] is False
        assert sp15["hops"] is None
        checks += 1

        # 6: c5->c6 is 1 hop
        sp56 = shortest_path(conn, "c5", "c6")
        assert sp56["reachable"] is True
        assert sp56["hops"] == 1
        checks += 1

        # 7: hop_distribution has entries
        hd = hop_distribution(conn)
        assert len(hd) > 0
        checks += 1

        # 8: 1-hop pairs: (c1,c2),(c2,c3),(c3,c4),(c5,c6) = 4
        one_hop = next(h for h in hd if h["hops"] == 1)
        assert one_hop["pair_count"] == 4
        checks += 1

        # 9: 3-hop pairs: (c1,c4) = 1
        three_hop = next(h for h in hd if h["hops"] == 3)
        assert three_hop["pair_count"] == 1
        checks += 1

        # 10: hop rates sum to 1.0
        rate_sum = sum(h["rate"] for h in hd)
        assert abs(rate_sum - 1.0) < 0.01
        checks += 1

        # 11: summary has 2 connected components
        summary = reachability_summary(conn)
        assert summary["connected_components"] == 2
        assert summary["nodes_in_graph"] == 6
        checks += 1

        # 12: summary diameter = 3
        assert summary["diameter"] == 3
        assert summary["total_edges"] == 4
        checks += 1

        # 13: reachable pairs = 4+2+1 + 1 = 8 (within components)
        # Component {c1,c2,c3,c4}: 6 pairs, Component {c5,c6}: 1 pair
        assert summary["reachable_pairs"] == 7
        assert summary["unreachable_pairs"] == 8
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(diam)
        _ = json.dumps(sp)
        _ = json.dumps(hd)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty_diam = graph_diameter(conn2)
        assert empty_diam["diameter"] == 0
        empty_summary = reachability_summary(conn2)
        assert empty_summary["nodes_in_graph"] == 0
        checks += 1

    print(
        f"PASS edge_reachability selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Claim graph reachability analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_diam = sub.add_parser("diameter",
                            help="Graph diameter")
    p_diam.add_argument("--db", default=DEFAULT_DB)
    p_diam.add_argument("--json", action="store_true")

    p_path = sub.add_parser("path",
                            help="Shortest path between chunks")
    p_path.add_argument("src", help="Source chunk_id")
    p_path.add_argument("tgt", help="Target chunk_id")
    p_path.add_argument("--db", default=DEFAULT_DB)
    p_path.add_argument("--json", action="store_true")

    p_hd = sub.add_parser("hop-distribution",
                           help="Pairwise distance distribution")
    p_hd.add_argument("--db", default=DEFAULT_DB)
    p_hd.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Reachability statistics")
    p_sum.add_argument("--db", default=DEFAULT_DB)
    p_sum.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "diameter":
        result = graph_diameter(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Diameter: {result['diameter']}  "
                  f"Nodes: {result['node_count']}")
            if result["endpoint_a"]:
                print(f"  Endpoints: {result['endpoint_a']} "
                      f"-> {result['endpoint_b']}")

    elif args.cmd == "path":
        result = shortest_path(conn, args.src, args.tgt)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["reachable"]:
                print(f"Hops: {result['hops']}  "
                      f"Path: {' -> '.join(result['path'])}")
            else:
                print(f"Unreachable: {result['source']} "
                      f"-> {result['target']}")

    elif args.cmd == "hop-distribution":
        results = hop_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['hops']:2d} hops  "
                      f"pairs={r['pair_count']:5d}  "
                      f"rate={r['rate']:.3f}")

    elif args.cmd == "summary":
        result = reachability_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Nodes: {result['nodes_in_graph']}  "
                  f"Edges: {result['total_edges']}  "
                  f"Components: "
                  f"{result['connected_components']}")
            print(f"  Diameter: {result['diameter']}  "
                  f"Mean hops: {result['mean_hops']:.1f}")
            print(f"  Reachable pairs: "
                  f"{result['reachable_pairs']}  "
                  f"Unreachable: "
                  f"{result['unreachable_pairs']}")

    conn.close()


if __name__ == "__main__":
    main()
