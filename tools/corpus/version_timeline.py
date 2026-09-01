#!/usr/bin/env python3
"""Version timeline: chunk_versions.snapshot_utc distribution and analysis.

The chunk_versions.snapshot_utc column had no temporal distribution
analysis.  No tool examined when version snapshots are taken, how
versioning activity varies over time, or the relationship between
version depth and snapshot timing.

Usage:
    python tools/corpus/version_timeline.py timeline [--db PATH] [--json]
    python tools/corpus/version_timeline.py depth [--db PATH] [--json]
    python tools/corpus/version_timeline.py churn [--db PATH] [--json]
    python tools/corpus/version_timeline.py summary [--db PATH] [--json]
    python tools/corpus/version_timeline.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _parse_month(s: str | None) -> str | None:
    if not s:
        return None
    try:
        return s[:7]
    except (TypeError, IndexError):
        return None


def snapshot_timeline(conn) -> list[dict]:
    """Distribution of version snapshot times by month."""
    rows = conn.execute(
        "SELECT snapshot_utc FROM chunk_versions "
        "WHERE snapshot_utc IS NOT NULL AND snapshot_utc != ''"
    ).fetchall()

    if not rows:
        return []

    by_month: dict[str, int] = {}
    for (sutc,) in rows:
        mk = _parse_month(sutc)
        if mk:
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


def version_depth_distribution(conn) -> list[dict]:
    """Distribution of max version depth per chunk."""
    rows = conn.execute(
        "SELECT chunk_id, max(version_num) AS max_ver "
        "FROM chunk_versions GROUP BY chunk_id"
    ).fetchall()

    if not rows:
        return []

    buckets: dict[str, int] = {}
    for _, max_ver in rows:
        if max_ver <= 1:
            b = "1"
        elif max_ver <= 3:
            b = "2-3"
        elif max_ver <= 5:
            b = "4-5"
        elif max_ver <= 10:
            b = "6-10"
        else:
            b = ">10"
        buckets[b] = buckets.get(b, 0) + 1

    order = ["1", "2-3", "4-5", "6-10", ">10"]
    results = [
        {"bucket": b, "count": buckets.get(b, 0)}
        for b in order if b in buckets
    ]
    return results


def version_churn_by_month(conn) -> list[dict]:
    """Version churn: distinct chunks versioned per month."""
    rows = conn.execute(
        "SELECT snapshot_utc, chunk_id FROM chunk_versions "
        "WHERE snapshot_utc IS NOT NULL AND snapshot_utc != ''"
    ).fetchall()

    if not rows:
        return []

    by_month: dict[str, set[str]] = {}
    for sutc, cid in rows:
        mk = _parse_month(sutc)
        if mk:
            if mk not in by_month:
                by_month[mk] = set()
            by_month[mk].add(cid)

    if not by_month:
        return []

    results = [
        {
            "month": m,
            "versions": len(by_month[m]) + sum(
                1 for _ in [] ),
            "distinct_chunks": len(chunks),
        }
        for m, chunks in sorted(by_month.items())
    ]

    for m in sorted(by_month):
        month_rows = [r for r in rows
                      if _parse_month(r[0]) == m]
        r = next(x for x in results if x["month"] == m)
        r["versions"] = len(month_rows)

    return results


def version_summary(conn) -> dict:
    """Aggregate version timeline statistics."""
    total_row = conn.execute(
        "SELECT count(*) FROM chunk_versions"
    ).fetchone()

    if not total_row or total_row[0] == 0:
        return {
            "total_versions": 0,
            "distinct_chunks": 0,
            "distinct_months": 0,
            "snapshot_range": None,
            "mean_versions_per_chunk": 0.0,
            "max_version_depth": 0,
        }

    total = total_row[0]

    chunk_row = conn.execute(
        "SELECT count(DISTINCT chunk_id) FROM chunk_versions"
    ).fetchone()
    distinct_chunks = chunk_row[0] if chunk_row else 0

    max_row = conn.execute(
        "SELECT max(version_num) FROM chunk_versions"
    ).fetchone()
    max_depth = max_row[0] if max_row and max_row[0] else 0

    tl = snapshot_timeline(conn)
    months = [r["month"] for r in tl]

    return {
        "total_versions": total,
        "distinct_chunks": distinct_chunks,
        "distinct_months": len(months),
        "snapshot_range": (
            {"earliest": months[0], "latest": months[-1]}
            if months else None
        ),
        "mean_versions_per_chunk": round(
            total / distinct_chunks, 2
        ) if distinct_chunks > 0 else 0.0,
        "max_version_depth": max_depth,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

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

        for i in range(3):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"c{i+1}", "s1", i, f"/h/c{i+1}", "claim", "en",
                 f"text c{i+1}", f"text c{i+1}", 10,
                 f"sha_c{i+1}", 0, 0, "accepted",
                 "2026-06-01T00:00:00Z"),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_versions ("
            "version_id TEXT PRIMARY KEY, "
            "chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), "
            "version_num INTEGER NOT NULL, "
            "norm_sha256 TEXT NOT NULL, "
            "word_count INTEGER NOT NULL, "
            "snapshot_utc TEXT NOT NULL, "
            "UNIQUE(chunk_id, version_num))"
        )

        versions = [
            ("v1", "c1", 1, "sha_v1", 10, "2026-06-10T00:00:00Z"),
            ("v2", "c1", 2, "sha_v2", 12, "2026-06-20T00:00:00Z"),
            ("v3", "c1", 3, "sha_v3", 15, "2026-07-05T00:00:00Z"),
            ("v4", "c2", 1, "sha_v4", 10, "2026-06-15T00:00:00Z"),
            ("v5", "c2", 2, "sha_v5", 11, "2026-07-10T00:00:00Z"),
            ("v6", "c3", 1, "sha_v6", 8, "2026-07-20T00:00:00Z"),
            ("v7", "c3", 2, "sha_v7", 9, "2026-08-01T00:00:00Z"),
            ("v8", "c3", 3, "sha_v8", 10, "2026-08-15T00:00:00Z"),
            ("v9", "c3", 4, "sha_v9", 11, "2026-08-20T00:00:00Z"),
        ]
        for vid, cid, vnum, sha, wc, sutc in versions:
            conn.execute(
                "INSERT INTO chunk_versions (version_id, chunk_id, "
                "version_num, norm_sha256, word_count, snapshot_utc) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (vid, cid, vnum, sha, wc, sutc),
            )

        conn.commit()

        # 1: timeline returns 3 months (Jun, Jul, Aug)
        tl = snapshot_timeline(conn)
        assert len(tl) == 3
        checks += 1

        # 2: June has 3 versions (v1, v2, v4)
        jun = next(t for t in tl if t["month"] == "2026-06")
        assert jun["count"] == 3
        checks += 1

        # 3: shares sum to 1.0
        share_sum = sum(t["share"] for t in tl)
        assert abs(share_sum - 1.0) < 0.01
        checks += 1

        # 4: August has 3 versions (v7, v8, v9)
        aug = next(t for t in tl if t["month"] == "2026-08")
        assert aug["count"] == 3
        checks += 1

        # 5: depth distribution returns entries
        dd = version_depth_distribution(conn)
        assert len(dd) > 0
        checks += 1

        # 6: c2 has max version 2, c1 has 3, c3 has 4
        # buckets: 2-3 has 2 chunks (c1, c2), 4-5 has 1 (c3)
        b23 = next((d for d in dd if d["bucket"] == "2-3"), None)
        assert b23 is not None
        assert b23["count"] == 2
        checks += 1

        # 7: bucket 4-5 has 1 chunk (c3 with 4 versions)
        b45 = next((d for d in dd if d["bucket"] == "4-5"), None)
        assert b45 is not None
        assert b45["count"] == 1
        checks += 1

        # 8: churn returns entries
        ch = version_churn_by_month(conn)
        assert len(ch) == 3
        checks += 1

        # 9: June has 2 distinct chunks (c1, c2)
        jun_ch = next(c for c in ch if c["month"] == "2026-06")
        assert jun_ch["distinct_chunks"] == 2
        checks += 1

        # 10: June has 3 versions
        assert jun_ch["versions"] == 3
        checks += 1

        # 11: summary has correct totals
        summary = version_summary(conn)
        assert summary["total_versions"] == 9
        assert summary["distinct_chunks"] == 3
        checks += 1

        # 12: mean versions per chunk is 3.0
        assert abs(summary["mean_versions_per_chunk"] - 3.0) < 0.01
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(tl)
        _ = json.dumps(dd)
        _ = json.dumps(ch)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_versions ("
            "version_id TEXT PRIMARY KEY, "
            "chunk_id TEXT NOT NULL, "
            "version_num INTEGER NOT NULL, "
            "norm_sha256 TEXT NOT NULL, "
            "word_count INTEGER NOT NULL, "
            "snapshot_utc TEXT NOT NULL, "
            "UNIQUE(chunk_id, version_num))"
        )
        empty = snapshot_timeline(conn2)
        assert empty == []
        empty_summary = version_summary(conn2)
        assert empty_summary["total_versions"] == 0
        checks += 1

    print(f"PASS version_timeline selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Version timeline analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_tl = sub.add_parser("timeline",
                          help="Snapshot times by month")
    p_tl.add_argument("--db", default=DEFAULT_DB)
    p_tl.add_argument("--json", action="store_true")

    p_dd = sub.add_parser("depth",
                          help="Version depth distribution")
    p_dd.add_argument("--db", default=DEFAULT_DB)
    p_dd.add_argument("--json", action="store_true")

    p_ch = sub.add_parser("churn",
                          help="Version churn by month")
    p_ch.add_argument("--db", default=DEFAULT_DB)
    p_ch.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Version statistics")
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
        results = snapshot_timeline(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['month']}  count={r['count']}  "
                      f"share={r['share']:.0%}")

    elif args.cmd == "depth":
        results = version_depth_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['bucket']:6s}  count={r['count']}")

    elif args.cmd == "churn":
        results = version_churn_by_month(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['month']}  versions={r['versions']}  "
                      f"chunks={r['distinct_chunks']}")

    elif args.cmd == "summary":
        result = version_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Versions: {result['total_versions']}  "
                  f"Chunks: {result['distinct_chunks']}  "
                  f"Months: {result['distinct_months']}")
            print(f"  Mean/chunk: "
                  f"{result['mean_versions_per_chunk']:.1f}  "
                  f"Max depth: {result['max_version_depth']}")
            if result["snapshot_range"]:
                sr = result["snapshot_range"]
                print(f"  Range: {sr['earliest']} to "
                      f"{sr['latest']}")

    conn.close()


if __name__ == "__main__":
    main()
