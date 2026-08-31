#!/usr/bin/env python3
"""Source argumentation balance: inbound vs outbound edge tone per source.

source_edge_stance.py profiles outgoing edge-type distribution.
edge_reciprocity_analysis.py measures mutual vs one-way edges.
No tool compares inbound and outbound argumentation tone per source,
measuring whether a source is predominantly cited in support or
contradiction, and whether its own outgoing edges agree with how
others reference it.

Usage:
    python tools/corpus/source_argumentation_balance.py balance [--db PATH] [--json]
    python tools/corpus/source_argumentation_balance.py inbound [--db PATH] [--json]
    python tools/corpus/source_argumentation_balance.py contrast [--db PATH] [--json]
    python tools/corpus/source_argumentation_balance.py summary [--db PATH] [--json]
    python tools/corpus/source_argumentation_balance.py selftest
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


def _load_directed_edges(conn) -> tuple[dict, dict]:
    """Load outbound and inbound edge-type counts per source."""
    rows = conn.execute(
        """
        SELECT cs.source_id as src_source, ct.source_id as tgt_source,
               e.edge_type, e.confidence
        FROM claim_edges e
        JOIN chunks cs ON cs.chunk_id = e.source_chunk
        JOIN chunks ct ON ct.chunk_id = e.target_chunk
        """
    ).fetchall()

    outbound: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    inbound: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for src_source, tgt_source, edge_type, conf in rows:
        outbound[src_source][edge_type].append(conf)
        inbound[tgt_source][edge_type].append(conf)

    return dict(outbound), dict(inbound)


def argumentation_balance(conn) -> list[dict]:
    """Per-source inbound vs outbound edge-type balance."""
    outbound, inbound = _load_directed_edges(conn)
    all_sources = set(outbound.keys()) | set(inbound.keys())

    if not all_sources:
        return []

    result = []
    for sid in all_sources:
        out_types = outbound.get(sid, {})
        in_types = inbound.get(sid, {})
        out_total = sum(len(v) for v in out_types.values())
        in_total = sum(len(v) for v in in_types.values())

        out_supports = len(out_types.get("supports", []))
        out_contradicts = len(out_types.get("contradicts", []))
        in_supports = len(in_types.get("supports", []))
        in_contradicts = len(in_types.get("contradicts", []))

        result.append({
            "source_id": sid,
            "outbound_total": out_total,
            "inbound_total": in_total,
            "out_supports": out_supports,
            "out_contradicts": out_contradicts,
            "in_supports": in_supports,
            "in_contradicts": in_contradicts,
            "net_support": (out_supports + in_supports) - (out_contradicts + in_contradicts),
        })

    result.sort(key=lambda r: -(r["outbound_total"] + r["inbound_total"]))
    return result


def inbound_profile(conn) -> list[dict]:
    """How each source is referenced by others (inbound edges only)."""
    _, inbound = _load_directed_edges(conn)
    if not inbound:
        return []

    result = []
    for sid, types in inbound.items():
        total = sum(len(v) for v in types.values())
        all_confs = [c for confs in types.values() for c in confs]
        result.append({
            "source_id": sid,
            "inbound_edges": total,
            "edge_types": {t: len(v) for t, v in types.items()},
            "avg_confidence": round(sum(all_confs) / len(all_confs), 4),
            "dominant_inbound_type": max(types, key=lambda t: len(types[t])),
        })

    result.sort(key=lambda r: -r["inbound_edges"])
    return result


def stance_contrast(conn) -> list[dict]:
    """Sources where inbound and outbound dominant types differ."""
    outbound, inbound = _load_directed_edges(conn)
    both = set(outbound.keys()) & set(inbound.keys())

    if not both:
        return []

    result = []
    for sid in both:
        out_types = outbound[sid]
        in_types = inbound[sid]

        out_dom = max(out_types, key=lambda t: len(out_types[t]))
        in_dom = max(in_types, key=lambda t: len(in_types[t]))

        if out_dom != in_dom:
            result.append({
                "source_id": sid,
                "outbound_dominant": out_dom,
                "inbound_dominant": in_dom,
                "outbound_total": sum(len(v) for v in out_types.values()),
                "inbound_total": sum(len(v) for v in in_types.values()),
            })

    result.sort(key=lambda r: -(r["outbound_total"] + r["inbound_total"]))
    return result


def balance_summary(conn) -> dict:
    """Aggregate argumentation balance statistics."""
    bal = argumentation_balance(conn)
    if not bal:
        return {
            "total_sources": 0,
            "sources_with_outbound": 0,
            "sources_with_inbound": 0,
            "net_supportive_sources": 0,
            "net_adversarial_sources": 0,
            "contrast_sources": 0,
            "avg_net_support": 0,
        }

    outbound, inbound = _load_directed_edges(conn)
    contrast = stance_contrast(conn)

    net_supportive = sum(1 for b in bal if b["net_support"] > 0)
    net_adversarial = sum(1 for b in bal if b["net_support"] < 0)
    nets = [b["net_support"] for b in bal]

    return {
        "total_sources": len(bal),
        "sources_with_outbound": sum(1 for b in bal if b["outbound_total"] > 0),
        "sources_with_inbound": sum(1 for b in bal if b["inbound_total"] > 0),
        "net_supportive_sources": net_supportive,
        "net_adversarial_sources": net_adversarial,
        "contrast_sources": len(contrast),
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
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None))

        for i, (cid, sid) in enumerate([
            ("c1", "s1"), ("c2", "s1"),
            ("c3", "s2"), ("c4", "s2"),
            ("c5", "s3"),
        ], 1):
            conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, i, "intro", "claim", None, "t", "t", 20, f"h{i}", 1000+i, 0, "accepted", None, t1))

        # s1 outbound: 2 supports (e1 c1->c3, e2 c2->c5)
        # s2 outbound: 2 contradicts (e3 c3->c1, e4 c4->c5)
        # s3 outbound: 1 refines (e5 c5->c3)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c3", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c5", "supports", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "contradicts", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c4", "c5", "contradicts", "text", 0.6, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c5", "c3", "refines", "text", 0.5, t1, None, None))
        conn.commit()

        # 1. balance: s1 out_supports=2, out_contradicts=0
        bal = argumentation_balance(conn)
        s1b = [b for b in bal if b["source_id"] == "s1"][0]
        assert s1b["out_supports"] == 2
        ok += 1

        # 2. s2 out_contradicts=2
        s2b = [b for b in bal if b["source_id"] == "s2"][0]
        assert s2b["out_contradicts"] == 2
        ok += 1

        # 3. s1 in_contradicts=1 (e3 targets c1 in s1)
        assert s1b["in_contradicts"] == 1
        ok += 1

        # 4. s1 net_support = (2+0) - (0+1) = 1
        assert s1b["net_support"] == 1
        ok += 1

        # 5. s2 net_support = (0+1) - (2+0) = -1 (1 inbound support from e1)
        assert s2b["net_support"] == -1
        ok += 1

        # 6. inbound: s3 has 2 inbound edges (e2 supports, e4 contradicts)
        inp = inbound_profile(conn)
        s3i = [r for r in inp if r["source_id"] == "s3"][0]
        assert s3i["inbound_edges"] == 2
        ok += 1

        # 7. s2 inbound: e1 supports + e5 refines = 2
        s2i = [r for r in inp if r["source_id"] == "s2"][0]
        assert s2i["inbound_edges"] == 2
        ok += 1

        # 8. contrast: s2 outbound dominant = contradicts, inbound dominant = supports or refines
        con = stance_contrast(conn)
        s2c = [c for c in con if c["source_id"] == "s2"]
        assert len(s2c) == 1
        assert s2c[0]["outbound_dominant"] == "contradicts"
        ok += 1

        # 9. s1 outbound dominant = supports, inbound = contradicts -> contrast
        s1c = [c for c in con if c["source_id"] == "s1"]
        assert len(s1c) == 1
        ok += 1

        # 10. summary: net_supportive_sources >= 1 (s1)
        s = balance_summary(conn)
        assert s["net_supportive_sources"] >= 1
        ok += 1

        # 11. net_adversarial_sources >= 1 (s2)
        assert s["net_adversarial_sources"] >= 1
        ok += 1

        # 12. contrast_sources >= 2
        assert s["contrast_sources"] >= 2
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
        s = balance_summary(conn)
        assert s["total_sources"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Source argumentation balance")
    ap.add_argument("command", choices=["balance", "inbound", "contrast", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS source_argumentation_balance selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "balance":
        rows = argumentation_balance(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No balance data found.")
            else:
                print(f"{'source':<12} {'out':<5} {'in':<5} {'o_sup':<6} {'o_con':<6} {'i_sup':<6} {'i_con':<6} {'net'}")
                for r in rows:
                    print(f"{r['source_id']:<12} {r['outbound_total']:<5} {r['inbound_total']:<5} {r['out_supports']:<6} {r['out_contradicts']:<6} {r['in_supports']:<6} {r['in_contradicts']:<6} {r['net_support']}")
    elif args.command == "inbound":
        rows = inbound_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No inbound data found.")
            else:
                print(f"{'source':<12} {'inbound':<8} {'avg_conf':<10} {'dominant'}")
                for r in rows:
                    print(f"{r['source_id']:<12} {r['inbound_edges']:<8} {r['avg_confidence']:<10.4f} {r['dominant_inbound_type']}")
    elif args.command == "contrast":
        rows = stance_contrast(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No stance contrasts found.")
            else:
                print(f"{'source':<12} {'out_dom':<15} {'in_dom':<15} {'out_n':<7} {'in_n'}")
                for r in rows:
                    print(f"{r['source_id']:<12} {r['outbound_dominant']:<15} {r['inbound_dominant']:<15} {r['outbound_total']:<7} {r['inbound_total']}")
    elif args.command == "summary":
        s = balance_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
