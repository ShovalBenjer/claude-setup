#!/usr/bin/env python3
"""Corpus timeline analysis.

Analyses temporal patterns across sources and chunks using
published_utc and ingested_utc timestamps.  Reveals ingestion
velocity, topic evolution over time, and publication age distribution.

Usage:
    python tools/corpus/timeline.py velocity [--db PATH] [--bucket month|week|day] [--json]
    python tools/corpus/timeline.py age [--db PATH] [--json]
    python tools/corpus/timeline.py topic-trend [--db PATH] [--top N] [--json]
    python tools/corpus/timeline.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

# ── helpers ──────────────────────────────────────────────────────────


def _bucket_key(ts: str, bucket: str) -> str:
    if not ts or len(ts) < 10:
        return "unknown"
    if bucket == "day":
        return ts[:10]
    if bucket == "week":
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(ts[:10])
            iso = dt.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        except ValueError:
            return "unknown"
    return ts[:7]


# ── subcommands ──────────────────────────────────────────────────────


def ingestion_velocity(conn, bucket: str = "month") -> list[dict]:
    rows = conn.execute(
        "SELECT ingested_utc FROM chunks "
        "WHERE status != 'superseded'"
    ).fetchall()
    if not rows:
        return []

    by_bucket: dict[str, int] = defaultdict(int)
    for (ts,) in rows:
        key = _bucket_key(ts, bucket)
        by_bucket[key] += 1

    return [{"period": key, "chunks_ingested": by_bucket[key]}
            for key in sorted(by_bucket)]


def age_distribution(conn) -> dict:
    rows = conn.execute(
        "SELECT s.published_utc, s.source_id "
        "FROM sources s "
        "JOIN chunks c ON c.source_id = s.source_id "
        "WHERE c.status != 'superseded' "
        "GROUP BY s.source_id"
    ).fetchall()

    if not rows:
        return {"total_sources": 0, "with_date": 0, "without_date": 0,
                "by_year": [], "oldest": None, "newest": None}

    from datetime import datetime

    years: dict[str, int] = defaultdict(int)
    dated = []
    without_date = 0

    for pub_utc, _ in rows:
        if not pub_utc or len(pub_utc) < 4:
            without_date += 1
            continue
        year = pub_utc[:4]
        years[year] += 1
        try:
            dt = datetime.fromisoformat(pub_utc[:10])
            dated.append((dt, pub_utc))
        except ValueError:
            pass

    by_year = [{"year": y, "count": c} for y, c in sorted(years.items())]
    oldest = min(dated, key=lambda x: x[0])[1] if dated else None
    newest = max(dated, key=lambda x: x[0])[1] if dated else None

    return {
        "total_sources": len(rows),
        "with_date": len(rows) - without_date,
        "without_date": without_date,
        "by_year": by_year,
        "oldest": oldest,
        "newest": newest,
    }


def topic_trend(conn, top_n: int = 10) -> list[dict]:
    has_table = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='chunk_topics'"
    ).fetchone()
    if not has_table:
        return []

    rows = conn.execute(
        "SELECT ct.topic_label, c.ingested_utc "
        "FROM chunk_topics ct "
        "JOIN chunks c ON c.chunk_id = ct.chunk_id "
        "WHERE c.status != 'superseded'"
    ).fetchall()
    if not rows:
        return []

    by_topic: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    topic_totals: dict[str, int] = defaultdict(int)

    for topic, ts in rows:
        month = _bucket_key(ts, "month")
        by_topic[topic][month] += 1
        topic_totals[topic] += 1

    top_topics = sorted(topic_totals.items(), key=lambda x: x[1],
                        reverse=True)[:top_n]

    results = []
    for topic, total in top_topics:
        months = by_topic[topic]
        timeline = [{"period": m, "count": months[m]}
                    for m in sorted(months)]
        results.append({
            "topic": topic,
            "total_chunks": total,
            "timeline": timeline,
        })
    return results


# ── selftest ─────────────────────────────────────────────────────────


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        t1 = "2025-03-15T10:00:00Z"
        t2 = "2025-04-20T12:00:00Z"
        t3 = "2026-01-10T08:00:00Z"

        for sid, uri, pub in [("s1", "https://a.com", "2024-01-15"),
                              ("s2", "https://b.com", "2023-06-01"),
                              ("s3", "https://c.com", "")]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 pub, t1, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunk_rows = [
            ("c1", "s1", 0, "H1", "claim", "en", "alpha", "alpha", 1, "n1", t1),
            ("c2", "s1", 1, "H2", "claim", "en", "beta", "beta", 1, "n2", t1),
            ("c3", "s2", 0, "H3", "claim", "en", "gamma", "gamma", 1, "n3", t2),
            ("c4", "s2", 1, "H4", "claim", "en", "delta", "delta", 1, "n4", t2),
            ("c5", "s3", 0, "H5", "claim", "en", "epsilon", "epsilon", 1, "n5", t3),
        ]
        for cr in chunk_rows:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                cr,
            )

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chunk_topics (
                chunk_id     TEXT NOT NULL,
                topic_label  TEXT NOT NULL,
                topic_weight REAL NOT NULL,
                fitted_utc   TEXT NOT NULL,
                PRIMARY KEY (chunk_id, topic_label)
            );
        """)

        topic_rows = [
            ("c1", "ml", 0.8, t1),
            ("c2", "ml", 0.6, t1),
            ("c3", "nlp", 0.9, t2),
            ("c4", "ml", 0.7, t2),
            ("c5", "security", 0.8, t3),
        ]
        for tr in topic_rows:
            conn.execute(
                "INSERT INTO chunk_topics "
                "(chunk_id, topic_label, topic_weight, fitted_utc) "
                "VALUES (?, ?, ?, ?)", tr,
            )
        conn.commit()

        # 1: velocity returns buckets
        vel = ingestion_velocity(conn, bucket="month")
        assert len(vel) > 0, "should have velocity data"
        checks += 1

        # 2: correct month buckets
        months = {v["period"] for v in vel}
        assert "2025-03" in months, "March 2025 should appear"
        assert "2025-04" in months, "April 2025 should appear"
        checks += 1

        # 3: correct counts per bucket
        mar = [v for v in vel if v["period"] == "2025-03"][0]
        assert mar["chunks_ingested"] == 2, "2 chunks in March"
        checks += 1

        # 4: week bucket works
        vel_w = ingestion_velocity(conn, bucket="week")
        assert len(vel_w) > 0
        assert all("-W" in v["period"] or v["period"] == "unknown"
                   for v in vel_w)
        checks += 1

        # 5: age distribution
        age = age_distribution(conn)
        assert age["total_sources"] == 3
        assert age["with_date"] == 2
        assert age["without_date"] == 1
        checks += 1

        # 6: by_year has entries
        assert len(age["by_year"]) == 2
        years = {y["year"] for y in age["by_year"]}
        assert "2024" in years
        assert "2023" in years
        checks += 1

        # 7: oldest and newest
        assert age["oldest"] is not None
        assert "2023" in age["oldest"]
        assert age["newest"] is not None
        assert "2024" in age["newest"]
        checks += 1

        # 8: topic_trend returns results
        trends = topic_trend(conn, top_n=10)
        assert len(trends) > 0
        checks += 1

        # 9: ml is the top topic
        assert trends[0]["topic"] == "ml"
        assert trends[0]["total_chunks"] == 3
        checks += 1

        # 10: ml has timeline entries
        assert len(trends[0]["timeline"]) >= 2
        checks += 1

        # 11: JSON output for velocity
        for row in vel:
            _ = json.dumps(row)
        checks += 1

        # 12: JSON output for age
        _ = json.dumps(age)
        checks += 1

        # 13: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert ingestion_velocity(conn2) == []
        assert age_distribution(conn2)["total_sources"] == 0
        assert topic_trend(conn2) == []
        checks += 1

        # 14: superseded chunks excluded
        conn.execute(
            "UPDATE chunks SET status = 'superseded' WHERE chunk_id = 'c1'"
        )
        conn.commit()
        vel2 = ingestion_velocity(conn, bucket="month")
        mar2 = [v for v in vel2 if v["period"] == "2025-03"]
        if mar2:
            assert mar2[0]["chunks_ingested"] == 1
        checks += 1

    print(f"PASS timeline selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Corpus timeline analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_vel = sub.add_parser("velocity", help="Ingestion velocity over time")
    p_vel.add_argument("--db", default=DEFAULT_DB)
    p_vel.add_argument("--bucket", choices=["month", "week", "day"],
                       default="month")
    p_vel.add_argument("--json", action="store_true")

    p_age = sub.add_parser("age", help="Source publication age distribution")
    p_age.add_argument("--db", default=DEFAULT_DB)
    p_age.add_argument("--json", action="store_true")

    p_trend = sub.add_parser("topic-trend",
                             help="Topic evolution over ingestion time")
    p_trend.add_argument("--db", default=DEFAULT_DB)
    p_trend.add_argument("--top", type=int, default=10)
    p_trend.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "velocity":
        results = ingestion_velocity(conn, bucket=args.bucket)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No ingestion data found.")
                return
            print(f"{'Period':<15} {'Chunks':>8}")
            print("-" * 25)
            for r in results:
                print(f"{r['period']:<15} {r['chunks_ingested']:>8}")

    elif args.cmd == "age":
        result = age_distribution(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']} "
                  f"({result['with_date']} dated, "
                  f"{result['without_date']} undated)")
            if result["oldest"]:
                print(f"Oldest: {result['oldest']}")
            if result["newest"]:
                print(f"Newest: {result['newest']}")
            if result["by_year"]:
                print(f"\n{'Year':<8} {'Count':>6}")
                print("-" * 16)
                for y in result["by_year"]:
                    print(f"{y['year']:<8} {y['count']:>6}")

    elif args.cmd == "topic-trend":
        results = topic_trend(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No topic trend data found.")
                return
            for t in results:
                print(f"\n{t['topic']} ({t['total_chunks']} chunks):")
                for entry in t["timeline"]:
                    print(f"  {entry['period']}: {entry['count']}")

    conn.close()


if __name__ == "__main__":
    main()
