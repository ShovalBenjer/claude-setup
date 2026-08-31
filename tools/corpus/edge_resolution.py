#!/usr/bin/env python3
"""Edge resolution analysis: patterns in how claim edges get resolved.

Tracks resolution rates by edge type, identifies long-pending edges,
and reports resolution velocity over time.

Usage:
    python tools/corpus/edge_resolution.py summary [--db PATH] [--json]
    python tools/corpus/edge_resolution.py pending [--db PATH] [--top N] [--json]
    python tools/corpus/edge_resolution.py velocity [--db PATH] [--bucket month|week] [--json]
    python tools/corpus/edge_resolution.py selftest
"""
from __future__ import annotations

import argparse
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


def resolution_summary(conn) -> dict:
    """Resolution rates and counts broken down by edge type."""
    if not _table_exists(conn, "claim_edges"):
        return {"total": 0, "resolved": 0, "unresolved": 0,
                "resolution_rate": 0.0, "by_type": {}}

    total = conn.execute(
        "SELECT count(*) FROM claim_edges"
    ).fetchone()[0]

    resolved = conn.execute(
        "SELECT count(*) FROM claim_edges WHERE resolution IS NOT NULL"
    ).fetchone()[0]

    unresolved = total - resolved

    rows = conn.execute(
        "SELECT edge_type, "
        "count(*) AS total, "
        "sum(CASE WHEN resolution IS NOT NULL THEN 1 ELSE 0 END) AS resolved "
        "FROM claim_edges GROUP BY edge_type ORDER BY total DESC"
    ).fetchall()

    by_type = {}
    for r in rows:
        t = r[1]
        res = r[2]
        by_type[r[0]] = {
            "total": t,
            "resolved": res,
            "unresolved": t - res,
            "resolution_rate": round(res / t, 4) if t else 0.0,
        }

    resolution_counts: dict[str, int] = {}
    res_rows = conn.execute(
        "SELECT resolution, count(*) FROM claim_edges "
        "WHERE resolution IS NOT NULL GROUP BY resolution "
        "ORDER BY count(*) DESC"
    ).fetchall()
    for r in res_rows:
        resolution_counts[r[0]] = r[1]

    return {
        "total": total,
        "resolved": resolved,
        "unresolved": unresolved,
        "resolution_rate": round(resolved / total, 4) if total else 0.0,
        "by_type": by_type,
        "resolution_values": resolution_counts,
    }


def pending_edges(conn, top_n: int = 20) -> list[dict]:
    """Longest-pending unresolved edges, ordered by detection date."""
    if not _table_exists(conn, "claim_edges"):
        return []

    rows = conn.execute(
        "SELECT edge_id, source_chunk, target_chunk, edge_type, "
        "confidence, detected_utc "
        "FROM claim_edges "
        "WHERE resolution IS NULL "
        "ORDER BY detected_utc ASC "
        "LIMIT ?",
        (top_n,),
    ).fetchall()

    return [
        {"edge_id": r[0], "source_chunk": r[1], "target_chunk": r[2],
         "edge_type": r[3], "confidence": round(r[4], 4),
         "detected_utc": r[5]}
        for r in rows
    ]


def resolution_velocity(conn, bucket: str = "month") -> list[dict]:
    """Resolution count per time bucket based on resolved_utc."""
    if not _table_exists(conn, "claim_edges"):
        return []

    if bucket == "week":
        fmt = "%Y-W%W"
    else:
        fmt = "%Y-%m"

    rows = conn.execute(
        "SELECT strftime(?, resolved_utc) AS period, count(*) "
        "FROM claim_edges "
        "WHERE resolution IS NOT NULL AND resolved_utc IS NOT NULL "
        "GROUP BY period ORDER BY period",
        (fmt,),
    ).fetchall()

    return [{"period": r[0], "resolved_count": r[1]} for r in rows]


