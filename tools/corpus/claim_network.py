#!/usr/bin/env python3
"""Claim network analysis for the research corpus.

Analyses claim_edges as a graph to find connected components,
bridge chunks (nodes connecting otherwise separate groups), and
contradiction clusters (tightly connected groups of contradicting
claims).

Usage:
    python tools/corpus/claim_network.py components [--db PATH] [--json]
    python tools/corpus/claim_network.py bridges [--db PATH] [--top N] [--json]
    python tools/corpus/claim_network.py clusters [--db PATH] [--min-size N] [--json]
    python tools/corpus/claim_network.py selftest
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

# ── helpers ──────────────────────────────────────────────────────────


def _load_edges(conn, edge_type: str | None = None,
                unresolved_only: bool = False) -> list[tuple[str, str, str, float]]:
    query = (
        "SELECT e.source_chunk, e.target_chunk, e.edge_type, e.confidence "
        "FROM claim_edges e "
        "JOIN chunks c1 ON c1.chunk_id = e.source_chunk "
        "JOIN chunks c2 ON c2.chunk_id = e.target_chunk "
        "WHERE c1.status != 'superseded' AND c2.status != 'superseded'"
    )
    params: list = []
    if edge_type:
        query += " AND e.edge_type = ?"
        params.append(edge_type)
    if unresolved_only:
        query += " AND e.resolution IS NULL"
    return conn.execute(query, params).fetchall()


def _build_adjacency(edges: list[tuple[str, str, str, float]],
                     ) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for src, tgt, _, _ in edges:
        adj[src].add(tgt)
        adj[tgt].add(src)
    return dict(adj)


def _connected_components(adj: dict[str, set[str]]) -> list[set[str]]:
    visited: set[str] = set()
    components: list[set[str]] = []
    for node in adj:
        if node in visited:
            continue
        component: set[str] = set()
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            stack.extend(nb for nb in adj.get(current, set())
                         if nb not in visited)
        components.append(component)
    return sorted(components, key=len, reverse=True)


# ── subcommands ──────────────────────────────────────────────────────


def network_components(conn) -> list[dict]:
    edges = _load_edges(conn)
    if not edges:
        return []

    adj = _build_adjacency(edges)
    components = _connected_components(adj)

    edge_types_by_component: list[dict[str, int]] = []
    for comp in components:
        type_counts: dict[str, int] = defaultdict(int)
        for src, tgt, etype, _ in edges:
            if src in comp or tgt in comp:
                type_counts[etype] += 1
        edge_types_by_component.append(dict(type_counts))

    return [
        {
            "component_id": i + 1,
            "size": len(comp),
            "members": sorted(comp),
            "edge_types": edge_types_by_component[i],
        }
        for i, comp in enumerate(components)
    ]


def bridge_chunks(conn, top_n: int = 10) -> list[dict]:
    edges = _load_edges(conn)
    if not edges:
        return []

    adj = _build_adjacency(edges)
    components = _connected_components(adj)

    if len(components) < 2:
        node_to_comp: dict[str, int] = {}
        for i, comp in enumerate(components):
            for node in comp:
                node_to_comp[node] = i

        results = []
        for node, neighbors in adj.items():
            degree = len(neighbors)
            edge_count = sum(
                1 for src, tgt, _, _ in edges
                if src == node or tgt == node
            )
            results.append({
                "chunk_id": node,
                "degree": degree,
                "edge_count": edge_count,
                "components_bridged": 0,
            })
        results.sort(key=lambda r: r["degree"], reverse=True)
        return results[:top_n]

    node_to_comp: dict[str, int] = {}
    for i, comp in enumerate(components):
        for node in comp:
            node_to_comp[node] = i

    results = []
    for node, neighbors in adj.items():
        own_comp = node_to_comp.get(node, -1)
        neighbor_comps = {node_to_comp.get(nb, -1) for nb in neighbors}
        bridged = neighbor_comps - {own_comp, -1}
        edge_count = sum(
            1 for src, tgt, _, _ in edges
            if src == node or tgt == node
        )
        results.append({
            "chunk_id": node,
            "degree": len(neighbors),
            "edge_count": edge_count,
            "components_bridged": len(bridged),
        })

    results.sort(key=lambda r: (r["components_bridged"], r["degree"]),
                 reverse=True)
    return results[:top_n]


def contradiction_clusters(conn, min_size: int = 2) -> list[dict]:
    edges = _load_edges(conn, edge_type="contradicts",
                        unresolved_only=True)
    if not edges:
        return []

    adj = _build_adjacency(edges)
    components = _connected_components(adj)

    results = []
    for i, comp in enumerate(components):
        if len(comp) < min_size:
            continue
        cluster_edges = [
            {"source": src, "target": tgt,
             "confidence": round(conf, 4)}
            for src, tgt, _, conf in edges
            if src in comp and tgt in comp
        ]
        avg_conf = (sum(e["confidence"] for e in cluster_edges)
                    / len(cluster_edges)) if cluster_edges else 0.0
        results.append({
            "cluster_id": i + 1,
            "size": len(comp),
            "members": sorted(comp),
            "contradiction_count": len(cluster_edges),
            "avg_confidence": round(avg_conf, 4),
        })

    results.sort(key=lambda r: r["size"], reverse=True)
    return results


# ── selftest ─────────────────────────────────────────────────────────


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Test",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha1", 1000, None),
        )

        for i in range(1, 8):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (f"c{i}", "s1", i - 1, f"H{i}", "claim", "en",
                 f"text{i}", f"text{i}", 1, f"n{i}", now),
            )

        edge_rows = [
            ("e1", "c1", "c2", "contradicts", "semantic", 0.9, now),
            ("e2", "c2", "c3", "contradicts", "semantic", 0.8, now),
            ("e3", "c1", "c3", "supports", "citation", 0.7, now),
            ("e4", "c4", "c5", "contradicts", "semantic", 0.85, now),
            ("e5", "c6", "c7", "supports", "citation", 0.6, now),
            ("e6", "c3", "c4", "refines", "semantic", 0.75, now),
        ]
        for eid, src, tgt, etype, basis, conf, ts in edge_rows:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (eid, src, tgt, etype, basis, conf, ts),
            )
        conn.commit()

        # 1: components returns results
        comps = network_components(conn)
        assert len(comps) > 0, "should find components"
        checks += 1

        # 2: two components (c1-c5 connected, c6-c7 separate)
        assert len(comps) == 2, f"expected 2 components, got {len(comps)}"
        checks += 1

        # 3: larger component has 5 nodes
        assert comps[0]["size"] == 5
        checks += 1

        # 4: smaller component has 2 nodes
        assert comps[1]["size"] == 2
        checks += 1

        # 5: edge types counted
        assert "contradicts" in comps[0]["edge_types"]
        checks += 1

        # 6: bridges returns results
        bridges = bridge_chunks(conn, top_n=10)
        assert len(bridges) > 0
        checks += 1

        # 7: c3 or c4 has high degree (they connect the chain)
        high_degree = [b for b in bridges if b["degree"] >= 3]
        assert len(high_degree) > 0
        checks += 1

        # 8: contradiction clusters
        clusters = contradiction_clusters(conn, min_size=2)
        assert len(clusters) > 0, "should find contradiction clusters"
        checks += 1

        # 9: cluster has contradictions
        assert clusters[0]["contradiction_count"] >= 2
        checks += 1

        # 10: avg confidence is reasonable
        assert 0.0 < clusters[0]["avg_confidence"] <= 1.0
        checks += 1

        # 11: JSON output
        for comp in comps:
            _ = json.dumps(comp)
        for b in bridges:
            _ = json.dumps(b)
        for cl in clusters:
            _ = json.dumps(cl)
        checks += 1

        # 12: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert network_components(conn2) == []
        assert bridge_chunks(conn2) == []
        assert contradiction_clusters(conn2) == []
        checks += 1

        # 13: resolved contradictions excluded from clusters
        conn.execute(
            "UPDATE claim_edges SET resolution = 'resolved', "
            "resolved_utc = ? WHERE edge_id = 'e1'", (now,)
        )
        conn.commit()
        clusters2 = contradiction_clusters(conn, min_size=2)
        if clusters2:
            total_contras = sum(c["contradiction_count"] for c in clusters2)
            assert total_contras < clusters[0]["contradiction_count"] + 1
        checks += 1

        # 14: superseded chunks excluded
        conn.execute(
            "UPDATE chunks SET status = 'superseded' WHERE chunk_id = 'c1'"
        )
        conn.commit()
        comps2 = network_components(conn)
        all_members = set()
        for c in comps2:
            all_members.update(c["members"])
        assert "c1" not in all_members
        checks += 1

    print(f"PASS claim_network selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Claim network analysis for the research corpus"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_comp = sub.add_parser("components",
                            help="Connected components in the claim graph")
    p_comp.add_argument("--db", default=DEFAULT_DB)
    p_comp.add_argument("--json", action="store_true")

    p_bridge = sub.add_parser("bridges",
                              help="Chunks bridging claim components")
    p_bridge.add_argument("--db", default=DEFAULT_DB)
    p_bridge.add_argument("--top", type=int, default=10)
    p_bridge.add_argument("--json", action="store_true")

    p_clust = sub.add_parser("clusters",
                             help="Contradiction clusters")
    p_clust.add_argument("--db", default=DEFAULT_DB)
    p_clust.add_argument("--min-size", type=int, default=2)
    p_clust.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "components":
        results = network_components(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No claim network components found.")
                return
            for c in results:
                types = ", ".join(f"{k}:{v}"
                                 for k, v in c["edge_types"].items())
                print(f"Component {c['component_id']}: "
                      f"{c['size']} chunks ({types})")

    elif args.cmd == "bridges":
        results = bridge_chunks(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No bridge chunks found.")
                return
            print(f"{'Chunk':<15} {'Degree':>7} {'Edges':>6} "
                  f"{'Bridged':>8}")
            print("-" * 40)
            for r in results:
                print(f"{r['chunk_id']:<15} {r['degree']:>7} "
                      f"{r['edge_count']:>6} "
                      f"{r['components_bridged']:>8}")

    elif args.cmd == "clusters":
        results = contradiction_clusters(conn, min_size=args.min_size)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No contradiction clusters found.")
                return
            for c in results:
                print(f"Cluster {c['cluster_id']}: {c['size']} chunks, "
                      f"{c['contradiction_count']} contradictions, "
                      f"avg conf {c['avg_confidence']:.4f}")

    conn.close()


if __name__ == "__main__":
    main()
