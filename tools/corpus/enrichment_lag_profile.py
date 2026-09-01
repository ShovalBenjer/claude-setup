#!/usr/bin/env python3
"""Enrichment lag profile: time between ingestion and enrichment.

source_enrichment_completeness.py measures enrichment presence.
No tool measures how long after ingestion each enrichment event
occurs, or which enrichment types lag furthest behind ingestion.

Usage:
    python tools/corpus/enrichment_lag_profile.py by-type [--db PATH] [--json]
    python tools/corpus/enrichment_lag_profile.py by-source [--db PATH] [--json]
    python tools/corpus/enrichment_lag_profile.py outliers [--db PATH] [--json]
    python tools/corpus/enrichment_lag_profile.py summary [--db PATH] [--json]
    python tools/corpus/enrichment_lag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

_CT_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_tags ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  tag TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  tagged_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, tag))"
)

_CD_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_domains ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  domain TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  classified_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, domain))"
)

_CV_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_versions ("
    "  version_id TEXT PRIMARY KEY,"
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  version_num INTEGER NOT NULL,"
    "  norm_sha256 TEXT NOT NULL,"
    "  word_count INTEGER NOT NULL,"
    "  snapshot_utc TEXT NOT NULL,"
    "  UNIQUE(chunk_id, version_num))"
)


def _ensure_tables(conn):
    conn.execute(_CT_DDL)
    conn.execute(_CD_DDL)
    conn.execute(_CV_DDL)


def lag_by_type(conn) -> list[dict]:
    """Average enrichment lag per enrichment type (in seconds)."""
    _ensure_tables(conn)
    results = []

    # tagging lag
    row = conn.execute(
        """
        SELECT COUNT(*) AS n,
               ROUND(AVG(
                   (julianday(ct.tagged_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS avg_lag_seconds,
               ROUND(MIN(
                   (julianday(ct.tagged_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS min_lag,
               ROUND(MAX(
                   (julianday(ct.tagged_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS max_lag
        FROM chunk_tags ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        """
    ).fetchone()
    if row[0] > 0:
        results.append({
            "enrichment_type": "tagging",
            "event_count": row[0],
            "avg_lag_seconds": row[1],
            "min_lag_seconds": row[2],
            "max_lag_seconds": row[3],
        })

    # classification lag
    row = conn.execute(
        """
        SELECT COUNT(*) AS n,
               ROUND(AVG(
                   (julianday(cd.classified_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS avg_lag_seconds,
               ROUND(MIN(
                   (julianday(cd.classified_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS min_lag,
               ROUND(MAX(
                   (julianday(cd.classified_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS max_lag
        FROM chunk_domains cd
        JOIN chunks c ON c.chunk_id = cd.chunk_id
        """
    ).fetchone()
    if row[0] > 0:
        results.append({
            "enrichment_type": "classification",
            "event_count": row[0],
            "avg_lag_seconds": row[1],
            "min_lag_seconds": row[2],
            "max_lag_seconds": row[3],
        })

    # versioning lag (first version snapshot vs ingestion)
    row = conn.execute(
        """
        SELECT COUNT(*) AS n,
               ROUND(AVG(
                   (julianday(cv.snapshot_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS avg_lag_seconds,
               ROUND(MIN(
                   (julianday(cv.snapshot_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS min_lag,
               ROUND(MAX(
                   (julianday(cv.snapshot_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS max_lag
        FROM chunk_versions cv
        JOIN chunks c ON c.chunk_id = cv.chunk_id
        WHERE cv.version_num = 1
        """
    ).fetchone()
    if row[0] > 0:
        results.append({
            "enrichment_type": "versioning",
            "event_count": row[0],
            "avg_lag_seconds": row[1],
            "min_lag_seconds": row[2],
            "max_lag_seconds": row[3],
        })

    # edge detection lag
    row = conn.execute(
        """
        SELECT COUNT(*) AS n,
               ROUND(AVG(
                   (julianday(e.detected_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS avg_lag_seconds,
               ROUND(MIN(
                   (julianday(e.detected_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS min_lag,
               ROUND(MAX(
                   (julianday(e.detected_utc) - julianday(c.ingested_utc)) * 86400
               ), 2) AS max_lag
        FROM claim_edges e
        JOIN chunks c ON c.chunk_id = e.source_chunk
        """
    ).fetchone()
    if row[0] > 0:
        results.append({
            "enrichment_type": "edge_detection",
            "event_count": row[0],
            "avg_lag_seconds": row[1],
            "min_lag_seconds": row[2],
            "max_lag_seconds": row[3],
        })

    results.sort(key=lambda r: r["avg_lag_seconds"], reverse=True)
    return results


def lag_by_source(conn) -> list[dict]:
    """Average enrichment lag per source (across all enrichment types)."""
    _ensure_tables(conn)
    rows = conn.execute(
        """
        SELECT s.source_id, s.title,
               COUNT(*) AS enrichment_events,
               ROUND(AVG(lag_seconds), 2) AS avg_lag_seconds,
               ROUND(MAX(lag_seconds), 2) AS max_lag_seconds
        FROM (
            SELECT c.source_id,
                   (julianday(ct.tagged_utc) - julianday(c.ingested_utc)) * 86400 AS lag_seconds
            FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            UNION ALL
            SELECT c.source_id,
                   (julianday(cd.classified_utc) - julianday(c.ingested_utc)) * 86400 AS lag_seconds
            FROM chunk_domains cd
            JOIN chunks c ON c.chunk_id = cd.chunk_id
            UNION ALL
            SELECT c.source_id,
                   (julianday(cv.snapshot_utc) - julianday(c.ingested_utc)) * 86400 AS lag_seconds
            FROM chunk_versions cv
            JOIN chunks c ON c.chunk_id = cv.chunk_id
            WHERE cv.version_num = 1
        ) lags
        JOIN sources s ON s.source_id = lags.source_id
        GROUP BY s.source_id
        ORDER BY avg_lag_seconds DESC, s.source_id
        """
    ).fetchall()
    return [
        {
            "source_id": r[0],
            "title": r[1],
            "enrichment_events": r[2],
            "avg_lag_seconds": r[3],
            "max_lag_seconds": r[4],
        }
        for r in rows
    ]


def lag_outliers(conn, threshold_seconds: float = 86400) -> list[dict]:
    """Enrichment events with lag exceeding threshold (default 24h)."""
    _ensure_tables(conn)
    rows = conn.execute(
        """
        SELECT chunk_id, enrichment_type, lag_seconds, event_utc, ingested_utc
        FROM (
            SELECT ct.chunk_id, 'tagging' AS enrichment_type,
                   (julianday(ct.tagged_utc) - julianday(c.ingested_utc)) * 86400 AS lag_seconds,
                   ct.tagged_utc AS event_utc, c.ingested_utc
            FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            UNION ALL
            SELECT cd.chunk_id, 'classification',
                   (julianday(cd.classified_utc) - julianday(c.ingested_utc)) * 86400,
                   cd.classified_utc, c.ingested_utc
            FROM chunk_domains cd
            JOIN chunks c ON c.chunk_id = cd.chunk_id
            UNION ALL
            SELECT cv.chunk_id, 'versioning',
                   (julianday(cv.snapshot_utc) - julianday(c.ingested_utc)) * 86400,
                   cv.snapshot_utc, c.ingested_utc
            FROM chunk_versions cv
            JOIN chunks c ON c.chunk_id = cv.chunk_id
            WHERE cv.version_num = 1
        )
        WHERE lag_seconds > ?
        ORDER BY lag_seconds DESC
        """,
        (threshold_seconds,),
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "enrichment_type": r[1],
            "lag_seconds": round(r[2], 2),
            "event_utc": r[3],
            "ingested_utc": r[4],
        }
        for r in rows
    ]


def lag_summary(conn) -> dict:
    """Aggregate enrichment lag statistics."""
    _ensure_tables(conn)
    by_type = lag_by_type(conn)
    by_source = lag_by_source(conn)

    total_events = sum(r["event_count"] for r in by_type)
    if by_type:
        overall_avg = round(
            sum(r["avg_lag_seconds"] * r["event_count"] for r in by_type) / max(total_events, 1),
            2,
        )
        slowest_type = by_type[0]["enrichment_type"]
    else:
        overall_avg = 0.0
        slowest_type = None

    slowest_source = by_source[0]["source_id"] if by_source else None
    outlier_count = len(lag_outliers(conn))

    return {
        "enrichment_types_measured": len(by_type),
        "total_enrichment_events": total_events,
        "overall_avg_lag_seconds": overall_avg,
        "slowest_enrichment_type": slowest_type,
        "slowest_source": slowest_source,
        "outliers_over_24h": outlier_count,
        "sources_with_enrichment": len(by_source),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        _ensure_tables(conn)

        t_ingest = "2026-01-01T00:00:00Z"
        t_tag_fast = "2026-01-01T01:00:00Z"      # 1h = 3600s lag
        t_tag_slow = "2026-01-03T00:00:00Z"       # 2d = 172800s lag
        t_classify = "2026-01-01T06:00:00Z"       # 6h = 21600s lag
        t_version = "2026-01-01T00:30:00Z"        # 30min = 1800s lag
        t_edge = "2026-01-02T00:00:00Z"           # 1d = 86400s lag

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t_ingest, None, None, "live", "abc", 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t_ingest, None, None, "live", "def", 200, None),
        )
        for i, (cid, sid) in enumerate([("c1", "s1"), ("c2", "s1"), ("c3", "s2")], 1):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t_ingest),
            )

        # fast tag on c1 (1h), slow tag on c2 (2d)
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t_tag_fast))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "ml", 0.8, t_tag_slow))

        # classification on c1 (6h)
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.7, t_classify))

        # version on c3 (30min)
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v1", "c3", 1, "sha1", 10, t_version))

        # edge from c1 (1d)
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t_edge, None, None),
        )
        conn.commit()

        # 1. lag_by_type returns 4 types
        bt = lag_by_type(conn)
        assert len(bt) == 4, f"types {len(bt)}"
        ok += 1

        # 2. tagging avg lag: (3600 + 172800) / 2 = 88200
        tag_row = [r for r in bt if r["enrichment_type"] == "tagging"][0]
        assert tag_row["avg_lag_seconds"] == 88200.0
        ok += 1

        # 3. tagging event_count is 2
        assert tag_row["event_count"] == 2
        ok += 1

        # 4. versioning lag is 1800
        ver_row = [r for r in bt if r["enrichment_type"] == "versioning"][0]
        assert ver_row["avg_lag_seconds"] == 1800.0
        ok += 1

        # 5. classification lag is 21600
        cls_row = [r for r in bt if r["enrichment_type"] == "classification"][0]
        assert cls_row["avg_lag_seconds"] == 21600.0
        ok += 1

        # 6. edge_detection lag is 86400
        edge_row = [r for r in bt if r["enrichment_type"] == "edge_detection"][0]
        assert edge_row["avg_lag_seconds"] == 86400.0
        ok += 1

        # 7. lag_by_source: s1 has enrichment events
        bs = lag_by_source(conn)
        s1_row = [r for r in bs if r["source_id"] == "s1"][0]
        assert s1_row["enrichment_events"] == 3  # 2 tags + 1 classification
        ok += 1

        # 8. s2 has 1 event (version)
        s2_row = [r for r in bs if r["source_id"] == "s2"][0]
        assert s2_row["enrichment_events"] == 1
        ok += 1

        # 9. outliers over 24h (86400s): c2 tagging (172800s)
        outliers = lag_outliers(conn)
        assert len(outliers) == 1
        assert outliers[0]["chunk_id"] == "c2"
        ok += 1

        # 10. outliers with lower threshold: 1h (3600s) catches c2 tag + c1 classify
        outliers_low = lag_outliers(conn, threshold_seconds=3600)
        assert len(outliers_low) == 2
        ok += 1

        # 11. summary: 4 types measured
        s = lag_summary(conn)
        assert s["enrichment_types_measured"] == 4
        ok += 1

        # 12. summary: total events is 6 (2 tags + 1 classify + 1 version + 1 edge + 1 edge counted via source_chunk)
        assert s["total_enrichment_events"] == 5  # 2 tags + 1 classify + 1 version + 1 edge
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["overall_avg_lag_seconds"] == s["overall_avg_lag_seconds"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = lag_summary(conn)
        assert s["enrichment_types_measured"] == 0
        assert s["total_enrichment_events"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Enrichment lag profile analysis")
    ap.add_argument("command", choices=["by-type", "by-source", "outliers", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS enrichment_lag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-type":
        rows = lag_by_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No enrichment events found.")
            else:
                print(f"{'type':<18} {'events':<8} {'avg_lag_s':<12} {'min_lag_s':<12} {'max_lag_s'}")
                for r in rows:
                    print(f"{r['enrichment_type']:<18} {r['event_count']:<8} {r['avg_lag_seconds']:<12.2f} {r['min_lag_seconds']:<12.2f} {r['max_lag_seconds']:.2f}")
    elif args.command == "by-source":
        rows = lag_by_source(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No enrichment events found.")
            else:
                print(f"{'source_id':<16} {'title':<20} {'events':<8} {'avg_lag_s':<12} {'max_lag_s'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['title']:<20} {r['enrichment_events']:<8} {r['avg_lag_seconds']:<12.2f} {r['max_lag_seconds']:.2f}")
    elif args.command == "outliers":
        rows = lag_outliers(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No outliers over 24h threshold.")
            else:
                print(f"{'chunk_id':<12} {'type':<18} {'lag_seconds':<14} {'event_utc':<24} {'ingested_utc'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['enrichment_type']:<18} {r['lag_seconds']:<14.2f} {r['event_utc']:<24} {r['ingested_utc']}")
    elif args.command == "summary":
        s = lag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
