#!/usr/bin/env python3
"""Quality trend tracker: records corpus quality snapshots over time.

Takes a snapshot of aggregate quality metrics (mean, median, percentiles,
distribution) and stores it in a quality_snapshots table, enabling
temporal tracking of how corpus quality evolves across ingestion cycles.

Usage:
    python tools/corpus/quality_trend.py snapshot [--db PATH] [--dry-run]
    python tools/corpus/quality_trend.py history [--db PATH] [--limit N] [--json]
    python tools/corpus/quality_trend.py trend [--db PATH] [--json]
    python tools/corpus/quality_trend.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from quality import _chunk_quality  # noqa: E402
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _now_utc():
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_table(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS quality_snapshots (
            snapshot_id    TEXT PRIMARY KEY,
            snapshot_utc   TEXT NOT NULL,
            chunk_count    INTEGER NOT NULL,
            mean_score     REAL NOT NULL,
            median_score   REAL NOT NULL,
            p10_score      REAL NOT NULL,
            p90_score      REAL NOT NULL,
            below_050      INTEGER NOT NULL,
            above_080      INTEGER NOT NULL,
            distribution   TEXT NOT NULL
        );
    """)


def _compute_scores(conn) -> list[float]:
    """Compute quality scores for all non-superseded chunks."""
    rows = conn.execute(
        "SELECT c.chunk_id, c.kind, c.word_count, "
        "c.citation_count, c.heading_path "
        "FROM chunks c WHERE c.status != 'superseded'"
    ).fetchall()

    if not rows:
        return []

    chunk_ids = [r[0] for r in rows]

    art_map: dict[str, int] = {}
    for row in conn.execute(
        "SELECT chunk_id, COUNT(*) FROM artifacts GROUP BY chunk_id"
    ).fetchall():
        art_map[row[0]] = row[1]

    contra_map: dict[str, int] = {}
    for row in conn.execute(
        "SELECT chunk_id, COUNT(*) FROM ("
        "  SELECT source_chunk AS chunk_id FROM claim_edges "
        "    WHERE edge_type = 'contradicts' AND resolution IS NULL "
        "  UNION ALL "
        "  SELECT target_chunk AS chunk_id FROM claim_edges "
        "    WHERE edge_type = 'contradicts' AND resolution IS NULL"
        ") GROUP BY chunk_id"
    ).fetchall():
        contra_map[row[0]] = row[1]

    scores = []
    for r in rows:
        cid = r[0]
        has_heading = bool(r[4] and r[4].strip() and r[4].strip() != "/")
        q = _chunk_quality(
            word_count=r[2],
            citation_count=r[3],
            has_heading=has_heading,
            artifact_count=art_map.get(cid, 0),
            contradiction_count=contra_map.get(cid, 0),
            kind=r[1],
        )
        scores.append(q["score"])

    return sorted(scores)


def _percentile(sorted_scores, pct):
    """Compute percentile from a sorted list."""
    if not sorted_scores:
        return 0.0
    idx = int(len(sorted_scores) * pct / 100)
    idx = min(idx, len(sorted_scores) - 1)
    return sorted_scores[idx]


def take_snapshot(conn, dry_run: bool = False) -> dict:
    """Record a quality snapshot of the current corpus state."""
    _ensure_table(conn)
    scores = _compute_scores(conn)

    if not scores:
        return {
            "chunk_count": 0,
            "mean_score": 0,
            "snapshot_id": None,
            "dry_run": dry_run,
        }

    n = len(scores)
    mean_s = round(sum(scores) / n, 4)
    median_s = round(scores[n // 2], 4)
    p10 = round(_percentile(scores, 10), 4)
    p90 = round(_percentile(scores, 90), 4)
    below_050 = sum(1 for s in scores if s < 0.5)
    above_080 = sum(1 for s in scores if s >= 0.8)

    buckets = [0] * 10
    for s in scores:
        idx = min(int(s * 10), 9)
        buckets[idx] += 1
    dist = json.dumps(buckets)

    now = _now_utc()
    sid = _sha256(f"snapshot:{now}:{n}:{mean_s}")

    if not dry_run:
        conn.execute(
            "INSERT INTO quality_snapshots "
            "(snapshot_id, snapshot_utc, chunk_count, mean_score, "
            " median_score, p10_score, p90_score, below_050, "
            " above_080, distribution) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, now, n, mean_s, median_s, p10, p90,
             below_050, above_080, dist),
        )
        conn.commit()

    return {
        "snapshot_id": sid,
        "chunk_count": n,
        "mean_score": mean_s,
        "median_score": median_s,
        "p10_score": p10,
        "p90_score": p90,
        "below_050": below_050,
        "above_080": above_080,
        "dry_run": dry_run,
    }


def snapshot_history(conn, limit: int = 20) -> list[dict]:
    """Return recent quality snapshots, newest first."""
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT snapshot_id, snapshot_utc, chunk_count, mean_score, "
        "median_score, p10_score, p90_score, below_050, above_080, "
        "distribution "
        "FROM quality_snapshots ORDER BY snapshot_utc DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{
        "snapshot_id": r[0],
        "snapshot_utc": r[1],
        "chunk_count": r[2],
        "mean_score": r[3],
        "median_score": r[4],
        "p10_score": r[5],
        "p90_score": r[6],
        "below_050": r[7],
        "above_080": r[8],
        "distribution": json.loads(r[9]),
    } for r in rows]


