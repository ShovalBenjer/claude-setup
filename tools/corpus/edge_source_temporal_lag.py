#!/usr/bin/env python3
"""Edge source temporal lag: time between source publication and edge creation.

edge_detection_timeline.py profiles edge creation timestamps alone.
temporal_distribution.py profiles source timestamps alone.
No tool joins source publication time with edge creation time to
measure how long after a source is published its chunks start
participating in claim edges, or whether older sources accumulate
edges differently than newer ones.

Usage:
    python tools/corpus/edge_source_temporal_lag.py pub-to-edge [--db PATH] [--json]
    python tools/corpus/edge_source_temporal_lag.py age-curve [--db PATH] [--json]
    python tools/corpus/edge_source_temporal_lag.py resolution-lag [--db PATH] [--json]
    python tools/corpus/edge_source_temporal_lag.py summary [--db PATH] [--json]
    python tools/corpus/edge_source_temporal_lag.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _parse_utc(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _days_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 86400


LAG_BANDS = [
    (0, 1, "0-1d"),
    (1, 7, "1-7d"),
    (7, 30, "7-30d"),
    (30, 90, "30-90d"),
    (90, 365, "90-365d"),
    (365, None, "365d+"),
]


def _lag_band(days: float) -> str:
    for lo, hi, label in LAG_BANDS:
        if hi is None:
            if days >= lo:
                return label
        elif lo <= days < hi:
            return label
    return "unknown"


def pub_to_edge_lag(conn) -> list[dict]:
    """Lag histogram from source publication to edge creation."""
    rows = conn.execute(
        """
        SELECT s.published_utc, e.detected_utc
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        WHERE s.published_utc IS NOT NULL AND e.detected_utc IS NOT NULL
        """
    ).fetchall()
    if not rows:
        return []

    lags: list[float] = []
    for pub_utc, edge_utc in rows:
        pub = _parse_utc(pub_utc)
        edge = _parse_utc(edge_utc)
        if pub and edge:
            lags.append(_days_between(pub, edge))

    if not lags:
        return []

    bands: dict[str, list[float]] = defaultdict(list)
    for lag in lags:
        bands[_lag_band(abs(lag))].append(lag)

    result = []
    for b, vals in bands.items():
        result.append({
            "band": b,
            "edge_count": len(vals),
            "min_lag_days": round(min(vals), 2),
            "max_lag_days": round(max(vals), 2),
            "avg_lag_days": round(sum(vals) / len(vals), 2),
        })

    band_order = [label for _, _, label in LAG_BANDS]
    result.sort(key=lambda r: band_order.index(r["band"]) if r["band"] in band_order else 99)
    return result


def age_curve(conn) -> list[dict]:
    """Edge accumulation grouped by source age at edge creation."""
    rows = conn.execute(
        """
        SELECT c.source_id, s.published_utc, e.detected_utc
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        WHERE s.published_utc IS NOT NULL AND e.detected_utc IS NOT NULL
        """
    ).fetchall()
    if not rows:
        return []

    by_source: dict[str, dict] = defaultdict(lambda: {"pub": None, "edge_ages": []})
    for source_id, pub_utc, edge_utc in rows:
        pub = _parse_utc(pub_utc)
        edge = _parse_utc(edge_utc)
        if pub and edge:
            by_source[source_id]["pub"] = pub
            by_source[source_id]["edge_ages"].append(_days_between(pub, edge))

    result = []
    for sid, d in by_source.items():
        ages = d["edge_ages"]
        if not ages:
            continue
        result.append({
            "source_id": sid,
            "edge_count": len(ages),
            "min_age_days": round(min(ages), 2),
            "max_age_days": round(max(ages), 2),
            "avg_age_days": round(sum(ages) / len(ages), 2),
            "span_days": round(max(ages) - min(ages), 2),
        })

    result.sort(key=lambda r: -r["edge_count"])
    return result


def resolution_lag(conn) -> list[dict]:
    """Time from edge creation to resolution, grouped by source age band."""
    rows = conn.execute(
        """
        SELECT s.published_utc, e.detected_utc, e.resolved_utc
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        WHERE s.published_utc IS NOT NULL
          AND e.detected_utc IS NOT NULL
          AND e.resolved_utc IS NOT NULL
        """
    ).fetchall()
    if not rows:
        return []

    bands: dict[str, list[float]] = defaultdict(list)
    for pub_utc, edge_utc, res_utc in rows:
        pub = _parse_utc(pub_utc)
        edge = _parse_utc(edge_utc)
        res = _parse_utc(res_utc)
        if pub and edge and res:
            source_age = _days_between(pub, edge)
            res_time = _days_between(edge, res)
            bands[_lag_band(abs(source_age))].append(res_time)

    result = []
    for b, vals in bands.items():
        result.append({
            "source_age_band": b,
            "resolved_edges": len(vals),
            "avg_resolution_days": round(sum(vals) / len(vals), 2),
            "min_resolution_days": round(min(vals), 2),
            "max_resolution_days": round(max(vals), 2),
        })

    band_order = [label for _, _, label in LAG_BANDS]
    result.sort(key=lambda r: band_order.index(r["source_age_band"]) if r["source_age_band"] in band_order else 99)
    return result


def temporal_lag_summary(conn) -> dict:
    """Aggregate temporal lag statistics."""
    pub_edge = pub_to_edge_lag(conn)
    ac = age_curve(conn)
    res = resolution_lag(conn)

    if not pub_edge:
        return {
            "total_edges_with_dates": 0,
            "sources_with_dates": 0,
            "lag_bands": 0,
            "resolved_edges": 0,
            "median_lag_days": 0,
            "avg_lag_days": 0,
        }

    all_rows = conn.execute(
        """
        SELECT s.published_utc, e.detected_utc
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        JOIN sources s ON s.source_id = c.source_id
        WHERE s.published_utc IS NOT NULL AND e.detected_utc IS NOT NULL
        """
    ).fetchall()

    lags = []
    for pub_utc, edge_utc in all_rows:
        pub = _parse_utc(pub_utc)
        edge = _parse_utc(edge_utc)
        if pub and edge:
            lags.append(_days_between(pub, edge))

    lags.sort()
    mid = len(lags) // 2
    median = lags[mid] if len(lags) % 2 == 1 else (lags[mid - 1] + lags[mid]) / 2

    total_resolved = sum(r["resolved_edges"] for r in res)

    return {
        "total_edges_with_dates": len(lags),
        "sources_with_dates": len(ac),
        "lag_bands": len(pub_edge),
        "resolved_edges": total_resolved,
        "median_lag_days": round(median, 2),
        "avg_lag_days": round(sum(lags) / len(lags), 2),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        # s1 published 2026-01-01, s2 published 2025-01-01 (1 year earlier)
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z", None, None, "live", "def", 200, None))

        t1 = "2026-01-01T00:00:00Z"
        for i, (cid, sid) in enumerate([("c1", "s1"), ("c2", "s1"), ("c3", "s2"), ("c4", "s2")], 1):
            conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, i, "intro", "claim", None, "t", "t", 20, f"h{i}", 1000+i, 0, "accepted", None, t1))

        # e1: s1 chunk, created 2026-01-10 (9 days after s1 pub) -- 0-1d? No, 1-7d? No, 7-30d
        # e2: s1 chunk, created 2026-02-01 (31 days after s1 pub) -- 30-90d
        # e3: s2 chunk, created 2026-01-01 (365 days after s2 pub) -- 90-365d
        # e4: s2 chunk, created 2026-01-01, resolved 2026-01-15 (365 days age, 14 days resolution)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, "2026-01-10T00:00:00Z", None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "supports", "text", 0.8, "2026-02-01T00:00:00Z", None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c1", "contradicts", "text", 0.6, "2026-01-01T00:00:00Z", None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c4", "c1", "refines", "text", 0.7, "2026-01-01T00:00:00Z", None, "2026-01-15T00:00:00Z"))
        conn.commit()

        # 1. pub-to-edge: e1 lag = 9 days (7-30d band)
        pte = pub_to_edge_lag(conn)
        assert len(pte) > 0
        ok += 1

        # 2. 7-30d band has e1 (9 days lag)
        b730 = [r for r in pte if r["band"] == "7-30d"]
        assert len(b730) == 1
        assert b730[0]["edge_count"] >= 1
        ok += 1

        # 3. e2 lag = 31 days (30-90d band)
        b3090 = [r for r in pte if r["band"] == "30-90d"]
        assert len(b3090) == 1
        ok += 1

        # 4. s2 edges: e3 lag = 365 days, e4 lag = 365 days (90-365d or 365d+)
        b365 = [r for r in pte if r["band"] == "365d+"]
        assert len(b365) == 1
        assert b365[0]["edge_count"] == 2
        ok += 1

        # 5. age-curve: s1 has 2 edges
        ac = age_curve(conn)
        s1_ac = [r for r in ac if r["source_id"] == "s1"][0]
        assert s1_ac["edge_count"] == 2
        ok += 1

        # 6. s2 has 2 edges with avg_age ~365 days
        s2_ac = [r for r in ac if r["source_id"] == "s2"][0]
        assert s2_ac["edge_count"] == 2
        assert s2_ac["avg_age_days"] >= 364
        ok += 1

        # 7. s1 min_age = 9 days (e1)
        assert 8 <= s1_ac["min_age_days"] <= 10
        ok += 1

        # 8. resolution-lag: 1 resolved edge (e4), resolution = 14 days
        rl = resolution_lag(conn)
        assert len(rl) == 1
        assert rl[0]["resolved_edges"] == 1
        ok += 1

        # 9. resolution time ~14 days
        assert 13 <= rl[0]["avg_resolution_days"] <= 15
        ok += 1

        # 10. summary: total_edges_with_dates = 4
        s = temporal_lag_summary(conn)
        assert s["total_edges_with_dates"] == 4
        ok += 1

        # 11. sources_with_dates = 2
        assert s["sources_with_dates"] == 2
        ok += 1

        # 12. resolved_edges = 1
        assert s["resolved_edges"] == 1
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["median_lag_days"] == s["median_lag_days"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = temporal_lag_summary(conn)
        assert s["total_edges_with_dates"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Edge source temporal lag")
    ap.add_argument("command", choices=["pub-to-edge", "age-curve", "resolution-lag", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS edge_source_temporal_lag selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "pub-to-edge":
        rows = pub_to_edge_lag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No temporal lag data found.")
            else:
                print(f"{'band':<12} {'edges':<8} {'min_days':<10} {'max_days':<10} {'avg_days'}")
                for r in rows:
                    print(f"{r['band']:<12} {r['edge_count']:<8} {r['min_lag_days']:<10.2f} {r['max_lag_days']:<10.2f} {r['avg_lag_days']:.2f}")
    elif args.command == "age-curve":
        rows = age_curve(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No age curve data found.")
            else:
                print(f"{'source_id':<16} {'edges':<8} {'min_age':<10} {'max_age':<10} {'avg_age':<10} {'span'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['edge_count']:<8} {r['min_age_days']:<10.2f} {r['max_age_days']:<10.2f} {r['avg_age_days']:<10.2f} {r['span_days']:.2f}")
    elif args.command == "resolution-lag":
        rows = resolution_lag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No resolution lag data found.")
            else:
                print(f"{'age_band':<12} {'resolved':<10} {'avg_res':<10} {'min_res':<10} {'max_res'}")
                for r in rows:
                    print(f"{r['source_age_band']:<12} {r['resolved_edges']:<10} {r['avg_resolution_days']:<10.2f} {r['min_resolution_days']:<10.2f} {r['max_resolution_days']:.2f}")
    elif args.command == "summary":
        s = temporal_lag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
