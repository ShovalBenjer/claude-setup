#!/usr/bin/env python3
"""Freshness scorer: per-chunk knowledge freshness from temporal signals.

Correlates chunk age (ingested_utc), source staleness (liveness), version
recency (chunk_versions.snapshot_utc), and quality trend direction
(quality_snapshots) into a per-chunk freshness score between 0 and 1.

Usage:
    python tools/corpus/freshness_scorer.py score [--db PATH] [--top N] [--json]
    python tools/corpus/freshness_scorer.py stale [--db PATH] [--threshold F] [--json]
    python tools/corpus/freshness_scorer.py summary [--db PATH] [--json]
    python tools/corpus/freshness_scorer.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
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


def _parse_utc(s: str | None) -> float | None:
    """Parse an ISO UTC timestamp to epoch seconds, or None."""
    if not s:
        return None
    import datetime
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def _now_epoch() -> float:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).timestamp()


def _age_decay(age_days: float, half_life: float = 180.0) -> float:
    """Exponential decay based on age in days. Half-life defaults to 180 days."""
    return math.exp(-0.693 * age_days / half_life)


_LIVENESS_SCORES = {
    "live": 1.0,
    "stale": 0.5,
    "archived": 0.25,
    "dead": 0.0,
}


def chunk_freshness(conn, now: float | None = None) -> list[dict]:
    """Compute per-chunk freshness scores from temporal signals.

    Freshness is a weighted combination of four signals:
    - age_score (0.3): exponential decay from ingested_utc
    - liveness_score (0.3): source liveness status
    - version_score (0.2): recency of latest version snapshot
    - trend_score (0.2): corpus quality trend direction
    """
    if now is None:
        now = _now_epoch()

    seconds_per_day = 86400.0

    has_versions = _table_exists(conn, "chunk_versions")
    has_snapshots = _table_exists(conn, "quality_snapshots")

    trend_score = 0.5
    if has_snapshots:
        snaps = conn.execute(
            "SELECT mean_score FROM quality_snapshots "
            "ORDER BY snapshot_utc DESC LIMIT 3"
        ).fetchall()
        if len(snaps) >= 2:
            recent = snaps[0][0]
            older = snaps[-1][0]
            if recent > older:
                trend_score = min(1.0, 0.5 + (recent - older))
            elif recent < older:
                trend_score = max(0.0, 0.5 - (older - recent))

    rows = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.ingested_utc, c.heading_path, "
        "c.kind, s.liveness "
        "FROM chunks c JOIN sources s ON c.source_id = s.source_id "
        "WHERE c.status != 'superseded'"
    ).fetchall()

    version_map: dict[str, float] = {}
    if has_versions:
        v_rows = conn.execute(
            "SELECT chunk_id, max(snapshot_utc) FROM chunk_versions "
            "GROUP BY chunk_id"
        ).fetchall()
        for cid, snap_utc in v_rows:
            ts = _parse_utc(snap_utc)
            if ts is not None:
                version_map[cid] = ts

    results = []
    for chunk_id, source_id, ingested_utc, heading, kind, liveness in rows:
        ing_ts = _parse_utc(ingested_utc)
        age_days = (now - ing_ts) / seconds_per_day if ing_ts else 365.0
        age_score = _age_decay(age_days)

        liveness_score = _LIVENESS_SCORES.get(liveness, 0.5)

        if chunk_id in version_map:
            ver_age_days = (now - version_map[chunk_id]) / seconds_per_day
            version_score = _age_decay(ver_age_days, half_life=90.0)
        else:
            version_score = age_score * 0.5

        freshness = round(
            0.3 * age_score
            + 0.3 * liveness_score
            + 0.2 * version_score
            + 0.2 * trend_score,
            4,
        )

        results.append({
            "chunk_id": chunk_id,
            "source_id": source_id,
            "heading": heading,
            "kind": kind,
            "freshness": freshness,
            "age_days": round(age_days, 1),
            "liveness": liveness,
            "has_versions": chunk_id in version_map,
        })

    results.sort(key=lambda r: r["freshness"], reverse=True)
    return results


def stale_chunks(conn, threshold: float = 0.4) -> list[dict]:
    """Return chunks with freshness below the given threshold."""
    all_scores = chunk_freshness(conn)
    return [c for c in all_scores if c["freshness"] < threshold]


def freshness_summary(conn) -> dict:
    """Aggregate freshness statistics across the corpus."""
    scores = chunk_freshness(conn)
    if not scores:
        return {
            "total_chunks": 0,
            "avg_freshness": 0.0,
            "min_freshness": 0.0,
            "max_freshness": 0.0,
            "stale_count": 0,
            "fresh_count": 0,
            "bands": {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0,
                       "0.6-0.8": 0, "0.8-1.0": 0},
        }

    vals = [s["freshness"] for s in scores]
    bands = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0,
             "0.6-0.8": 0, "0.8-1.0": 0}
    for v in vals:
        if v < 0.2:
            bands["0.0-0.2"] += 1
        elif v < 0.4:
            bands["0.2-0.4"] += 1
        elif v < 0.6:
            bands["0.4-0.6"] += 1
        elif v < 0.8:
            bands["0.6-0.8"] += 1
        else:
            bands["0.8-1.0"] += 1

    return {
        "total_chunks": len(vals),
        "avg_freshness": round(sum(vals) / len(vals), 4),
        "min_freshness": round(min(vals), 4),
        "max_freshness": round(max(vals), 4),
        "stale_count": sum(1 for v in vals if v < 0.4),
        "fresh_count": sum(1 for v in vals if v >= 0.8),
        "bands": bands,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now_dt = datetime.datetime(2026, 8, 31, 12, 0, 0,
                                   tzinfo=datetime.timezone.utc)
        now = now_dt.timestamp()
        now_str = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        recent_dt = datetime.datetime(2026, 8, 30, 12, 0, 0,
                                      tzinfo=datetime.timezone.utc)
        recent_str = recent_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        old_dt = datetime.datetime(2025, 6, 1, 12, 0, 0,
                                   tzinfo=datetime.timezone.utc)
        old_str = old_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Live Source",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now_str, now_str, "", "", "live", "sha_s1", 1000, None),
        )
        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s2", "https://b.com", "paper", "Dead Source",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             old_str, old_str, "", "", "dead", "sha_s2", 500, None),
        )

        conn.execute(
            "INSERT INTO chunks (chunk_id, source_id, ordinal, "
            "heading_path, kind, lang, norm_text, raw_text, "
            "word_count, norm_sha256, simhash, status, ingested_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            ("c1", "s1", 0, "Recent", "claim", "en",
             "text", "text", 10, "n_c1", "accepted", recent_str),
        )
        conn.execute(
            "INSERT INTO chunks (chunk_id, source_id, ordinal, "
            "heading_path, kind, lang, norm_text, raw_text, "
            "word_count, norm_sha256, simhash, status, ingested_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            ("c2", "s2", 0, "Old", "claim", "en",
             "text", "text", 10, "n_c2", "accepted", old_str),
        )
        conn.execute(
            "INSERT INTO chunks (chunk_id, source_id, ordinal, "
            "heading_path, kind, lang, norm_text, raw_text, "
            "word_count, norm_sha256, simhash, status, ingested_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            ("c3", "s1", 1, "Versioned", "claim", "en",
             "text", "text", 10, "n_c3", "accepted", old_str),
        )
        conn.execute(
            "INSERT INTO chunks (chunk_id, source_id, ordinal, "
            "heading_path, kind, lang, norm_text, raw_text, "
            "word_count, norm_sha256, simhash, status, ingested_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            ("c4", "s1", 2, "Superseded", "claim", "en",
             "text", "text", 10, "n_c4", "superseded", now_str),
        )

        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v1", "c3", 1, "sha_old", 10, old_str),
        )
        conn.execute(
            "INSERT INTO chunk_versions (version_id, chunk_id, version_num, "
            "norm_sha256, word_count, snapshot_utc) VALUES (?, ?, ?, ?, ?, ?)",
            ("v2", "c3", 2, "sha_new", 12, recent_str),
        )

        conn.commit()

        # 1: scores are computed for non-superseded chunks
        scores = chunk_freshness(conn, now=now)
        ids = [s["chunk_id"] for s in scores]
        assert "c4" not in ids, "superseded chunk should be excluded"
        assert len(scores) == 3
        checks += 1

        # 2: recent chunk from live source scores higher than old chunk from dead source
        c1_score = [s for s in scores if s["chunk_id"] == "c1"][0]
        c2_score = [s for s in scores if s["chunk_id"] == "c2"][0]
        assert c1_score["freshness"] > c2_score["freshness"]
        checks += 1

        # 3: freshness values are between 0 and 1
        for s in scores:
            assert 0.0 <= s["freshness"] <= 1.0
        checks += 1

        # 4: results are sorted by freshness descending
        vals = [s["freshness"] for s in scores]
        assert vals == sorted(vals, reverse=True)
        checks += 1

        # 5: version-tracked chunk has has_versions flag
        c3_score = [s for s in scores if s["chunk_id"] == "c3"][0]
        assert c3_score["has_versions"] is True
        checks += 1

        # 6: non-version-tracked chunk lacks has_versions flag
        assert c1_score["has_versions"] is False
        checks += 1

        # 7: age_days is reasonable for recent chunk (~1 day)
        assert c1_score["age_days"] < 5.0
        checks += 1

        # 8: age_days is large for old chunk (~456 days)
        assert c2_score["age_days"] > 400.0
        checks += 1

        # 9: liveness is propagated from source
        assert c1_score["liveness"] == "live"
        assert c2_score["liveness"] == "dead"
        checks += 1

        # 10: stale_chunks filters below threshold
        stale = stale_chunks(conn, threshold=0.5)
        stale_ids = [s["chunk_id"] for s in stale]
        assert "c2" in stale_ids
        checks += 1

        # 11: summary has required keys
        summary = freshness_summary(conn)
        assert summary["total_chunks"] == 3
        assert "avg_freshness" in summary
        assert "bands" in summary
        assert len(summary["bands"]) == 5
        checks += 1

        # 12: band counts sum to total
        band_sum = sum(summary["bands"].values())
        assert band_sum == summary["total_chunks"]
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(scores)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = chunk_freshness(conn2)
        assert empty == []
        empty_summary = freshness_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(f"PASS freshness_scorer selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freshness scorer: per-chunk knowledge freshness"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_score = sub.add_parser("score",
                             help="Per-chunk freshness scores")
    p_score.add_argument("--db", default=DEFAULT_DB)
    p_score.add_argument("--top", type=int, default=0,
                         help="Show only top N chunks (0 = all)")
    p_score.add_argument("--json", action="store_true")

    p_stale = sub.add_parser("stale",
                             help="Chunks below freshness threshold")
    p_stale.add_argument("--db", default=DEFAULT_DB)
    p_stale.add_argument("--threshold", type=float, default=0.4)
    p_stale.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Aggregate freshness statistics")
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

    if args.cmd == "score":
        results = chunk_freshness(conn)
        if args.top > 0:
            results = results[:args.top]
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                ver = "V" if r["has_versions"] else " "
                print(f"  {r['freshness']:.2f}  [{ver}] {r['liveness']:8s} "
                      f"{r['age_days']:6.0f}d  {r['chunk_id'][:12]:12s}  "
                      f"{r['heading']}")

    elif args.cmd == "stale":
        results = stale_chunks(conn, threshold=args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No chunks below threshold "
                      f"{args.threshold:.2f}")
            else:
                print(f"{len(results)} stale chunks "
                      f"(below {args.threshold:.2f}):")
                for r in results:
                    print(f"  {r['freshness']:.2f}  {r['liveness']:8s} "
                          f"{r['age_days']:6.0f}d  {r['chunk_id'][:12]:12s}  "
                          f"{r['heading']}")

    elif args.cmd == "summary":
        result = freshness_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Corpus Freshness: {result['avg_freshness']:.1%} avg "
                  f"({result['total_chunks']} chunks)")
            print(f"  Range: {result['min_freshness']:.2f} - "
                  f"{result['max_freshness']:.2f}")
            print(f"  Stale (<0.4): {result['stale_count']}  "
                  f"Fresh (>=0.8): {result['fresh_count']}")
            for band, count in result["bands"].items():
                bar = "#" * int(count / max(result["total_chunks"], 1) * 20)
                print(f"  {band:7s} [{bar:20s}] {count}")

    conn.close()


if __name__ == "__main__":
    main()
