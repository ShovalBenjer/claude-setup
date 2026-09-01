#!/usr/bin/env python3
"""Source lifecycle: ingestion lag, liveness states, and kind profiles.

Analyses the time between publication and ingestion, how sources
distribute across liveness states, and which source kinds dominate.

Usage:
    python tools/corpus/source_lifecycle.py lag [--db PATH] [--json]
    python tools/corpus/source_lifecycle.py liveness [--db PATH] [--json]
    python tools/corpus/source_lifecycle.py kinds [--db PATH] [--json]
    python tools/corpus/source_lifecycle.py summary [--db PATH] [--json]
    python tools/corpus/source_lifecycle.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _parse_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def ingestion_lag(conn) -> list[dict]:
    """Per-source lag between published_utc and fetched_utc."""
    rows = conn.execute(
        "SELECT source_id, title, kind, published_utc, fetched_utc "
        "FROM sources"
    ).fetchall()

    if not rows:
        return []

    results = []
    for src_id, title, kind, pub, fetch in rows:
        pub_dt = _parse_utc(pub)
        fetch_dt = _parse_utc(fetch)

        if pub_dt and fetch_dt:
            lag_seconds = (fetch_dt - pub_dt).total_seconds()
            lag_days = round(lag_seconds / 86400, 2)
        else:
            lag_days = None

        results.append({
            "source_id": src_id,
            "title": title,
            "kind": kind,
            "published_utc": pub or "",
            "fetched_utc": fetch or "",
            "lag_days": lag_days,
        })

    results.sort(key=lambda r: r["lag_days"] if r["lag_days"] is not None else -1,
                 reverse=True)
    return results


def liveness_distribution(conn) -> list[dict]:
    """Distribution of sources across liveness states."""
    rows = conn.execute(
        "SELECT liveness, count(*) FROM sources GROUP BY liveness"
    ).fetchall()

    if not rows:
        return []

    total = sum(count for _, count in rows)
    results = []
    for state, count in rows:
        results.append({
            "liveness": state,
            "count": count,
            "share": round(count / total, 4) if total > 0 else 0.0,
        })

    results.sort(key=lambda r: r["count"], reverse=True)
    return results


def kind_distribution(conn) -> list[dict]:
    """Distribution of sources across kind values."""
    rows = conn.execute(
        "SELECT kind, count(*), avg(bytes) FROM sources GROUP BY kind"
    ).fetchall()

    if not rows:
        return []

    total = sum(count for _, count, _ in rows)
    results = []
    for kind, count, avg_bytes in rows:
        chunk_count = conn.execute(
            "SELECT count(*) FROM chunks c "
            "JOIN sources s ON c.source_id = s.source_id "
            "WHERE s.kind = ? AND c.status = 'accepted'",
            (kind,),
        ).fetchone()[0]

        results.append({
            "kind": kind,
            "source_count": count,
            "share": round(count / total, 4) if total > 0 else 0.0,
            "avg_bytes": round(avg_bytes) if avg_bytes else 0,
            "accepted_chunks": chunk_count,
        })

    results.sort(key=lambda r: r["source_count"], reverse=True)
    return results


def lifecycle_summary(conn) -> dict:
    """Aggregate source lifecycle statistics."""
    total = conn.execute("SELECT count(*) FROM sources").fetchone()[0]

    if total == 0:
        return {
            "total_sources": 0,
            "with_lag": 0,
            "mean_lag_days": 0.0,
            "median_lag_days": 0.0,
            "max_lag_days": 0.0,
            "liveness_states": 0,
            "source_kinds": 0,
            "live_count": 0,
            "stale_or_dead_count": 0,
        }

    lags = ingestion_lag(conn)
    valid_lags = sorted(
        r["lag_days"] for r in lags if r["lag_days"] is not None and r["lag_days"] >= 0
    )

    mean_lag = round(sum(valid_lags) / len(valid_lags), 2) if valid_lags else 0.0
    median_lag = round(valid_lags[len(valid_lags) // 2], 2) if valid_lags else 0.0
    max_lag = round(max(valid_lags), 2) if valid_lags else 0.0

    liveness = liveness_distribution(conn)
    live_count = sum(r["count"] for r in liveness if r["liveness"] == "live")
    stale_dead = sum(
        r["count"] for r in liveness if r["liveness"] in ("stale", "dead")
    )

    kinds = kind_distribution(conn)

    return {
        "total_sources": total,
        "with_lag": len(valid_lags),
        "mean_lag_days": mean_lag,
        "median_lag_days": median_lag,
        "max_lag_days": max_lag,
        "liveness_states": len(liveness),
        "source_kinds": len(kinds),
        "live_count": live_count,
        "stale_or_dead_count": stale_dead,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        sources = [
            ("s1", "https://a.com", "paper", "Paper A",
             "2026-01-01T00:00:00Z", "2026-01-15T00:00:00Z", "live"),
            ("s2", "https://b.com", "paper", "Paper B",
             "2026-02-01T00:00:00Z", "2026-02-03T00:00:00Z", "live"),
            ("s3", "https://c.com", "local_md", "Local C",
             "2026-03-01T00:00:00Z", "2026-03-01T00:00:00Z", "stale"),
            ("s4", "https://d.com", "hf_dataset", "Dataset D",
             "2026-04-01T00:00:00Z", "2026-04-20T00:00:00Z", "dead"),
        ]

        for sid, uri, kind, title, pub, fetch, live in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, kind, title,
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 pub, fetch, "", "", live, f"sha_{sid}", 1000, None),
            )

        for i in range(6):
            sid = f"s{(i % 4) + 1}"
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", sid, i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_c{i}",
                 "accepted", "2026-01-15T00:00:00Z"),
            )

        conn.commit()

        # 1: lag returns all sources
        lags = ingestion_lag(conn)
        assert len(lags) == 4
        checks += 1

        # 2: s1 has 14-day lag
        s1 = next(r for r in lags if r["source_id"] == "s1")
        assert s1["lag_days"] == 14.0
        checks += 1

        # 3: s3 has 0-day lag (same day)
        s3 = next(r for r in lags if r["source_id"] == "s3")
        assert s3["lag_days"] == 0.0
        checks += 1

        # 4: sorted by lag descending
        valid = [r["lag_days"] for r in lags if r["lag_days"] is not None]
        assert valid == sorted(valid, reverse=True)
        checks += 1

        # 5: liveness returns all states
        live_dist = liveness_distribution(conn)
        states = {r["liveness"] for r in live_dist}
        assert states == {"live", "stale", "dead"}
        checks += 1

        # 6: shares sum to approximately 1.0
        total_share = sum(r["share"] for r in live_dist)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 7: live has most sources
        live_row = next(r for r in live_dist if r["liveness"] == "live")
        assert live_row["count"] == 2
        checks += 1

        # 8: kind distribution returns all kinds
        kinds = kind_distribution(conn)
        kind_set = {r["kind"] for r in kinds}
        assert kind_set == {"paper", "local_md", "hf_dataset"}
        checks += 1

        # 9: paper kind has 2 sources
        paper = next(r for r in kinds if r["kind"] == "paper")
        assert paper["source_count"] == 2
        checks += 1

        # 10: accepted_chunks is non-negative
        assert all(r["accepted_chunks"] >= 0 for r in kinds)
        checks += 1

        # 11: summary has required keys
        summary = lifecycle_summary(conn)
        assert summary["total_sources"] == 4
        assert summary["liveness_states"] == 3
        assert summary["source_kinds"] == 3
        checks += 1

        # 12: mean lag is positive
        assert summary["mean_lag_days"] > 0
        assert summary["max_lag_days"] >= summary["mean_lag_days"]
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(lags)
        _ = json.dumps(live_dist)
        _ = json.dumps(kinds)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = ingestion_lag(conn2)
        assert empty == []
        empty_summary = lifecycle_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS source_lifecycle selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Source lifecycle: ingestion lag, liveness, and kind profiles"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_lag = sub.add_parser("lag",
                           help="Per-source ingestion lag")
    p_lag.add_argument("--db", default=DEFAULT_DB)
    p_lag.add_argument("--json", action="store_true")

    p_live = sub.add_parser("liveness",
                            help="Liveness state distribution")
    p_live.add_argument("--db", default=DEFAULT_DB)
    p_live.add_argument("--json", action="store_true")

    p_kinds = sub.add_parser("kinds",
                             help="Source kind distribution")
    p_kinds.add_argument("--db", default=DEFAULT_DB)
    p_kinds.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Lifecycle statistics")
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

    if args.cmd == "lag":
        results = ingestion_lag(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                lag = f"{r['lag_days']:7.1f}d" if r["lag_days"] is not None else "    n/a"
                print(f"  {lag}  {r['kind']:10s}  "
                      f"{r['source_id'][:12]:12s}  {r['title'][:30]}")

    elif args.cmd == "liveness":
        results = liveness_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['liveness']:10s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "kinds":
        results = kind_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['kind']:12s}  {r['source_count']:3d} sources  "
                      f"{r['accepted_chunks']:4d} chunks  "
                      f"{r['avg_bytes']:7d}B avg")

    elif args.cmd == "summary":
        result = lifecycle_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}  "
                  f"Kinds: {result['source_kinds']}  "
                  f"Liveness states: {result['liveness_states']}")
            print(f"  Ingestion lag: mean {result['mean_lag_days']:.1f}d  "
                  f"median {result['median_lag_days']:.1f}d  "
                  f"max {result['max_lag_days']:.1f}d")
            print(f"  Live: {result['live_count']}  "
                  f"Stale/dead: {result['stale_or_dead_count']}")

    conn.close()


if __name__ == "__main__":
    main()
