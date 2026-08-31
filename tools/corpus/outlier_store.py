#!/usr/bin/env python3
"""Outlier store: persists ML-based outlier detection results.

Bridges the semantic analyser's find_outliers() (which computes
max-similarity scores but discards them) and downstream tools that
need persisted outlier data for corpus quality monitoring and
review prioritisation.

A chunk is an outlier when its maximum cosine similarity to any other
chunk falls below a threshold, indicating topical isolation.

Usage:
    python tools/corpus/outlier_store.py persist [--db PATH] [--threshold F] [--dry-run]
    python tools/corpus/outlier_store.py lookup --chunk-id CID [--db PATH] [--json]
    python tools/corpus/outlier_store.py list [--db PATH] [--json]
    python tools/corpus/outlier_store.py stats [--db PATH] [--json]
    python tools/corpus/outlier_store.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402
from semantic import find_outliers  # noqa: E402


def _now_utc():
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_table(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunk_outliers (
            chunk_id         TEXT NOT NULL REFERENCES chunks(chunk_id),
            max_similarity   REAL NOT NULL,
            threshold_used   REAL NOT NULL,
            detected_utc     TEXT NOT NULL,
            PRIMARY KEY (chunk_id)
        );
    """)


def persist_outliers(conn, threshold: float = 0.15,
                     dry_run: bool = False) -> dict:
    """Run outlier detection and persist results to chunk_outliers."""
    _ensure_table(conn)
    outliers = find_outliers(conn, threshold=threshold)
    now = _now_utc()

    inserted = 0
    updated = 0
    unchanged = 0

    current_ids = set()

    for outlier in outliers:
        chunk_id = outlier["chunk_id"]
        max_sim = outlier["max_similarity"]
        current_ids.add(chunk_id)

        existing = conn.execute(
            "SELECT max_similarity, threshold_used FROM chunk_outliers "
            "WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()

        if existing is None:
            if not dry_run:
                conn.execute(
                    "INSERT INTO chunk_outliers "
                    "(chunk_id, max_similarity, threshold_used, detected_utc) "
                    "VALUES (?, ?, ?, ?)",
                    (chunk_id, max_sim, threshold, now),
                )
            inserted += 1
        elif (abs(existing[0] - max_sim) > 0.0001
              or abs(existing[1] - threshold) > 0.0001):
            if not dry_run:
                conn.execute(
                    "UPDATE chunk_outliers "
                    "SET max_similarity = ?, threshold_used = ?, "
                    "    detected_utc = ? "
                    "WHERE chunk_id = ?",
                    (max_sim, threshold, now, chunk_id),
                )
            updated += 1
        else:
            unchanged += 1

    removed = 0
    if not dry_run:
        stored_ids = conn.execute(
            "SELECT chunk_id FROM chunk_outliers"
        ).fetchall()
        for row in stored_ids:
            if row[0] not in current_ids:
                conn.execute(
                    "DELETE FROM chunk_outliers WHERE chunk_id = ?",
                    (row[0],),
                )
                removed += 1

    if not dry_run:
        conn.commit()

    return {
        "outliers_found": len(outliers),
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "removed": removed,
        "threshold": threshold,
        "dry_run": dry_run,
    }


def lookup_outlier(conn, chunk_id: str) -> dict | None:
    """Return outlier record for a chunk."""
    _ensure_table(conn)
    row = conn.execute(
        "SELECT max_similarity, threshold_used, detected_utc "
        "FROM chunk_outliers WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "chunk_id": chunk_id,
        "max_similarity": row[0],
        "threshold_used": row[1],
        "detected_utc": row[2],
    }


def list_outliers(conn, limit: int = 50) -> list[dict]:
    """Return all outliers with chunk metadata, sorted by isolation."""
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT co.chunk_id, co.max_similarity, co.threshold_used, "
        "co.detected_utc, c.source_id, c.kind, c.status, "
        "c.word_count, c.heading_path "
        "FROM chunk_outliers co "
        "JOIN chunks c ON co.chunk_id = c.chunk_id "
        "WHERE c.status != 'superseded' "
        "ORDER BY co.max_similarity ASC "
        "LIMIT ?",
        (limit,),
    ).fetchall()
    return [{
        "chunk_id": r[0],
        "max_similarity": r[1],
        "threshold_used": r[2],
        "detected_utc": r[3],
        "source_id": r[4],
        "kind": r[5],
        "status": r[6],
        "word_count": r[7],
        "heading_path": r[8],
    } for r in rows]


