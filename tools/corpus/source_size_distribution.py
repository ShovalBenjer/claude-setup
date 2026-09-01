#!/usr/bin/env python3
"""Source size distribution: byte-count patterns across sources.

Analyses the distribution of source sizes in bytes, detecting
unusually small or large sources that may indicate truncated
downloads or unbounded extraction.

Usage:
    python tools/corpus/source_size_distribution.py histogram [--db PATH] [--json]
    python tools/corpus/source_size_distribution.py per-kind [--db PATH] [--json]
    python tools/corpus/source_size_distribution.py outliers [--db PATH] [--threshold F] [--json]
    python tools/corpus/source_size_distribution.py summary [--db PATH] [--json]
    python tools/corpus/source_size_distribution.py selftest
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

SIZE_BINS = [
    (0, 1024, "<1KB"),
    (1025, 10240, "1-10KB"),
    (10241, 102400, "10-100KB"),
    (102401, 1048576, "100KB-1MB"),
    (1048577, None, ">1MB"),
]


def size_histogram(conn) -> list[dict]:
    """Size histogram across all sources."""
    rows = conn.execute(
        "SELECT bytes FROM sources WHERE bytes IS NOT NULL"
    ).fetchall()

    if not rows:
        return []

    sizes = [r[0] for r in rows]
    total = len(sizes)

    results = []
    for lo, hi, label in SIZE_BINS:
        if hi is None:
            n = sum(1 for s in sizes if s >= lo)
        else:
            n = sum(1 for s in sizes if lo <= s <= hi)
        results.append({
            "bin": label,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        })

    return results


def per_kind_sizes(conn) -> list[dict]:
    """Size statistics per source kind."""
    rows = conn.execute(
        "SELECT kind, bytes FROM sources WHERE bytes IS NOT NULL"
    ).fetchall()

    if not rows:
        return []

    by_kind: dict[str, list[int]] = {}
    for kind, size in rows:
        by_kind.setdefault(kind, []).append(size)

    results = []
    for kind, sizes in sorted(by_kind.items()):
        n = len(sizes)
        mean = sum(sizes) / n
        sorted_sizes = sorted(sizes)
        median = sorted_sizes[n // 2]
        variance = sum((s - mean) ** 2 for s in sizes) / n if n > 1 else 0.0

        results.append({
            "kind": kind,
            "count": n,
            "mean_bytes": round(mean, 0),
            "median_bytes": median,
            "min_bytes": min(sizes),
            "max_bytes": max(sizes),
            "total_bytes": sum(sizes),
            "stddev": round(math.sqrt(variance), 0),
        })

    results.sort(key=lambda r: r["mean_bytes"], reverse=True)
    return results


def size_outliers(conn, threshold: float = 2.0) -> list[dict]:
    """Sources whose size deviates beyond threshold standard deviations."""
    rows = conn.execute(
        "SELECT source_id, title, kind, bytes FROM sources "
        "WHERE bytes IS NOT NULL"
    ).fetchall()

    if not rows:
        return []

    sizes = [r[3] for r in rows]
    mean = sum(sizes) / len(sizes)
    variance = sum((s - mean) ** 2 for s in sizes) / len(sizes)
    stddev = math.sqrt(variance) if variance > 0 else 1.0

    results = []
    for src_id, title, kind, size in rows:
        z = (size - mean) / stddev
        if abs(z) > threshold:
            results.append({
                "source_id": src_id,
                "title": title,
                "kind": kind,
                "bytes": size,
                "z_score": round(z, 2),
                "direction": "large" if z > 0 else "small",
            })

    results.sort(key=lambda r: abs(r["z_score"]), reverse=True)
    return results


def size_summary(conn) -> dict:
    """Aggregate source size statistics."""
    rows = conn.execute(
        "SELECT bytes FROM sources WHERE bytes IS NOT NULL"
    ).fetchall()

    if not rows:
        return {
            "total_sources": 0,
            "total_bytes": 0,
            "mean_bytes": 0.0,
            "median_bytes": 0,
            "min_bytes": 0,
            "max_bytes": 0,
            "stddev": 0.0,
            "tiny_sources": 0,
            "large_sources": 0,
        }

    sizes = sorted(r[0] for r in rows)
    n = len(sizes)
    mean = sum(sizes) / n
    median = sizes[n // 2]
    variance = sum((s - mean) ** 2 for s in sizes) / n if n > 1 else 0.0

    return {
        "total_sources": n,
        "total_bytes": sum(sizes),
        "mean_bytes": round(mean, 0),
        "median_bytes": median,
        "min_bytes": min(sizes),
        "max_bytes": max(sizes),
        "stddev": round(math.sqrt(variance), 0),
        "tiny_sources": sum(1 for s in sizes if s <= 1024),
        "large_sources": sum(1 for s in sizes if s > 1048576),
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

        sources = [
            ("s1", "paper", 500),
            ("s2", "paper", 5000),
            ("s3", "local_md", 50000),
            ("s4", "local_md", 200000),
            ("s5", "repo", 800000),
            ("s6", "hf_dataset", 2000000),
            ("s7", "paper", 300),
        ]
        for sid, kind, size in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", size, None),
            )

        conn.commit()

        # 1: histogram returns 5 bins
        hist = size_histogram(conn)
        assert len(hist) == 5
        checks += 1

        # 2: shares sum to approximately 1.0
        total_share = sum(b["share"] for b in hist)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 3: counts sum to total sources
        total_count = sum(b["count"] for b in hist)
        assert total_count == 7
        checks += 1

        # 4: <1KB bin has 2 sources (500 and 300)
        tiny_bin = next(b for b in hist if b["bin"] == "<1KB")
        assert tiny_bin["count"] == 2
        checks += 1

        # 5: per-kind returns all kinds
        per_kind = per_kind_sizes(conn)
        kind_set = {k["kind"] for k in per_kind}
        assert kind_set == {"paper", "local_md", "repo", "hf_dataset"}
        checks += 1

        # 6: sorted by mean_bytes descending
        means = [k["mean_bytes"] for k in per_kind]
        assert means == sorted(means, reverse=True)
        checks += 1

        # 7: mean is between min and max for each kind
        for k in per_kind:
            assert k["min_bytes"] <= k["mean_bytes"] <= k["max_bytes"]
        checks += 1

        # 8: outliers with low threshold returns some
        outliers = size_outliers(conn, threshold=1.0)
        assert len(outliers) > 0
        checks += 1

        # 9: s6 (2MB) is a large outlier
        s6 = [o for o in outliers if o["source_id"] == "s6"]
        assert len(s6) == 1
        assert s6[0]["direction"] == "large"
        checks += 1

        # 10: outliers sorted by abs(z_score) descending
        z_scores = [abs(o["z_score"]) for o in outliers]
        assert z_scores == sorted(z_scores, reverse=True)
        checks += 1

        # 11: summary has correct totals
        summary = size_summary(conn)
        assert summary["total_sources"] == 7
        assert summary["total_bytes"] == sum(s for _, _, s in sources)
        checks += 1

        # 12: mean is between min and max
        assert summary["min_bytes"] <= summary["mean_bytes"]
        assert summary["mean_bytes"] <= summary["max_bytes"]
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
        empty = size_histogram(conn2)
        assert empty == []
        empty_summary = size_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS source_size_distribution selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Source size distribution: byte-count patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_hist = sub.add_parser("histogram",
                            help="Source size histogram")
    p_hist.add_argument("--db", default=DEFAULT_DB)
    p_hist.add_argument("--json", action="store_true")

    p_kind = sub.add_parser("per-kind",
                            help="Size statistics per source kind")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_out = sub.add_parser("outliers",
                           help="Sources with extreme sizes")
    p_out.add_argument("--db", default=DEFAULT_DB)
    p_out.add_argument("--threshold", type=float, default=2.0)
    p_out.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Source size statistics")
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
        results = size_histogram(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['bin']:12s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "per-kind":
        results = per_kind_sizes(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['kind']:12s}  n={r['count']:3d}  "
                      f"mean={r['mean_bytes']:,.0f}B  "
                      f"med={r['median_bytes']:,}B  "
                      f"range={r['min_bytes']:,}-{r['max_bytes']:,}B")

    elif args.cmd == "outliers":
        results = size_outliers(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No size outliers found.")
            else:
                print(f"{len(results)} outlier sources "
                      f"(>{args.threshold:.1f} SD):")
                for r in results:
                    print(f"  z={r['z_score']:+5.2f}  {r['direction']:5s}  "
                          f"{r['bytes']:>10,}B  {r['kind']:12s}  "
                          f"{r['source_id'][:12]}")

    elif args.cmd == "summary":
        result = size_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}, "
                  f"{result['total_bytes']:,} total bytes")
            print(f"  Mean: {result['mean_bytes']:,.0f}B  "
                  f"Median: {result['median_bytes']:,}B  "
                  f"SD: {result['stddev']:,.0f}B  "
                  f"Range: {result['min_bytes']:,}-"
                  f"{result['max_bytes']:,}B")
            print(f"  Tiny (<=1KB): {result['tiny_sources']}  "
                  f"Large (>1MB): {result['large_sources']}")

    conn.close()


if __name__ == "__main__":
    main()
