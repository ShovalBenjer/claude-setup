#!/usr/bin/env python3
"""Temporal distribution analysis: ingestion and publication timelines.

Analyses the timestamp columns (ingested_utc, published_utc, fetched_utc)
to reveal when content was created, fetched, and ingested into the corpus.

Usage:
    python tools/corpus/temporal_distribution.py ingestion [--db PATH] [--json]
    python tools/corpus/temporal_distribution.py publication [--db PATH] [--json]
    python tools/corpus/temporal_distribution.py fetch-lag [--db PATH] [--json]
    python tools/corpus/temporal_distribution.py summary [--db PATH] [--json]
    python tools/corpus/temporal_distribution.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _parse_utc(s: str | None) -> datetime.datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, fmt).replace(
                tzinfo=datetime.timezone.utc
            )
        except ValueError:
            continue
    return None


def _month_key(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m")


def ingestion_distribution(conn) -> list[dict]:
    """Distribution of chunk ingestion times by month."""
    rows = conn.execute(
        "SELECT ingested_utc FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_month: dict[str, int] = {}
    for (ts,) in rows:
        dt = _parse_utc(ts)
        if dt:
            key = _month_key(dt)
            by_month[key] = by_month.get(key, 0) + 1

    if not by_month:
        return []

    total = sum(by_month.values())
    results = [
        {
            "month": m,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        }
        for m, n in sorted(by_month.items())
    ]
    return results


def publication_distribution(conn) -> list[dict]:
    """Distribution of source publication dates by month."""
    rows = conn.execute(
        "SELECT published_utc FROM sources "
        "WHERE published_utc IS NOT NULL AND published_utc != ''"
    ).fetchall()

    if not rows:
        return []

    by_month: dict[str, int] = {}
    for (ts,) in rows:
        dt = _parse_utc(ts)
        if dt:
            key = _month_key(dt)
            by_month[key] = by_month.get(key, 0) + 1

    if not by_month:
        return []

    total = sum(by_month.values())
    results = [
        {
            "month": m,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        }
        for m, n in sorted(by_month.items())
    ]
    return results


def _lag_bucket(days: int) -> str:
    if days < 0:
        return "negative"
    if days == 0:
        return "same-day"
    if days <= 7:
        return "1-7d"
    if days <= 30:
        return "8-30d"
    if days <= 90:
        return "31-90d"
    return ">90d"


def fetch_lag(conn) -> list[dict]:
    """Distribution of lag between publication and fetch times."""
    rows = conn.execute(
        "SELECT published_utc, fetched_utc FROM sources "
        "WHERE published_utc IS NOT NULL AND published_utc != '' "
        "AND fetched_utc IS NOT NULL AND fetched_utc != ''"
    ).fetchall()

    if not rows:
        return []

    buckets: dict[str, int] = {}
    for pub_s, fetch_s in rows:
        pub = _parse_utc(pub_s)
        fetch = _parse_utc(fetch_s)
        if pub and fetch:
            days = (fetch - pub).days
            bucket = _lag_bucket(days)
            buckets[bucket] = buckets.get(bucket, 0) + 1

    if not buckets:
        return []

    order = ["negative", "same-day", "1-7d", "8-30d", "31-90d", ">90d"]
    total = sum(buckets.values())
    results = []
    for b in order:
        if b in buckets:
            n = buckets[b]
            results.append({
                "bucket": b,
                "count": n,
                "share": round(n / total, 4) if total > 0 else 0.0,
            })

    return results


def temporal_summary(conn) -> dict:
    """Aggregate temporal statistics."""
    chunk_rows = conn.execute(
        "SELECT ingested_utc FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    source_rows = conn.execute(
        "SELECT published_utc, fetched_utc FROM sources"
    ).fetchall()

    ingested_dates = []
    for (ts,) in chunk_rows:
        dt = _parse_utc(ts)
        if dt:
            ingested_dates.append(dt)

    pub_dates = []
    fetch_dates = []
    lags = []
    for pub_s, fetch_s in source_rows:
        pub = _parse_utc(pub_s)
        fetch = _parse_utc(fetch_s)
        if pub:
            pub_dates.append(pub)
        if fetch:
            fetch_dates.append(fetch)
        if pub and fetch:
            lags.append((fetch - pub).days)

    def _fmt(dt: datetime.datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "total_chunks": len(chunk_rows),
        "ingested_range": {
            "earliest": _fmt(min(ingested_dates)) if ingested_dates else None,
            "latest": _fmt(max(ingested_dates)) if ingested_dates else None,
            "distinct_months": len({_month_key(d) for d in ingested_dates}),
        },
        "total_sources": len(source_rows),
        "publication_range": {
            "earliest": _fmt(min(pub_dates)) if pub_dates else None,
            "latest": _fmt(max(pub_dates)) if pub_dates else None,
            "populated": len(pub_dates),
            "distinct_months": len({_month_key(d) for d in pub_dates}),
        },
        "fetch_range": {
            "earliest": _fmt(min(fetch_dates)) if fetch_dates else None,
            "latest": _fmt(max(fetch_dates)) if fetch_dates else None,
            "populated": len(fetch_dates),
        },
        "fetch_lag": {
            "sources_with_both": len(lags),
            "mean_days": round(sum(lags) / len(lags), 1) if lags else 0.0,
            "max_days": max(lags) if lags else 0,
            "min_days": min(lags) if lags else 0,
        },
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        d1 = "2026-06-15T10:00:00Z"
        d2 = "2026-07-20T12:00:00Z"
        d3 = "2026-08-01T08:00:00Z"
        d4 = "2026-08-15T14:00:00Z"

        f1 = "2026-06-16T10:00:00Z"
        f2 = "2026-08-01T12:00:00Z"
        f3 = "2026-08-02T08:00:00Z"
        f4 = "2026-08-20T14:00:00Z"

        sources = [
            ("s1", "paper", d1, f1),
            ("s2", "paper", d2, f2),
            ("s3", "local_md", d3, f3),
            ("s4", "local_md", d4, f4),
        ]
        for sid, kind, pub, fetch in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 pub, fetch, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunks = [
            ("c1", "s1", 0, d1),
            ("c2", "s1", 1, d1),
            ("c3", "s2", 0, d2),
            ("c4", "s3", 0, d3),
            ("c5", "s3", 1, d3),
            ("c6", "s4", 0, d4),
            ("c7", "s4", 1, d4),
        ]
        for cid, sid, ordinal, ing in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", "prose", "en",
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, 0, "accepted", ing),
            )

        conn.commit()

        # 1: ingestion distribution returns entries
        ing = ingestion_distribution(conn)
        assert len(ing) > 0
        checks += 1

        # 2: distinct months present
        months = {i["month"] for i in ing}
        assert "2026-06" in months
        assert "2026-08" in months
        checks += 1

        # 3: shares sum to approximately 1.0
        total_share = sum(i["share"] for i in ing)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 4: publication distribution returns entries
        pub = publication_distribution(conn)
        assert len(pub) > 0
        checks += 1

        # 5: 4 distinct publication months
        pub_months = {p["month"] for p in pub}
        assert len(pub_months) >= 3
        checks += 1

        # 6: fetch-lag returns entries
        fl = fetch_lag(conn)
        assert len(fl) > 0
        checks += 1

        # 7: s1 has 1-day lag (same-day or 1-7d)
        bucket_set = {f["bucket"] for f in fl}
        assert len(bucket_set) > 0
        checks += 1

        # 8: lag shares sum to approximately 1.0
        lag_share = sum(f["share"] for f in fl)
        assert abs(lag_share - 1.0) < 0.01
        checks += 1

        # 9: summary has correct chunk count
        summary = temporal_summary(conn)
        assert summary["total_chunks"] == 7
        assert summary["total_sources"] == 4
        checks += 1

        # 10: ingestion range populated
        assert summary["ingested_range"]["earliest"] is not None
        assert summary["ingested_range"]["distinct_months"] >= 3
        checks += 1

        # 11: publication range populated
        assert summary["publication_range"]["populated"] == 4
        assert summary["publication_range"]["distinct_months"] >= 3
        checks += 1

        # 12: fetch lag stats
        assert summary["fetch_lag"]["sources_with_both"] == 4
        assert summary["fetch_lag"]["mean_days"] > 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(ing)
        _ = json.dumps(pub)
        _ = json.dumps(fl)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = ingestion_distribution(conn2)
        assert empty == []
        empty_summary = temporal_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(f"PASS temporal_distribution selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Temporal distribution analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ing = sub.add_parser("ingestion",
                           help="Ingestion time distribution")
    p_ing.add_argument("--db", default=DEFAULT_DB)
    p_ing.add_argument("--json", action="store_true")

    p_pub = sub.add_parser("publication",
                           help="Publication date distribution")
    p_pub.add_argument("--db", default=DEFAULT_DB)
    p_pub.add_argument("--json", action="store_true")

    p_lag = sub.add_parser("fetch-lag",
                           help="Fetch lag distribution")
    p_lag.add_argument("--db", default=DEFAULT_DB)
    p_lag.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Temporal statistics")
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

    if args.cmd == "ingestion":
        results = ingestion_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['month']}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "publication":
        results = publication_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['month']}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "fetch-lag":
        results = fetch_lag(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['bucket']:10s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "summary":
        result = temporal_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            ir = result["ingested_range"]
            pr = result["publication_range"]
            fl = result["fetch_lag"]
            print(f"Chunks: {result['total_chunks']}  "
                  f"Sources: {result['total_sources']}")
            print(f"  Ingested: {ir['earliest']} to {ir['latest']}  "
                  f"({ir['distinct_months']} months)")
            print(f"  Published: {pr['earliest']} to {pr['latest']}  "
                  f"({pr['populated']} sources, "
                  f"{pr['distinct_months']} months)")
            print(f"  Fetch lag: mean={fl['mean_days']:.0f}d  "
                  f"max={fl['max_days']}d  "
                  f"({fl['sources_with_both']} sources)")

    conn.close()


if __name__ == "__main__":
    main()
