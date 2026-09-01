#!/usr/bin/env python3
"""Tag entropy: information content of per-chunk tag assignments.

Measures how surprising each chunk's tag set is relative to the
corpus-wide tag distribution.  Chunks with common tags have low
entropy (predictable); chunks with rare tag combinations have high
entropy (surprising, possibly miscategorised or niche).

Usage:
    python tools/corpus/tag_entropy.py scores [--db PATH] [--json]
    python tools/corpus/tag_entropy.py outliers [--db PATH] [--threshold F] [--json]
    python tools/corpus/tag_entropy.py summary [--db PATH] [--json]
    python tools/corpus/tag_entropy.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _corpus_tag_probs(conn) -> dict[str, float]:
    """Corpus-wide probability of each tag (fraction of tagged chunks)."""
    total_tagged = conn.execute(
        "SELECT count(DISTINCT ct.chunk_id) "
        "FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchone()[0]

    if total_tagged == 0:
        return {}

    tag_counts = conn.execute(
        "SELECT ct.tag, count(DISTINCT ct.chunk_id) "
        "FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY ct.tag"
    ).fetchall()

    return {tag: count / total_tagged for tag, count in tag_counts}


def tag_entropy_scores(conn) -> list[dict]:
    """Per-chunk tag entropy: information content of tag assignments."""
    probs = _corpus_tag_probs(conn)
    if not probs:
        return []

    chunk_tags_rows = conn.execute(
        "SELECT ct.chunk_id, ct.tag "
        "FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' "
        "ORDER BY ct.chunk_id"
    ).fetchall()

    if not chunk_tags_rows:
        return []

    chunk_tag_map: dict[str, list[str]] = {}
    for chunk_id, tag in chunk_tags_rows:
        chunk_tag_map.setdefault(chunk_id, []).append(tag)

    chunk_info = dict(conn.execute(
        "SELECT chunk_id, heading_path FROM chunks "
        "WHERE status = 'accepted' AND chunk_id IN "
        f"({','.join('?' for _ in chunk_tag_map)})",
        list(chunk_tag_map.keys()),
    ).fetchall())

    chunk_sources = dict(conn.execute(
        "SELECT chunk_id, source_id FROM chunks "
        "WHERE status = 'accepted' AND chunk_id IN "
        f"({','.join('?' for _ in chunk_tag_map)})",
        list(chunk_tag_map.keys()),
    ).fetchall())

    results = []
    for chunk_id, tags in chunk_tag_map.items():
        info_bits = 0.0
        for tag in tags:
            p = probs.get(tag, 0.001)
            info_bits += -math.log2(p)

        avg_info = round(info_bits / len(tags), 4) if tags else 0.0

        results.append({
            "chunk_id": chunk_id,
            "source_id": chunk_sources.get(chunk_id, ""),
            "heading": chunk_info.get(chunk_id, ""),
            "tag_count": len(tags),
            "tags": sorted(tags),
            "total_info_bits": round(info_bits, 4),
            "avg_info_bits": avg_info,
        })

    results.sort(key=lambda r: r["avg_info_bits"], reverse=True)
    return results


def tag_entropy_outliers(conn, threshold: float = 3.0) -> list[dict]:
    """Chunks whose average tag information exceeds threshold bits."""
    scores = tag_entropy_scores(conn)
    return [s for s in scores if s["avg_info_bits"] > threshold]


def tag_entropy_summary(conn) -> dict:
    """Aggregate tag entropy statistics."""
    scores = tag_entropy_scores(conn)

    if not scores:
        return {
            "tagged_chunks": 0,
            "total_unique_tags": 0,
            "mean_avg_info": 0.0,
            "median_avg_info": 0.0,
            "max_avg_info": 0.0,
            "min_avg_info": 0.0,
            "high_entropy_chunks": 0,
            "low_entropy_chunks": 0,
            "mean_tags_per_chunk": 0.0,
        }

    probs = _corpus_tag_probs(conn)

    avg_infos = sorted(s["avg_info_bits"] for s in scores)
    mean_info = round(sum(avg_infos) / len(avg_infos), 4)
    median_info = round(avg_infos[len(avg_infos) // 2], 4)

    tag_counts = [s["tag_count"] for s in scores]
    mean_tags = round(sum(tag_counts) / len(tag_counts), 2)

    high_threshold = mean_info + 1.0
    low_threshold = max(mean_info - 1.0, 0.0)

    return {
        "tagged_chunks": len(scores),
        "total_unique_tags": len(probs),
        "mean_avg_info": mean_info,
        "median_avg_info": median_info,
        "max_avg_info": round(max(avg_infos), 4),
        "min_avg_info": round(min(avg_infos), 4),
        "high_entropy_chunks": sum(1 for a in avg_infos if a > high_threshold),
        "low_entropy_chunks": sum(1 for a in avg_infos if a < low_threshold),
        "mean_tags_per_chunk": mean_tags,
    }


# -- selftest ----------------------------------------------------------------


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

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(5):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", "s1", i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_c{i}",
                 "accepted", now),
            )

        common_tag = "machine-learning"
        rare_tag = "quantum-topology"
        medium_tag = "optimization"

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c0", common_tag, 0.9, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c1", common_tag, 0.8, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c2", common_tag, 0.7, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c3", common_tag, 0.6, now))

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c0", medium_tag, 0.7, now))
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c1", medium_tag, 0.6, now))

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)", ("c4", rare_tag, 0.9, now))

        conn.commit()

        # 1: scores returns all tagged chunks
        scores = tag_entropy_scores(conn)
        assert len(scores) == 5
        checks += 1

        # 2: sorted by avg_info_bits descending
        avg_infos = [s["avg_info_bits"] for s in scores]
        assert avg_infos == sorted(avg_infos, reverse=True)
        checks += 1

        # 3: rare tag chunk has highest entropy
        c4 = next(s for s in scores if s["chunk_id"] == "c4")
        c3 = next(s for s in scores if s["chunk_id"] == "c3")
        assert c4["avg_info_bits"] > c3["avg_info_bits"]
        checks += 1

        # 4: common-only tag chunk has lower entropy
        assert c3["avg_info_bits"] < c4["avg_info_bits"]
        checks += 1

        # 5: tag counts are correct
        c0 = next(s for s in scores if s["chunk_id"] == "c0")
        assert c0["tag_count"] == 2
        assert c4["tag_count"] == 1
        checks += 1

        # 6: total_info_bits is positive
        assert all(s["total_info_bits"] > 0 for s in scores)
        checks += 1

        # 7: outliers with low threshold returns some
        outliers = tag_entropy_outliers(conn, threshold=0.0)
        assert len(outliers) > 0
        checks += 1

        # 8: outliers with very high threshold returns fewer
        outliers_high = tag_entropy_outliers(conn, threshold=99.0)
        assert len(outliers_high) <= len(outliers)
        checks += 1

        # 9: summary has required keys
        summary = tag_entropy_summary(conn)
        assert summary["tagged_chunks"] == 5
        assert summary["total_unique_tags"] == 3
        checks += 1

        # 10: mean info is positive
        assert summary["mean_avg_info"] > 0
        checks += 1

        # 11: max >= mean >= min
        assert summary["max_avg_info"] >= summary["mean_avg_info"]
        assert summary["mean_avg_info"] >= summary["min_avg_info"]
        checks += 1

        # 12: mean_tags_per_chunk is positive
        assert summary["mean_tags_per_chunk"] > 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(scores)
        _ = json.dumps(outliers)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = tag_entropy_scores(conn2)
        assert empty == []
        empty_summary = tag_entropy_summary(conn2)
        assert empty_summary["tagged_chunks"] == 0
        checks += 1

    print(f"PASS tag_entropy selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tag entropy: information content of tag assignments"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_scores = sub.add_parser("scores",
                              help="Per-chunk tag entropy scores")
    p_scores.add_argument("--db", default=DEFAULT_DB)
    p_scores.add_argument("--json", action="store_true")

    p_out = sub.add_parser("outliers",
                           help="Chunks with high tag entropy")
    p_out.add_argument("--db", default=DEFAULT_DB)
    p_out.add_argument("--threshold", type=float, default=3.0)
    p_out.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Tag entropy statistics")
    p_sum.add_argument("--db", default=DEFAULT_DB)
    p_sum.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "scores":
        results = tag_entropy_scores(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                tags = ", ".join(r["tags"][:3])
                if len(r["tags"]) > 3:
                    tags += f" +{len(r['tags']) - 3}"
                print(f"  {r['avg_info_bits']:5.2f}b  {r['tag_count']:2d} tags  "
                      f"{r['chunk_id'][:12]:12s}  {tags}")

    elif args.cmd == "outliers":
        results = tag_entropy_outliers(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No high-entropy tag assignments found.")
            else:
                print(f"{len(results)} chunks with avg info > "
                      f"{args.threshold:.1f} bits:")
                for r in results:
                    print(f"  {r['avg_info_bits']:5.2f}b  "
                          f"{r['chunk_id'][:12]:12s}  "
                          f"{', '.join(r['tags'])}")

    elif args.cmd == "summary":
        result = tag_entropy_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Tag Entropy: {result['tagged_chunks']} chunks, "
                  f"{result['total_unique_tags']} unique tags")
            print(f"  Mean info: {result['mean_avg_info']:.2f}b  "
                  f"Median: {result['median_avg_info']:.2f}b  "
                  f"Range: {result['min_avg_info']:.2f}-"
                  f"{result['max_avg_info']:.2f}b")
            print(f"  High entropy: {result['high_entropy_chunks']}  "
                  f"Low entropy: {result['low_entropy_chunks']}  "
                  f"Mean tags/chunk: {result['mean_tags_per_chunk']:.1f}")

    conn.close()


if __name__ == "__main__":
    main()
