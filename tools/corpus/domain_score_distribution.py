#!/usr/bin/env python3
"""Domain score distribution: classification confidence patterns.

Analyses the distribution of domain classification scores across
accepted chunks, measuring calibration quality and identifying
low-confidence assignments that may need reclassification.

Usage:
    python tools/corpus/domain_score_distribution.py bands [--db PATH] [--json]
    python tools/corpus/domain_score_distribution.py per-domain [--db PATH] [--json]
    python tools/corpus/domain_score_distribution.py low-confidence [--db PATH] [--threshold F] [--json]
    python tools/corpus/domain_score_distribution.py summary [--db PATH] [--json]
    python tools/corpus/domain_score_distribution.py selftest
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

SCORE_BANDS = [
    (0.0, 0.25, "0.00-0.25"),
    (0.25, 0.50, "0.25-0.50"),
    (0.50, 0.75, "0.50-0.75"),
    (0.75, 1.01, "0.75-1.00"),
]


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def score_bands(conn) -> list[dict]:
    """Score histogram across all domain assignments for accepted chunks."""
    if not _table_exists(conn, "chunk_domains"):
        return []

    rows = conn.execute(
        "SELECT cd.score FROM chunk_domains cd "
        "JOIN chunks c ON cd.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    scores = [r[0] for r in rows]
    total = len(scores)

    results = []
    for lo, hi, label in SCORE_BANDS:
        n = sum(1 for s in scores if lo <= s < hi)
        results.append({
            "band": label,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        })

    return results


def per_domain_scores(conn) -> list[dict]:
    """Score statistics per domain."""
    if not _table_exists(conn, "chunk_domains"):
        return []

    rows = conn.execute(
        "SELECT cd.domain, cd.score FROM chunk_domains cd "
        "JOIN chunks c ON cd.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_domain: dict[str, list[float]] = {}
    for domain, score in rows:
        by_domain.setdefault(domain, []).append(score)

    results = []
    for domain, scores in sorted(by_domain.items()):
        n = len(scores)
        mean = sum(scores) / n
        sorted_scores = sorted(scores)
        median = sorted_scores[n // 2]
        variance = sum((s - mean) ** 2 for s in scores) / n if n > 1 else 0.0

        results.append({
            "domain": domain,
            "count": n,
            "mean_score": round(mean, 4),
            "median_score": round(median, 4),
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
            "stddev": round(math.sqrt(variance), 4),
        })

    results.sort(key=lambda r: r["mean_score"])
    return results


def low_confidence(conn, threshold: float = 0.5) -> list[dict]:
    """Domain assignments with score below threshold."""
    if not _table_exists(conn, "chunk_domains"):
        return []

    rows = conn.execute(
        "SELECT cd.chunk_id, cd.domain, cd.score, c.source_id, c.kind "
        "FROM chunk_domains cd "
        "JOIN chunks c ON cd.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' AND cd.score < ? "
        "ORDER BY cd.score ASC",
        (threshold,),
    ).fetchall()

    return [
        {
            "chunk_id": r[0],
            "domain": r[1],
            "score": round(r[2], 4),
            "source_id": r[3],
            "kind": r[4],
        }
        for r in rows
    ]


def score_summary(conn) -> dict:
    """Aggregate domain score statistics."""
    if not _table_exists(conn, "chunk_domains"):
        return {
            "total_assignments": 0,
            "unique_domains": 0,
            "mean_score": 0.0,
            "median_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "stddev": 0.0,
            "low_confidence_count": 0,
            "high_confidence_count": 0,
        }

    rows = conn.execute(
        "SELECT cd.score FROM chunk_domains cd "
        "JOIN chunks c ON cd.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_assignments": 0,
            "unique_domains": 0,
            "mean_score": 0.0,
            "median_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "stddev": 0.0,
            "low_confidence_count": 0,
            "high_confidence_count": 0,
        }

    scores = sorted(r[0] for r in rows)
    n = len(scores)
    mean = sum(scores) / n
    median = scores[n // 2]
    variance = sum((s - mean) ** 2 for s in scores) / n if n > 1 else 0.0

    domain_row = conn.execute(
        "SELECT count(DISTINCT cd.domain) FROM chunk_domains cd "
        "JOIN chunks c ON cd.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchone()

    return {
        "total_assignments": n,
        "unique_domains": domain_row[0],
        "mean_score": round(mean, 4),
        "median_score": round(median, 4),
        "min_score": round(min(scores), 4),
        "max_score": round(max(scores), 4),
        "stddev": round(math.sqrt(variance), 4),
        "low_confidence_count": sum(1 for s in scores if s < 0.5),
        "high_confidence_count": sum(1 for s in scores if s >= 0.75),
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains ("
            "chunk_id TEXT NOT NULL, domain TEXT NOT NULL, "
            "score REAL, classified_utc TEXT, "
            "PRIMARY KEY (chunk_id, domain))"
        )

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
                 f"text {i}", f"text {i}", 50, f"n_c{i}",
                 "accepted", now),
            )

        assignments = [
            ("c0", "ml", 0.9),
            ("c0", "nlp", 0.7),
            ("c1", "ml", 0.85),
            ("c2", "systems", 0.3),
            ("c2", "ml", 0.2),
            ("c3", "nlp", 0.6),
            ("c4", "systems", 0.15),
        ]
        for chunk_id, domain, score in assignments:
            conn.execute(
                "INSERT INTO chunk_domains (chunk_id, domain, score, "
                "classified_utc) VALUES (?, ?, ?, ?)",
                (chunk_id, domain, score, now),
            )

        conn.commit()

        # 1: score_bands returns 4 bands
        bands = score_bands(conn)
        assert len(bands) == 4
        checks += 1

        # 2: shares sum to approximately 1.0
        total_share = sum(b["share"] for b in bands)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 3: counts sum to total assignments
        total_count = sum(b["count"] for b in bands)
        assert total_count == 7
        checks += 1

        # 4: low band (0.00-0.25) has 2 entries (0.2 and 0.15)
        low_band = next(b for b in bands if b["band"] == "0.00-0.25")
        assert low_band["count"] == 2
        checks += 1

        # 5: per-domain returns all domains
        per_dom = per_domain_scores(conn)
        domain_set = {d["domain"] for d in per_dom}
        assert domain_set == {"ml", "nlp", "systems"}
        checks += 1

        # 6: sorted by mean_score ascending
        means = [d["mean_score"] for d in per_dom]
        assert means == sorted(means)
        checks += 1

        # 7: mean is between min and max for each domain
        for d in per_dom:
            assert d["min_score"] <= d["mean_score"] <= d["max_score"]
        checks += 1

        # 8: low_confidence returns entries below threshold
        low = low_confidence(conn, threshold=0.5)
        assert len(low) > 0
        checks += 1

        # 9: all low-confidence entries have score < 0.5
        for lc in low:
            assert lc["score"] < 0.5
        checks += 1

        # 10: low-confidence sorted by score ascending
        lc_scores = [lc["score"] for lc in low]
        assert lc_scores == sorted(lc_scores)
        checks += 1

        # 11: summary has correct total
        summary = score_summary(conn)
        assert summary["total_assignments"] == 7
        assert summary["unique_domains"] == 3
        checks += 1

        # 12: low and high confidence counts
        assert summary["low_confidence_count"] == 3
        assert summary["high_confidence_count"] == 2
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(bands)
        _ = json.dumps(per_dom)
        _ = json.dumps(low)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = score_bands(conn2)
        assert empty == []
        empty_summary = score_summary(conn2)
        assert empty_summary["total_assignments"] == 0
        checks += 1

    print(f"PASS domain_score_distribution selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Domain score distribution: classification confidence patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_bands = sub.add_parser("bands",
                             help="Score histogram in four bands")
    p_bands.add_argument("--db", default=DEFAULT_DB)
    p_bands.add_argument("--json", action="store_true")

    p_dom = sub.add_parser("per-domain",
                           help="Score statistics per domain")
    p_dom.add_argument("--db", default=DEFAULT_DB)
    p_dom.add_argument("--json", action="store_true")

    p_low = sub.add_parser("low-confidence",
                           help="Assignments below confidence threshold")
    p_low.add_argument("--db", default=DEFAULT_DB)
    p_low.add_argument("--threshold", type=float, default=0.5)
    p_low.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Domain score statistics")
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

    if args.cmd == "bands":
        results = score_bands(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No domain assignments found.")
            else:
                for r in results:
                    bar = "#" * int(r["share"] * 40)
                    print(f"  {r['band']:10s}  {r['count']:4d}  "
                          f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "per-domain":
        results = per_domain_scores(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No domain assignments found.")
            else:
                for r in results:
                    print(f"  {r['domain']:12s}  n={r['count']:3d}  "
                          f"mean={r['mean_score']:.4f}  "
                          f"med={r['median_score']:.4f}  "
                          f"range={r['min_score']:.2f}-{r['max_score']:.2f}  "
                          f"sd={r['stddev']:.4f}")

    elif args.cmd == "low-confidence":
        results = low_confidence(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No low-confidence assignments found.")
            else:
                print(f"{len(results)} assignments with score "
                      f"< {args.threshold:.2f}:")
                for r in results:
                    print(f"  {r['score']:.4f}  {r['domain']:12s}  "
                          f"{r['kind']:8s}  {r['chunk_id'][:12]}")

    elif args.cmd == "summary":
        result = score_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Domain Scores: {result['total_assignments']} assignments, "
                  f"{result['unique_domains']} domains")
            print(f"  Mean: {result['mean_score']:.4f}  "
                  f"Median: {result['median_score']:.4f}  "
                  f"SD: {result['stddev']:.4f}  "
                  f"Range: {result['min_score']:.2f}-{result['max_score']:.2f}")
            print(f"  Low (<0.5): {result['low_confidence_count']}  "
                  f"High (>=0.75): {result['high_confidence_count']}")

    conn.close()


if __name__ == "__main__":
    main()
