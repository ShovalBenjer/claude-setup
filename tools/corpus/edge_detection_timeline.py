#!/usr/bin/env python3
"""Edge detection timeline: claim_edges.detected_utc temporal analysis.

Analyses the claim_edges.detected_utc column which had zero analytical
queries anywhere in the codebase, revealing when edges were discovered,
detection patterns by edge type, and resolution lag.

Usage:
    python tools/corpus/edge_detection_timeline.py timeline [--db PATH] [--json]
    python tools/corpus/edge_detection_timeline.py by-type [--db PATH] [--json]
    python tools/corpus/edge_detection_timeline.py resolution-lag [--db PATH] [--json]
    python tools/corpus/edge_detection_timeline.py summary [--db PATH] [--json]
    python tools/corpus/edge_detection_timeline.py selftest
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


def detection_timeline(conn) -> list[dict]:
    """Distribution of edge detection times by month."""
    rows = conn.execute(
        "SELECT detected_utc FROM claim_edges"
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


def detection_by_type(conn) -> list[dict]:
    """Edge detection timeline broken down by edge type."""
    rows = conn.execute(
        "SELECT edge_type, detected_utc FROM claim_edges"
    ).fetchall()

    if not rows:
        return []

    type_months: dict[str, dict[str, int]] = {}
    for edge_type, ts in rows:
        dt = _parse_utc(ts)
        if dt:
            if edge_type not in type_months:
                type_months[edge_type] = {}
            key = _month_key(dt)
            type_months[edge_type][key] = (
                type_months[edge_type].get(key, 0) + 1
            )

    if not type_months:
        return []

    results = []
    for etype, months in sorted(type_months.items()):
        total = sum(months.values())
        results.append({
            "edge_type": etype,
            "total": total,
            "months": dict(sorted(months.items())),
            "distinct_months": len(months),
        })

    return results


def resolution_lag(conn) -> list[dict]:
    """Lag between detection and resolution for resolved edges."""
    rows = conn.execute(
        "SELECT edge_type, detected_utc, resolved_utc "
        "FROM claim_edges "
        "WHERE resolved_utc IS NOT NULL AND resolved_utc != ''"
    ).fetchall()

    if not rows:
        return []

    type_lags: dict[str, list[int]] = {}
    for etype, det_s, res_s in rows:
        det = _parse_utc(det_s)
        res = _parse_utc(res_s)
        if det and res:
            days = (res - det).days
            if etype not in type_lags:
                type_lags[etype] = []
            type_lags[etype].append(days)

    if not type_lags:
        return []

    results = []
    for etype, lags in sorted(type_lags.items()):
        n = len(lags)
        results.append({
            "edge_type": etype,
            "resolved_count": n,
            "mean_days": round(sum(lags) / n, 1) if n > 0 else 0.0,
            "max_days": max(lags),
            "min_days": min(lags),
        })

    return results


def detection_summary(conn) -> dict:
    """Aggregate edge detection statistics."""
    rows = conn.execute(
        "SELECT edge_type, detected_utc, resolved_utc, resolution, "
        "confidence "
        "FROM claim_edges"
    ).fetchall()

    if not rows:
        return {
            "total_edges": 0,
            "distinct_types": 0,
            "detection_range": {"earliest": None, "latest": None},
            "distinct_months": 0,
            "resolved_count": 0,
            "resolved_rate": 0.0,
            "mean_confidence": 0.0,
        }

    n = len(rows)
    det_dates = []
    months: set[str] = set()
    types: set[str] = set()
    resolved = 0
    confidences = []

    for etype, det_s, res_s, resolution, conf in rows:
        types.add(etype)
        dt = _parse_utc(det_s)
        if dt:
            det_dates.append(dt)
            months.add(_month_key(dt))
        if res_s:
            resolved += 1
        if conf is not None:
            confidences.append(conf)

    def _fmt(dt: datetime.datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "total_edges": n,
        "distinct_types": len(types),
        "detection_range": {
            "earliest": _fmt(min(det_dates)) if det_dates else None,
            "latest": _fmt(max(det_dates)) if det_dates else None,
        },
        "distinct_months": len(months),
        "resolved_count": resolved,
        "resolved_rate": round(resolved / n, 4) if n > 0 else 0.0,
        "mean_confidence": (
            round(sum(confidences) / len(confidences), 3)
            if confidences else 0.0
        ),
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source s1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(4):
            cid = f"c{i+1}"
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, "s1", i, f"/h/{cid}", "claim", "en",
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        d1 = "2026-06-15T10:00:00Z"
        d2 = "2026-06-20T12:00:00Z"
        d3 = "2026-07-01T08:00:00Z"
        d4 = "2026-07-15T14:00:00Z"
        d5 = "2026-08-01T09:00:00Z"

        r1 = "2026-06-18T10:00:00Z"
        r2 = "2026-07-10T12:00:00Z"

        edges = [
            ("e1", "c1", "c2", "supports", "shared premise", 0.9,
             d1, "accepted", r1),
            ("e2", "c1", "c3", "contradicts", "opposing claims", 0.7,
             d2, None, None),
            ("e3", "c2", "c3", "supports", "evidence chain", 0.85,
             d3, "accepted", r2),
            ("e4", "c3", "c4", "contradicts", "methodology conflict", 0.6,
             d4, None, None),
            ("e5", "c1", "c4", "refines", "scope limitation", 0.75,
             d5, None, None),
        ]
        for eid, src, tgt, etype, basis, conf, det, res, res_utc in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc, resolution, resolved_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (eid, src, tgt, etype, basis, conf, det, res, res_utc),
            )

        conn.commit()

        # 1: timeline returns entries
        tl = detection_timeline(conn)
        assert len(tl) > 0
        checks += 1

        # 2: three distinct months (June, July, August)
        months = {t["month"] for t in tl}
        assert "2026-06" in months
        assert "2026-07" in months
        assert "2026-08" in months
        checks += 1

        # 3: shares sum to approximately 1.0
        total_share = sum(t["share"] for t in tl)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 4: June has 2 edges (e1, e2)
        june = next(t for t in tl if t["month"] == "2026-06")
        assert june["count"] == 2
        checks += 1

        # 5: by-type returns entries
        bt = detection_by_type(conn)
        assert len(bt) > 0
        checks += 1

        # 6: supports has 2 edges across 2 months
        supports = next(
            (b for b in bt if b["edge_type"] == "supports"), None
        )
        assert supports is not None
        assert supports["total"] == 2
        assert supports["distinct_months"] == 2
        checks += 1

        # 7: contradicts has 2 edges
        contrad = next(
            (b for b in bt if b["edge_type"] == "contradicts"), None
        )
        assert contrad is not None
        assert contrad["total"] == 2
        checks += 1

        # 8: resolution lag returns entries
        rl = resolution_lag(conn)
        assert len(rl) > 0
        checks += 1

        # 9: supports has 2 resolved edges
        sup_lag = next(
            (r for r in rl if r["edge_type"] == "supports"), None
        )
        assert sup_lag is not None
        assert sup_lag["resolved_count"] == 2
        checks += 1

        # 10: e1 lag is 3 days (June 15 to June 18)
        assert sup_lag["min_days"] == 3
        checks += 1

        # 11: summary has correct totals
        summary = detection_summary(conn)
        assert summary["total_edges"] == 5
        assert summary["distinct_types"] == 3
        checks += 1

        # 12: resolved count and confidence
        assert summary["resolved_count"] == 2
        assert summary["mean_confidence"] > 0
        assert summary["distinct_months"] == 3
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(tl)
        _ = json.dumps(bt)
        _ = json.dumps(rl)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = detection_timeline(conn2)
        assert empty == []
        empty_summary = detection_summary(conn2)
        assert empty_summary["total_edges"] == 0
        checks += 1

    print(f"PASS edge_detection_timeline selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Edge detection timeline analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_tl = sub.add_parser("timeline",
                          help="Detection time distribution")
    p_tl.add_argument("--db", default=DEFAULT_DB)
    p_tl.add_argument("--json", action="store_true")

    p_type = sub.add_parser("by-type",
                            help="Detection timeline by edge type")
    p_type.add_argument("--db", default=DEFAULT_DB)
    p_type.add_argument("--json", action="store_true")

    p_lag = sub.add_parser("resolution-lag",
                           help="Detection to resolution lag")
    p_lag.add_argument("--db", default=DEFAULT_DB)
    p_lag.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Detection statistics")
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
        results = detection_timeline(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['month']}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "by-type":
        results = detection_by_type(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['edge_type']:15s}  n={r['total']:3d}  "
                      f"months={r['distinct_months']}")

    elif args.cmd == "resolution-lag":
        results = resolution_lag(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['edge_type']:15s}  "
                      f"resolved={r['resolved_count']:3d}  "
                      f"mean={r['mean_days']:.0f}d  "
                      f"max={r['max_days']}d  "
                      f"min={r['min_days']}d")

    elif args.cmd == "summary":
        result = detection_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            dr = result["detection_range"]
            print(f"Edges: {result['total_edges']}  "
                  f"Types: {result['distinct_types']}")
            print(f"  Detected: {dr['earliest']} to {dr['latest']}  "
                  f"({result['distinct_months']} months)")
            print(f"  Resolved: {result['resolved_count']} "
                  f"({result['resolved_rate']:.0%})  "
                  f"Mean confidence: {result['mean_confidence']:.2f}")

    conn.close()


if __name__ == "__main__":
    main()