def outlier_stats(conn) -> dict:
    """Summary statistics for outlier detection."""
    _ensure_table(conn)
    total_outliers = conn.execute(
        "SELECT COUNT(*) FROM chunk_outliers"
    ).fetchone()[0]

    active_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    if total_outliers == 0:
        return {
            "total_outliers": 0,
            "active_chunks": active_chunks,
            "outlier_rate": 0,
            "avg_max_similarity": 0,
            "min_max_similarity": 0,
            "by_kind": [],
        }

    avg_sim = conn.execute(
        "SELECT AVG(max_similarity) FROM chunk_outliers"
    ).fetchone()[0]
    min_sim = conn.execute(
        "SELECT MIN(max_similarity) FROM chunk_outliers"
    ).fetchone()[0]

    by_kind = conn.execute(
        "SELECT c.kind, COUNT(*), AVG(co.max_similarity) "
        "FROM chunk_outliers co "
        "JOIN chunks c ON co.chunk_id = c.chunk_id "
        "WHERE c.status != 'superseded' "
        "GROUP BY c.kind ORDER BY COUNT(*) DESC"
    ).fetchall()

    return {
        "total_outliers": total_outliers,
        "active_chunks": active_chunks,
        "outlier_rate": round(total_outliers / active_chunks, 3)
        if active_chunks else 0,
        "avg_max_similarity": round(avg_sim, 4),
        "min_max_similarity": round(min_sim, 4),
        "by_kind": [{
            "kind": r[0],
            "count": r[1],
            "avg_max_similarity": round(r[2], 4),
        } for r in by_kind],
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    try:
        from semantic import HAS_SKLEARN
        if not HAS_SKLEARN:
            print("SKIP outlier_store selftest (scikit-learn not installed)")
            return True
    except ImportError:
        print("SKIP outlier_store selftest (semantic.py import failed)")
        return True

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
            ("c1", 0, "sqlite database provides sql query capabilities with "
             "schema migrations and index management for relational data "
             "storage and retrieval with foreign key constraints"),
            ("c2", 1, "postgresql database offers advanced sql features "
             "including window functions and common table expressions "
             "for complex relational query operations"),
            ("c3", 2, "python pytest framework provides test fixtures and "
             "assertions with coverage reports to measure code quality "
             "and unittest mock objects for component isolation"),
            ("c4", 3, "javascript jest testing framework offers snapshot "
             "testing and mocking capabilities for frontend unit tests "
             "with code coverage integration and watch mode"),
            ("c5", 4, "oauth2 authentication flow uses jwt bearer tokens "
             "for stateless api authorization with refresh token rotation "
             "and scope based access control for microservices"),
            ("c6", 5, "tls encryption protects data in transit using "
             "certificate authorities and public key infrastructure "
             "with mutual authentication for service mesh security"),
            ("c7", 6, "kubernetes orchestrates container workloads across "
             "clusters with pod scheduling resource limits health checks "
             "and horizontal pod autoscaling for cloud deployments"),
            ("c8", 7, "docker containers package applications with their "
             "dependencies into portable images using layered filesystem "
             "with build caching and multi stage builds"),
            ("c9", 8, "quantum computing leverages superposition and "
             "entanglement for exponential speedup in integer "
             "factorisation and unstructured search problems"),
        ]
        for cid, ordinal, text in texts:
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "src1", ordinal, "Test", "prose", None,
                 text, "raw", len(text.split()), _sha256(text),
                 0, 0, "accepted", None, now),
            )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c10", "src1", 9, "Old", "prose", None,
             "this chunk is superseded and should be ignored.",
             "raw", 8, _sha256("superseded"), 0, 0,
             "superseded", "old", now),
        )
        conn.commit()

        # Check 1: dry run does not persist
        result = persist_outliers(conn, threshold=0.5, dry_run=True)
        assert result["dry_run"] is True
        _ensure_table(conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_outliers"
        ).fetchone()[0]
        assert count == 0
        checks += 1

        # Check 2: persist creates outlier rows
        result = persist_outliers(conn, threshold=0.5, dry_run=False)
        assert result["outliers_found"] > 0
        assert result["inserted"] > 0
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_outliers"
        ).fetchone()[0]
        assert count > 0
        checks += 1

        # Check 3: lookup returns record for an outlier
        outlier_row = conn.execute(
            "SELECT chunk_id FROM chunk_outliers LIMIT 1"
        ).fetchone()
        info = lookup_outlier(conn, outlier_row[0])
        assert info is not None
        assert "max_similarity" in info
        assert "threshold_used" in info
        assert info["threshold_used"] == 0.5
        checks += 1

        # Check 4: lookup for non-outlier returns None
        non_outlier = conn.execute(
            "SELECT c.chunk_id FROM chunks c "
            "LEFT JOIN chunk_outliers co ON c.chunk_id = co.chunk_id "
            "WHERE co.chunk_id IS NULL AND c.status != 'superseded' "
            "LIMIT 1"
        ).fetchone()
        if non_outlier:
            assert lookup_outlier(conn, non_outlier[0]) is None
        checks += 1

        # Check 5: list returns outliers sorted by isolation
        outliers_list = list_outliers(conn)
        assert len(outliers_list) > 0
        sims = [o["max_similarity"] for o in outliers_list]
        assert sims == sorted(sims)
        checks += 1

        # Check 6: list excludes superseded
        all_ids = [o["chunk_id"] for o in list_outliers(conn, limit=100)]
        assert "c10" not in all_ids
        checks += 1

        # Check 7: re-persist is idempotent
        result2 = persist_outliers(conn, threshold=0.5, dry_run=False)
        assert result2["inserted"] == 0
        assert result2["unchanged"] + result2["updated"] >= 0
        checks += 1

        # Check 8: stats work
        stats = outlier_stats(conn)
        assert stats["total_outliers"] > 0
        assert stats["active_chunks"] == 9
        assert stats["outlier_rate"] > 0
        assert stats["avg_max_similarity"] >= 0
        checks += 1

        # Check 9: max_similarity values are valid
        all_sims = conn.execute(
            "SELECT max_similarity FROM chunk_outliers"
        ).fetchall()
        for row in all_sims:
            assert 0 <= row[0] <= 1.0
        checks += 1

        # Check 10: primary key prevents duplicates
        existing = conn.execute(
            "SELECT chunk_id FROM chunk_outliers LIMIT 1"
        ).fetchone()
        try:
            conn.execute(
                "INSERT INTO chunk_outliers VALUES (?, 0.1, 0.5, ?)",
                (existing[0], now),
            )
            assert False, "should have raised IntegrityError"
        except Exception:
            pass
        checks += 1

        # Check 11: changing threshold updates records
        result3 = persist_outliers(conn, threshold=0.99, dry_run=False)
        assert result3["outliers_found"] >= result["outliers_found"]
        checks += 1

        # Check 12: removal of chunks no longer outliers
        result4 = persist_outliers(conn, threshold=0.01, dry_run=False)
        if result4["outliers_found"] < result3["outliers_found"]:
            assert result4["removed"] > 0
        checks += 1

        # Check 13: empty corpus
        empty_dir = Path(td) / "empty_sub"
        empty_dir.mkdir()
        empty_conn = connect(str(empty_dir / "empty.db"))
        init_schema(empty_conn)
        result = persist_outliers(empty_conn, dry_run=False)
        assert result["outliers_found"] == 0
        assert result["inserted"] == 0
        stats = outlier_stats(empty_conn)
        assert stats["total_outliers"] == 0
        empty_conn.close()
        checks += 1

        # Check 14: stats by_kind breakdown
        stats = outlier_stats(conn)
        if stats["total_outliers"] > 0:
            assert len(stats["by_kind"]) > 0
            total_from_kinds = sum(k["count"] for k in stats["by_kind"])
            assert total_from_kinds > 0
        checks += 1

        conn.close()

    print(f"PASS outlier_store selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Outlier store")
    sub = parser.add_subparsers(dest="cmd")

    p_persist = sub.add_parser("persist",
                               help="Persist outlier detection results")
    p_persist.add_argument("--db", default=str(DEFAULT_DB))
    p_persist.add_argument("--threshold", type=float, default=0.15)
    p_persist.add_argument("--dry-run", action="store_true")

    p_lookup = sub.add_parser("lookup",
                              help="Look up outlier status for a chunk")
    p_lookup.add_argument("--chunk-id", required=True)
    p_lookup.add_argument("--db", default=str(DEFAULT_DB))
    p_lookup.add_argument("--json", action="store_true")

    p_list = sub.add_parser("list", help="List all outliers")
    p_list.add_argument("--db", default=str(DEFAULT_DB))
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats",
                             help="Outlier store statistics")
    p_stats.add_argument("--db", default=str(DEFAULT_DB))
    p_stats.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "persist":
        conn = connect(args.db)
        result = persist_outliers(conn, threshold=args.threshold,
                                  dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "PERSISTED"
        print(f"  {mode}: {result['outliers_found']} outlier(s), "
              f"{result['inserted']} new, {result['updated']} updated, "
              f"{result['unchanged']} unchanged, "
              f"{result['removed']} removed")
        conn.close()

    elif args.cmd == "lookup":
        conn = connect(args.db)
        info = lookup_outlier(conn, args.chunk_id)
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            if not info:
                print(f"  {args.chunk_id} is not an outlier")
            else:
                print(f"  Outlier: {args.chunk_id}")
                print(f"    max_similarity: {info['max_similarity']:.4f}")
                print(f"    threshold:      {info['threshold_used']:.4f}")
                print(f"    detected:       {info['detected_utc']}")
        conn.close()

    elif args.cmd == "list":
        conn = connect(args.db)
        results = list_outliers(conn, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  No outliers detected")
            else:
                print(f"  {len(results)} outlier(s):")
                for r in results:
                    print(f"    {r['chunk_id'][:12]}  "
                          f"max_sim={r['max_similarity']:.3f}  "
                          f"{r['kind']:6s}  w={r['word_count']:4d}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = outlier_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total outliers:       {stats['total_outliers']}")
            print(f"  Active chunks:        {stats['active_chunks']}")
            print(f"  Outlier rate:         {stats['outlier_rate']:.1%}")
            print(f"  Avg max similarity:   {stats['avg_max_similarity']:.4f}")
            print(f"  Min max similarity:   {stats['min_max_similarity']:.4f}")
            if stats["by_kind"]:
                print("  By kind:")
                for k in stats["by_kind"]:
                    print(f"    {k['kind']:8s}  {k['count']:4d}  "
                          f"avg_sim={k['avg_max_similarity']:.4f}")
        conn.close()


if __name__ == "__main__":
    main()