# ── selftest ─────────────────────────────────────────────────────────


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

        earlier = "2026-07-15T10:00:00Z"
        mid = "2026-08-01T10:00:00Z"

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

        for i in range(1, 6):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (f"c{i}", "s1", i - 1, f"H{i}", "claim", "en",
                 f"text{i}", f"text{i}", 10, f"n{i}", now),
            )

        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e1", "c1", "c2", "contradicts", "semantic", 0.9, earlier),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc, "
            "resolution, resolved_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("e2", "c2", "c3", "supports", "semantic", 0.8, earlier,
             "accepted", mid),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc, "
            "resolution, resolved_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("e3", "c3", "c4", "contradicts", "semantic", 0.7, mid,
             "rejected", now),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e4", "c4", "c5", "duplicates", "exact", 0.95, now),
        )
        conn.commit()

        # 1: summary totals
        s = resolution_summary(conn)
        assert s["total"] == 4
        assert s["resolved"] == 2
        assert s["unresolved"] == 2
        assert s["resolution_rate"] == 0.5
        checks += 1

        # 2: by-type breakdown
        assert "contradicts" in s["by_type"]
        assert s["by_type"]["contradicts"]["total"] == 2
        assert s["by_type"]["contradicts"]["resolved"] == 1
        checks += 1

        # 3: supports fully resolved
        assert s["by_type"]["supports"]["resolved"] == 1
        assert s["by_type"]["supports"]["resolution_rate"] == 1.0
        checks += 1

        # 4: duplicates unresolved
        assert s["by_type"]["duplicates"]["unresolved"] == 1
        checks += 1

        # 5: resolution values
        assert "accepted" in s["resolution_values"]
        assert "rejected" in s["resolution_values"]
        assert s["resolution_values"]["accepted"] == 1
        checks += 1

        # 6: pending edges ordered by detection date
        pe = pending_edges(conn, top_n=10)
        assert len(pe) == 2
        assert pe[0]["edge_id"] == "e1"
        assert pe[1]["edge_id"] == "e4"
        checks += 1

        # 7: pending edge details
        assert pe[0]["edge_type"] == "contradicts"
        assert pe[0]["detected_utc"] == earlier
        checks += 1

        # 8: top_n limit
        pe2 = pending_edges(conn, top_n=1)
        assert len(pe2) == 1
        checks += 1

        # 9: velocity by month
        vel = resolution_velocity(conn, bucket="month")
        assert len(vel) >= 1
        total_resolved = sum(v["resolved_count"] for v in vel)
        assert total_resolved == 2
        checks += 1

        # 10: velocity periods are sorted
        periods = [v["period"] for v in vel]
        assert periods == sorted(periods)
        checks += 1

        # 11: velocity by week
        vel_w = resolution_velocity(conn, bucket="week")
        assert len(vel_w) >= 1
        checks += 1

        # 12: JSON serialisable
        _ = json.dumps(s)
        _ = json.dumps(pe)
        _ = json.dumps(vel)
        checks += 1

        # 13: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        s2 = resolution_summary(conn2)
        assert s2["total"] == 0
        pe2 = pending_edges(conn2)
        assert pe2 == []
        vel2 = resolution_velocity(conn2)
        assert vel2 == []
        checks += 1

        # 14: all resolved scenario
        conn.execute(
            "UPDATE claim_edges SET resolution = 'accepted', "
            "resolved_utc = ? WHERE resolution IS NULL",
            (now,),
        )
        conn.commit()
        s3 = resolution_summary(conn)
        assert s3["unresolved"] == 0
        assert s3["resolution_rate"] == 1.0
        pe3 = pending_edges(conn)
        assert pe3 == []
        checks += 1

    print(f"PASS edge_resolution selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Edge resolution analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_s = sub.add_parser("summary", help="Resolution rates by edge type")
    p_s.add_argument("--db", default=DEFAULT_DB)
    p_s.add_argument("--json", action="store_true")

    p_p = sub.add_parser("pending", help="Longest-pending unresolved edges")
    p_p.add_argument("--db", default=DEFAULT_DB)
    p_p.add_argument("--top", type=int, default=20)
    p_p.add_argument("--json", action="store_true")

    p_v = sub.add_parser("velocity",
                         help="Resolution count per time bucket")
    p_v.add_argument("--db", default=DEFAULT_DB)
    p_v.add_argument("--bucket", choices=["month", "week"], default="month")
    p_v.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "summary":
        result = resolution_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Edges: {result['total']} total, "
                  f"{result['resolved']} resolved, "
                  f"{result['unresolved']} unresolved "
                  f"({result['resolution_rate']:.1%})")
            for etype, stats in sorted(result["by_type"].items()):
                print(f"  {etype}: {stats['total']} total, "
                      f"{stats['resolved']} resolved "
                      f"({stats['resolution_rate']:.1%})")
            if result.get("resolution_values"):
                vals = ", ".join(
                    f"{k}: {v}"
                    for k, v in sorted(result["resolution_values"].items())
                )
                print(f"  Resolution values: {vals}")

    elif args.cmd == "pending":
        result = pending_edges(conn, top_n=args.top)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Longest-pending edges: {len(result)}")
            for r in result:
                print(f"  {r['edge_id']}: {r['source_chunk']} -> "
                      f"{r['target_chunk']} ({r['edge_type']}, "
                      f"conf {r['confidence']}) since {r['detected_utc']}")

    elif args.cmd == "velocity":
        result = resolution_velocity(conn, bucket=args.bucket)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Resolution velocity ({args.bucket}):")
            for r in result:
                print(f"  {r['period']}: {r['resolved_count']} resolved")

    conn.close()


if __name__ == "__main__":
    main()
