#!/usr/bin/env python3
"""Version churn rate: temporal velocity of chunk revisions.

Measures how frequently chunks change over time, identifies
acceleration or deceleration in revision activity, and reports
per-period churn rates.

Usage:
    python tools/corpus/version_churn.py rate [--db PATH] [--json]
    python tools/corpus/version_churn.py hotspots [--db PATH] [--top N] [--json]
    python tools/corpus/version_churn.py summary [--db PATH] [--json]
    python tools/corpus/version_churn.py selftest
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


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _parse_month(s: str) -> str:
    """Extract YYYY-MM from an ISO timestamp."""
    return s[:7] if s and len(s) >= 7 else "unknown"


def churn_rate(conn) -> list[dict]:
    """Per-month revision counts showing churn velocity over time."""
    if not _table_exists(conn, "chunk_versions"):
        return []

    rows = conn.execute(
        "SELECT snapshot_utc FROM chunk_versions "
        "WHERE snapshot_utc IS NOT NULL "
        "ORDER BY snapshot_utc"
    ).fetchall()

    if not rows:
        return []

    monthly: dict[str, int] = {}
    for (ts,) in rows:
        month = _parse_month(ts)
        monthly[month] = monthly.get(month, 0) + 1

    sorted_months = sorted(monthly.keys())
    results = []
    prev_count = None
    for month in sorted_months:
        count = monthly[month]
        delta = None
        trend = "stable"
        if prev_count is not None:
            delta = count - prev_count
            if delta > 0:
                trend = "accelerating"
            elif delta < 0:
                trend = "decelerating"
        results.append({
            "month": month,
            "revisions": count,
            "delta": delta,
            "trend": trend,
        })
        prev_count = count

    return results


def churn_hotspots(conn, top_n: int = 20) -> list[dict]:
    """Chunks with the highest churn rate (revisions per day of active life)."""
    if not _table_exists(conn, "chunk_versions"):
        return []

    rows = conn.execute(
        "SELECT cv.chunk_id, count(*) AS rev_count, "
        "min(cv.snapshot_utc) AS first_snap, "
        "max(cv.snapshot_utc) AS last_snap, "
        "c.heading_path, c.kind, c.source_id "
        "FROM chunk_versions cv "
        "JOIN chunks c ON c.chunk_id = cv.chunk_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY cv.chunk_id "
        "HAVING rev_count > 1 "
        "ORDER BY rev_count DESC"
    ).fetchall()

    if not rows:
        return []

    results = []
    for chunk_id, rev_count, first_snap, last_snap, heading, kind, source_id in rows:
        span_days = 1.0
        if first_snap and last_snap and first_snap != last_snap:
            try:
                f = first_snap.replace("Z", "+00:00")
                l = last_snap.replace("Z", "+00:00")
                fd = datetime.datetime.fromisoformat(f)
                ld = datetime.datetime.fromisoformat(l)
                span_days = max((ld - fd).total_seconds() / 86400, 1.0)
            except (ValueError, TypeError):
                pass

        rate = round(rev_count / span_days, 4)
        results.append({
            "chunk_id": chunk_id,
            "source_id": source_id,
            "heading": heading,
            "kind": kind,
            "revision_count": rev_count,
            "span_days": round(span_days, 1),
            "churn_rate": rate,
        })

    results.sort(key=lambda r: r["churn_rate"], reverse=True)
    return results[:top_n]


def churn_summary(conn) -> dict:
    """Aggregate churn statistics."""
    if not _table_exists(conn, "chunk_versions"):
        return {
            "total_revisions": 0,
            "versioned_chunks": 0,
            "multi_revision_chunks": 0,
            "months_active": 0,
            "mean_monthly_revisions": 0.0,
            "peak_month": None,
            "peak_revisions": 0,
            "latest_trend": "stable",
        }

    total_revisions = conn.execute(
        "SELECT count(*) FROM chunk_versions"
    ).fetchone()[0]

    versioned = conn.execute(
        "SELECT count(DISTINCT chunk_id) FROM chunk_versions"
    ).fetchone()[0]

    multi = conn.execute(
        "SELECT count(*) FROM ("
        "SELECT chunk_id FROM chunk_versions "
        "GROUP BY chunk_id HAVING count(*) > 1)"
    ).fetchone()[0]

    rates = churn_rate(conn)

    if not rates:
        return {
            "total_revisions": total_revisions,
            "versioned_chunks": versioned,
            "multi_revision_chunks": multi,
            "months_active": 0,
            "mean_monthly_revisions": 0.0,
            "peak_month": None,
            "peak_revisions": 0,
            "latest_trend": "stable",
        }

    months_active = len(rates)
    mean_monthly = round(
        sum(r["revisions"] for r in rates) / months_active, 1
    ) if months_active > 0 else 0.0

    peak = max(rates, key=lambda r: r["revisions"])
    latest_trend = rates[-1]["trend"] if rates else "stable"

    return {
        "total_revisions": total_revisions,
        "versioned_chunks": versioned,
        "multi_revision_chunks": multi,
        "months_active": months_active,
        "mean_monthly_revisions": mean_monthly,
        "peak_month": peak["month"],
        "peak_revisions": peak["revisions"],
        "latest_trend": latest_trend,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
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

        for i in range(3):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", "s1", i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_c{i}",
                 "accepted", now),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_versions "
            "(version_id TEXT PRIMARY KEY, chunk_id TEXT, version_num INTEGER, "
            "norm_sha256 TEXT, word_count INTEGER, snapshot_utc TEXT, "
            "UNIQUE(chunk_id, version_num))"
        )

        versions = [
            ("v1", "c0", 1, "sha_v1", 10, "2026-06-01T00:00:00Z"),
            ("v2", "c0", 2, "sha_v2", 12, "2026-06-15T00:00:00Z"),
            ("v3", "c0", 3, "sha_v3", 11, "2026-07-01T00:00:00Z"),
            ("v4", "c0", 4, "sha_v4", 13, "2026-07-10T00:00:00Z"),
            ("v5", "c1", 1, "sha_v5", 10, "2026-07-01T00:00:00Z"),
            ("v6", "c1", 2, "sha_v6", 15, "2026-08-01T00:00:00Z"),
            ("v7", "c2", 1, "sha_v7", 10, "2026-08-01T00:00:00Z"),
        ]
        for vid, cid, vn, sha, wc, ts in versions:
            conn.execute(
                "INSERT INTO chunk_versions VALUES (?, ?, ?, ?, ?, ?)",
                (vid, cid, vn, sha, wc, ts),
            )

        conn.commit()

        # 1: churn rate returns monthly entries
        rates = churn_rate(conn)
        assert len(rates) >= 2
        checks += 1

        # 2: months are sorted chronologically
        months = [r["month"] for r in rates]
        assert months == sorted(months)
        checks += 1

        # 3: revisions are positive
        assert all(r["revisions"] > 0 for r in rates)
        checks += 1

        # 4: delta is None for first month, integer for others
        assert rates[0]["delta"] is None
        assert all(r["delta"] is not None for r in rates[1:])
        checks += 1

        # 5: trend values are valid
        valid_trends = {"stable", "accelerating", "decelerating"}
        assert all(r["trend"] in valid_trends for r in rates)
        checks += 1

        # 6: hotspots returns chunks with multiple revisions
        hotspots = churn_hotspots(conn)
        assert len(hotspots) >= 1
        checks += 1

        # 7: c0 has highest churn (4 revisions)
        c0 = next((h for h in hotspots if h["chunk_id"] == "c0"), None)
        assert c0 is not None
        assert c0["revision_count"] == 4
        checks += 1

        # 8: churn rate is positive
        assert all(h["churn_rate"] > 0 for h in hotspots)
        checks += 1

        # 9: sorted by churn_rate descending
        churn_rates = [h["churn_rate"] for h in hotspots]
        assert churn_rates == sorted(churn_rates, reverse=True)
        checks += 1

        # 10: single-revision chunks excluded from hotspots
        hotspot_ids = [h["chunk_id"] for h in hotspots]
        assert "c2" not in hotspot_ids
        checks += 1

        # 11: summary has required keys
        summary = churn_summary(conn)
        assert summary["total_revisions"] == 7
        assert summary["versioned_chunks"] == 3
        assert summary["multi_revision_chunks"] == 2
        checks += 1

        # 12: peak month identified
        assert summary["peak_month"] is not None
        assert summary["peak_revisions"] > 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(rates)
        _ = json.dumps(hotspots)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = churn_rate(conn2)
        assert empty == []
        empty_summary = churn_summary(conn2)
        assert empty_summary["total_revisions"] == 0
        checks += 1

    print(f"PASS version_churn selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Version churn rate: revision velocity over time"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_rate = sub.add_parser("rate",
                            help="Per-month revision churn rate")
    p_rate.add_argument("--db", default=DEFAULT_DB)
    p_rate.add_argument("--json", action="store_true")

    p_hot = sub.add_parser("hotspots",
                           help="Chunks with highest churn rate")
    p_hot.add_argument("--db", default=DEFAULT_DB)
    p_hot.add_argument("--top", type=int, default=20)
    p_hot.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Churn statistics")
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

    if args.cmd == "rate":
        results = churn_rate(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                delta_str = f"{r['delta']:+4d}" if r["delta"] is not None else "   -"
                print(f"  {r['month']}  {r['revisions']:4d} revisions  "
                      f"{delta_str}  {r['trend']}")

    elif args.cmd == "hotspots":
        results = churn_hotspots(conn, args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No multi-revision chunks found.")
            else:
                print(f"Top {len(results)} churn hotspots:")
                for h in results:
                    print(f"  {h['churn_rate']:.3f}/d  {h['revision_count']:3d} revs  "
                          f"{h['span_days']:.0f}d  {h['chunk_id'][:12]:12s}  "
                          f"{h['heading']}")

    elif args.cmd == "summary":
        result = churn_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Version Churn: {result['total_revisions']} revisions "
                  f"across {result['versioned_chunks']} chunks")
            print(f"  Multi-revision: {result['multi_revision_chunks']}  "
                  f"Active months: {result['months_active']}")
            print(f"  Mean monthly: {result['mean_monthly_revisions']:.1f}  "
                  f"Latest trend: {result['latest_trend']}")
            if result["peak_month"]:
                print(f"  Peak: {result['peak_month']} "
                      f"({result['peak_revisions']} revisions)")

    conn.close()


if __name__ == "__main__":
    main()
