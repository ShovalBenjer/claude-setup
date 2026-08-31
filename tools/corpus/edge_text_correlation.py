#!/usr/bin/env python3
"""Edge text correlation: how chunk text properties relate to claim edges.

source_edge_stance.py profiles edge-type distribution per source.
edge_confidence_profile.py profiles confidence across types and bands.
No tool correlates chunk text properties (word_count, kind) with
claim edge patterns, measuring whether longer or shorter chunks
attract more edges, higher confidence, or different edge types.

Usage:
    python tools/corpus/edge_text_correlation.py by-wordcount [--db PATH] [--json]
    python tools/corpus/edge_text_correlation.py by-kind [--db PATH] [--json]
    python tools/corpus/edge_text_correlation.py density [--db PATH] [--json]
    python tools/corpus/edge_text_correlation.py summary [--db PATH] [--json]
    python tools/corpus/edge_text_correlation.py selftest
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

WORD_COUNT_BANDS = [
    (0, 25, "0-25"),
    (26, 50, "26-50"),
    (51, 100, "51-100"),
    (101, 250, "101-250"),
    (251, 500, "251-500"),
    (501, None, "501+"),
]


def _wc_band(wc: int) -> str:
    for lo, hi, label in WORD_COUNT_BANDS:
        if hi is None:
            if wc >= lo:
                return label
        elif lo <= wc <= hi:
            return label
    return "unknown"


def edges_by_wordcount(conn) -> list[dict]:
    """Edge statistics bucketed by source-chunk word count."""
    rows = conn.execute(
        """
        SELECT c.word_count, e.edge_type, e.confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        WHERE c.word_count IS NOT NULL
        """
    ).fetchall()
    if not rows:
        return []

    bands: dict[str, dict] = {}
    for wc, edge_type, conf in rows:
        b = _wc_band(wc)
        if b not in bands:
            bands[b] = {"edges": 0, "types": defaultdict(int), "confidences": []}
        bands[b]["edges"] += 1
        bands[b]["types"][edge_type] += 1
        bands[b]["confidences"].append(conf)

    result = []
    for b, d in bands.items():
        confs = d["confidences"]
        result.append({
            "band": b,
            "edge_count": d["edges"],
            "edge_types": dict(d["types"]),
            "avg_confidence": round(sum(confs) / len(confs), 4),
            "min_confidence": round(min(confs), 4),
            "max_confidence": round(max(confs), 4),
        })

    band_order = [label for _, _, label in WORD_COUNT_BANDS]
    result.sort(key=lambda r: band_order.index(r["band"]) if r["band"] in band_order else 99)
    return result


def edges_by_chunk_kind(conn) -> list[dict]:
    """Edge statistics per source-chunk kind."""
    rows = conn.execute(
        """
        SELECT c.kind, e.edge_type, e.confidence
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        """
    ).fetchall()
    if not rows:
        return []

    by_kind: dict[str, dict] = {}
    for kind, edge_type, conf in rows:
        if kind not in by_kind:
            by_kind[kind] = {"edges": 0, "types": defaultdict(int), "confidences": []}
        by_kind[kind]["edges"] += 1
        by_kind[kind]["types"][edge_type] += 1
        by_kind[kind]["confidences"].append(conf)

    result = []
    for kind, d in by_kind.items():
        confs = d["confidences"]
        result.append({
            "kind": kind,
            "edge_count": d["edges"],
            "edge_types": dict(d["types"]),
            "avg_confidence": round(sum(confs) / len(confs), 4),
            "dominant_type": max(d["types"], key=d["types"].get),
        })

    result.sort(key=lambda r: -r["edge_count"])
    return result


def edge_density_by_wordcount(conn) -> list[dict]:
    """Edge density (edges per chunk) bucketed by word count."""
    chunk_rows = conn.execute(
        "SELECT chunk_id, word_count FROM chunks WHERE word_count IS NOT NULL"
    ).fetchall()
    if not chunk_rows:
        return []

    chunk_bands: dict[str, int] = defaultdict(int)
    for _, wc in chunk_rows:
        chunk_bands[_wc_band(wc)] += 1

    edge_rows = conn.execute(
        """
        SELECT c.word_count
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        WHERE c.word_count IS NOT NULL
        """
    ).fetchall()

    edge_bands: dict[str, int] = defaultdict(int)
    for (wc,) in edge_rows:
        edge_bands[_wc_band(wc)] += 1

    result = []
    for b, chunk_count in chunk_bands.items():
        edge_count = edge_bands.get(b, 0)
        result.append({
            "band": b,
            "chunks": chunk_count,
            "edges": edge_count,
            "density": round(edge_count / max(chunk_count, 1), 4),
        })

    band_order = [label for _, _, label in WORD_COUNT_BANDS]
    result.sort(key=lambda r: band_order.index(r["band"]) if r["band"] in band_order else 99)
    return result


def edge_text_summary(conn) -> dict:
    """Aggregate text-edge correlation statistics."""
    by_wc = edges_by_wordcount(conn)
    by_kind = edges_by_chunk_kind(conn)
    density = edge_density_by_wordcount(conn)

    if not by_wc:
        return {
            "total_edges_analyzed": 0,
            "word_count_bands": 0,
            "chunk_kinds": 0,
            "highest_density_band": "",
            "lowest_density_band": "",
            "highest_confidence_band": "",
            "avg_density": 0,
        }

    densities = [d for d in density if d["edges"] > 0]
    all_densities = [d for d in density]

    highest_density = max(densities, key=lambda d: d["density"]) if densities else {"band": ""}
    lowest_density = min(all_densities, key=lambda d: d["density"]) if all_densities else {"band": ""}
    highest_conf = max(by_wc, key=lambda r: r["avg_confidence"]) if by_wc else {"band": ""}

    total_edges = sum(r["edge_count"] for r in by_wc)
    total_chunks = sum(d["chunks"] for d in density)
    avg_density = round(total_edges / max(total_chunks, 1), 4)

    return {
        "total_edges_analyzed": total_edges,
        "word_count_bands": len(by_wc),
        "chunk_kinds": len(by_kind),
        "highest_density_band": highest_density["band"],
        "lowest_density_band": lowest_density["band"],
        "highest_confidence_band": highest_conf["band"],
        "avg_density": avg_density,
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

        # c1: 10 words (0-25 band), claim
        # c2: 40 words (26-50 band), claim
        # c3: 150 words (101-250 band), claim
        # c4: 600 words (501+ band), prose
        # c5: 30 words (26-50 band), claim -- no outgoing edges
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 10, "h1", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 40, "h2", 1002, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "results", "claim", None, "t", "t", 150, "h3", 1003, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "discussion", "prose", None, "t", "t", 600, "h4", 1004, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "methods", "claim", None, "t", "t", 30, "h5", 1005, 0, "accepted", None, t1))

        # e1: c1->c2 supports 0.9 (source in 0-25 band)
        # e2: c2->c3 supports 0.8 (source in 26-50 band)
        # e3: c3->c4 contradicts 0.6 (source in 101-250 band)
        # e4: c4->c1 refines 0.7 (source in 501+ band)
        # e5: c1->c3 supports 0.5 (source in 0-25 band)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "supports", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "contradicts", "text", 0.6, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c4", "c1", "refines", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c1", "c3", "supports", "text", 0.5, t1, None, None))
        conn.commit()

        # 1. by-wordcount: 0-25 band has 2 edges (e1, e5)
        bwc = edges_by_wordcount(conn)
        b025 = [r for r in bwc if r["band"] == "0-25"][0]
        assert b025["edge_count"] == 2
        ok += 1

        # 2. 0-25 band avg confidence = (0.9 + 0.5) / 2 = 0.7
        assert b025["avg_confidence"] == 0.7
        ok += 1

        # 3. 501+ band has 1 edge (e4) with confidence 0.7
        b501 = [r for r in bwc if r["band"] == "501+"][0]
        assert b501["edge_count"] == 1
        ok += 1

        # 4. by-kind: "claim" has 4 edges (e1, e2, e3, e5)
        bk = edges_by_chunk_kind(conn)
        claim_k = [r for r in bk if r["kind"] == "claim"][0]
        assert claim_k["edge_count"] == 4
        ok += 1

        # 5. "prose" has 1 edge (e4)
        def_k = [r for r in bk if r["kind"] == "prose"][0]
        assert def_k["edge_count"] == 1
        ok += 1

        # 6. claim dominant type is supports (3 supports vs 1 contradicts)
        assert claim_k["dominant_type"] == "supports"
        ok += 1

        # 7. density: 0-25 band has 1 chunk (c1) and 2 edges, density = 2.0
        dens = edge_density_by_wordcount(conn)
        d025 = [r for r in dens if r["band"] == "0-25"][0]
        assert d025["density"] == 2.0
        ok += 1

        # 8. 26-50 band has 2 chunks (c2, c5) and 1 edge, density = 0.5
        d2650 = [r for r in dens if r["band"] == "26-50"][0]
        assert d2650["density"] == 0.5
        ok += 1

        # 9. 501+ band has 1 chunk (c4) and 1 edge, density = 1.0
        d501 = [r for r in dens if r["band"] == "501+"][0]
        assert d501["density"] == 1.0
        ok += 1

        # 10. summary: total_edges_analyzed = 5
        s = edge_text_summary(conn)
        assert s["total_edges_analyzed"] == 5
        ok += 1

        # 11. highest_density_band = "0-25" (density 2.0)
        assert s["highest_density_band"] == "0-25"
        ok += 1

        # 12. chunk_kinds = 2 (claim, prose)
        assert s["chunk_kinds"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["avg_density"] == s["avg_density"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = edge_text_summary(conn)
        assert s["total_edges_analyzed"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Edge text correlation")
    ap.add_argument("command", choices=["by-wordcount", "by-kind", "density", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS edge_text_correlation selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-wordcount":
        rows = edges_by_wordcount(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge-wordcount data found.")
            else:
                print(f"{'band':<12} {'edges':<8} {'avg_conf':<10} {'min_conf':<10} {'max_conf'}")
                for r in rows:
                    print(f"{r['band']:<12} {r['edge_count']:<8} {r['avg_confidence']:<10.4f} {r['min_confidence']:<10.4f} {r['max_confidence']:.4f}")
    elif args.command == "by-kind":
        rows = edges_by_chunk_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge-kind data found.")
            else:
                print(f"{'kind':<16} {'edges':<8} {'avg_conf':<10} {'dominant'}")
                for r in rows:
                    print(f"{r['kind']:<16} {r['edge_count']:<8} {r['avg_confidence']:<10.4f} {r['dominant_type']}")
    elif args.command == "density":
        rows = edge_density_by_wordcount(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No density data found.")
            else:
                print(f"{'band':<12} {'chunks':<8} {'edges':<8} {'density'}")
                for r in rows:
                    print(f"{r['band']:<12} {r['chunks']:<8} {r['edges']:<8} {r['density']:.4f}")
    elif args.command == "summary":
        s = edge_text_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
