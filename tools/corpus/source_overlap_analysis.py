#!/usr/bin/env python3
"""Source overlap analysis: measure content overlap between sources.

chunk_similarity_clusters.py clusters chunks by simhash distance.
No tool measures pairwise overlap between sources by comparing chunk
simhash fingerprints across source boundaries, quantifying which
source pairs share the most near-duplicate content.

Usage:
    python tools/corpus/source_overlap_analysis.py pairs [--db PATH] [--json] [--threshold N]
    python tools/corpus/source_overlap_analysis.py matrix [--db PATH] [--json] [--threshold N]
    python tools/corpus/source_overlap_analysis.py isolated [--db PATH] [--json] [--threshold N]
    python tools/corpus/source_overlap_analysis.py summary [--db PATH] [--json] [--threshold N]
    python tools/corpus/source_overlap_analysis.py selftest
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


def _hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _load_chunks_by_source(conn) -> dict[str, list[tuple[str, int]]]:
    """Load chunks grouped by source: source_id -> [(chunk_id, simhash)]."""
    rows = conn.execute(
        "SELECT chunk_id, source_id, simhash FROM chunks WHERE simhash IS NOT NULL"
    ).fetchall()
    by_source: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for chunk_id, source_id, simhash in rows:
        by_source[source_id].append((chunk_id, simhash))
    return dict(by_source)


def find_overlapping_pairs(conn, threshold: int = 3) -> list[dict]:
    """Find source pairs with overlapping chunks (simhash distance <= threshold)."""
    by_source = _load_chunks_by_source(conn)
    sources = sorted(by_source.keys())
    pairs = []

    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            s1, s2 = sources[i], sources[j]
            matches = []
            for c1_id, c1_hash in by_source[s1]:
                for c2_id, c2_hash in by_source[s2]:
                    dist = _hamming_distance(c1_hash, c2_hash)
                    if dist <= threshold:
                        matches.append({
                            "chunk_a": c1_id,
                            "chunk_b": c2_id,
                            "distance": dist,
                        })
            if matches:
                chunks_a = set(m["chunk_a"] for m in matches)
                chunks_b = set(m["chunk_b"] for m in matches)
                pairs.append({
                    "source_a": s1,
                    "source_b": s2,
                    "match_count": len(matches),
                    "chunks_a": len(chunks_a),
                    "chunks_b": len(chunks_b),
                    "total_a": len(by_source[s1]),
                    "total_b": len(by_source[s2]),
                    "overlap_rate_a": round(len(chunks_a) / max(len(by_source[s1]), 1), 4),
                    "overlap_rate_b": round(len(chunks_b) / max(len(by_source[s2]), 1), 4),
                })

    pairs.sort(key=lambda p: -p["match_count"])
    return pairs


def overlap_matrix(conn, threshold: int = 3) -> list[dict]:
    """Per-source overlap summary across all other sources."""
    pairs = find_overlapping_pairs(conn, threshold)
    by_source = _load_chunks_by_source(conn)
    sources: dict[str, dict] = defaultdict(lambda: {"overlapping_sources": 0, "overlapping_chunks": set(), "total_chunks": 0})

    for sid, chunks in by_source.items():
        sources[sid]["total_chunks"] = len(chunks)

    for p in pairs:
        sources[p["source_a"]]["overlapping_sources"] += 1
        sources[p["source_b"]]["overlapping_sources"] += 1
        for pair_data in find_overlapping_pairs(conn, threshold):
            if pair_data["source_a"] == p["source_a"] and pair_data["source_b"] == p["source_b"]:
                break

    for p in pairs:
        by_src = _load_chunks_by_source(conn)
        for c1_id, c1_hash in by_src.get(p["source_a"], []):
            for c2_id, c2_hash in by_src.get(p["source_b"], []):
                if _hamming_distance(c1_hash, c2_hash) <= threshold:
                    sources[p["source_a"]]["overlapping_chunks"].add(c1_id)
                    sources[p["source_b"]]["overlapping_chunks"].add(c2_id)

    return sorted(
        [
            {
                "source_id": sid,
                "total_chunks": d["total_chunks"],
                "overlapping_sources": d["overlapping_sources"],
                "overlapping_chunks": len(d["overlapping_chunks"]),
                "overlap_rate": round(len(d["overlapping_chunks"]) / max(d["total_chunks"], 1), 4),
            }
            for sid, d in sources.items()
        ],
        key=lambda r: -r["overlapping_chunks"],
    )


def find_isolated_sources(conn, threshold: int = 3) -> list[dict]:
    """Sources with no overlapping chunks in any other source."""
    pairs = find_overlapping_pairs(conn, threshold)
    by_source = _load_chunks_by_source(conn)
    involved = set()
    for p in pairs:
        involved.add(p["source_a"])
        involved.add(p["source_b"])

    isolated = []
    for sid, chunks in by_source.items():
        if sid not in involved:
            isolated.append({
                "source_id": sid,
                "chunk_count": len(chunks),
            })

    isolated.sort(key=lambda r: -r["chunk_count"])
    return isolated


def overlap_summary(conn, threshold: int = 3) -> dict:
    """Aggregate overlap statistics."""
    by_source = _load_chunks_by_source(conn)
    total_sources = len(by_source)
    total_chunks = sum(len(v) for v in by_source.values())

    pairs = find_overlapping_pairs(conn, threshold)
    isolated = find_isolated_sources(conn, threshold)

    if not pairs:
        return {
            "total_sources": total_sources,
            "total_chunks_with_simhash": total_chunks,
            "overlapping_pairs": 0,
            "sources_with_overlap": 0,
            "isolated_sources": len(isolated),
            "total_matches": 0,
            "avg_overlap_rate": 0,
            "threshold": threshold,
        }

    involved = set()
    total_matches = 0
    for p in pairs:
        involved.add(p["source_a"])
        involved.add(p["source_b"])
        total_matches += p["match_count"]

    matrix = overlap_matrix(conn, threshold)
    rates = [r["overlap_rate"] for r in matrix if r["overlapping_chunks"] > 0]
    avg_rate = round(sum(rates) / len(rates), 4) if rates else 0

    return {
        "total_sources": total_sources,
        "total_chunks_with_simhash": total_chunks,
        "overlapping_pairs": len(pairs),
        "sources_with_overlap": len(involved),
        "isolated_sources": len(isolated),
        "total_matches": total_matches,
        "avg_overlap_rate": avg_rate,
        "threshold": threshold,
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

        # s1: c1(simhash=0x0F), c2(simhash=0x0E) -- c1 and c2 are near each other
        # s2: c3(simhash=0x0F), c4(simhash=0xFF00) -- c3 overlaps with s1's c1
        # s3: c5(simhash=0xFF000000) -- isolated, far from everything
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "h1", 0x0F, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 20, "h2", 0x0E, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 20, "h3", 0x0F, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s2", 2, "methods", "claim", None, "t", "t", 20, "h4", 0xFF00, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s3", 1, "results", "claim", None, "t", "t", 20, "h5", 0xFF000000, 0, "accepted", None, t1))
        conn.commit()

        # 1. pairs: s1-s2 overlap (c1~c3 dist 0, c2~c3 dist 1)
        pairs = find_overlapping_pairs(conn, threshold=3)
        assert len(pairs) == 1
        ok += 1

        # 2. the pair is s1-s2
        assert pairs[0]["source_a"] == "s1" and pairs[0]["source_b"] == "s2"
        ok += 1

        # 3. match_count = 2 (c1~c3 and c2~c3)
        assert pairs[0]["match_count"] == 2
        ok += 1

        # 4. chunks_a = 2 (c1, c2 both match c3)
        assert pairs[0]["chunks_a"] == 2
        ok += 1

        # 5. chunks_b = 1 (only c3 matches)
        assert pairs[0]["chunks_b"] == 1
        ok += 1

        # 6. isolated: s3 has no overlap with anything
        iso = find_isolated_sources(conn, threshold=3)
        assert len(iso) == 1
        assert iso[0]["source_id"] == "s3"
        ok += 1

        # 7. matrix: s1 has 2 overlapping chunks
        mat = overlap_matrix(conn, threshold=3)
        s1_mat = [r for r in mat if r["source_id"] == "s1"][0]
        assert s1_mat["overlapping_chunks"] == 2
        ok += 1

        # 8. s2 has 1 overlapping chunk
        s2_mat = [r for r in mat if r["source_id"] == "s2"][0]
        assert s2_mat["overlapping_chunks"] == 1
        ok += 1

        # 9. s1 overlap_rate = 2/2 = 1.0
        assert s1_mat["overlap_rate"] == 1.0
        ok += 1

        # 10. s2 overlap_rate = 1/2 = 0.5
        assert s2_mat["overlap_rate"] == 0.5
        ok += 1

        # 11. summary: overlapping_pairs = 1
        s = overlap_summary(conn, threshold=3)
        assert s["overlapping_pairs"] == 1
        ok += 1

        # 12. isolated_sources = 1
        assert s["isolated_sources"] == 1
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["avg_overlap_rate"] == s["avg_overlap_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = overlap_summary(conn, threshold=3)
        assert s["total_sources"] == 0
        assert s["overlapping_pairs"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Source overlap analysis")
    ap.add_argument("command", choices=["pairs", "matrix", "isolated", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--threshold", type=int, default=3)
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS source_overlap_analysis selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "pairs":
        rows = find_overlapping_pairs(conn, args.threshold)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No overlapping source pairs found.")
            else:
                print(f"{'source_a':<12} {'source_b':<12} {'matches':<10} {'chunks_a':<10} {'chunks_b':<10} {'rate_a':<8} {'rate_b'}")
                for r in rows:
                    print(f"{r['source_a']:<12} {r['source_b']:<12} {r['match_count']:<10} {r['chunks_a']:<10} {r['chunks_b']:<10} {r['overlap_rate_a']:<8.4f} {r['overlap_rate_b']:.4f}")
    elif args.command == "matrix":
        rows = overlap_matrix(conn, args.threshold)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No overlap matrix data found.")
            else:
                print(f"{'source_id':<16} {'chunks':<8} {'overlap_src':<12} {'overlap_chk':<12} {'rate'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['total_chunks']:<8} {r['overlapping_sources']:<12} {r['overlapping_chunks']:<12} {r['overlap_rate']:.4f}")
    elif args.command == "isolated":
        rows = find_isolated_sources(conn, args.threshold)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No isolated sources found.")
            else:
                print(f"{'source_id':<16} {'chunks'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['chunk_count']}")
    elif args.command == "summary":
        s = overlap_summary(conn, args.threshold)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
