#!/usr/bin/env python3
"""Source edge stance: per-source edge-type distribution.

source_impact.py ranks sources by total edge count.
edge_confidence_profile.py breaks down confidence by type or band.
No tool profiles how edge_type distributes per source, revealing
which sources produce predominantly supports vs contradicts edges
and measuring argumentative stance at the source level.

Usage:
    python tools/corpus/source_edge_stance.py stance [--db PATH] [--json]
    python tools/corpus/source_edge_stance.py cross-source [--db PATH] [--json]
    python tools/corpus/source_edge_stance.py outliers [--db PATH] [--json]
    python tools/corpus/source_edge_stance.py summary [--db PATH] [--json]
    python tools/corpus/source_edge_stance.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def stance_profile(conn) -> list[dict]:
    """Per-source edge-type distribution from outgoing edges."""
    rows = conn.execute(
        """
        SELECT c.source_id, e.edge_type, COUNT(*) as cnt
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        GROUP BY c.source_id, e.edge_type
        """
    ).fetchall()
    if not rows:
        return []

    by_source: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for source_id, edge_type, cnt in rows:
        by_source[source_id][edge_type] = cnt

    result = []
    for sid, types in by_source.items():
        total = sum(types.values())
        result.append({
            "source_id": sid,
            "total_edges": total,
            "edge_types": dict(types),
            "supports_rate": round(types.get("supports", 0) / max(total, 1), 4),
            "contradicts_rate": round(types.get("contradicts", 0) / max(total, 1), 4),
            "dominant_type": max(types, key=types.get),
        })

    result.sort(key=lambda r: -r["total_edges"])
    return result


def cross_source_edges(conn) -> list[dict]:
    """Pairwise source connections via claim_edges with edge-type breakdown."""
    rows = conn.execute(
        """
        SELECT cs.source_id, ct.source_id, e.edge_type, COUNT(*) as cnt
        FROM claim_edges e
        JOIN chunks cs ON cs.chunk_id = e.source_chunk
        JOIN chunks ct ON ct.chunk_id = e.target_chunk
        WHERE cs.source_id != ct.source_id
        GROUP BY cs.source_id, ct.source_id, e.edge_type
        """
    ).fetchall()
    if not rows:
        return []

    pairs: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for src, tgt, edge_type, cnt in rows:
        pairs[(src, tgt)][edge_type] = cnt

    result = []
    for (src, tgt), types in pairs.items():
        total = sum(types.values())
        result.append({
            "source_a": src,
            "source_b": tgt,
            "total_edges": total,
            "edge_types": dict(types),
            "dominant_type": max(types, key=types.get),
        })

    result.sort(key=lambda r: -r["total_edges"])
    return result


def stance_outliers(conn) -> list[dict]:
    """Sources whose edge-type ratios deviate most from corpus averages."""
    profiles = stance_profile(conn)
    if not profiles:
        return []

    all_types: dict[str, int] = defaultdict(int)
    total_all = 0
    for p in profiles:
        for etype, cnt in p["edge_types"].items():
            all_types[etype] += cnt
            total_all += cnt

    if total_all == 0:
        return []

    corpus_rates = {t: cnt / total_all for t, cnt in all_types.items()}

    result = []
    for p in profiles:
        total = p["total_edges"]
        if total < 2:
            continue
        max_dev = 0.0
        max_dev_type = ""
        for etype in corpus_rates:
            src_rate = p["edge_types"].get(etype, 0) / total
            dev = abs(src_rate - corpus_rates[etype])
            if dev > max_dev:
                max_dev = dev
                max_dev_type = etype

        result.append({
            "source_id": p["source_id"],
            "total_edges": total,
            "max_deviation": round(max_dev, 4),
            "deviation_type": max_dev_type,
            "source_rate": round(p["edge_types"].get(max_dev_type, 0) / total, 4),
            "corpus_rate": round(corpus_rates.get(max_dev_type, 0), 4),
        })

    result.sort(key=lambda r: -r["max_deviation"])
    return result


def stance_summary(conn) -> dict:
    """Aggregate stance statistics."""
    profiles = stance_profile(conn)
    if not profiles:
        return {
            "total_sources": 0,
            "sources_with_edges": 0,
            "total_edges": 0,
            "edge_type_counts": {},
            "corpus_supports_rate": 0,
            "corpus_contradicts_rate": 0,
            "dominant_supports_sources": 0,
            "dominant_contradicts_sources": 0,
        }

    total_sources = conn.execute(
        "SELECT COUNT(DISTINCT source_id) FROM chunks"
    ).fetchone()[0]

    all_types: dict[str, int] = defaultdict(int)
    total_edges = 0
    dom_supports = 0
    dom_contradicts = 0

    for p in profiles:
        for etype, cnt in p["edge_types"].items():
            all_types[etype] += cnt
            total_edges += cnt
        if p["dominant_type"] == "supports":
            dom_supports += 1
        elif p["dominant_type"] == "contradicts":
            dom_contradicts += 1

    cross = cross_source_edges(conn)

    return {
        "total_sources": total_sources,
        "sources_with_edges": len(profiles),
        "total_edges": total_edges,
        "edge_type_counts": dict(all_types),
        "corpus_supports_rate": round(all_types.get("supports", 0) / max(total_edges, 1), 4),
        "corpus_contradicts_rate": round(all_types.get("contradicts", 0) / max(total_edges, 1), 4),
        "dominant_supports_sources": dom_supports,
        "dominant_contradicts_sources": dom_contradicts,
        "cross_source_pairs": len(cross),
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
            ("c1", "s1"), ("c2", "s1"), ("c3", "s1"),
            ("c4", "s2"), ("c5", "s2"),
            ("c6", "s3"),
        ], 1):
            conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, i, "intro", "claim", None, "t", "t", 20, f"h{i}", 1000+i, 0, "accepted", None, t1))

        # s1 chunks: supports-heavy (3 supports, 1 contradicts)
        # s2 chunks: contradicts-heavy (2 contradicts)
        # s3 chunk: 1 refines (cross-source to s1)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "supports", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c2", "c3", "supports", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c2", "c4", "contradicts", "text", 0.6, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c4", "c1", "contradicts", "text", 0.5, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e6", "c5", "c3", "contradicts", "text", 0.4, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e7", "c6", "c1", "refines", "text", 0.7, t1, None, None))
        conn.commit()

        # 1. stance: s1 has 4 outgoing edges (e1, e2, e3, e4)
        sp = stance_profile(conn)
        s1p = [r for r in sp if r["source_id"] == "s1"][0]
        assert s1p["total_edges"] == 4
        ok += 1

        # 2. s1 dominant type is supports (3 supports vs 1 contradicts)
        assert s1p["dominant_type"] == "supports"
        ok += 1

        # 3. s1 supports_rate = 3/4 = 0.75
        assert s1p["supports_rate"] == 0.75
        ok += 1

        # 4. s2 has 2 outgoing edges, both contradicts
        s2p = [r for r in sp if r["source_id"] == "s2"][0]
        assert s2p["contradicts_rate"] == 1.0
        ok += 1

        # 5. s3 dominant type is refines
        s3p = [r for r in sp if r["source_id"] == "s3"][0]
        assert s3p["dominant_type"] == "refines"
        ok += 1

        # 6. cross-source: e4 (s1->s2), e5 (s2->s1), e6 (s2->s1), e7 (s3->s1)
        cs = cross_source_edges(conn)
        assert len(cs) >= 3
        ok += 1

        # 7. s2->s1 cross-source pair has 2 edges (e5 contradicts, e6 contradicts)
        s2_to_s1 = [r for r in cs if r["source_a"] == "s2" and r["source_b"] == "s1"][0]
        assert s2_to_s1["total_edges"] == 2
        ok += 1

        # 8. s3->s1 cross-source pair has 1 edge (e7 refines)
        s3_to_s1 = [r for r in cs if r["source_a"] == "s3" and r["source_b"] == "s1"][0]
        assert s3_to_s1["dominant_type"] == "refines"
        ok += 1

        # 9. outliers: s2 should be an outlier (100% contradicts vs corpus avg)
        out = stance_outliers(conn)
        assert len(out) > 0
        ok += 1

        # 10. s2 has high deviation (all contradicts, corpus is mixed)
        s2_out = [r for r in out if r["source_id"] == "s2"][0]
        assert s2_out["max_deviation"] > 0.2
        ok += 1

        # 11. summary: sources_with_edges = 3
        s = stance_summary(conn)
        assert s["sources_with_edges"] == 3
        ok += 1

        # 12. total_edges = 7
        assert s["total_edges"] == 7
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["corpus_supports_rate"] == s["corpus_supports_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = stance_summary(conn)
        assert s["total_sources"] == 0
        assert s["sources_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Source edge stance")
    ap.add_argument("command", choices=["stance", "cross-source", "outliers", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS source_edge_stance selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "stance":
        rows = stance_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge stance data found.")
            else:
                print(f"{'source_id':<16} {'edges':<8} {'supports':<10} {'contradicts':<12} {'dominant'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['total_edges']:<8} {r['supports_rate']:<10.4f} {r['contradicts_rate']:<12.4f} {r['dominant_type']}")
    elif args.command == "cross-source":
        rows = cross_source_edges(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cross-source edges found.")
            else:
                print(f"{'source_a':<12} {'source_b':<12} {'edges':<8} {'dominant'}")
                for r in rows:
                    print(f"{r['source_a']:<12} {r['source_b']:<12} {r['total_edges']:<8} {r['dominant_type']}")
    elif args.command == "outliers":
        rows = stance_outliers(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No stance outliers found.")
            else:
                print(f"{'source_id':<16} {'edges':<8} {'max_dev':<10} {'type':<15} {'src_rate':<10} {'corpus_rate'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['total_edges']:<8} {r['max_deviation']:<10.4f} {r['deviation_type']:<15} {r['source_rate']:<10.4f} {r['corpus_rate']:.4f}")
    elif args.command == "summary":
        s = stance_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
