#!/usr/bin/env python3
"""Tag score trends: tagging confidence patterns over time.

Analyses how tag classification scores evolve over time, measuring
whether newer chunks are tagged more or less confidently and
identifying tags whose scores drift.

Usage:
    python tools/corpus/tag_score_trends.py by-period [--db PATH] [--bucket month|week] [--json]
    python tools/corpus/tag_score_trends.py per-tag [--db PATH] [--json]
    python tools/corpus/tag_score_trends.py drift [--db PATH] [--json]
    python tools/corpus/tag_score_trends.py summary [--db PATH] [--json]
    python tools/corpus/tag_score_trends.py selftest
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


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _date_bucket(utc_str: str, bucket: str) -> str:
    """Truncate an ISO timestamp to a month or week bucket."""
    if not utc_str or len(utc_str) < 10:
        return "unknown"
    date_part = utc_str[:10]
    if bucket == "month":
        return date_part[:7]
    from datetime import date
    try:
        d = date.fromisoformat(date_part)
        week_start = d.fromisocalendar(d.isocalendar()[0], d.isocalendar()[1], 1)
        return week_start.isoformat()
    except (ValueError, AttributeError):
        return date_part[:7]


def scores_by_period(conn, bucket: str = "month") -> list[dict]:
    """Mean tag score per time period."""
    if not _table_exists(conn, "chunk_tags"):
        return []

    rows = conn.execute(
        "SELECT ct.score, ct.tagged_utc FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_period: dict[str, list[float]] = {}
    for score, utc in rows:
        period = _date_bucket(utc, bucket)
        by_period.setdefault(period, []).append(score)

    results = []
    for period in sorted(by_period):
        scores = by_period[period]
        n = len(scores)
        mean = sum(scores) / n
        results.append({
            "period": period,
            "count": n,
            "mean_score": round(mean, 4),
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
        })

    return results


def per_tag_trends(conn) -> list[dict]:
    """Score statistics per tag with earliest and latest periods."""
    if not _table_exists(conn, "chunk_tags"):
        return []

    rows = conn.execute(
        "SELECT ct.tag, ct.score, ct.tagged_utc FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' "
        "ORDER BY ct.tag, ct.tagged_utc"
    ).fetchall()

    if not rows:
        return []

    by_tag: dict[str, list[tuple[float, str]]] = {}
    for tag, score, utc in rows:
        by_tag.setdefault(tag, []).append((score, utc or ""))

    results = []
    for tag, entries in sorted(by_tag.items()):
        scores = [s for s, _ in entries]
        utcs = sorted(u for _, u in entries if u)
        n = len(scores)
        mean = sum(scores) / n
        variance = sum((s - mean) ** 2 for s in scores) / n if n > 1 else 0.0

        results.append({
            "tag": tag,
            "count": n,
            "mean_score": round(mean, 4),
            "stddev": round(math.sqrt(variance), 4),
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
            "earliest": utcs[0][:10] if utcs else None,
            "latest": utcs[-1][:10] if utcs else None,
        })

    results.sort(key=lambda r: r["mean_score"])
    return results


def score_drift(conn) -> list[dict]:
    """Tags whose score changed between their first and second half of assignments.

    Splits each tag's assignments chronologically and compares the mean
    score of the first half to the second half.  A positive drift means
    scores are improving; negative means degrading.
    """
    if not _table_exists(conn, "chunk_tags"):
        return []

    rows = conn.execute(
        "SELECT ct.tag, ct.score, ct.tagged_utc FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' "
        "ORDER BY ct.tag, ct.tagged_utc"
    ).fetchall()

    if not rows:
        return []

    by_tag: dict[str, list[float]] = {}
    for tag, score, _ in rows:
        by_tag.setdefault(tag, []).append(score)

    results = []
    for tag, scores in sorted(by_tag.items()):
        if len(scores) < 2:
            continue
        mid = len(scores) // 2
        first_half = scores[:mid]
        second_half = scores[mid:]
        first_mean = sum(first_half) / len(first_half)
        second_mean = sum(second_half) / len(second_half)
        drift = second_mean - first_mean

        results.append({
            "tag": tag,
            "count": len(scores),
            "first_half_mean": round(first_mean, 4),
            "second_half_mean": round(second_mean, 4),
            "drift": round(drift, 4),
            "direction": "improving" if drift > 0 else "degrading" if drift < 0 else "stable",
        })

    results.sort(key=lambda r: abs(r["drift"]), reverse=True)
    return results


def trend_summary(conn) -> dict:
    """Aggregate tag score trend statistics."""
    if not _table_exists(conn, "chunk_tags"):
        return {
            "total_assignments": 0,
            "unique_tags": 0,
            "mean_score": 0.0,
            "periods_covered": 0,
            "improving_tags": 0,
            "degrading_tags": 0,
            "stable_tags": 0,
        }

    rows = conn.execute(
        "SELECT ct.score, ct.tagged_utc FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_assignments": 0,
            "unique_tags": 0,
            "mean_score": 0.0,
            "periods_covered": 0,
            "improving_tags": 0,
            "degrading_tags": 0,
            "stable_tags": 0,
        }

    scores = [r[0] for r in rows]
    periods = {_date_bucket(r[1], "month") for r in rows if r[1]}

    tag_row = conn.execute(
        "SELECT count(DISTINCT ct.tag) FROM chunk_tags ct "
        "JOIN chunks c ON ct.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted'"
    ).fetchone()

    drift = score_drift(conn)
    improving = sum(1 for d in drift if d["direction"] == "improving")
    degrading = sum(1 for d in drift if d["direction"] == "degrading")
    stable = sum(1 for d in drift if d["direction"] == "stable")

    return {
        "total_assignments": len(scores),
        "unique_tags": tag_row[0],
        "mean_score": round(sum(scores) / len(scores), 4),
        "periods_covered": len(periods),
        "improving_tags": improving,
        "degrading_tags": degrading,
        "stable_tags": stable,
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
            "CREATE TABLE IF NOT EXISTS chunk_tags ("
            "chunk_id TEXT NOT NULL, tag TEXT NOT NULL, "
            "score REAL, tagged_utc TEXT, "
            "PRIMARY KEY (chunk_id, tag))"
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

        for i in range(6):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", "s1", i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 50, f"n_c{i}",
                 "accepted", now),
            )

        tags = [
            ("c0", "ml", 0.6, "2026-07-01T10:00:00Z"),
            ("c1", "ml", 0.7, "2026-07-15T10:00:00Z"),
            ("c2", "ml", 0.8, "2026-08-01T10:00:00Z"),
            ("c3", "ml", 0.85, "2026-08-15T10:00:00Z"),
            ("c0", "nlp", 0.9, "2026-07-01T10:00:00Z"),
            ("c1", "nlp", 0.85, "2026-07-15T10:00:00Z"),
            ("c2", "nlp", 0.7, "2026-08-01T10:00:00Z"),
            ("c3", "nlp", 0.6, "2026-08-15T10:00:00Z"),
            ("c4", "systems", 0.5, "2026-08-01T10:00:00Z"),
            ("c5", "systems", 0.5, "2026-08-15T10:00:00Z"),
        ]
        for chunk_id, tag, score, utc in tags:
            conn.execute(
                "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
                "VALUES (?, ?, ?, ?)",
                (chunk_id, tag, score, utc),
            )

        conn.commit()

        # 1: by-period returns entries
        by_per = scores_by_period(conn, "month")
        assert len(by_per) >= 2
        checks += 1

        # 2: periods are sorted chronologically
        periods = [r["period"] for r in by_per]
        assert periods == sorted(periods)
        checks += 1

        # 3: each period has positive count
        for r in by_per:
            assert r["count"] > 0
            assert 0.0 <= r["mean_score"] <= 1.0
        checks += 1

        # 4: per-tag returns all tags
        per_tag = per_tag_trends(conn)
        tag_set = {t["tag"] for t in per_tag}
        assert tag_set == {"ml", "nlp", "systems"}
        checks += 1

        # 5: sorted by mean_score ascending
        means = [t["mean_score"] for t in per_tag]
        assert means == sorted(means)
        checks += 1

        # 6: ml tag has earliest in July
        ml = next(t for t in per_tag if t["tag"] == "ml")
        assert ml["earliest"] == "2026-07-01"
        checks += 1

        # 7: drift returns tags with >= 2 assignments
        drift = score_drift(conn)
        assert len(drift) >= 2
        checks += 1

        # 8: ml tag is improving (scores go up over time)
        ml_drift = next(d for d in drift if d["tag"] == "ml")
        assert ml_drift["direction"] == "improving"
        assert ml_drift["drift"] > 0
        checks += 1

        # 9: nlp tag is degrading (scores go down over time)
        nlp_drift = next(d for d in drift if d["tag"] == "nlp")
        assert nlp_drift["direction"] == "degrading"
        assert nlp_drift["drift"] < 0
        checks += 1

        # 10: drift sorted by abs(drift) descending
        drifts = [abs(d["drift"]) for d in drift]
        assert drifts == sorted(drifts, reverse=True)
        checks += 1

        # 11: summary has correct totals
        summary = trend_summary(conn)
        assert summary["total_assignments"] == 10
        assert summary["unique_tags"] == 3
        checks += 1

        # 12: improving and degrading counts
        assert summary["improving_tags"] >= 1
        assert summary["degrading_tags"] >= 1
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(by_per)
        _ = json.dumps(per_tag)
        _ = json.dumps(drift)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = scores_by_period(conn2)
        assert empty == []
        empty_summary = trend_summary(conn2)
        assert empty_summary["total_assignments"] == 0
        checks += 1

    print(f"PASS tag_score_trends selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tag score trends: tagging confidence over time"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_per = sub.add_parser("by-period",
                           help="Mean tag score per time period")
    p_per.add_argument("--db", default=DEFAULT_DB)
    p_per.add_argument("--bucket", choices=["month", "week"],
                       default="month")
    p_per.add_argument("--json", action="store_true")

    p_tag = sub.add_parser("per-tag",
                           help="Score statistics per tag")
    p_tag.add_argument("--db", default=DEFAULT_DB)
    p_tag.add_argument("--json", action="store_true")

    p_drift = sub.add_parser("drift",
                             help="Tags with score drift over time")
    p_drift.add_argument("--db", default=DEFAULT_DB)
    p_drift.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Tag score trend statistics")
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

    if args.cmd == "by-period":
        results = scores_by_period(conn, args.bucket)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No tagged chunks found.")
            else:
                for r in results:
                    bar = "#" * int(r["mean_score"] * 40)
                    print(f"  {r['period']:10s}  n={r['count']:4d}  "
                          f"mean={r['mean_score']:.4f}  "
                          f"range={r['min_score']:.2f}-{r['max_score']:.2f}  "
                          f"{bar}")

    elif args.cmd == "per-tag":
        results = per_tag_trends(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No tagged chunks found.")
            else:
                for r in results:
                    span = ""
                    if r["earliest"] and r["latest"]:
                        span = f"  {r['earliest']}..{r['latest']}"
                    print(f"  {r['tag']:12s}  n={r['count']:3d}  "
                          f"mean={r['mean_score']:.4f}  "
                          f"sd={r['stddev']:.4f}{span}")

    elif args.cmd == "drift":
        results = score_drift(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No tags with enough data for drift analysis.")
            else:
                for r in results:
                    arrow = "+" if r["drift"] > 0 else ""
                    print(f"  {r['tag']:12s}  {r['direction']:10s}  "
                          f"drift={arrow}{r['drift']:.4f}  "
                          f"({r['first_half_mean']:.3f} -> "
                          f"{r['second_half_mean']:.3f})")

    elif args.cmd == "summary":
        result = trend_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Tags: {result['total_assignments']} assignments, "
                  f"{result['unique_tags']} tags, "
                  f"{result['periods_covered']} periods")
            print(f"  Mean score: {result['mean_score']:.4f}")
            print(f"  Drift: {result['improving_tags']} improving, "
                  f"{result['degrading_tags']} degrading, "
                  f"{result['stable_tags']} stable")

    conn.close()


if __name__ == "__main__":
    main()