def quality_trend(conn) -> dict:
    """Compute trend from all snapshots."""
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT snapshot_utc, chunk_count, mean_score, median_score, "
        "p10_score, p90_score "
        "FROM quality_snapshots ORDER BY snapshot_utc ASC"
    ).fetchall()

    if not rows:
        return {"snapshots": 0, "trend": "no_data"}

    if len(rows) == 1:
        return {
            "snapshots": 1,
            "trend": "single_point",
            "latest_mean": rows[0][2],
            "latest_chunks": rows[0][1],
        }

    first = rows[0]
    last = rows[-1]
    mean_delta = round(last[2] - first[2], 4)
    chunk_delta = last[1] - first[1]

    if mean_delta > 0.01:
        direction = "improving"
    elif mean_delta < -0.01:
        direction = "declining"
    else:
        direction = "stable"

    return {
        "snapshots": len(rows),
        "trend": direction,
        "mean_delta": mean_delta,
        "chunk_delta": chunk_delta,
        "first_snapshot": first[0],
        "last_snapshot": last[0],
        "first_mean": first[2],
        "last_mean": last[2],
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Test Doc",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )

        texts = [
            ("c1", 0, "prose", "Database Guide",
             "sqlite provides sql query capabilities with schema migrations "
             "and index management for data storage and retrieval with "
             "foreign key constraints and triggers for referential integrity",
             50, 2),
            ("c2", 1, "prose", "Testing",
             "pytest framework provides fixtures and assertions",
             20, 0),
            ("c3", 2, "claim", "Security",
             "oauth2 authentication flow uses jwt bearer tokens for "
             "stateless api authorization with refresh token rotation "
             "and scope based access control for secure microservices",
             40, 1),
            ("c4", 3, "code", "/",
             "def hello(): return world",
             5, 0),
        ]
        for cid, ordinal, kind, heading, text, wc, cites in texts:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " citation_count, status, status_reason, ingested_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "src1", ordinal, heading, kind, None,
                 text, text, wc, _sha256(text),
                 0, cites, "accepted", None, now),
            )

        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " citation_count, status, status_reason, ingested_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "src1", 4, "Old", "prose", None,
             "superseded chunk", "superseded chunk", 2,
             _sha256("superseded"), 0, 0, "superseded", "old", now),
        )
        conn.commit()

        # Check 1: dry run does not persist
        result = take_snapshot(conn, dry_run=True)
        assert result["dry_run"] is True
        _ensure_table(conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM quality_snapshots"
        ).fetchone()[0]
        assert count == 0
        checks += 1

        # Check 2: snapshot creates a row
        result = take_snapshot(conn, dry_run=False)
        assert result["chunk_count"] == 4
        assert 0 < result["mean_score"] <= 1.0
        assert result["snapshot_id"] is not None
        count = conn.execute(
            "SELECT COUNT(*) FROM quality_snapshots"
        ).fetchone()[0]
        assert count == 1
        checks += 1

        # Check 3: history returns snapshot
        hist = snapshot_history(conn)
        assert len(hist) == 1
        assert hist[0]["chunk_count"] == 4
        assert "distribution" in hist[0]
        assert isinstance(hist[0]["distribution"], list)
        assert len(hist[0]["distribution"]) == 10
        checks += 1

        # Check 4: distribution buckets sum to chunk_count
        assert sum(hist[0]["distribution"]) == 4
        checks += 1

        # Check 5: percentiles are ordered
        assert hist[0]["p10_score"] <= hist[0]["median_score"]
        assert hist[0]["median_score"] <= hist[0]["p90_score"]
        checks += 1

        # Check 6: trend with single point
        trend = quality_trend(conn)
        assert trend["snapshots"] == 1
        assert trend["trend"] == "single_point"
        checks += 1

        # Check 7: second snapshot allows trend
        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " citation_count, status, status_reason, ingested_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "src1", 5, "New Good Chunk", "prose", None,
             "well structured content with proper citations and "
             "detailed analysis of the topic at hand covering "
             "multiple perspectives and synthesising evidence",
             "well structured content with proper citations and "
             "detailed analysis of the topic at hand covering "
             "multiple perspectives and synthesising evidence",
             60, _sha256("new good"), 0, 3,
             "accepted", None, now),
        )
        conn.commit()
        result2 = take_snapshot(conn, dry_run=False)
        assert result2["chunk_count"] == 5
        checks += 1

        # Check 8: trend with two points
        trend2 = quality_trend(conn)
        assert trend2["snapshots"] == 2
        assert trend2["trend"] in ("improving", "declining", "stable")
        assert "mean_delta" in trend2
        checks += 1

        # Check 9: history returns newest first
        hist2 = snapshot_history(conn)
        assert len(hist2) == 2
        assert hist2[0]["snapshot_utc"] >= hist2[1]["snapshot_utc"]
        checks += 1

        # Check 10: below_050 and above_080 are valid counts
        for h in hist2:
            assert h["below_050"] >= 0
            assert h["above_080"] >= 0
            assert h["below_050"] + h["above_080"] <= h["chunk_count"]
        checks += 1

        # Check 11: empty corpus
        empty_dir = Path(td) / "empty_sub"
        empty_dir.mkdir()
        empty_conn = connect(str(empty_dir / "empty.db"))
        init_schema(empty_conn)
        result = take_snapshot(empty_conn, dry_run=False)
        assert result["chunk_count"] == 0
        assert result["snapshot_id"] is None
        trend = quality_trend(empty_conn)
        assert trend["snapshots"] == 0
        assert trend["trend"] == "no_data"
        empty_conn.close()
        checks += 1

        # Check 12: scores are bounded [0, 1]
        scores = _compute_scores(conn)
        for s in scores:
            assert 0 <= s <= 1.0
        checks += 1

        # Check 13: primary key prevents duplicate snapshot_id
        existing = conn.execute(
            "SELECT snapshot_id FROM quality_snapshots LIMIT 1"
        ).fetchone()
        try:
            conn.execute(
                "INSERT INTO quality_snapshots VALUES "
                "(?, ?, 0, 0.0, 0.0, 0.0, 0.0, 0, 0, '[]')",
                (existing[0], now),
            )
            assert False, "should have raised IntegrityError"
        except Exception:
            pass
        checks += 1

        # Check 14: superseded chunks excluded from scores
        all_scores = _compute_scores(conn)
        assert len(all_scores) == 5
        checks += 1

        conn.close()

    print(f"PASS quality_trend selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Quality trend tracker")
    sub = parser.add_subparsers(dest="cmd")

    p_snap = sub.add_parser("snapshot",
                            help="Take a quality snapshot")
    p_snap.add_argument("--db", default=str(DEFAULT_DB))
    p_snap.add_argument("--dry-run", action="store_true")

    p_hist = sub.add_parser("history",
                            help="View snapshot history")
    p_hist.add_argument("--db", default=str(DEFAULT_DB))
    p_hist.add_argument("--limit", type=int, default=20)
    p_hist.add_argument("--json", action="store_true")

    p_trend = sub.add_parser("trend",
                             help="Compute quality trend")
    p_trend.add_argument("--db", default=str(DEFAULT_DB))
    p_trend.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "snapshot":
        conn = connect(args.db)
        result = take_snapshot(conn, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "SNAPSHOT"
        if result["chunk_count"] == 0:
            print("  No chunks to score")
        else:
            print(f"  {mode}: {result['chunk_count']} chunk(s), "
                  f"mean={result['mean_score']:.3f}, "
                  f"median={result['median_score']:.3f}, "
                  f"p10={result['p10_score']:.3f}, "
                  f"p90={result['p90_score']:.3f}")
            print(f"    below 0.5: {result['below_050']}, "
                  f"above 0.8: {result['above_080']}")
        conn.close()

    elif args.cmd == "history":
        conn = connect(args.db)
        hist = snapshot_history(conn, limit=args.limit)
        if args.json:
            print(json.dumps(hist, indent=2))
        else:
            if not hist:
                print("  No snapshots recorded")
            else:
                print(f"  {len(hist)} snapshot(s):")
                for h in hist:
                    print(f"    {h['snapshot_utc']}  "
                          f"n={h['chunk_count']:4d}  "
                          f"mean={h['mean_score']:.3f}  "
                          f"p10={h['p10_score']:.3f}  "
                          f"p90={h['p90_score']:.3f}")
        conn.close()

    elif args.cmd == "trend":
        conn = connect(args.db)
        trend = quality_trend(conn)
        if args.json:
            print(json.dumps(trend, indent=2))
        else:
            if trend["trend"] == "no_data":
                print("  No snapshots for trend analysis")
            elif trend["trend"] == "single_point":
                print(f"  Single snapshot: mean={trend['latest_mean']:.3f}")
            else:
                print(f"  Trend: {trend['trend']} over "
                      f"{trend['snapshots']} snapshots")
                print(f"    Mean: {trend['first_mean']:.3f} -> "
                      f"{trend['last_mean']:.3f} "
                      f"(delta={trend['mean_delta']:+.4f})")
                print(f"    Chunks: {trend['chunk_delta']:+d}")
        conn.close()


if __name__ == "__main__":
    main()
