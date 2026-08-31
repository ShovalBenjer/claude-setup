#!/usr/bin/env python3
"""Cross-domain directional edge flow analysis.

domain_edge_profile.py profiles edges per domain but treats source
and target sides symmetrically. domain_edge_depth.py measures edge
density within each domain. No tool maps directional flow between
domains, measuring whether domain X supports domain Y but contradicts
domain Z, revealing inter-field tension and reinforcement patterns.

Usage:
    python tools/corpus/domain_edge_flow.py flow [--db PATH] [--json]
    python tools/corpus/domain_edge_flow.py tension [--db PATH] [--json]
    python tools/corpus/domain_edge_flow.py balance [--db PATH] [--json]
    python tools/corpus/domain_edge_flow.py summary [--db PATH] [--json]
    python tools/corpus/domain_edge_flow.py selftest
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


def _load_domain_edges(conn) -> list[tuple[str, str, str]]:
    """Load (source_domain, target_domain, edge_type) triples.

    A chunk can belong to multiple domains, so one edge can produce
    multiple domain-pair records. Self-domain edges (same domain on
    both sides) are included for completeness.
    """
    rows = conn.execute(
        """
        SELECT sd.domain, td.domain, e.edge_type
        FROM claim_edges e
        JOIN chunk_domains sd ON sd.chunk_id = e.source_chunk
        JOIN chunk_domains td ON td.chunk_id = e.target_chunk
        """
    ).fetchall()
    return rows


def domain_flow(conn) -> list[dict]:
    """Directional edge-type counts between domain pairs."""
    rows = _load_domain_edges(conn)
    if not rows:
        return []

    counts: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for src_dom, tgt_dom, etype in rows:
        counts[(src_dom, tgt_dom)][etype] += 1

    result = []
    for (src, tgt), types in counts.items():
        total = sum(types.values())
        dominant = max(types, key=lambda t: types[t])
        result.append({
            "source_domain": src,
            "target_domain": tgt,
            "total_edges": total,
            "edge_types": dict(types),
            "dominant_type": dominant,
            "is_cross_domain": src != tgt,
        })

    result.sort(key=lambda r: -r["total_edges"])
    return result


def domain_tension(conn) -> list[dict]:
    """Cross-domain pairs with both supports and contradicts edges."""
    rows = _load_domain_edges(conn)
    if not rows:
        return []

    counts: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for src_dom, tgt_dom, etype in rows:
        if src_dom != tgt_dom:
            counts[(src_dom, tgt_dom)][etype] += 1

    result = []
    for (src, tgt), types in counts.items():
        sup = types.get("supports", 0)
        con = types.get("contradicts", 0)
        if sup > 0 and con > 0:
            result.append({
                "source_domain": src,
                "target_domain": tgt,
                "supports": sup,
                "contradicts": con,
                "tension_ratio": round(min(sup, con) / max(sup, con), 4),
                "total": sum(types.values()),
            })

    result.sort(key=lambda r: (-r["tension_ratio"], -r["total"]))
    return result


def domain_balance(conn) -> list[dict]:
    """Per-domain net support balance across all cross-domain edges."""
    rows = _load_domain_edges(conn)
    if not rows:
        return []

    outbound: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    inbound: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for src_dom, tgt_dom, etype in rows:
        if src_dom != tgt_dom:
            outbound[src_dom][etype] += 1
            inbound[tgt_dom][etype] += 1

    all_domains = set(outbound.keys()) | set(inbound.keys())
    if not all_domains:
        return []

    result = []
    for dom in all_domains:
        out_sup = outbound[dom].get("supports", 0)
        out_con = outbound[dom].get("contradicts", 0)
        in_sup = inbound[dom].get("supports", 0)
        in_con = inbound[dom].get("contradicts", 0)
        out_total = sum(outbound[dom].values())
        in_total = sum(inbound[dom].values())

        result.append({
            "domain": dom,
            "outbound_total": out_total,
            "inbound_total": in_total,
            "out_supports": out_sup,
            "out_contradicts": out_con,
            "in_supports": in_sup,
            "in_contradicts": in_con,
            "net_support": (out_sup + in_sup) - (out_con + in_con),
        })

    result.sort(key=lambda r: -(r["outbound_total"] + r["inbound_total"]))
    return result


def flow_summary(conn) -> dict:
    """Aggregate cross-domain flow statistics."""
    fl = domain_flow(conn)
    if not fl:
        return {
            "total_domain_pairs": 0,
            "cross_domain_pairs": 0,
            "self_domain_pairs": 0,
            "cross_domain_edges": 0,
            "self_domain_edges": 0,
            "tension_pairs": 0,
            "avg_net_support": 0,
        }

    cross = [f for f in fl if f["is_cross_domain"]]
    self_pairs = [f for f in fl if not f["is_cross_domain"]]
    tension = domain_tension(conn)
    bal = domain_balance(conn)

    nets = [b["net_support"] for b in bal] if bal else [0]

    return {
        "total_domain_pairs": len(fl),
        "cross_domain_pairs": len(cross),
        "self_domain_pairs": len(self_pairs),
        "cross_domain_edges": sum(f["total_edges"] for f in cross),
        "self_domain_edges": sum(f["total_edges"] for f in self_pairs),
        "tension_pairs": len(tension),
        "avg_net_support": round(sum(nets) / len(nets), 4),
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

        # c1 in domain "ml", c2 in domain "ml", c3 in domain "ethics", c4 in domain "ethics"
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ethics", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "ethics", 0.7, t1))

        # e1: c1(ml)->c3(ethics) supports
        # e2: c2(ml)->c4(ethics) contradicts
        # e3: c3(ethics)->c1(ml) supports
        # e4: c1(ml)->c2(ml) supports (self-domain)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c3", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c4", "contradicts", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "supports", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c1", "c2", "supports", "text", 0.6, t1, None, None))
        conn.commit()

        # 1. flow: ml->ethics pair exists
        fl = domain_flow(conn)
        ml_eth = [f for f in fl if f["source_domain"] == "ml" and f["target_domain"] == "ethics"]
        assert len(ml_eth) == 1
        ok += 1

        # 2. ml->ethics has 2 edges (e1 supports, e2 contradicts)
        assert ml_eth[0]["total_edges"] == 2
        ok += 1

        # 3. ml->ethics is cross-domain
        assert ml_eth[0]["is_cross_domain"] is True
        ok += 1

        # 4. ml->ml self-domain pair exists with 1 edge (e4)
        ml_ml = [f for f in fl if f["source_domain"] == "ml" and f["target_domain"] == "ml"]
        assert len(ml_ml) == 1
        assert ml_ml[0]["total_edges"] == 1
        ok += 1

        # 5. ethics->ml pair has 1 support edge (e3)
        eth_ml = [f for f in fl if f["source_domain"] == "ethics" and f["target_domain"] == "ml"]
        assert len(eth_ml) == 1
        assert eth_ml[0]["edge_types"].get("supports", 0) == 1
        ok += 1

        # 6. tension: ml->ethics has both supports and contradicts
        ten = domain_tension(conn)
        ml_eth_t = [t for t in ten if t["source_domain"] == "ml" and t["target_domain"] == "ethics"]
        assert len(ml_eth_t) == 1
        ok += 1

        # 7. tension ratio: min(1,1)/max(1,1) = 1.0
        assert ml_eth_t[0]["tension_ratio"] == 1.0
        ok += 1

        # 8. ethics->ml has no tension (only supports)
        eth_ml_t = [t for t in ten if t["source_domain"] == "ethics" and t["target_domain"] == "ml"]
        assert len(eth_ml_t) == 0
        ok += 1

        # 9. balance: ml domain has cross-domain outbound edges
        bal = domain_balance(conn)
        ml_bal = [b for b in bal if b["domain"] == "ml"]
        assert len(ml_bal) == 1
        assert ml_bal[0]["outbound_total"] == 2
        ok += 1

        # 10. balance: ethics inbound has 2 edges
        eth_bal = [b for b in bal if b["domain"] == "ethics"]
        assert len(eth_bal) == 1
        assert eth_bal[0]["inbound_total"] == 2
        ok += 1

        # 11. summary: cross_domain_pairs >= 2 (ml->ethics, ethics->ml)
        s = flow_summary(conn)
        assert s["cross_domain_pairs"] >= 2
        ok += 1

        # 12. summary: self_domain_pairs >= 1 (ml->ml)
        assert s["self_domain_pairs"] >= 1
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["avg_net_support"] == s["avg_net_support"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = flow_summary(conn)
        assert s["total_domain_pairs"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Cross-domain directional edge flow")
    ap.add_argument("command", choices=["flow", "tension", "balance", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS domain_edge_flow selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "flow":
        rows = domain_flow(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain flow data found.")
            else:
                print(f"{'src_domain':<15} {'tgt_domain':<15} {'edges':<7} {'dominant':<15} {'cross'}")
                for r in rows:
                    print(f"{r['source_domain']:<15} {r['target_domain']:<15} {r['total_edges']:<7} {r['dominant_type']:<15} {r['is_cross_domain']}")
    elif args.command == "tension":
        rows = domain_tension(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tension pairs found.")
            else:
                print(f"{'src_domain':<15} {'tgt_domain':<15} {'sup':<5} {'con':<5} {'ratio':<8} {'total'}")
                for r in rows:
                    print(f"{r['source_domain']:<15} {r['target_domain']:<15} {r['supports']:<5} {r['contradicts']:<5} {r['tension_ratio']:<8.4f} {r['total']}")
    elif args.command == "balance":
        rows = domain_balance(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain balance data found.")
            else:
                print(f"{'domain':<15} {'out':<5} {'in':<5} {'o_sup':<6} {'o_con':<6} {'i_sup':<6} {'i_con':<6} {'net'}")
                for r in rows:
                    print(f"{r['domain']:<15} {r['outbound_total']:<5} {r['inbound_total']:<5} {r['out_supports']:<6} {r['out_contradicts']:<6} {r['in_supports']:<6} {r['in_contradicts']:<6} {r['net_support']}")
    elif args.command == "summary":
        s = flow_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
