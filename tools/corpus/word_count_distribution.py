#!/usr/bin/env python3
"""Word count distribution: chunk length patterns across the corpus.

Analyses word count distribution by source, kind, and domain,
detecting unusually short or long chunks that may indicate
extraction issues.

Usage:
    python tools/corpus/word_count_distribution.py histogram [--db PATH] [--json]
    python tools/corpus/word_count_distribution.py per-kind [--db PATH] [--json]
    python tools/corpus/word_count_distribution.py outliers [--db PATH] [--threshold F] [--json]
    python tools/corpus/word_count_distribution.py summary [--db PATH] [--json]
    python tools/corpus/word_count_distribution.py selftest
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

HISTOGRAM_BINS = [
    (0, 10, "0-10"),
    (11, 50, "11-50"),
    (51, 100, "51-100"),
    (101, 250, "101-250"),
    (251, 500, "251-500"),
    (501, 1000, "501-1000"),
    (1001, None, "1001+"),
]


def word_count_histogram(conn) -> list[dict]:
    """Word count histogram across all accepted chunks."""
    rows = conn.execute(
        "SELECT word_count FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    total = len(rows)
    counts = [r[0] for r in rows]

    results = []
    for lo, hi, label in HISTOGRAM_BINS:
        if hi is None:
            n = sum(1 for c in counts if c >= lo)
        else:
            n = sum(1 for c in counts if lo <= c <= hi)
        results.append({
            "bin": label,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        })

    return results


def per_kind_word_counts(conn) -> list[dict]:
    """Word count statistics per chunk kind."""
    rows = conn.execute(
        "SELECT kind, word_count FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_kind: dict[str, list[int]] = {}
    for kind, wc in rows:
        by_kind.setdefault(kind, []).append(wc)

    results = []
    for kind, wcs in sorted(by_kind.items()):
        n = len(wcs)
        mean_wc = sum(wcs) / n
        sorted_wcs = sorted(wcs)
        median_wc = sorted_wcs[n // 2]
        variance = sum((w - mean_wc) ** 2 for w in wcs) / n if n > 1 else 0.0

        results.append({
            "kind": kind,
            "count": n,
            "mean_word_count": round(mean_wc, 1),
            "median_word_count": median_wc,
            "min_word_count": min(wcs),
            "max_word_count": max(wcs),
            "stddev": round(math.sqrt(variance), 1),
        })

    results.sort(key=lambda r: r["mean_word_count"], reverse=True)
    return results


def word_count_outliers(conn, threshold: float = 2.0) -> list[dict]:
    """Chunks whose word count deviates beyond threshold standard deviations."""
    rows = conn.execute(
        "SELECT chunk_id, source_id, kind, heading_path, word_count "
        "FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    wcs = [r[4] for r in rows]
    mean_wc = sum(wcs) / len(wcs)
    variance = sum((w - mean_wc) ** 2 for w in wcs) / len(wcs)
    stddev = math.sqrt(variance) if variance > 0 else 1.0

    results = []
    for chunk_id, source_id, kind, heading, wc in rows:
        z = (wc - mean_wc) / stddev
        if abs(z) > threshold:
            results.append({
                "chunk_id": chunk_id,
                "source_id": source_id,
                "kind": kind,
                "heading": heading,
                "word_count": wc,
                "z_score": round(z, 2),
                "direction": "long" if z > 0 else "short",
            })

    results.sort(key=lambda r: abs(r["z_score"]), reverse=True)
    return results


def word_count_summary(conn) -> dict:
    """Aggregate word count statistics."""
    rows = conn.execute(
        "SELECT word_count FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_chunks": 0,
            "total_words": 0,
            "mean_word_count": 0.0,
            "median_word_count": 0,
            "min_word_count": 0,
            "max_word_count": 0,
            "stddev": 0.0,
            "short_chunks": 0,
            "long_chunks": 0,
        }

    wcs = sorted(r[0] for r in rows)
    n = len(wcs)
    mean_wc = sum(wcs) / n
    median_wc = wcs[n // 2]
    variance = sum((w - mean_wc) ** 2 for w in wcs) / n if n > 1 else 0.0
    stddev = math.sqrt(variance)

    return {
        "total_chunks": n,
        "total_words": sum(wcs),
        "mean_word_count": round(mean_wc, 1),
        "median_word_count": median_wc,
        "min_word_count": min(wcs),
        "max_word_count": max(wcs),
        "stddev": round(stddev, 1),
        "short_chunks": sum(1 for w in wcs if w <= 10),
        "long_chunks": sum(1 for w in wcs if w > 500),
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

        chunks = [
            ("c0", "claim", 5),
            ("c1", "claim", 25),
            ("c2", "prose", 150),
            ("c3", "prose", 200),
            ("c4", "code", 80),
            ("c5", "claim", 8),
            ("c6", "prose", 600),
        ]
        for i, (cid, kind, wc) in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, "s1", i, f"Heading {i}", kind, "en",
                 f"text {i}", f"text {i}", wc, f"n_{cid}",
                 "accepted", now),
            )

        conn.commit()

        # 1: histogram returns 7 bins
        hist = word_count_histogram(conn)
        assert len(hist) == 7
        checks += 1

        # 2: shares sum to approximately 1.0
        total_share = sum(b["share"] for b in hist)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 3: counts sum to total chunks
        total_count = sum(b["count"] for b in hist)
        assert total_count == 7
        checks += 1

        # 4: 0-10 bin has 2 chunks (5 and 8)
        short_bin = next(b for b in hist if b["bin"] == "0-10")
        assert short_bin["count"] == 2
        checks += 1

        # 5: per-kind returns all kinds
        per_kind = per_kind_word_counts(conn)
        kind_set = {k["kind"] for k in per_kind}
        assert kind_set == {"claim", "prose", "code"}
        checks += 1

        # 6: prose has highest mean word count
        assert per_kind[0]["kind"] == "prose"
        checks += 1

        # 7: mean is between min and max for each kind
        for k in per_kind:
            assert k["min_word_count"] <= k["mean_word_count"] <= k["max_word_count"]
        checks += 1

        # 8: outliers with low threshold returns some
        outliers = word_count_outliers(conn, threshold=1.0)
        assert len(outliers) > 0
        checks += 1

        # 9: c6 (600 words) is a long outlier
        c6_outliers = [o for o in outliers if o["chunk_id"] == "c6"]
        assert len(c6_outliers) == 1
        assert c6_outliers[0]["direction"] == "long"
        checks += 1

        # 10: outliers sorted by abs(z_score) descending
        z_scores = [abs(o["z_score"]) for o in outliers]
        assert z_scores == sorted(z_scores, reverse=True)
        checks += 1

        # 11: summary has required keys
        summary = word_count_summary(conn)
        assert summary["total_chunks"] == 7
        assert summary["total_words"] == sum(wc for _, _, wc in chunks)
        checks += 1

        # 12: mean is positive and between min and max
        assert summary["min_word_count"] <= summary["mean_word_count"]
        assert summary["mean_word_count"] <= summary["max_word_count"]
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(hist)
        _ = json.dumps(per_kind)
        _ = json.dumps(outliers)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = word_count_histogram(conn2)
        assert empty == []
        empty_summary = word_count_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(f"PASS word_count_distribution selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Word count distribution: chunk length patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_hist = sub.add_parser("histogram",
                            help="Word count histogram")
    p_hist.add_argument("--db", default=DEFAULT_DB)
    p_hist.add_argument("--json", action="store_true")

    p_kind = sub.add_parser("per-kind",
                            help="Word count statistics per chunk kind")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_out = sub.add_parser("outliers",
                           help="Chunks with extreme word counts")
    p_out.add_argument("--db", default=DEFAULT_DB)
    p_out.add_argument("--threshold", type=float, default=2.0)
    p_out.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Word count statistics")
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

    if args.cmd == "histogram":
        results = word_count_histogram(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['bin']:10s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "per-kind":
        results = per_kind_word_counts(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['kind']:8s}  n={r['count']:3d}  "
                      f"mean={r['mean_word_count']:6.1f}  "
                      f"med={r['median_word_count']:4d}  "
                      f"range={r['min_word_count']}-{r['max_word_count']}  "
                      f"sd={r['stddev']:.1f}")

    elif args.cmd == "outliers":
        results = word_count_outliers(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No word count outliers found.")
            else:
                print(f"{len(results)} outlier chunks "
                      f"(>{args.threshold:.1f} SD):")
                for r in results:
                    print(f"  z={r['z_score']:+5.2f}  {r['direction']:5s}  "
                          f"{r['word_count']:5d}w  {r['kind']:8s}  "
                          f"{r['chunk_id'][:12]}")

    elif args.cmd == "summary":
        result = word_count_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Word Counts: {result['total_chunks']} chunks, "
                  f"{result['total_words']} total words")
            print(f"  Mean: {result['mean_word_count']:.1f}  "
                  f"Median: {result['median_word_count']}  "
                  f"SD: {result['stddev']:.1f}  "
                  f"Range: {result['min_word_count']}-"
                  f"{result['max_word_count']}")
            print(f"  Short (<=10w): {result['short_chunks']}  "
                  f"Long (>500w): {result['long_chunks']}")

    conn.close()


if __name__ == "__main__":
    main()
