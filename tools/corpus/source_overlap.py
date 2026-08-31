#!/usr/bin/env python3
"""Source overlap analysis for the research corpus.

Measures content overlap between sources by aggregating chunk-level
similarity scores from chunk_similarities.  Identifies redundant
source pairs and sources that contribute mostly duplicated content.

Usage:
    python tools/corpus/source_overlap.py pairs [--db PATH] [--top N] [--min-score F] [--json]
    python tools/corpus/source_overlap.py detail --source-id SID [--db PATH] [--json]
    python tools/corpus/source_overlap.py redundant [--db PATH] [--threshold F] [--json]
    python tools/corpus/source_overlap.py selftest
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

# ── helpers ──────────────────────────────────────────────────────────


def _source_chunk_map(conn) -> dict[str, list[str]]:
    rows = conn.execute(
        "SELECT chunk_id, source_id FROM chunks "
        "WHERE status != 'superseded'"
    ).fetchall()
    by_source: dict[str, list[str]] = defaultdict(list)
    for chunk_id, source_id in rows:
        by_source[source_id].append(chunk_id)
    return dict(by_source)


def _chunk_to_source(conn) -> dict[str, str]:
    rows = conn.execute(
        "SELECT chunk_id, source_id FROM chunks "
        "WHERE status != 'superseded'"
    ).fetchall()
    return {r[0]: r[1] for r in rows}


# ── subcommands ──────────────────────────────────────────────────────


def overlap_pairs(conn, top_n: int = 20,
                  min_score: float = 0.5) -> list[dict]:
    chunk_source = _chunk_to_source(conn)
    if not chunk_source:
        return []

    rows = conn.execute(
        "SELECT chunk_id_a, chunk_id_b, cosine_score "
        "FROM chunk_similarities "
        "WHERE cosine_score >= ?",
        (min_score,),
    ).fetchall()

    pair_scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    for cid_a, cid_b, score in rows:
        src_a = chunk_source.get(cid_a)
        src_b = chunk_source.get(cid_b)
        if not src_a or not src_b or src_a == src_b:
            continue
        key = tuple(sorted([src_a, src_b]))
        pair_scores[key].append(score)

    source_chunks = _source_chunk_map(conn)
    results = []
    for (sa, sb), scores in pair_scores.items():
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        chunks_a = len(source_chunks.get(sa, []))
        chunks_b = len(source_chunks.get(sb, []))
        min_chunks = min(chunks_a, chunks_b)
        overlap_ratio = len(scores) / min_chunks if min_chunks > 0 else 0.0
        results.append({
            "source_a": sa,
            "source_b": sb,
            "similar_pairs": len(scores),
            "avg_score": round(avg_score, 4),
            "max_score": round(max_score, 4),
            "overlap_ratio": round(overlap_ratio, 4),
            "chunks_a": chunks_a,
            "chunks_b": chunks_b,
        })

    results.sort(key=lambda r: r["overlap_ratio"], reverse=True)
    return results[:top_n]


def source_detail(conn, source_id: str) -> dict:
    source_chunks = _source_chunk_map(conn)
    my_chunks = source_chunks.get(source_id, [])
    if not my_chunks:
        return {"source_id": source_id, "chunk_count": 0,
                "overlapping_sources": []}

    chunk_source = _chunk_to_source(conn)
    placeholders = ",".join("?" for _ in my_chunks)

    rows = conn.execute(
        f"SELECT chunk_id_a, chunk_id_b, cosine_score "
        f"FROM chunk_similarities "
        f"WHERE chunk_id_a IN ({placeholders}) "
        f"   OR chunk_id_b IN ({placeholders})",
        my_chunks + my_chunks,
    ).fetchall()

    by_other: dict[str, list[dict]] = defaultdict(list)
    for cid_a, cid_b, score in rows:
        src_a = chunk_source.get(cid_a)
        src_b = chunk_source.get(cid_b)
        if not src_a or not src_b:
            continue
        if src_a == source_id and src_b != source_id:
            by_other[src_b].append({
                "my_chunk": cid_a, "their_chunk": cid_b,
                "score": round(score, 4),
            })
        elif src_b == source_id and src_a != source_id:
            by_other[src_a].append({
                "my_chunk": cid_b, "their_chunk": cid_a,
                "score": round(score, 4),
            })

    overlapping = []
    for other_src, pairs in sorted(by_other.items(),
                                   key=lambda x: len(x[1]), reverse=True):
        avg = sum(p["score"] for p in pairs) / len(pairs)
        overlapping.append({
            "source_id": other_src,
            "similar_pairs": len(pairs),
            "avg_score": round(avg, 4),
            "top_pairs": sorted(pairs, key=lambda p: p["score"],
                                reverse=True)[:5],
        })

    return {
        "source_id": source_id,
        "chunk_count": len(my_chunks),
        "overlapping_sources": overlapping,
    }


def redundant_sources(conn, threshold: float = 0.7) -> list[dict]:
    source_chunks = _source_chunk_map(conn)
    chunk_source = _chunk_to_source(conn)
    if not chunk_source:
        return []

    rows = conn.execute(
        "SELECT chunk_id_a, chunk_id_b, cosine_score "
        "FROM chunk_similarities "
        "WHERE cosine_score >= ?",
        (threshold,),
    ).fetchall()

    high_sim_chunks: dict[str, set[str]] = defaultdict(set)
    for cid_a, cid_b, _ in rows:
        src_a = chunk_source.get(cid_a)
        src_b = chunk_source.get(cid_b)
        if not src_a or not src_b or src_a == src_b:
            continue
        high_sim_chunks[src_a].add(cid_a)
        high_sim_chunks[src_b].add(cid_b)

    results = []
    for src, overlapping in high_sim_chunks.items():
        total = len(source_chunks.get(src, []))
        if total == 0:
            continue
        ratio = len(overlapping) / total
        results.append({
            "source_id": src,
            "total_chunks": total,
            "overlapping_chunks": len(overlapping),
            "redundancy_ratio": round(ratio, 4),
        })

    results.sort(key=lambda r: r["redundancy_ratio"], reverse=True)
    return results


# ── selftest ─────────────────────────────────────────────────────────


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        for sid, uri in [("s1", "https://a.com"), ("s2", "https://b.com"),
                         ("s3", "https://c.com")]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunk_rows = [
            ("c1", "s1", 0, "H1", "claim", "en", "alpha", "alpha", 1, "n1"),
            ("c2", "s1", 1, "H2", "claim", "en", "beta", "beta", 1, "n2"),
            ("c3", "s1", 2, "H3", "claim", "en", "gamma", "gamma", 1, "n3"),
            ("c4", "s2", 0, "H4", "claim", "en", "delta", "delta", 1, "n4"),
            ("c5", "s2", 1, "H5", "claim", "en", "epsilon", "epsilon", 1, "n5"),
            ("c6", "s3", 0, "H6", "claim", "en", "zeta", "zeta", 1, "n6"),
        ]
        for cr in chunk_rows:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (*cr, now),
            )

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chunk_similarities (
                chunk_id_a   TEXT NOT NULL,
                chunk_id_b   TEXT NOT NULL,
                cosine_score REAL NOT NULL,
                computed_utc TEXT NOT NULL,
                PRIMARY KEY (chunk_id_a, chunk_id_b)
            );
        """)

        sim_rows = [
            ("c1", "c4", 0.85, now),
            ("c2", "c5", 0.75, now),
            ("c1", "c6", 0.60, now),
            ("c3", "c6", 0.40, now),
        ]
        for sr in sim_rows:
            conn.execute(
                "INSERT INTO chunk_similarities "
                "(chunk_id_a, chunk_id_b, cosine_score, computed_utc) "
                "VALUES (?, ?, ?, ?)", sr,
            )
        conn.commit()

        # 1: pairs returns results
        pairs = overlap_pairs(conn, top_n=50, min_score=0.5)
        assert len(pairs) > 0, "should find overlapping pairs"
        checks += 1

        # 2: s1-s2 overlap exists
        s1_s2 = [p for p in pairs
                 if {p["source_a"], p["source_b"]} == {"s1", "s2"}]
        assert len(s1_s2) == 1, "s1-s2 should overlap"
        assert s1_s2[0]["similar_pairs"] == 2, "c1-c4 and c2-c5"
        checks += 1

        # 3: overlap_ratio is correct for s1-s2
        assert s1_s2[0]["overlap_ratio"] > 0, "overlap ratio should be positive"
        checks += 1

        # 4: avg_score is between min and max
        assert s1_s2[0]["avg_score"] >= 0.75
        assert s1_s2[0]["avg_score"] <= 0.85
        checks += 1

        # 5: detail returns source info
        det = source_detail(conn, "s1")
        assert det["source_id"] == "s1"
        assert det["chunk_count"] == 3
        assert len(det["overlapping_sources"]) > 0
        checks += 1

        # 6: detail shows s2 as overlapping
        s2_overlap = [o for o in det["overlapping_sources"]
                      if o["source_id"] == "s2"]
        assert len(s2_overlap) == 1
        assert s2_overlap[0]["similar_pairs"] == 2
        checks += 1

        # 7: detail for nonexistent source
        det_none = source_detail(conn, "nonexistent")
        assert det_none["chunk_count"] == 0
        checks += 1

        # 8: redundant sources
        red = redundant_sources(conn, threshold=0.7)
        assert len(red) > 0, "should find redundant sources"
        checks += 1

        # 9: s1 has redundant chunks
        s1_red = [r for r in red if r["source_id"] == "s1"]
        assert len(s1_red) == 1
        assert s1_red[0]["overlapping_chunks"] >= 1
        checks += 1

        # 10: redundancy_ratio is between 0 and 1
        for r in red:
            assert 0.0 <= r["redundancy_ratio"] <= 1.0
        checks += 1

        # 11: JSON output for pairs
        for row in pairs:
            _ = json.dumps(row)
        checks += 1

        # 12: JSON output for detail
        _ = json.dumps(det)
        checks += 1

        # 13: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert overlap_pairs(conn2) == []
        assert redundant_sources(conn2) == []
        checks += 1

        # 14: superseded chunks excluded
        conn.execute(
            "UPDATE chunks SET status = 'superseded' WHERE chunk_id = 'c1'"
        )
        conn.commit()
        pairs2 = overlap_pairs(conn, top_n=50, min_score=0.5)
        s1_s2_2 = [p for p in pairs2
                   if {p["source_a"], p["source_b"]} == {"s1", "s2"}]
        if s1_s2_2:
            assert s1_s2_2[0]["similar_pairs"] < 2
        checks += 1

    print(f"PASS source_overlap selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Source overlap analysis for the research corpus"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_pairs = sub.add_parser("pairs", help="Top overlapping source pairs")
    p_pairs.add_argument("--db", default=DEFAULT_DB)
    p_pairs.add_argument("--top", type=int, default=20)
    p_pairs.add_argument("--min-score", type=float, default=0.5)
    p_pairs.add_argument("--json", action="store_true")

    p_det = sub.add_parser("detail", help="Overlap detail for one source")
    p_det.add_argument("--source-id", required=True)
    p_det.add_argument("--db", default=DEFAULT_DB)
    p_det.add_argument("--json", action="store_true")

    p_red = sub.add_parser("redundant", help="Sources with high redundancy")
    p_red.add_argument("--db", default=DEFAULT_DB)
    p_red.add_argument("--threshold", type=float, default=0.7)
    p_red.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "pairs":
        results = overlap_pairs(conn, top_n=args.top,
                                min_score=args.min_score)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No overlapping source pairs found.")
                return
            print(f"{'Source A':<15} {'Source B':<15} {'Pairs':>6} "
                  f"{'Avg':>7} {'Max':>7} {'Overlap':>8}")
            print("-" * 64)
            for r in results:
                print(f"{r['source_a']:<15} {r['source_b']:<15} "
                      f"{r['similar_pairs']:>6} {r['avg_score']:>7.4f} "
                      f"{r['max_score']:>7.4f} {r['overlap_ratio']:>8.4f}")

    elif args.cmd == "detail":
        result = source_detail(conn, args.source_id)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Source: {result['source_id']} "
                  f"({result['chunk_count']} chunks)")
            if not result["overlapping_sources"]:
                print("  No overlapping sources found.")
            for ov in result["overlapping_sources"]:
                print(f"  {ov['source_id']}: {ov['similar_pairs']} pairs, "
                      f"avg {ov['avg_score']:.4f}")

    elif args.cmd == "redundant":
        results = redundant_sources(conn, threshold=args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No redundant sources found.")
                return
            print(f"{'Source':<15} {'Total':>6} {'Overlap':>8} "
                  f"{'Ratio':>8}")
            print("-" * 42)
            for r in results:
                print(f"{r['source_id']:<15} {r['total_chunks']:>6} "
                      f"{r['overlapping_chunks']:>8} "
                      f"{r['redundancy_ratio']:>8.4f}")

    conn.close()


if __name__ == "__main__":
    main()
