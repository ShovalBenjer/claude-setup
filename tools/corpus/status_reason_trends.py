#!/usr/bin/env python3
"""Status reason trends: quarantine and rejection patterns over time.

Analyses why chunks leave the accepted state, tracking status_reason
frequency over time and by source to identify systematic extraction
or quality issues.

Usage:
    python tools/corpus/status_reason_trends.py by-time [--db PATH] [--bucket month|week] [--json]
    python tools/corpus/status_reason_trends.py by-source [--db PATH] [--json]
    python tools/corpus/status_reason_trends.py by-kind [--db PATH] [--json]
    python tools/corpus/status_reason_trends.py summary [--db PATH] [--json]
    python tools/corpus/status_reason_trends.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _date_bucket(utc_str: str, bucket: str) -> str:
    """Truncate an ISO timestamp to a month or week bucket."""
    if not utc_str or len(utc_str) < 10:
        return "unknown"
    date_part = utc_str[:10]
    if bucket == "month":
        return date_part[:7]
    # week: truncate to ISO week start (Monday)
    from datetime import date
    try:
        d = date.fromisoformat(date_part)
        week_start = d.fromisocalendar(d.isocalendar()[0], d.isocalendar()[1], 1)
        return week_start.isoformat()
    except (ValueError, AttributeError):
        return date_part[:7]


def reason_by_time(conn, bucket: str = "month") -> list[dict]:
    """Status reason counts bucketed by time period."""
    rows = conn.execute(
        "SELECT status_reason, ingested_utc FROM chunks "
        "WHERE status != 'accepted' AND status_reason IS NOT NULL "
        "AND status_reason != ''"
    ).fetchall()

    if not rows:
        return []

    by_period: dict[str, dict[str, int]] = {}
    for reason, utc in rows:
        period = _date_bucket(utc, bucket)
        by_period.setdefault(period, {})
        by_period[period][reason] = by_period[period].get(reason, 0) + 1

    results = []
    for period in sorted(by_period):
        for reason, count in sorted(by_period[period].items()):
            results.append({
                "period": period,
                "reason": reason,
                "count": count,
            })

    return results


def reason_by_source(conn) -> list[dict]:
    """Per-source breakdown of non-accepted chunk reasons."""
    rows = conn.execute(
        "SELECT c.source_id, s.title, c.status_reason, count(*) as cnt "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "WHERE c.status != 'accepted' AND c.status_reason IS NOT NULL "
        "AND c.status_reason != '' "
        "GROUP BY c.source_id, c.status_reason "
        "ORDER BY cnt DESC"
    ).fetchall()

    if not rows:
        return []

    return [
        {
            "source_id": r[0],
            "title": r[1],
            "reason": r[2],
            "count": r[3],
        }
        for r in rows
    ]


def reason_by_kind(conn) -> list[dict]:
    """Status reason frequency per chunk kind."""
    rows = conn.execute(
        "SELECT kind, status_reason, count(*) as cnt "
        "FROM chunks "
        "WHERE status != 'accepted' AND status_reason IS NOT NULL "
        "AND status_reason != '' "
        "GROUP BY kind, status_reason "
        "ORDER BY cnt DESC"
    ).fetchall()

    if not rows:
        return []

    return [
        {
            "kind": r[0],
            "reason": r[1],
            "count": r[2],
        }
        for r in rows
    ]


def reason_summary(conn) -> dict:
    """Aggregate status reason statistics."""
    total_row = conn.execute(
        "SELECT count(*) FROM chunks"
    ).fetchone()
    total = total_row[0] or 0

    non_accepted_row = conn.execute(
        "SELECT count(*) FROM chunks WHERE status != 'accepted'"
    ).fetchone()
    non_accepted = non_accepted_row[0] or 0

    reason_rows = conn.execute(
        "SELECT status_reason, count(*) as cnt FROM chunks "
        "WHERE status != 'accepted' AND status_reason IS NOT NULL "
        "AND status_reason != '' "
        "GROUP BY status_reason ORDER BY cnt DESC"
    ).fetchall()

    reasons = {r[0]: r[1] for r in reason_rows}

    status_rows = conn.execute(
        "SELECT status, count(*) FROM chunks "
        "WHERE status != 'accepted' "
        "GROUP BY status"
    ).fetchall()

    statuses = {r[0]: r[1] for r in status_rows}

    source_row = conn.execute(
        "SELECT count(DISTINCT source_id) FROM chunks "
        "WHERE status != 'accepted'"
    ).fetchone()

    return {
        "total_chunks": total,
        "non_accepted": non_accepted,
        "non_accepted_rate": round(non_accepted / total, 4) if total > 0 else 0.0,
        "unique_reasons": len(reasons),
        "top_reason": reason_rows[0][0] if reason_rows else None,
        "top_reason_count": reason_rows[0][1] if reason_rows else 0,
        "by_status": statuses,
        "affected_sources": source_row[0] if source_row else 0,
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

        for sid, uri in [("s1", "https://a.com"), ("s2", "https://b.com")]:
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

        chunks_data = [
            ("c0", "s1", "claim", "accepted", None, "2026-07-15T10:00:00Z"),
            ("c1", "s1", "claim", "quarantined", "uncited", "2026-07-15T10:00:00Z"),
            ("c2", "s1", "prose", "quarantined", "uncited", "2026-08-01T10:00:00Z"),
            ("c3", "s2", "claim", "rejected", "duplicate", "2026-08-01T10:00:00Z"),
            ("c4", "s2", "code", "quarantined", "low_quality", "2026-08-15T10:00:00Z"),
            ("c5", "s1", "claim", "rejected", "duplicate", "2026-08-15T10:00:00Z"),
            ("c6", "s2", "prose", "accepted", None, "2026-08-15T10:00:00Z"),
        ]
        for i, (cid, sid, kind, status, reason, utc) in enumerate(chunks_data):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, "
                "status_reason, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
                (cid, sid, i, f"Heading {i}", kind, "en",
                 f"text {i}", f"text {i}", 50, f"n_{cid}",
                 status, reason, utc),
            )

        conn.commit()

        # 1: by-time returns entries
        by_time = reason_by_time(conn, "month")
        assert len(by_time) > 0
        checks += 1

        # 2: entries span multiple months
        periods = {r["period"] for r in by_time}
        assert len(periods) >= 2
        checks += 1

        # 3: uncited appears in July
        july_uncited = [r for r in by_time
                        if r["period"] == "2026-07" and r["reason"] == "uncited"]
        assert len(july_uncited) == 1
        assert july_uncited[0]["count"] == 1
        checks += 1

        # 4: by-source returns entries
        by_src = reason_by_source(conn)
        assert len(by_src) > 0
        checks += 1

        # 5: both sources appear
        sources = {r["source_id"] for r in by_src}
        assert sources == {"s1", "s2"}
        checks += 1

        # 6: s1 has uncited and duplicate reasons
        s1_reasons = {r["reason"] for r in by_src if r["source_id"] == "s1"}
        assert "uncited" in s1_reasons
        assert "duplicate" in s1_reasons
        checks += 1

        # 7: by-kind returns entries
        by_kind = reason_by_kind(conn)
        assert len(by_kind) > 0
        checks += 1

        # 8: claim kind has most non-accepted
        claim_total = sum(r["count"] for r in by_kind if r["kind"] == "claim")
        assert claim_total == 3
        checks += 1

        # 9: sorted by count descending
        counts = [r["count"] for r in by_kind]
        assert counts == sorted(counts, reverse=True)
        checks += 1

        # 10: summary has correct totals
        summary = reason_summary(conn)
        assert summary["total_chunks"] == 7
        assert summary["non_accepted"] == 5
        checks += 1

        # 11: non-accepted rate
        expected_rate = round(5 / 7, 4)
        assert summary["non_accepted_rate"] == expected_rate
        checks += 1

        # 12: unique reasons count
        assert summary["unique_reasons"] == 3
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(by_time)
        _ = json.dumps(by_src)
        _ = json.dumps(by_kind)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = reason_by_time(conn2)
        assert empty == []
        empty_summary = reason_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(f"PASS status_reason_trends selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Status reason trends: quarantine and rejection patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_time = sub.add_parser("by-time",
                            help="Reason counts by time period")
    p_time.add_argument("--db", default=DEFAULT_DB)
    p_time.add_argument("--bucket", choices=["month", "week"],
                        default="month")
    p_time.add_argument("--json", action="store_true")

    p_src = sub.add_parser("by-source",
                           help="Reason counts by source")
    p_src.add_argument("--db", default=DEFAULT_DB)
    p_src.add_argument("--json", action="store_true")

    p_kind = sub.add_parser("by-kind",
                            help="Reason counts by chunk kind")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Reason statistics")
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

    if args.cmd == "by-time":
        results = reason_by_time(conn, args.bucket)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No non-accepted chunks with reasons found.")
            else:
                cur_period = None
                for r in results:
                    if r["period"] != cur_period:
                        cur_period = r["period"]
                        print(f"\n  {cur_period}:")
                    print(f"    {r['reason']:20s}  {r['count']:4d}")

    elif args.cmd == "by-source":
        results = reason_by_source(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No non-accepted chunks with reasons found.")
            else:
                for r in results:
                    print(f"  {r['count']:4d}  {r['reason']:20s}  "
                          f"{r['source_id'][:12]:12s}  {r['title'][:30]}")

    elif args.cmd == "by-kind":
        results = reason_by_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No non-accepted chunks with reasons found.")
            else:
                for r in results:
                    print(f"  {r['count']:4d}  {r['kind']:8s}  {r['reason']}")

    elif args.cmd == "summary":
        result = reason_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Chunks: {result['total_chunks']} total, "
                  f"{result['non_accepted']} non-accepted "
                  f"({result['non_accepted_rate']:.1%})")
            print(f"  Unique reasons: {result['unique_reasons']}  "
                  f"Top: {result['top_reason']} "
                  f"({result['top_reason_count']})")
            if result["by_status"]:
                parts = [f"{s}: {c}" for s, c in
                         sorted(result["by_status"].items())]
                print(f"  By status: {', '.join(parts)}")
            print(f"  Affected sources: {result['affected_sources']}")

    conn.close()


if __name__ == "__main__":
    main()
