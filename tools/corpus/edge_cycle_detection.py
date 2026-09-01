#!/usr/bin/env python3
"""Edge cycle detection: find closed loops in the claim_edges graph.

edge_chain_analysis.py walks acyclic multi-hop paths.
No tool detects cycles where argumentation circles back on itself
(A supports B, B supports C, C contradicts A), measuring how many
chunks participate in circular reasoning and which edge types
appear in cycles.

Usage:
    python tools/corpus/edge_cycle_detection.py cycles [--db PATH] [--json] [--max-length N]
    python tools/corpus/edge_cycle_detection.py by-type [--db PATH] [--json]
    python tools/corpus/edge_cycle_detection.py members [--db PATH] [--json]
    python tools/corpus/edge_cycle_detection.py summary [--db PATH] [--json] [--max-length N]
    python tools/corpus/edge_cycle_detection.py selftest
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


def find_cycles(conn, max_length: int = 5) -> list[dict]:
    """Find all simple cycles up to max_length in the claim_edges graph.

    Returns cycles as lists of nodes where the last node connects back
    to the first. Each cycle is normalized so the lexicographically
    smallest node comes first, preventing duplicate reporting.
    """
    adj = _build_adjacency(conn)
    seen_cycles: set[tuple[str, ...]] = set()
    cycles: list[dict] = []

    def _normalize(path: list[str]) -> tuple[str, ...]:
        min_idx = path.index(min(path))
        rotated = path[min_idx:] + path[:min_idx]
        return tuple(rotated)

    def walk(start: str, path: list[str], types: list[str], edge_ids: list[str]):
        if len(path) > max_length:
            return
        head = path[-1]
        if head not in adj:
            return
        for tgt, etype, eid in adj[head]:
            if tgt == start and len(path) >= 2:
                norm = _normalize(path)
                if norm not in seen_cycles:
                    seen_cycles.add(norm)
                    has_contradiction = "contradicts" in types + [etype]
                    has_non_contradiction = any(t != "contradicts" for t in types + [etype])
                    cycles.append({
                        "cycle_length": len(path),
                        "path": list(path) + [start],
                        "edge_types": types + [etype],
                        "edge_ids": edge_ids + [eid],
                        "has_tension": has_contradiction and has_non_contradiction,
                        "uniform": len(set(types + [etype])) == 1,
                    })
            elif tgt not in path and len(path) < max_length:
                path.append(tgt)
                types.append(etype)
                edge_ids.append(eid)
                walk(start, path, types, edge_ids)
                path.pop()
                types.pop()
                edge_ids.pop()

    for start in sorted(adj):
        walk(start, [start], [], [])

    cycles.sort(key=lambda c: (c["cycle_length"], c["path"][0]))
    return cycles


def cycles_by_edge_type(conn, max_length: int = 5) -> list[dict]:
    """Edge type distribution across cycles."""
    all_cycles = find_cycles(conn, max_length)
    types: dict[str, dict] = defaultdict(lambda: {"cycle_count": 0, "total_edges": 0, "chunks": set()})
    for c in all_cycles:
        for i, etype in enumerate(c["edge_types"]):
            types[etype]["cycle_count"] += 1
            types[etype]["total_edges"] += 1
            types[etype]["chunks"].add(c["path"][i])
    return sorted(
        [
            {
                "edge_type": t,
                "cycle_count": d["cycle_count"],
                "total_edges": d["total_edges"],
                "distinct_chunks": len(d["chunks"]),
            }
            for t, d in types.items()
        ],
        key=lambda r: -r["cycle_count"],
    )


def cycle_members(conn, max_length: int = 5) -> list[dict]:
    """Chunks participating in cycles, ranked by cycle count."""
    all_cycles = find_cycles(conn, max_length)
    members: dict[str, dict] = defaultdict(lambda: {"cycle_count": 0, "min_cycle": float("inf"), "max_cycle": 0, "edge_types": set()})
    for c in all_cycles:
        for node in c["path"][:-1]:
            members[node]["cycle_count"] += 1
            members[node]["min_cycle"] = min(members[node]["min_cycle"], c["cycle_length"])
            members[node]["max_cycle"] = max(members[node]["max_cycle"], c["cycle_length"])
            members[node]["edge_types"].update(c["edge_types"])
    return sorted(
        [
            {
                "chunk_id": cid,
                "cycle_count": d["cycle_count"],
                "min_cycle_length": d["min_cycle"],
                "max_cycle_length": d["max_cycle"],
                "edge_types_seen": len(d["edge_types"]),
            }
            for cid, d in members.items()
        ],
        key=lambda r: -r["cycle_count"],
    )


def cycle_summary(conn, max_length: int = 5) -> dict:
    """Aggregate cycle statistics."""
    all_cycles = find_cycles(conn, max_length)
    total_edges = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]
    total_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM ("
        "  SELECT source_chunk AS chunk_id FROM claim_edges"
        "  UNION"
        "  SELECT target_chunk AS chunk_id FROM claim_edges"
        ")"
    ).fetchone()[0]

    if not all_cycles:
        return {
            "total_edges": total_edges,
            "total_chunks_in_graph": total_chunks,
            "total_cycles": 0,
            "max_cycle_length": 0,
            "tension_cycles": 0,
            "uniform_cycles": 0,
            "avg_cycle_length": 0,
            "chunks_in_cycles": 0,
            "cycle_participation_rate": 0,
        }

    lengths = [c["cycle_length"] for c in all_cycles]
    tension = sum(1 for c in all_cycles if c["has_tension"])
    uniform = sum(1 for c in all_cycles if c["uniform"])
    all_members = set()
    for c in all_cycles:
        all_members.update(c["path"][:-1])

    return {
        "total_edges": total_edges,
        "total_chunks_in_graph": total_chunks,
        "total_cycles": len(all_cycles),
        "max_cycle_length": max(lengths),
        "tension_cycles": tension,
        "uniform_cycles": uniform,
        "avg_cycle_length": round(sum(lengths) / len(lengths), 4),
        "chunks_in_cycles": len(all_members),
        "cycle_participation_rate": round(len(all_members) / max(total_chunks, 1), 4),
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

        # Triangle cycle: c1 -> c2 -> c3 -> c1
        # Plus: c3 -> c4 (no cycle), c4 -> c5 -> c3 (second cycle sharing c3)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "contradicts", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "supports", "text", 0.85, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c3", "c4", "refines", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c4", "c5", "supports", "text", 0.75, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e6", "c5", "c3", "supports", "text", 0.8, t1, None, None))
        conn.commit()

        # 1. find_cycles detects the c1->c2->c3 triangle
        cyc = find_cycles(conn, max_length=5)
        tri = [c for c in cyc if c["cycle_length"] == 3 and "c1" in c["path"]]
        assert len(tri) == 1
        ok += 1

        # 2. the triangle has tension (supports + contradicts)
        assert tri[0]["has_tension"] is True
        ok += 1

        # 3. the triangle is not uniform
        assert tri[0]["uniform"] is False
        ok += 1

        # 4. c3->c4->c5->c3 is a second triangle
        tri2 = [c for c in cyc if c["cycle_length"] == 3 and "c4" in c["path"]]
        assert len(tri2) == 1
        ok += 1

        # 5. the c3-c4-c5 triangle is not uniform (refines + supports + supports)
        assert tri2[0]["uniform"] is False
        ok += 1

        # 6. total cycles = 2 triangles
        assert len(cyc) == 2
        ok += 1

        # 7. by-type: "supports" appears in cycles
        bt = cycles_by_edge_type(conn, max_length=5)
        supports = [r for r in bt if r["edge_type"] == "supports"]
        assert len(supports) == 1 and supports[0]["cycle_count"] >= 2
        ok += 1

        # 8. "contradicts" appears in 1 cycle
        contradicts = [r for r in bt if r["edge_type"] == "contradicts"]
        assert len(contradicts) == 1 and contradicts[0]["cycle_count"] == 1
        ok += 1

        # 9. members: c3 participates in 2 cycles (both triangles)
        mem = cycle_members(conn, max_length=5)
        c3_mem = [m for m in mem if m["chunk_id"] == "c3"][0]
        assert c3_mem["cycle_count"] == 2
        ok += 1

        # 10. c1 participates in 1 cycle
        c1_mem = [m for m in mem if m["chunk_id"] == "c1"][0]
        assert c1_mem["cycle_count"] == 1
        ok += 1

        # 11. summary: total_cycles = 2
        s = cycle_summary(conn, max_length=5)
        assert s["total_cycles"] == 2
        ok += 1

        # 12. chunks_in_cycles = 5 (c1, c2, c3, c4, c5 all participate)
        assert s["chunks_in_cycles"] == 5
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["avg_cycle_length"] == s["avg_cycle_length"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = cycle_summary(conn, max_length=5)
        assert s["total_cycles"] == 0
        assert s["chunks_in_cycles"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Edge cycle detection")
    ap.add_argument("command", choices=["cycles", "by-type", "members", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-length", type=int, default=5)
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS edge_cycle_detection selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "cycles":
        rows = find_cycles(conn, args.max_length)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cycles found.")
            else:
                print(f"{'length':<8} {'path':<40} {'types':<30} {'tension':<8} {'uniform'}")
                for r in rows:
                    path = " -> ".join(r["path"])
                    types = ", ".join(r["edge_types"])
                    print(f"{r['cycle_length']:<8} {path:<40} {types:<30} {r['has_tension']!s:<8} {r['uniform']}")
    elif args.command == "by-type":
        rows = cycles_by_edge_type(conn, args.max_length)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cycle edge type data found.")
            else:
                print(f"{'edge_type':<15} {'cycles':<10} {'edges':<10} {'chunks'}")
                for r in rows:
                    print(f"{r['edge_type']:<15} {r['cycle_count']:<10} {r['total_edges']:<10} {r['distinct_chunks']}")
    elif args.command == "members":
        rows = cycle_members(conn, args.max_length)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cycle members found.")
            else:
                print(f"{'chunk_id':<12} {'cycles':<8} {'min_len':<8} {'max_len':<8} {'edge_types'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['cycle_count']:<8} {r['min_cycle_length']:<8} {r['max_cycle_length']:<8} {r['edge_types_seen']}")
    elif args.command == "summary":
        s = cycle_summary(conn, args.max_length)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
