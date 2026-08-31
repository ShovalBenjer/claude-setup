#!/usr/bin/env python3
"""Chunk connectivity profile: how chunks participate in the edge graph.

chunk_position_analysis.py profiles ordinal distribution.
edge_text_correlation.py correlates word count with edges.
No tool profiles per-chunk connectivity in the claim_edges graph,
measuring in-degree, out-degree, and total degree to identify
argumentative hubs and isolated chunks.

Usage:
    python tools/corpus/chunk_connectivity_profile.py degree [--db PATH] [--json]
    python tools/corpus/chunk_connectivity_profile.py by-position [--db PATH] [--json]
    python tools/corpus/chunk_connectivity_profile.py isolated [--db PATH] [--json]
    python tools/corpus/chunk_connectivity_profile.py summary [--db PATH] [--json]
    python tools/corpus/chunk_connectivity_profile.py selftest
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

POSITION_BANDS = [
    (1, 1, "first"),
    (2, 3, "early"),
    (4, 6, "middle"),
    (7, None, "late"),
]


def _position_band(ordinal: int) -> str:
    for lo, hi, label in POSITION_BANDS:
        if hi is None:
            if ordinal >= lo:
                return label
        elif lo <= ordinal <= hi:
            return label
    return "unknown"


def chunk_degree(conn) -> list[dict]:
    """Per-chunk in-degree, out-degree, and total degree."""
    out_rows = conn.execute(
        "SELECT source_chunk, COUNT(*) FROM claim_edges GROUP BY source_chunk"
    ).fetchall()
    in_rows = conn.execute(
        "SELECT target_chunk, COUNT(*) FROM claim_edges GROUP BY target_chunk"
    ).fetchall()

    out_deg: dict[str, int] = dict(out_rows)
    in_deg: dict[str, int] = dict(in_rows)

    all_chunks = set(out_deg.keys()) | set(in_deg.keys())
    if not all_chunks:
        return []

    chunk_info = {}
    rows = conn.execute(
        "SELECT chunk_id, source_id, ordinal, kind FROM chunks"
    ).fetchall()
    for cid, sid, ordinal, kind in rows:
        chunk_info[cid] = {"source_id": sid, "ordinal": ordinal, "kind": kind}

    result = []
    for cid in all_chunks:
        od = out_deg.get(cid, 0)
        ind = in_deg.get(cid, 0)
        info = chunk_info.get(cid, {"source_id": "", "ordinal": 0, "kind": ""})
        result.append({
            "chunk_id": cid,
            "source_id": info["source_id"],
            "ordinal": info["ordinal"],
            "kind": info["kind"],
            "in_degree": ind,
            "out_degree": od,
            "total_degree": ind + od,
        })

    result.sort(key=lambda r: -r["total_degree"])
    return result


def connectivity_by_position(conn) -> list[dict]:
    """Average connectivity metrics grouped by ordinal position band."""
    degrees = chunk_degree(conn)
    if not degrees:
        return []

    bands: dict[str, dict] = defaultdict(lambda: {"in": [], "out": [], "total": [], "count": 0})
    for d in degrees:
        b = _position_band(d["ordinal"])
        bands[b]["in"].append(d["in_degree"])
        bands[b]["out"].append(d["out_degree"])
        bands[b]["total"].append(d["total_degree"])
        bands[b]["count"] += 1

    result = []
    for b, data in bands.items():
        n = data["count"]
        result.append({
            "position": b,
            "chunk_count": n,
            "avg_in_degree": round(sum(data["in"]) / n, 4),
            "avg_out_degree": round(sum(data["out"]) / n, 4),
            "avg_total_degree": round(sum(data["total"]) / n, 4),
            "max_total_degree": max(data["total"]),
        })

    band_order = [label for _, _, label in POSITION_BANDS]
    result.sort(key=lambda r: band_order.index(r["position"]) if r["position"] in band_order else 99)
    return result


def isolated_chunks(conn) -> list[dict]:
    """Chunks with no edges (neither source nor target in any claim_edge)."""
    connected = set()
    for (cid,) in conn.execute("SELECT DISTINCT source_chunk FROM claim_edges").fetchall():
        connected.add(cid)
    for (cid,) in conn.execute("SELECT DISTINCT target_chunk FROM claim_edges").fetchall():
        connected.add(cid)

    rows = conn.execute(
        "SELECT chunk_id, source_id, ordinal, kind, word_count FROM chunks"
    ).fetchall()

    result = []
    for cid, sid, ordinal, kind, wc in rows:
        if cid not in connected:
            result.append({
                "chunk_id": cid,
                "source_id": sid,
                "ordinal": ordinal,
                "kind": kind,
                "word_count": wc,
            })

    result.sort(key=lambda r: (r["source_id"], r["ordinal"]))
    return result


def connectivity_summary(conn) -> dict:
    """Aggregate connectivity statistics."""
    degrees = chunk_degree(conn)
    iso = isolated_chunks(conn)
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    if not degrees and total_chunks == 0:
        return {
            "total_chunks": 0,
            "connected_chunks": 0,
            "isolated_chunks": 0,
            "isolation_rate": 0,
            "total_edges": 0,
            "avg_degree": 0,
            "max_degree": 0,
            "hub_chunks": 0,
        }

    total_edges = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]
    connected = len(degrees)

    if not degrees:
        return {
            "total_chunks": total_chunks,
            "connected_chunks": 0,
            "isolated_chunks": len(iso),
            "isolation_rate": 1.0,
            "total_edges": 0,
            "avg_degree": 0,
            "max_degree": 0,
            "hub_chunks": 0,
        }

    all_degrees = [d["total_degree"] for d in degrees]
    avg_deg = sum(all_degrees) / len(all_degrees)
    max_deg = max(all_degrees)
    hub_threshold = avg_deg * 2
    hubs = sum(1 for d in all_degrees if d >= hub_threshold)

    return {
        "total_chunks": total_chunks,
        "connected_chunks": connected,
        "isolated_chunks": len(iso),
        "isolation_rate": round(len(iso) / max(total_chunks, 1), 4),
        "total_edges": total_edges,
        "avg_degree": round(avg_deg, 4),
        "max_degree": max_deg,
        "hub_chunks": hubs,
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

        # c1: ordinal 1 (first), c2: ordinal 2 (early), c3: ordinal 3 (early)
        # c4: ordinal 5 (middle), c5: ordinal 8 (late) -- c5 has no edges (isolated)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "h1", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 40, "h2", 1002, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "results", "claim", None, "t", "t", 60, "h3", 1003, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 5, "discussion", "claim", None, "t", "t", 80, "h4", 1004, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 8, "appendix", "claim", None, "t", "t", 30, "h5", 1005, 0, "accepted", None, t1))

        # e1: c1->c2, e2: c1->c3, e3: c2->c3, e4: c3->c4, e5: c4->c1
        # c1: out=2, in=1 (from e5), total=3 -- hub
        # c2: out=1, in=1, total=2
        # c3: out=1, in=2, total=3 -- hub
        # c4: out=1, in=1, total=2
        # c5: no edges -- isolated
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "supports", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c2", "c3", "contradicts", "text", 0.7, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c3", "c4", "refines", "text", 0.6, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c4", "c1", "supports", "text", 0.5, t1, None, None))
        conn.commit()

        # 1. degree: c1 total_degree = 3 (out=2, in=1)
        deg = chunk_degree(conn)
        c1d = [d for d in deg if d["chunk_id"] == "c1"][0]
        assert c1d["total_degree"] == 3
        ok += 1

        # 2. c1 out_degree = 2
        assert c1d["out_degree"] == 2
        ok += 1

        # 3. c3 in_degree = 2
        c3d = [d for d in deg if d["chunk_id"] == "c3"][0]
        assert c3d["in_degree"] == 2
        ok += 1

        # 4. 4 connected chunks (c1-c4)
        assert len(deg) == 4
        ok += 1

        # 5. by-position: "first" band has c1 with avg_total_degree = 3
        bp = connectivity_by_position(conn)
        first = [r for r in bp if r["position"] == "first"][0]
        assert first["avg_total_degree"] == 3.0
        ok += 1

        # 6. "early" band has c2, c3 with avg_total_degree = (2+3)/2 = 2.5
        early = [r for r in bp if r["position"] == "early"][0]
        assert early["avg_total_degree"] == 2.5
        ok += 1

        # 7. "middle" band has c4 with avg_total_degree = 2
        mid = [r for r in bp if r["position"] == "middle"][0]
        assert mid["avg_total_degree"] == 2.0
        ok += 1

        # 8. isolated: c5 is isolated
        iso = isolated_chunks(conn)
        assert len(iso) == 1
        assert iso[0]["chunk_id"] == "c5"
        ok += 1

        # 9. isolated chunk has ordinal 8
        assert iso[0]["ordinal"] == 8
        ok += 1

        # 10. summary: connected_chunks = 4
        s = connectivity_summary(conn)
        assert s["connected_chunks"] == 4
        ok += 1

        # 11. isolated_chunks = 1
        assert s["isolated_chunks"] == 1
        ok += 1

        # 12. total_edges = 5
        assert s["total_edges"] == 5
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["avg_degree"] == s["avg_degree"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = connectivity_summary(conn)
        assert s["total_chunks"] == 0
        assert s["connected_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Chunk connectivity profile")
    ap.add_argument("command", choices=["degree", "by-position", "isolated", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS chunk_connectivity_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "degree":
        rows = chunk_degree(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No connectivity data found.")
            else:
                print(f"{'chunk_id':<16} {'source':<12} {'ord':<5} {'kind':<10} {'in':<5} {'out':<5} {'total'}")
                for r in rows:
                    print(f"{r['chunk_id']:<16} {r['source_id']:<12} {r['ordinal']:<5} {r['kind']:<10} {r['in_degree']:<5} {r['out_degree']:<5} {r['total_degree']}")
    elif args.command == "by-position":
        rows = connectivity_by_position(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No position data found.")
            else:
                print(f"{'position':<10} {'chunks':<8} {'avg_in':<8} {'avg_out':<8} {'avg_total':<10} {'max'}")
                for r in rows:
                    print(f"{r['position']:<10} {r['chunk_count']:<8} {r['avg_in_degree']:<8.4f} {r['avg_out_degree']:<8.4f} {r['avg_total_degree']:<10.4f} {r['max_total_degree']}")
    elif args.command == "isolated":
        rows = isolated_chunks(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No isolated chunks found.")
            else:
                print(f"{'chunk_id':<16} {'source':<12} {'ord':<5} {'kind':<10} {'words'}")
                for r in rows:
                    print(f"{r['chunk_id']:<16} {r['source_id']:<12} {r['ordinal']:<5} {r['kind']:<10} {r['word_count']}")
    elif args.command == "summary":
        s = connectivity_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
