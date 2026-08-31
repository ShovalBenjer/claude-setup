#!/usr/bin/env python3
"""Edge confidence profile: how confidence scores distribute across claim edges.

edge_chain_analysis.py walks multi-hop paths.
edge_bridge_analysis.py identifies structural bridges.
No tool profiles how the confidence column in claim_edges distributes
across edge types, sources, or confidence bands, measuring where the
corpus has high-confidence vs low-confidence argumentative connections.

Usage:
    python tools/corpus/edge_confidence_profile.py by-band [--db PATH] [--json]
    python tools/corpus/edge_confidence_profile.py by-type [--db PATH] [--json]
    python tools/corpus/edge_confidence_profile.py by-source [--db PATH] [--json]
    python tools/corpus/edge_confidence_profile.py summary [--db PATH] [--json]
    python tools/corpus/edge_confidence_profile.py selftest
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


def _confidence_band(c: float) -> str:
    if c < 0.25:
        return "low (<0.25)"
    if c < 0.5:
        return "medium (0.25-0.5)"
    if c < 0.75:
        return "high (0.5-0.75)"
    return "very-high (0.75+)"


def edges_by_confidence_band(conn) -> list[dict]:
    """Edge statistics per confidence band."""
    rows = conn.execute(
        "SELECT edge_id, edge_type, confidence FROM claim_edges WHERE confidence IS NOT NULL"
    ).fetchall()
    bands: dict[str, dict] = {}
    for edge_id, edge_type, conf in rows:
        b = _confidence_band(conf)
        if b not in bands:
            bands[b] = {"edges": set(), "types": set(), "confidences": []}
        bands[b]["edges"].add(edge_id)
        bands[b]["types"].add(edge_type)
        bands[b]["confidences"].append(conf)

    return sorted(
        [
            {
                "band": b,
                "edge_count": len(d["edges"]),
                "edge_types": len(d["types"]),
                "min_confidence": round(min(d["confidences"]), 4),
                "max_confidence": round(max(d["confidences"]), 4),
                "avg_confidence": round(sum(d["confidences"]) / len(d["confidences"]), 4),
            }
            for b, d in bands.items()
        ],
        key=lambda r: r["min_confidence"],
    )


def confidence_by_edge_type(conn) -> list[dict]:
    """Confidence distribution per edge type."""
    rows = conn.execute(
        "SELECT edge_type, confidence FROM claim_edges WHERE confidence IS NOT NULL"
    ).fetchall()
    types: dict[str, list[float]] = defaultdict(list)
    for edge_type, conf in rows:
        types[edge_type].append(conf)

    return sorted(
        [
            {
                "edge_type": t,
                "edge_count": len(confs),
                "min_confidence": round(min(confs), 4),
                "max_confidence": round(max(confs), 4),
                "avg_confidence": round(sum(confs) / len(confs), 4),
                "bands": len(set(_confidence_band(c) for c in confs)),
            }
            for t, confs in types.items()
        ],
        key=lambda r: -r["avg_confidence"],
    )


def confidence_by_source(conn) -> list[dict]:
    """Confidence distribution per source (via source_chunk)."""
    rows = conn.execute(
        """
        SELECT c.source_id, e.confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        WHERE e.confidence IS NOT NULL
        """
    ).fetchall()
    sources: dict[str, list[float]] = defaultdict(list)
    for source_id, conf in rows:
        sources[source_id].append(conf)

    return sorted(
        [
            {
                "source_id": sid,
                "edge_count": len(confs),
                "min_confidence": round(min(confs), 4),
                "max_confidence": round(max(confs), 4),
                "avg_confidence": round(sum(confs) / len(confs), 4),
            }
            for sid, confs in sources.items()
        ],
        key=lambda r: -r["avg_confidence"],
    )


def confidence_summary(conn) -> dict:
    """Aggregate confidence statistics."""
    total_edges = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]
    with_conf = conn.execute(
        "SELECT COUNT(*) FROM claim_edges WHERE confidence IS NOT NULL"
    ).fetchone()[0]

    if with_conf == 0:
        return {
            "total_edges": total_edges,
            "edges_with_confidence": 0,
            "confidence_coverage": 0,
            "min_confidence": 0,
            "max_confidence": 0,
            "avg_confidence": 0,
            "median_confidence": 0,
            "low_confidence_count": 0,
            "high_confidence_count": 0,
        }

    confs = [r[0] for r in conn.execute(
        "SELECT confidence FROM claim_edges WHERE confidence IS NOT NULL ORDER BY confidence"
    ).fetchall()]

    mid = len(confs) // 2
    median = confs[mid] if len(confs) % 2 == 1 else (confs[mid - 1] + confs[mid]) / 2

    low = sum(1 for c in confs if c < 0.5)
    high = sum(1 for c in confs if c >= 0.75)

    return {
        "total_edges": total_edges,
        "edges_with_confidence": with_conf,
        "confidence_coverage": round(with_conf / max(total_edges, 1), 4),
        "min_confidence": round(min(confs), 4),
        "max_confidence": round(max(confs), 4),
        "avg_confidence": round(sum(confs) / len(confs), 4),
        "median_confidence": round(median, 4),
        "low_confidence_count": low,
        "high_confidence_count": high,
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

        for i, cid in enumerate(["c1", "c2", "c3", "c4", "c5"], 1):
            sid = "s1" if i <= 3 else "s2"
            conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, i, "intro", "claim", None, "t", "t", 20, f"h{i}", 1000+i, 0, "accepted", None, t1))

        # e1: very-high confidence supports, e2: low confidence contradicts
        # e3: medium confidence refines, e4: very-high confidence supports
        # e5: high confidence supports
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "contradicts", "text", 0.2, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "refines", "text", 0.45, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c4", "c5", "supports", "text", 0.85, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c1", "c3", "supports", "text", 0.6, t1, None, None))
        conn.commit()

        # 1. by-band: "very-high (0.75+)" has 2 edges (e1=0.9, e4=0.85)
        bb = edges_by_confidence_band(conn)
        vh = [r for r in bb if r["band"] == "very-high (0.75+)"][0]
        assert vh["edge_count"] == 2
        ok += 1

        # 2. "low (<0.25)" has 1 edge (e2=0.2)
        low = [r for r in bb if r["band"] == "low (<0.25)"][0]
        assert low["edge_count"] == 1
        ok += 1

        # 3. "medium (0.25-0.5)" has 1 edge (e3=0.45)
        med = [r for r in bb if r["band"] == "medium (0.25-0.5)"][0]
        assert med["edge_count"] == 1
        ok += 1

        # 4. by-type: "supports" avg confidence = (0.9 + 0.85 + 0.6) / 3
        bt = confidence_by_edge_type(conn)
        supports = [r for r in bt if r["edge_type"] == "supports"][0]
        assert supports["edge_count"] == 3
        ok += 1

        # 5. "contradicts" has 1 edge with confidence 0.2
        contradicts = [r for r in bt if r["edge_type"] == "contradicts"][0]
        assert contradicts["avg_confidence"] == 0.2
        ok += 1

        # 6. by-source: s1 has edges e1, e2, e3, e5 (source_chunks c1, c2, c3, c1)
        bs = confidence_by_source(conn)
        s1 = [r for r in bs if r["source_id"] == "s1"][0]
        assert s1["edge_count"] == 4
        ok += 1

        # 7. s2 has edge e4 (confidence 0.85)
        s2 = [r for r in bs if r["source_id"] == "s2"][0]
        assert s2["avg_confidence"] == 0.85
        ok += 1

        # 8. summary: edges_with_confidence = 5 (all have confidence)
        s = confidence_summary(conn)
        assert s["edges_with_confidence"] == 5
        ok += 1

        # 9. total_edges = 5
        assert s["total_edges"] == 5
        ok += 1

        # 10. min_confidence = 0.2
        assert s["min_confidence"] == 0.2
        ok += 1

        # 11. max_confidence = 0.9
        assert s["max_confidence"] == 0.9
        ok += 1

        # 12. low_confidence_count = 2 (e2=0.2, e3=0.45 both < 0.5)
        assert s["low_confidence_count"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["median_confidence"] == s["median_confidence"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = confidence_summary(conn)
        assert s["total_edges"] == 0
        assert s["edges_with_confidence"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Edge confidence profile")
    ap.add_argument("command", choices=["by-band", "by-type", "by-source", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS edge_confidence_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-band":
        rows = edges_by_confidence_band(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No confidence data found.")
            else:
                print(f"{'band':<22} {'edges':<8} {'types':<8} {'min':<8} {'max':<8} {'avg'}")
                for r in rows:
                    print(f"{r['band']:<22} {r['edge_count']:<8} {r['edge_types']:<8} {r['min_confidence']:<8.4f} {r['max_confidence']:<8.4f} {r['avg_confidence']:.4f}")
    elif args.command == "by-type":
        rows = confidence_by_edge_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge type confidence data found.")
            else:
                print(f"{'edge_type':<15} {'edges':<8} {'min':<8} {'max':<8} {'avg':<8} {'bands'}")
                for r in rows:
                    print(f"{r['edge_type']:<15} {r['edge_count']:<8} {r['min_confidence']:<8.4f} {r['max_confidence']:<8.4f} {r['avg_confidence']:<8.4f} {r['bands']}")
    elif args.command == "by-source":
        rows = confidence_by_source(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No source confidence data found.")
            else:
                print(f"{'source_id':<16} {'edges':<8} {'min':<8} {'max':<8} {'avg'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['edge_count']:<8} {r['min_confidence']:<8.4f} {r['max_confidence']:<8.4f} {r['avg_confidence']:.4f}")
    elif args.command == "summary":
        s = confidence_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
