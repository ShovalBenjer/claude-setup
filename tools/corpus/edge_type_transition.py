#!/usr/bin/env python3
"""Edge type transition patterns along multi-hop paths.

edge_chain_analysis.py walks directed multi-hop paths.
edge_reciprocity_analysis.py measures mutual vs one-way edges.
No tool analyzes the sequence of edge types along multi-hop paths,
measuring how argumentation tone changes step-by-step (e.g.
supports-then-contradicts vs supports-then-supports), surfacing
rhetorical escalation and argumentation flow patterns.

Usage:
    python tools/corpus/edge_type_transition.py bigrams [--db PATH] [--json]
    python tools/corpus/edge_type_transition.py paths [--db PATH] [--json] [--max-hops N]
    python tools/corpus/edge_type_transition.py flow [--db PATH] [--json]
    python tools/corpus/edge_type_transition.py summary [--db PATH] [--json]
    python tools/corpus/edge_type_transition.py selftest
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


def _build_adjacency(conn) -> dict[str, list[tuple[str, str]]]:
    """Build directed adjacency: chunk -> [(target, edge_type)]."""
    rows = conn.execute(
        "SELECT source_chunk, target_chunk, edge_type FROM claim_edges"
    ).fetchall()
    adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for src, tgt, etype in rows:
        adj[src].append((tgt, etype))
    return dict(adj)


def _walk_paths(adj: dict, max_hops: int = 3) -> list[list[str]]:
    """Walk all paths of length 2..max_hops, returning edge-type sequences."""
    sequences: list[list[str]] = []

    def walk(node: str, types: list[str], visited: set[str]):
        if len(types) >= 2:
            sequences.append(list(types))
        if len(types) >= max_hops:
            return
        for tgt, etype in adj.get(node, []):
            if tgt not in visited:
                visited.add(tgt)
                types.append(etype)
                walk(tgt, types, visited)
                types.pop()
                visited.discard(tgt)

    for start in adj:
        visited = {start}
        for tgt, etype in adj[start]:
            if tgt not in visited:
                visited.add(tgt)
                walk(tgt, [etype], visited)
                visited.discard(tgt)

    return sequences


def type_bigrams(conn) -> list[dict]:
    """Count consecutive edge-type pairs (bigrams) across all 2-hop paths."""
    adj = _build_adjacency(conn)
    if not adj:
        return []

    counts: dict[tuple[str, str], int] = defaultdict(int)
    for start in adj:
        visited = {start}
        for mid, etype1 in adj[start]:
            if mid not in visited:
                for _, etype2 in adj.get(mid, []):
                    counts[(etype1, etype2)] += 1

    result = [
        {"from_type": k[0], "to_type": k[1], "count": v}
        for k, v in counts.items()
    ]
    result.sort(key=lambda r: -r["count"])
    return result


def transition_paths(conn, max_hops: int = 3) -> list[dict]:
    """Count distinct edge-type sequences across multi-hop paths."""
    adj = _build_adjacency(conn)
    if not adj:
        return []

    sequences = _walk_paths(adj, max_hops)
    counts: dict[str, int] = defaultdict(int)
    for seq in sequences:
        key = " -> ".join(seq)
        counts[key] += 1

    result = [{"sequence": k, "count": v, "length": len(k.split(" -> "))} for k, v in counts.items()]
    result.sort(key=lambda r: (-r["count"], r["sequence"]))
    return result


def type_flow(conn) -> list[dict]:
    """Per edge-type, what types tend to follow it in the next hop."""
    adj = _build_adjacency(conn)
    if not adj:
        return []

    follows: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for start in adj:
        visited = {start}
        for mid, etype1 in adj[start]:
            if mid not in visited:
                for _, etype2 in adj.get(mid, []):
                    follows[etype1][etype2] += 1

    result = []
    for etype, nexts in follows.items():
        total = sum(nexts.values())
        dominant = max(nexts, key=lambda t: nexts[t])
        result.append({
            "edge_type": etype,
            "total_transitions": total,
            "next_types": dict(nexts),
            "dominant_next": dominant,
            "dominant_rate": round(nexts[dominant] / total, 4),
        })

    result.sort(key=lambda r: -r["total_transitions"])
    return result


def transition_summary(conn) -> dict:
    """Aggregate transition pattern statistics."""
    bigrams = type_bigrams(conn)
    if not bigrams:
        return {
            "total_bigrams": 0,
            "distinct_bigram_types": 0,
            "reinforcing_bigrams": 0,
            "shifting_bigrams": 0,
            "most_common_bigram": None,
            "reinforcement_rate": 0,
        }

    total = sum(b["count"] for b in bigrams)
    reinforcing = sum(b["count"] for b in bigrams if b["from_type"] == b["to_type"])
    shifting = total - reinforcing

    return {
        "total_bigrams": total,
        "distinct_bigram_types": len(bigrams),
        "reinforcing_bigrams": reinforcing,
        "shifting_bigrams": shifting,
        "most_common_bigram": f"{bigrams[0]['from_type']} -> {bigrams[0]['to_type']}",
        "reinforcement_rate": round(reinforcing / max(total, 1), 4),
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

        # Chain: c1 -supports-> c2 -supports-> c3 -contradicts-> c4 -supports-> c5
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "supports", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "contradicts", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c4", "c5", "supports", "text", 0.6, t1, None, None))
        # Branch: c2 -refines-> c4
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c2", "c4", "refines", "text", 0.5, t1, None, None))
        conn.commit()

        # 1. bigrams: supports->supports exists (c1->c2->c3)
        bg = type_bigrams(conn)
        ss = [b for b in bg if b["from_type"] == "supports" and b["to_type"] == "supports"]
        assert len(ss) == 1 and ss[0]["count"] >= 1
        ok += 1

        # 2. bigrams: supports->contradicts exists (c2->c3->c4)
        sc = [b for b in bg if b["from_type"] == "supports" and b["to_type"] == "contradicts"]
        assert len(sc) == 1
        ok += 1

        # 3. bigrams: contradicts->supports exists (c3->c4->c5)
        cs = [b for b in bg if b["from_type"] == "contradicts" and b["to_type"] == "supports"]
        assert len(cs) == 1
        ok += 1

        # 4. bigrams: supports->refines exists (c1->c2->c4 or c2 branch)
        sr = [b for b in bg if b["from_type"] == "supports" and b["to_type"] == "refines"]
        assert len(sr) == 1
        ok += 1

        # 5. transition_paths: "supports -> supports" sequence exists
        tp = transition_paths(conn, max_hops=3)
        ss_paths = [p for p in tp if p["sequence"] == "supports -> supports"]
        assert len(ss_paths) == 1
        ok += 1

        # 6. transition_paths: 3-hop sequence "supports -> supports -> contradicts" exists
        ssc = [p for p in tp if p["sequence"] == "supports -> supports -> contradicts"]
        assert len(ssc) == 1
        ok += 1

        # 7. all paths have length >= 2
        assert all(p["length"] >= 2 for p in tp)
        ok += 1

        # 8. type_flow: supports has transitions
        fl = type_flow(conn)
        sup_flow = [f for f in fl if f["edge_type"] == "supports"]
        assert len(sup_flow) == 1
        assert sup_flow[0]["total_transitions"] >= 2
        ok += 1

        # 9. type_flow: contradicts has dominant_next = supports
        con_flow = [f for f in fl if f["edge_type"] == "contradicts"]
        assert len(con_flow) == 1
        assert con_flow[0]["dominant_next"] == "supports"
        ok += 1

        # 10. type_flow: refines has transitions (c2->c4->c5)
        ref_flow = [f for f in fl if f["edge_type"] == "refines"]
        assert len(ref_flow) == 1
        ok += 1

        # 11. summary: total_bigrams > 0
        s = transition_summary(conn)
        assert s["total_bigrams"] > 0
        ok += 1

        # 12. summary: reinforcing_bigrams >= 1 (supports->supports)
        assert s["reinforcing_bigrams"] >= 1
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["reinforcement_rate"] == s["reinforcement_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = transition_summary(conn)
        assert s["total_bigrams"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Edge type transition patterns")
    ap.add_argument("command", choices=["bigrams", "paths", "flow", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-hops", type=int, default=3)
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS edge_type_transition selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "bigrams":
        rows = type_bigrams(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No bigrams found.")
            else:
                print(f"{'from_type':<15} {'to_type':<15} {'count'}")
                for r in rows:
                    print(f"{r['from_type']:<15} {r['to_type']:<15} {r['count']}")
    elif args.command == "paths":
        rows = transition_paths(conn, max_hops=args.max_hops)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No transition paths found.")
            else:
                print(f"{'sequence':<50} {'count':<7} {'len'}")
                for r in rows:
                    print(f"{r['sequence']:<50} {r['count']:<7} {r['length']}")
    elif args.command == "flow":
        rows = type_flow(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No flow data found.")
            else:
                print(f"{'type':<15} {'transitions':<13} {'dominant_next':<15} {'rate'}")
                for r in rows:
                    print(f"{r['edge_type']:<15} {r['total_transitions']:<13} {r['dominant_next']:<15} {r['dominant_rate']:.4f}")
    elif args.command == "summary":
        s = transition_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
