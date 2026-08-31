#!/usr/bin/env python3
"""Chunk readability scorer: text complexity metrics per chunk.

Computes readability signals from norm_text: average word length,
type-token ratio (vocabulary richness), long word ratio, and a
composite complexity score.  Identifies chunks that are unusually
dense or simple relative to the corpus.

Usage:
    python tools/corpus/readability.py score [--db PATH] [--json]
    python tools/corpus/readability.py complex [--db PATH] [--threshold F] [--json]
    python tools/corpus/readability.py summary [--db PATH] [--json]
    python tools/corpus/readability.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _chunk_readability(norm_text: str) -> dict:
    """Compute readability metrics for a single text."""
    words = norm_text.split()
    if not words:
        return {
            "word_count": 0,
            "avg_word_length": 0.0,
            "type_token_ratio": 0.0,
            "long_word_ratio": 0.0,
            "complexity_score": 0.0,
        }

    word_count = len(words)
    total_chars = sum(len(w) for w in words)
    avg_word_length = total_chars / word_count

    unique_words = len({w.lower() for w in words})
    type_token_ratio = unique_words / word_count

    long_words = sum(1 for w in words if len(w) >= 8)
    long_word_ratio = long_words / word_count

    complexity = (
        0.4 * min(avg_word_length / 10.0, 1.0)
        + 0.3 * (1.0 - type_token_ratio)
        + 0.3 * long_word_ratio
    )

    return {
        "word_count": word_count,
        "avg_word_length": round(avg_word_length, 2),
        "type_token_ratio": round(type_token_ratio, 4),
        "long_word_ratio": round(long_word_ratio, 4),
        "complexity_score": round(complexity, 4),
    }


def readability_scores(conn) -> list[dict]:
    """Per-chunk readability scores for accepted chunks."""
    rows = conn.execute(
        "SELECT chunk_id, source_id, heading_path, kind, norm_text "
        "FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    results = []
    for chunk_id, source_id, heading, kind, norm_text in rows:
        metrics = _chunk_readability(norm_text or "")
        results.append({
            "chunk_id": chunk_id,
            "source_id": source_id,
            "heading": heading,
            "kind": kind,
            **metrics,
        })

    results.sort(key=lambda r: r["complexity_score"], reverse=True)
    return results


def complex_chunks(conn, threshold: float = 0.5) -> list[dict]:
    """Chunks above the complexity threshold."""
    all_scores = readability_scores(conn)
    return [c for c in all_scores if c["complexity_score"] >= threshold]


def readability_summary(conn) -> dict:
    """Aggregate readability statistics."""
    all_scores = readability_scores(conn)

    if not all_scores:
        return {
            "total_chunks": 0,
            "mean_complexity": 0.0,
            "median_complexity": 0.0,
            "mean_avg_word_length": 0.0,
            "mean_type_token_ratio": 0.0,
            "mean_long_word_ratio": 0.0,
            "complex_count": 0,
            "simple_count": 0,
            "by_kind": {},
        }

    complexities = sorted(c["complexity_score"] for c in all_scores)
    n = len(complexities)

    complex_count = sum(1 for c in complexities if c >= 0.5)
    simple_count = sum(1 for c in complexities if c < 0.2)

    by_kind: dict[str, list[float]] = {}
    for s in all_scores:
        by_kind.setdefault(s["kind"], []).append(s["complexity_score"])

    kind_summary = {}
    for kind, vals in sorted(by_kind.items()):
        kind_summary[kind] = {
            "count": len(vals),
            "mean_complexity": round(sum(vals) / len(vals), 4),
        }

    return {
        "total_chunks": n,
        "mean_complexity": round(sum(complexities) / n, 4),
        "median_complexity": round(complexities[n // 2], 4),
        "mean_avg_word_length": round(
            sum(c["avg_word_length"] for c in all_scores) / n, 2),
        "mean_type_token_ratio": round(
            sum(c["type_token_ratio"] for c in all_scores) / n, 4),
        "mean_long_word_ratio": round(
            sum(c["long_word_ratio"] for c in all_scores) / n, 4),
        "complex_count": complex_count,
        "simple_count": simple_count,
        "by_kind": kind_summary,
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

        chunk_data = [
            ("c1", "Simple Text", "claim",
             "the cat sat on the mat by the door"),
            ("c2", "Complex Technical", "claim",
             "implementing sophisticated parallelization strategies "
             "for distributed computational infrastructure requires "
             "understanding asynchronous orchestration mechanisms"),
            ("c3", "Medium Text", "code",
             "function returns the computed average value from "
             "the provided dataset collection"),
            ("c4", "Another Simple", "prose",
             "go to the top of the hill and look at the view"),
        ]
        for i, (cid, heading, kind, text) in enumerate(chunk_data):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, "s1", i, heading, kind, "en",
                 text, text, len(text.split()), f"n_{cid}",
                 "accepted", now),
            )

        conn.commit()

        # 1: scores returned for all chunks
        scores = readability_scores(conn)
        assert len(scores) == 4
        checks += 1

        # 2: sorted by complexity descending
        cscores = [s["complexity_score"] for s in scores]
        assert cscores == sorted(cscores, reverse=True)
        checks += 1

        # 3: complex text (c2) scores higher than simple (c1)
        c1 = next(s for s in scores if s["chunk_id"] == "c1")
        c2 = next(s for s in scores if s["chunk_id"] == "c2")
        assert c2["complexity_score"] > c1["complexity_score"]
        checks += 1

        # 4: avg_word_length is positive
        assert c2["avg_word_length"] > 0
        checks += 1

        # 5: type_token_ratio between 0 and 1
        for s in scores:
            assert 0.0 <= s["type_token_ratio"] <= 1.0
        checks += 1

        # 6: long_word_ratio between 0 and 1
        for s in scores:
            assert 0.0 <= s["long_word_ratio"] <= 1.0
        checks += 1

        # 7: complex chunks filters by threshold
        high = complex_chunks(conn, threshold=0.3)
        assert len(high) <= len(scores)
        checks += 1

        # 8: simple text excluded from high complexity
        high_ids = [c["chunk_id"] for c in high]
        if c1["complexity_score"] < 0.3:
            assert "c1" not in high_ids
        checks += 1

        # 9: summary has required keys
        summary = readability_summary(conn)
        assert summary["total_chunks"] == 4
        assert "mean_complexity" in summary
        assert "by_kind" in summary
        checks += 1

        # 10: complexity scores bounded 0-1
        for s in scores:
            assert 0.0 <= s["complexity_score"] <= 1.0
        checks += 1

        # 11: by_kind has entries for chunk kinds
        assert len(summary["by_kind"]) > 0
        checks += 1

        # 12: mean values are positive
        assert summary["mean_avg_word_length"] > 0
        assert summary["mean_type_token_ratio"] > 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(scores)
        _ = json.dumps(high)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = readability_scores(conn2)
        assert empty == []
        empty_summary = readability_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(f"PASS readability selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk readability: text complexity metrics"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_score = sub.add_parser("score",
                             help="Per-chunk readability scores")
    p_score.add_argument("--db", default=DEFAULT_DB)
    p_score.add_argument("--json", action="store_true")

    p_complex = sub.add_parser("complex",
                               help="Chunks above complexity threshold")
    p_complex.add_argument("--db", default=DEFAULT_DB)
    p_complex.add_argument("--threshold", type=float, default=0.5)
    p_complex.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Readability statistics")
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

    if args.cmd == "score":
        results = readability_scores(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['complexity_score']:.3f}  "
                      f"{r['avg_word_length']:5.1f}awl  "
                      f"{r['type_token_ratio']:.2f}ttr  "
                      f"{r['kind']:6s}  {r['chunk_id'][:12]:12s}  "
                      f"{r['heading']}")

    elif args.cmd == "complex":
        results = complex_chunks(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No chunks above threshold.")
            else:
                print(f"{len(results)} complex chunks "
                      f"(>= {args.threshold}):")
                for c in results:
                    print(f"  {c['complexity_score']:.3f}  "
                          f"{c['chunk_id'][:12]:12s}  {c['heading']}")

    elif args.cmd == "summary":
        result = readability_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Readability: {result['mean_complexity']:.3f} mean "
                  f"complexity ({result['total_chunks']} chunks)")
            print(f"  Avg word length: {result['mean_avg_word_length']:.1f}  "
                  f"TTR: {result['mean_type_token_ratio']:.3f}  "
                  f"Long word ratio: {result['mean_long_word_ratio']:.3f}")
            print(f"  Complex (>=0.5): {result['complex_count']}  "
                  f"Simple (<0.2): {result['simple_count']}")
            if result["by_kind"]:
                for kind, stats in result["by_kind"].items():
                    print(f"    {kind}: {stats['count']} chunks, "
                          f"mean {stats['mean_complexity']:.3f}")

    conn.close()


if __name__ == "__main__":
    main()
