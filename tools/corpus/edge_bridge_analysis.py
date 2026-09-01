#!/usr/bin/env python3
"""Edge bridge analysis: identify bridge edges in the claim_edges graph.

edge_chain_analysis.py walks multi-hop paths.
edge_cycle_detection.py finds closed loops.
No tool identifies bridge edges whose removal would disconnect
components of the argumentation graph, measuring structural fragility
and which edge types serve as critical connectors.

Usage:
    python tools/corpus/edge_bridge_analysis.py bridges [--db PATH] [--json]
    python tools/corpus/edge_bridge_analysis.py components [--db PATH] [--json]
    python tools/corpus/edge_bridge_analysis.py by-type [--db PATH] [--json]
    python tools/corpus/edge_bridge_analysis.py summary [--db PATH] [--json]
    python tools/corpus/edge_bridge_analysis.py selftest
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


def _build_undirected(conn) -> tuple[dict[str, set[str]], list[tuple[str, str, str, str]]]:
    """Build undirected adjacency and edge list from claim_edges."""
    rows = conn.execute(
        "SELECT edge_id, source_chunk, target_chunk, edge_type FROM claim_edges"
    ).fetchall()
    adj: dict[str, set[str]] = defaultdict(set)
    edges = []
    for edge_id, src, tgt, etype in rows:
        adj[src].add(tgt)
        adj[tgt].add(src)
        edges.append((edge_id, src, tgt, etype))
    return dict(adj), edges


def _find_components(adj: dict[str, set[str]]) -> list[set[str]]:
    """Find connected components via BFS on undirected adjacency."""
    visited: set[str] = set()
    components: list[set[str]] = []
    for node in adj:
        if node in visited:
            continue
        component: set[str] = set()
        queue = [node]
        while queue:
            current = queue.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adj.get(current, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)
    return components


def _is_bridge(adj: dict[str, set[str]], src: str, tgt: str) -> bool:
    """Check if removing edge src-tgt disconnects the graph."""
    adj_copy: dict[str, set[str]] = {}
    for k, v in adj.items():
        adj_copy[k] = set(v)
    adj_copy[src].discard(tgt)
    adj_copy[tgt].discard(src)
    visited: set[str] = set()
    queue = [src]
    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        for neighbor in adj_copy.get(current, set()):
            if neighbor not in visited:
                queue.append(neighbor)
    return tgt not in visited


def find_bridges(conn) -> list[dict]:
    """Identify bridge edges whose removal disconnects graph components."""
    adj, edges = _build_undirected(conn)
    bridges = []
    seen_pairs: set[tuple[str, str]] = set()
    for edge_id, src, tgt, etype in edges:
        pair = (min(src, tgt), max(src, tgt))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        if _is_bridge(adj, src, tgt):
            bridges.append({
                "edge_id": edge_id,
                "source_chunk": src,
                "target_chunk": tgt,
                "edge_type": etype,
            })
    bridges.sort(key=lambda b: b["edge_id"])
    return bridges


def component_analysis(conn) -> list[dict]:
    """Analyze connected components of the claim_edges graph."""
    adj, edges = _build_undirected(conn)
    components = _find_components(adj)
    edge_types_by_component: list[set[str]] = []
    edge_counts: list[int] = []
    for comp in components:
        comp_types: set[str] = set()
        comp_edges = 0
        for _, src, tgt, etype in edges:
            if src in comp and tgt in comp:
                comp_types.add(etype)
                comp_edges += 1
        edge_types_by_component.append(comp_types)
        edge_counts.append(comp_edges)

    result = []
    for i, comp in enumerate(components):
        result.append({
            "component_id": i,
            "chunk_count": len(comp),
            "edge_count": edge_counts[i],
            "edge_types": len(edge_types_by_component[i]),
            "chunks": sorted(comp),
        })
    result.sort(key=lambda c: -c["chunk_count"])
    return result


def bridges_by_edge_type(conn) -> list[dict]:
    """Bridge count per edge type."""
    bridges = find_bridges(conn)
    adj, edges = _build_undirected(conn)
    total_by_type: dict[str, int] = defaultdict(int)
    for _, _, _, etype in edges:
        total_by_type[etype] += 1

    bridge_by_type: dict[str, int] = defaultdict(int)
    for b in bridges:
        bridge_by_type[b["edge_type"]] += 1

    all_types = set(total_by_type) | set(bridge_by_type)
    return sorted(
        [
            {
                "edge_type": t,
                "bridge_count": bridge_by_type.get(t, 0),
                "total_edges": total_by_type.get(t, 0),
                "bridge_rate": round(bridge_by_type.get(t, 0) / max(total_by_type.get(t, 0), 1), 4),
            }
            for t in all_types
        ],
        key=lambda r: -r["bridge_count"],
    )


def bridge_summary(conn) -> dict:
    """Aggregate bridge and component statistics."""
    adj, edges = _build_undirected(conn)
    total_edges = len(edges)
    total_nodes = len(adj)
    components = _find_components(adj)
    bridges = find_bridges(conn)

    if total_edges == 0:
        return {
            "total_edges": 0,
            "total_nodes": 0,
            "components": 0,
            "largest_component": 0,
            "bridge_count": 0,
            "bridge_rate": 0,
            "fragility": 0,
        }

    largest = max(len(c) for c in components) if components else 0
    bridge_nodes = set()
    for b in bridges:
        bridge_nodes.add(b["source_chunk"])
        bridge_nodes.add(b["target_chunk"])

    return {
        "total_edges": total_edges,
        "total_nodes": total_nodes,
        "components": len(components),
        "largest_component": largest,
        "bridge_count": len(bridges),
        "bridge_rate": round(len(bridges) / max(total_edges, 1), 4),
        "fragility": round(len(bridge_nodes) / max(total_nodes, 1), 4),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        for i, cid in enumerate(["c1", "c2", "c3", "c4", "c5", "c6"], 1):
            conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "s1", i, "intro", "claim", None, "t", "t", 20, f"h{i}", 1000+i, 0, "accepted", None, t1))

        # Component 1: c1-c2-c3 triangle (no bridges within)
        # Bridge: c3-c4 connects two components
        # Component 2: c4-c5 (single edge, is a bridge itself)
        # c6 isolated via c5-c6 bridge
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "supports", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "contradicts", "text", 0.85, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c3", "c4", "refines", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c4", "c5", "supports", "text", 0.75, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e6", "c5", "c6", "supports", "text", 0.8, t1, None, None))
        conn.commit()

        # 1. bridges: e4 (c3-c4), e5 (c4-c5), e6 (c5-c6) are bridges
        br = find_bridges(conn)
        bridge_ids = {b["edge_id"] for b in br}
        assert "e4" in bridge_ids
        ok += 1

        # 2. e5 is a bridge
        assert "e5" in bridge_ids
        ok += 1

        # 3. e6 is a bridge
        assert "e6" in bridge_ids
        ok += 1

        # 4. e1, e2, e3 are NOT bridges (triangle)
        assert "e1" not in bridge_ids
        assert "e2" not in bridge_ids
        assert "e3" not in bridge_ids
        ok += 1

        # 5. total bridges = 3
        assert len(br) == 3
        ok += 1

        # 6. components: 1 connected component (all reachable via undirected edges)
        comp = component_analysis(conn)
        assert len(comp) == 1
        ok += 1

        # 7. that component has 6 chunks
        assert comp[0]["chunk_count"] == 6
        ok += 1

        # 8. by-type: "refines" has 1 bridge out of 1 edge = 1.0 rate
        bt = bridges_by_edge_type(conn)
        refines = [r for r in bt if r["edge_type"] == "refines"][0]
        assert refines["bridge_count"] == 1
        assert refines["bridge_rate"] == 1.0
        ok += 1

        # 9. "supports" has 2 bridges out of 4 edges
        supports = [r for r in bt if r["edge_type"] == "supports"][0]
        assert supports["bridge_count"] == 2
        ok += 1

        # 10. "contradicts" has 0 bridges
        contradicts = [r for r in bt if r["edge_type"] == "contradicts"][0]
        assert contradicts["bridge_count"] == 0
        ok += 1

        # 11. summary: bridge_count = 3
        s = bridge_summary(conn)
        assert s["bridge_count"] == 3
        ok += 1

        # 12. components = 1
        assert s["components"] == 1
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["bridge_rate"] == s["bridge_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = bridge_summary(conn)
        assert s["total_edges"] == 0
        assert s["bridge_count"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Edge bridge analysis")
    ap.add_argument("command", choices=["bridges", "components", "by-type", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS edge_bridge_analysis selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "bridges":
        rows = find_bridges(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No bridge edges found.")
            else:
                print(f"{'edge_id':<10} {'source':<12} {'target':<12} {'type'}")
                for r in rows:
                    print(f"{r['edge_id']:<10} {r['source_chunk']:<12} {r['target_chunk']:<12} {r['edge_type']}")
    elif args.command == "components":
        rows = component_analysis(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No components found.")
            else:
                print(f"{'id':<6} {'chunks':<8} {'edges':<8} {'types':<8} {'members'}")
                for r in rows:
                    print(f"{r['component_id']:<6} {r['chunk_count']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {', '.join(r['chunks'][:5])}{'...' if len(r['chunks']) > 5 else ''}")
    elif args.command == "by-type":
        rows = bridges_by_edge_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge type data found.")
            else:
                print(f"{'edge_type':<15} {'bridges':<10} {'total':<8} {'bridge_rate'}")
                for r in rows:
                    print(f"{r['edge_type']:<15} {r['bridge_count']:<10} {r['total_edges']:<8} {r['bridge_rate']:.4f}")
    elif args.command == "summary":
        s = bridge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
