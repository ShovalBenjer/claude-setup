#!/usr/bin/env python3
"""Edge reciprocity analysis: mutual vs one-way argumentation.

edge_chain_analysis.py walks multi-hop paths.
chunk_connectivity_profile.py measures degree per chunk.
No tool measures whether edges between chunk pairs are reciprocal
(A->B and B->A both exist), whether reciprocal pairs agree or
disagree in edge type, or what fraction of edges are one-way vs
mutual.

Usage:
    python tools/corpus/edge_reciprocity_analysis.py reciprocal [--db PATH] [--json]
    python tools/corpus/edge_reciprocity_analysis.py asymmetric [--db PATH] [--json]
    python tools/corpus/edge_reciprocity_analysis.py type-agreement [--db PATH] [--json]
    python tools/corpus/edge_reciprocity_analysis.py summary [--db PATH] [--json]
    python tools/corpus/edge_reciprocity_analysis.py selftest
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


def _load_edges(conn) -> list[tuple[str, str, str, str, float]]:
    """Load edges as (edge_id, source_chunk, target_chunk, edge_type, confidence)."""
    return conn.execute(
        "SELECT edge_id, source_chunk, target_chunk, edge_type, confidence FROM claim_edges"
    ).fetchall()


def find_reciprocal_pairs(conn) -> list[dict]:
    """Find chunk pairs with edges in both directions."""
    edges = _load_edges(conn)
    if not edges:
        return []

    forward: dict[tuple[str, str], list[tuple[str, str, float]]] = defaultdict(list)
    for eid, src, tgt, etype, conf in edges:
        forward[(src, tgt)].append((eid, etype, conf))

    seen = set()
    result = []
    for (src, tgt), fwd_edges in forward.items():
        rev_key = (tgt, src)
        if rev_key in forward and (tgt, src) not in seen:
            seen.add((src, tgt))
            seen.add((tgt, src))
            rev_edges = forward[rev_key]
            fwd_types = set(e[1] for e in fwd_edges)
            rev_types = set(e[1] for e in rev_edges)
            agrees = fwd_types == rev_types
            result.append({
                "chunk_a": src,
                "chunk_b": tgt,
                "forward_edges": len(fwd_edges),
                "reverse_edges": len(rev_edges),
                "forward_types": sorted(fwd_types),
                "reverse_types": sorted(rev_types),
                "type_agreement": agrees,
            })

    result.sort(key=lambda r: -(r["forward_edges"] + r["reverse_edges"]))
    return result


def find_asymmetric_edges(conn) -> list[dict]:
    """Find edges with no reciprocal counterpart."""
    edges = _load_edges(conn)
    if not edges:
        return []

    pairs = set()
    for _, src, tgt, _, _ in edges:
        pairs.add((src, tgt))

    result = []
    for eid, src, tgt, etype, conf in edges:
        if (tgt, src) not in pairs:
            result.append({
                "edge_id": eid,
                "source_chunk": src,
                "target_chunk": tgt,
                "edge_type": etype,
                "confidence": conf,
            })

    result.sort(key=lambda r: -r["confidence"])
    return result


def type_agreement_profile(conn) -> list[dict]:
    """How reciprocal pairs compare in edge type."""
    reciprocals = find_reciprocal_pairs(conn)
    if not reciprocals:
        return []

    patterns: dict[str, int] = defaultdict(int)
    for r in reciprocals:
        fwd = ",".join(r["forward_types"])
        rev = ",".join(r["reverse_types"])
        if fwd == rev:
            pattern = f"{fwd} <-> {rev} (agree)"
        else:
            pattern = f"{fwd} -> {rev} (disagree)"
        patterns[pattern] += 1

    result = [{"pattern": p, "count": c} for p, c in patterns.items()]
    result.sort(key=lambda r: -r["count"])
    return result


def reciprocity_summary(conn) -> dict:
    """Aggregate reciprocity statistics."""
    edges = _load_edges(conn)
    if not edges:
        return {
            "total_edges": 0,
            "reciprocal_pairs": 0,
            "reciprocal_edges": 0,
            "asymmetric_edges": 0,
            "reciprocity_rate": 0,
            "type_agreement_rate": 0,
        }

    reciprocals = find_reciprocal_pairs(conn)
    asymmetric = find_asymmetric_edges(conn)

    reciprocal_edge_count = sum(r["forward_edges"] + r["reverse_edges"] for r in reciprocals)
    agreeing = sum(1 for r in reciprocals if r["type_agreement"])

    return {
        "total_edges": len(edges),
        "reciprocal_pairs": len(reciprocals),
        "reciprocal_edges": reciprocal_edge_count,
        "asymmetric_edges": len(asymmetric),
        "reciprocity_rate": round(reciprocal_edge_count / max(len(edges), 1), 4),
        "type_agreement_rate": round(agreeing / max(len(reciprocals), 1), 4),
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

        for i, cid in enumerate(["c1", "c2", "c3", "c4"], 1):
            conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "s1", i, "intro", "claim", None, "t", "t", 20, f"h{i}", 1000+i, 0, "accepted", None, t1))

        # e1: c1->c2 supports (reciprocal pair with e2, same type = agree)
        # e2: c2->c1 supports
        # e3: c1->c3 supports (reciprocal pair with e4, different type = disagree)
        # e4: c3->c1 contradicts
        # e5: c2->c4 refines (asymmetric, no c4->c2)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c1", "supports", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c1", "c3", "supports", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c3", "c1", "contradicts", "text", 0.6, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c2", "c4", "refines", "text", 0.5, t1, None, None))
        conn.commit()

        # 1. reciprocal pairs: 2 (c1-c2, c1-c3)
        rp = find_reciprocal_pairs(conn)
        assert len(rp) == 2
        ok += 1

        # 2. c1-c2 pair has type_agreement = True (both supports)
        c1c2 = [r for r in rp if set([r["chunk_a"], r["chunk_b"]]) == {"c1", "c2"}][0]
        assert c1c2["type_agreement"] is True
        ok += 1

        # 3. c1-c3 pair has type_agreement = False (supports vs contradicts)
        c1c3 = [r for r in rp if set([r["chunk_a"], r["chunk_b"]]) == {"c1", "c3"}][0]
        assert c1c3["type_agreement"] is False
        ok += 1

        # 4. c1-c2 forward_edges + reverse_edges = 2
        assert c1c2["forward_edges"] + c1c2["reverse_edges"] == 2
        ok += 1

        # 5. asymmetric: e5 is the only asymmetric edge
        asym = find_asymmetric_edges(conn)
        assert len(asym) == 1
        ok += 1

        # 6. e5 is the asymmetric edge
        assert asym[0]["edge_id"] == "e5"
        ok += 1

        # 7. type agreement profile has patterns
        tap = type_agreement_profile(conn)
        assert len(tap) >= 1
        ok += 1

        # 8. total pattern count = 2 (one agreeing, one disagreeing)
        total_patterns = sum(r["count"] for r in tap)
        assert total_patterns == 2
        ok += 1

        # 9. summary: reciprocal_pairs = 2
        s = reciprocity_summary(conn)
        assert s["reciprocal_pairs"] == 2
        ok += 1

        # 10. reciprocal_edges = 4 (e1, e2, e3, e4)
        assert s["reciprocal_edges"] == 4
        ok += 1

        # 11. asymmetric_edges = 1 (e5)
        assert s["asymmetric_edges"] == 1
        ok += 1

        # 12. type_agreement_rate = 1/2 = 0.5
        assert s["type_agreement_rate"] == 0.5
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["reciprocity_rate"] == s["reciprocity_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = reciprocity_summary(conn)
        assert s["total_edges"] == 0
        assert s["reciprocal_pairs"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Edge reciprocity analysis")
    ap.add_argument("command", choices=["reciprocal", "asymmetric", "type-agreement", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS edge_reciprocity_analysis selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "reciprocal":
        rows = find_reciprocal_pairs(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No reciprocal pairs found.")
            else:
                print(f"{'chunk_a':<12} {'chunk_b':<12} {'fwd':<5} {'rev':<5} {'agree'}")
                for r in rows:
                    print(f"{r['chunk_a']:<12} {r['chunk_b']:<12} {r['forward_edges']:<5} {r['reverse_edges']:<5} {r['type_agreement']}")
    elif args.command == "asymmetric":
        rows = find_asymmetric_edges(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No asymmetric edges found.")
            else:
                print(f"{'edge_id':<12} {'source':<12} {'target':<12} {'type':<12} {'conf'}")
                for r in rows:
                    print(f"{r['edge_id']:<12} {r['source_chunk']:<12} {r['target_chunk']:<12} {r['edge_type']:<12} {r['confidence']:.4f}")
    elif args.command == "type-agreement":
        rows = type_agreement_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No type agreement data found.")
            else:
                print(f"{'pattern':<40} {'count'}")
                for r in rows:
                    print(f"{r['pattern']:<40} {r['count']}")
    elif args.command == "summary":
        s = reciprocity_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
