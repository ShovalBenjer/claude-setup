#!/usr/bin/env python3
"""Edge chain analysis: multi-hop paths through the claim_edges graph.

claim_network.py measures direct connections.
edge_reachability.py measures which chunks are reachable.
No tool walks multi-hop chains to find transitive support paths
(A supports B, B supports C), transitive tension paths
(A supports B, B contradicts C), or mixed chains, measuring how
argumentative structure propagates across the corpus.

Usage:
    python tools/corpus/edge_chain_analysis.py chains [--db PATH] [--json] [--max-hops N]
    python tools/corpus/edge_chain_analysis.py tension [--db PATH] [--json]
    python tools/corpus/edge_chain_analysis.py hub-chains [--db PATH] [--json]
    python tools/corpus/edge_chain_analysis.py summary [--db PATH] [--json] [--max-hops N]
    python tools/corpus/edge_chain_analysis.py selftest
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


def _build_adjacency(conn) -> dict[str, list[tuple[str, str, str]]]:
    """Build directed adjacency list: source_chunk -> [(target_chunk, edge_type, edge_id)]."""
    rows = conn.execute(
        "SELECT edge_id, source_chunk, target_chunk, edge_type FROM claim_edges"
    ).fetchall()
    adj: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for edge_id, src, tgt, etype in rows:
        adj[src].append((tgt, etype, edge_id))
    return dict(adj)


def find_chains(conn, max_hops: int = 3) -> list[dict]:
    """Find all chains of length 2..max_hops in the claim_edges graph."""
    adj = _build_adjacency(conn)
    chains: list[dict] = []

    def walk(path: list[str], types: list[str], edge_ids: list[str]):
        if len(path) >= 2:
            has_contradiction = "contradicts" in types
            chains.append({
                "chain_length": len(path) - 1,
                "path": list(path),
                "edge_types": list(types),
                "edge_ids": list(edge_ids),
                "has_tension": has_contradiction and any(t != "contradicts" for t in types),
                "uniform": len(set(types)) == 1,
            })
        if len(path) - 1 >= max_hops:
            return
        head = path[-1]
        if head not in adj:
            return
        for tgt, etype, eid in adj[head]:
            if tgt not in path:
                path.append(tgt)
                types.append(etype)
                edge_ids.append(eid)
                walk(path, types, edge_ids)
                path.pop()
                types.pop()
                edge_ids.pop()

    for start in adj:
        walk([start], [], [])

    chains.sort(key=lambda c: (-c["chain_length"], c["path"][0]))
    return chains


def find_tension_chains(conn, max_hops: int = 3) -> list[dict]:
    """Find chains containing both contradicts and non-contradicts edges."""
    all_chains = find_chains(conn, max_hops)
    return [c for c in all_chains if c["has_tension"]]


def hub_chain_analysis(conn, max_hops: int = 3) -> list[dict]:
    """Identify chunks that appear in the most chains (hub nodes)."""
    all_chains = find_chains(conn, max_hops)
    chunk_counts: dict[str, dict] = defaultdict(lambda: {"as_start": 0, "as_end": 0, "as_middle": 0, "total_chains": 0})
    for c in all_chains:
        path = c["path"]
        for i, chunk_id in enumerate(path):
            chunk_counts[chunk_id]["total_chains"] += 1
            if i == 0:
                chunk_counts[chunk_id]["as_start"] += 1
            elif i == len(path) - 1:
                chunk_counts[chunk_id]["as_end"] += 1
            else:
                chunk_counts[chunk_id]["as_middle"] += 1
    return sorted(
        [
            {
                "chunk_id": cid,
                "total_chains": d["total_chains"],
                "as_start": d["as_start"],
                "as_end": d["as_end"],
                "as_middle": d["as_middle"],
            }
            for cid, d in chunk_counts.items()
        ],
        key=lambda r: -r["total_chains"],
    )


def chain_summary(conn, max_hops: int = 3) -> dict:
    """Aggregate chain statistics."""
    all_chains = find_chains(conn, max_hops)

    total_edges = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]

    if not all_chains:
        return {
            "total_edges": total_edges,
            "total_chains": 0,
            "max_chain_length": 0,
            "tension_chains": 0,
            "uniform_chains": 0,
            "avg_chain_length": 0,
            "distinct_chunks_in_chains": 0,
        }

    lengths = [c["chain_length"] for c in all_chains]
    tension = sum(1 for c in all_chains if c["has_tension"])
    uniform = sum(1 for c in all_chains if c["uniform"])
    all_chunks = set()
    for c in all_chains:
        all_chunks.update(c["path"])

    return {
        "total_edges": total_edges,
        "total_chains": len(all_chains),
        "max_chain_length": max(lengths),
        "tension_chains": tension,
        "uniform_chains": uniform,
        "avg_chain_length": round(sum(lengths) / len(lengths), 4),
        "distinct_chunks_in_chains": len(all_chunks),
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

        for i, cid in enumerate(["c1", "c2", "c3", "c4", "c5"], 1):
            conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "s1", i, "intro", "claim", None, "t", "t", 20, f"h{i}", 1000+i, 0, "accepted", None, t1))

        # Chain: c1 -supports-> c2 -contradicts-> c3 -supports-> c4
        # Also: c1 -refines-> c5 (branch)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "contradicts", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "supports", "text", 0.85, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c1", "c5", "refines", "text", 0.7, t1, None, None))
        conn.commit()

        # 1. chains: c1->c2 is a 1-hop chain
        chains = find_chains(conn, max_hops=3)
        hop1 = [c for c in chains if c["chain_length"] == 1]
        assert len(hop1) == 4  # e1, e2, e3, e4
        ok += 1

        # 2. c1->c2->c3 is a 2-hop chain with tension (supports + contradicts)
        hop2 = [c for c in chains if c["chain_length"] == 2]
        c1_c2_c3 = [c for c in hop2 if c["path"] == ["c1", "c2", "c3"]]
        assert len(c1_c2_c3) == 1
        ok += 1

        # 3. that chain has tension
        assert c1_c2_c3[0]["has_tension"] is True
        ok += 1

        # 4. c1->c2->c3->c4 is a 3-hop chain
        hop3 = [c for c in chains if c["chain_length"] == 3]
        assert len(hop3) == 1
        ok += 1

        # 5. the 3-hop chain has tension (supports, contradicts, supports)
        assert hop3[0]["has_tension"] is True
        ok += 1

        # 6. c2->c3->c4 is a 2-hop uniform=False chain (contradicts + supports)
        c2_c3_c4 = [c for c in hop2 if c["path"] == ["c2", "c3", "c4"]]
        assert c2_c3_c4[0]["uniform"] is False
        ok += 1

        # 7. tension chains: chains with both contradicts and non-contradicts
        tension = find_tension_chains(conn, max_hops=3)
        assert len(tension) >= 2  # at least c1->c2->c3 and c1->c2->c3->c4
        ok += 1

        # 8. hub analysis: c1 starts the most chains (c1->c2, c1->c5, c1->c2->c3, c1->c2->c3->c4)
        hubs = hub_chain_analysis(conn, max_hops=3)
        c1_hub = [h for h in hubs if h["chunk_id"] == "c1"][0]
        assert c1_hub["as_start"] >= 4  # 4 chains starting from c1
        ok += 1

        # 9. c4 only appears as end
        c4_hub = [h for h in hubs if h["chunk_id"] == "c4"][0]
        assert c4_hub["as_start"] == 0
        ok += 1

        # 10. c2 appears as middle in 2+ chains (c1->c2->c3, c1->c2->c3->c4)
        c2_hub = [h for h in hubs if h["chunk_id"] == "c2"][0]
        assert c2_hub["as_middle"] >= 2
        ok += 1

        # 11. summary: total_chains includes all lengths
        s = chain_summary(conn, max_hops=3)
        assert s["total_chains"] == len(chains)
        ok += 1

        # 12. max_chain_length = 3
        assert s["max_chain_length"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["avg_chain_length"] == s["avg_chain_length"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = chain_summary(conn, max_hops=3)
        assert s["total_chains"] == 0
        assert s["total_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Edge chain analysis")
    ap.add_argument("command", choices=["chains", "tension", "hub-chains", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-hops", type=int, default=3)
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS edge_chain_analysis selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "chains":
        rows = find_chains(conn, args.max_hops)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No chains found.")
            else:
                print(f"{'length':<8} {'path':<40} {'types':<30} {'tension':<8} {'uniform'}")
                for r in rows:
                    path = " -> ".join(r["path"])
                    types = ", ".join(r["edge_types"])
                    print(f"{r['chain_length']:<8} {path:<40} {types:<30} {r['has_tension']!s:<8} {r['uniform']}")
    elif args.command == "tension":
        rows = find_tension_chains(conn, args.max_hops)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tension chains found.")
            else:
                print(f"{'length':<8} {'path':<40} {'types'}")
                for r in rows:
                    path = " -> ".join(r["path"])
                    types = ", ".join(r["edge_types"])
                    print(f"{r['chain_length']:<8} {path:<40} {types}")
    elif args.command == "hub-chains":
        rows = hub_chain_analysis(conn, args.max_hops)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No hub nodes found.")
            else:
                print(f"{'chunk_id':<12} {'total':<8} {'start':<8} {'end':<8} {'middle'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['total_chains']:<8} {r['as_start']:<8} {r['as_end']:<8} {r['as_middle']}")
    elif args.command == "summary":
        s = chain_summary(conn, args.max_hops)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
