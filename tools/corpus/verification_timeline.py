#!/usr/bin/env python3
"""Verification timeline: citations.verified_utc distribution and lag analysis.

The citations.verified_utc column had no temporal distribution analysis.
Existing tools (citation_age, citation_verification) examine per-citation
age and verification rates but never when verification activity happens
over time or how it correlates with tag or verification status.

Usage:
    python tools/corpus/verification_timeline.py timeline [--db PATH] [--json]
    python tools/corpus/verification_timeline.py by-tag [--db PATH] [--json]
    python tools/corpus/verification_timeline.py lag [--db PATH] [--json]
    python tools/corpus/verification_timeline.py summary [--db PATH] [--json]
    python tools/corpus/verification_timeline.py selftest
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
            return datetime.datetime.strptime(
                s, fmt
            ).replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
    return None


def _month_key(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m")


def verification_timeline(conn) -> list[dict]:
    """Distribution of citation verification times by month."""
    rows = conn.execute(
        "SELECT verified_utc FROM citations "
        "WHERE verified = 1 AND verified_utc IS NOT NULL "
        "AND verified_utc != ''"
    ).fetchall()

    if not rows:
        return []

    by_month: dict[str, int] = {}
    for (vutc,) in rows:
        dt = _parse_utc(vutc)
        if dt:
            mk = _month_key(dt)
            by_month[mk] = by_month.get(mk, 0) + 1

    if not by_month:
        return []

    total = sum(by_month.values())
    results = [
        {
            "month": m,
            "count": c,
            "share": round(c / total, 4),
        }
        for m, c in sorted(by_month.items())
    ]
    return results


def verification_by_tag(conn) -> list[dict]:
    """Verification timeline broken down by citation tag."""
    rows = conn.execute(
        "SELECT tag, verified, verified_utc FROM citations"
    ).fetchall()

    if not rows:
        return []

    by_tag: dict[str, dict] = {}
    for tag, verified, vutc in rows:
        t = tag or "(none)"
        if t not in by_tag:
            by_tag[t] = {
                "total": 0, "verified": 0, "months": set()
            }
        by_tag[t]["total"] += 1
        if verified:
            by_tag[t]["verified"] += 1
            dt = _parse_utc(vutc)
            if dt:
                by_tag[t]["months"].add(_month_key(dt))

    results = []
    for tag in sorted(by_tag):
        info = by_tag[tag]
        results.append({
            "tag": tag,
            "total": info["total"],
            "verified": info["verified"],
            "verification_rate": round(
                info["verified"] / info["total"], 4
            ) if info["total"] > 0 else 0.0,
            "distinct_months": len(info["months"]),
        })

    return results


def verification_lag(conn) -> list[dict]:
    """Lag between chunk ingestion and citation verification."""
    rows = conn.execute(
        "SELECT c.verified_utc, ch.ingested_utc, c.tag "
        "FROM citations c "
        "JOIN chunks ch ON c.chunk_id = ch.chunk_id "
        "WHERE c.verified = 1 AND c.verified_utc IS NOT NULL "
        "AND c.verified_utc != ''"
    ).fetchall()

    if not rows:
        return []

    by_tag: dict[str, list[float]] = {}
    for vutc, iutc, tag in rows:
        v_dt = _parse_utc(vutc)
        i_dt = _parse_utc(iutc)
        if v_dt and i_dt:
            lag_days = (v_dt - i_dt).total_seconds() / 86400
            t = tag or "(none)"
            if t not in by_tag:
                by_tag[t] = []
            by_tag[t].append(lag_days)

    if not by_tag:
        return []

    results = []
    for tag in sorted(by_tag):
        lags = by_tag[tag]
        results.append({
            "tag": tag,
            "count": len(lags),
            "mean_lag_days": round(sum(lags) / len(lags), 2),
            "max_lag_days": round(max(lags), 2),
            "min_lag_days": round(min(lags), 2),
        })

    return results


def verification_summary(conn) -> dict:
    """Aggregate verification timeline statistics."""
    total_row = conn.execute(
        "SELECT count(*), "
        "sum(CASE WHEN verified = 1 THEN 1 ELSE 0 END) "
        "FROM citations"
    ).fetchone()

    if not total_row or total_row[0] == 0:
        return {
            "total_citations": 0,
            "verified_citations": 0,
            "verification_rate": 0.0,
            "distinct_months": 0,
            "verification_range": None,
            "tags_with_verification": 0,
            "total_tags": 0,
        }

    total_cites = total_row[0]
    verified_count = total_row[1]

    tl = verification_timeline(conn)
    bt = verification_by_tag(conn)

    months = [r["month"] for r in tl]
    tags_with = sum(1 for t in bt if t["verified"] > 0)

    return {
        "total_citations": total_cites,
        "verified_citations": verified_count,
        "verification_rate": round(
            verified_count / total_cites, 4
        ) if total_cites > 0 else 0.0,
        "distinct_months": len(months),
        "verification_range": (
            {"earliest": months[0], "latest": months[-1]}
            if months else None
        ),
        "tags_with_verification": tags_with,
        "total_tags": len(bt),
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        # source
        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             "2026-06-01T00:00:00Z", "2026-06-01T00:00:00Z",
             "", "", "live", "sha_s1", 1000, None),
        )

        # chunks ingested at different times
        for i, itime in enumerate([
            "2026-06-01T00:00:00Z",
            "2026-06-15T00:00:00Z",
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
        ]):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"c{i+1}", "s1", i, f"/h/c{i+1}", "claim", "en",
                 f"text c{i+1}", f"text c{i+1}", 10,
                 f"sha_c{i+1}", 0, 2, "accepted", itime),
            )

        # citations: mix of verified/unverified, different tags/months
        citations = [
            ("cit1", "c1", "https://ref1.com", "url", 1,
             "2026-06-15T00:00:00Z"),
            ("cit2", "c1", "https://ref2.com", "doi", 1,
             "2026-06-20T00:00:00Z"),
            ("cit3", "c2", "https://ref3.com", "url", 1,
             "2026-07-10T00:00:00Z"),
            ("cit4", "c2", "https://ref4.com", "doi", 0, None),
            ("cit5", "c3", "https://ref5.com", "url", 1,
             "2026-07-20T00:00:00Z"),
            ("cit6", "c3", "https://ref6.com", None, 0, None),
            ("cit7", "c4", "https://ref7.com", "url", 1,
             "2026-08-05T00:00:00Z"),
            ("cit8", "c4", "https://ref8.com", "doi", 0, None),
        ]
        for cid, chid, uri, tag, v, vutc in citations:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, "
                "target_uri, tag, verified, verified_utc) VALUES "
                "(?, ?, ?, ?, ?, ?)",
                (cid, chid, uri, tag, v, vutc),
            )

        conn.commit()

        # 1: timeline returns entries for 3 months (Jun, Jul, Aug)
        tl = verification_timeline(conn)
        assert len(tl) == 3
        checks += 1

        # 2: June has 2 verified citations
        jun = next(t for t in tl if t["month"] == "2026-06")
        assert jun["count"] == 2
        checks += 1

        # 3: shares sum to 1.0
        share_sum = sum(t["share"] for t in tl)
        assert abs(share_sum - 1.0) < 0.01
        checks += 1

        # 4: August has 1 verified citation
        aug = next(t for t in tl if t["month"] == "2026-08")
        assert aug["count"] == 1
        checks += 1

        # 5: by-tag returns entries
        bt = verification_by_tag(conn)
        assert len(bt) > 0
        checks += 1

        # 6: url tag has 4 total citations, 4 verified
        url_tag = next(t for t in bt if t["tag"] == "url")
        assert url_tag["total"] == 4
        assert url_tag["verified"] == 4
        checks += 1

        # 7: doi tag has 3 total, 1 verified
        doi_tag = next(t for t in bt if t["tag"] == "doi")
        assert doi_tag["total"] == 3
        assert doi_tag["verified"] == 1
        checks += 1

        # 8: (none) tag has 1 total, 0 verified
        none_tag = next(t for t in bt if t["tag"] == "(none)")
        assert none_tag["total"] == 1
        assert none_tag["verified"] == 0
        checks += 1

        # 9: verification lag returns entries
        vl = verification_lag(conn)
        assert len(vl) > 0
        checks += 1

        # 10: url lag: cit1 ingested Jun 1, verified Jun 15 = 14d;
        #     cit3 ingested Jun 15, verified Jul 10 = 25d;
        #     cit5 ingested Jul 1, verified Jul 20 = 19d;
        #     cit7 ingested Jul 15, verified Aug 5 = 21d
        url_lag = next(l for l in vl if l["tag"] == "url")
        assert url_lag["count"] == 4
        assert abs(url_lag["min_lag_days"] - 14.0) < 0.1
        checks += 1

        # 11: doi lag: cit2 ingested Jun 1, verified Jun 20 = 19d
        doi_lag = next(l for l in vl if l["tag"] == "doi")
        assert doi_lag["count"] == 1
        assert abs(doi_lag["mean_lag_days"] - 19.0) < 0.1
        checks += 1

        # 12: summary has correct totals
        summary = verification_summary(conn)
        assert summary["total_citations"] == 8
        assert summary["verified_citations"] == 5
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(tl)
        _ = json.dumps(bt)
        _ = json.dumps(vl)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = verification_timeline(conn2)
        assert empty == []
        empty_summary = verification_summary(conn2)
        assert empty_summary["total_citations"] == 0
        checks += 1

    print(f"PASS verification_timeline selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verification timeline analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_tl = sub.add_parser("timeline",
                          help="Verification times by month")
    p_tl.add_argument("--db", default=DEFAULT_DB)
    p_tl.add_argument("--json", action="store_true")

    p_bt = sub.add_parser("by-tag",
                          help="Verification per citation tag")
    p_bt.add_argument("--db", default=DEFAULT_DB)
    p_bt.add_argument("--json", action="store_true")

    p_lag = sub.add_parser("lag",
                           help="Ingestion-to-verification lag")
    p_lag.add_argument("--db", default=DEFAULT_DB)
    p_lag.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Verification statistics")
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

    if args.cmd == "timeline":
        results = verification_timeline(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['month']}  count={r['count']}  "
                      f"share={r['share']:.0%}")

    elif args.cmd == "by-tag":
        results = verification_by_tag(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tag']:12s}  n={r['total']:3d}  "
                      f"verified={r['verified']}  "
                      f"rate={r['verification_rate']:.0%}  "
                      f"months={r['distinct_months']}")

    elif args.cmd == "lag":
        results = verification_lag(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tag']:12s}  n={r['count']}  "
                      f"mean={r['mean_lag_days']:.1f}d  "
                      f"max={r['max_lag_days']:.1f}d  "
                      f"min={r['min_lag_days']:.1f}d")

    elif args.cmd == "summary":
        result = verification_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Citations: {result['total_citations']}  "
                  f"Verified: {result['verified_citations']} "
                  f"({result['verification_rate']:.1%})")
            print(f"  Months: {result['distinct_months']}  "
                  f"Tags with verification: "
                  f"{result['tags_with_verification']}/"
                  f"{result['total_tags']}")
            if result["verification_range"]:
                vr = result["verification_range"]
                print(f"  Range: {vr['earliest']} to "
                      f"{vr['latest']}")

    conn.close()


if __name__ == "__main__":
    main()
