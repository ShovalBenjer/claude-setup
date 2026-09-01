#!/usr/bin/env python3
"""Similarity store: precomputes and persists nearest-neighbor pairs.

Uses the fitted embedding vectors from embed.py to compute pairwise
cosine similarities and stores pairs above a threshold in the database.
Enables instant "find similar" queries via SQL joins without
re-computing TF-IDF or loading vectors at query time.

Usage:
    python tools/corpus/similarity_store.py persist [--db PATH] [--threshold F] [--top-k N] [--dry-run]
    python tools/corpus/similarity_store.py similar --chunk-id CID [--db PATH] [--json]
    python tools/corpus/similarity_store.py mutual --chunk-id CID [--db PATH] [--json]
    python tools/corpus/similarity_store.py stats [--db PATH] [--json]
    python tools/corpus/similarity_store.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed import _load_vectors  # noqa: E402
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _now_utc():
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_table(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunk_similarities (
            chunk_id_a     TEXT NOT NULL REFERENCES chunks(chunk_id),
            chunk_id_b     TEXT NOT NULL REFERENCES chunks(chunk_id),
            cosine_score   REAL NOT NULL,
            computed_utc   TEXT NOT NULL,
            PRIMARY KEY (chunk_id_a, chunk_id_b)
        );
        CREATE INDEX IF NOT EXISTS ix_sim_a
            ON chunk_similarities(chunk_id_a);
        CREATE INDEX IF NOT EXISTS ix_sim_b
            ON chunk_similarities(chunk_id_b);
    """)


def persist_similarities(conn, threshold: float = 0.3,
                         top_k: int = 10, dry_run: bool = False,
                         db_path=None) -> dict:
    """Compute and persist nearest-neighbor pairs above threshold."""
    _ensure_table(conn)

    Z, meta, err = _load_vectors(db_path)
    if err:
        return {
            "status": "unavailable",
            "reason": err,
            "pairs_stored": 0,
            "dry_run": dry_run,
        }

    chunk_ids = meta["chunk_ids"]
    n = len(chunk_ids)

    if n < 2:
        return {
            "status": "ok",
            "chunks_processed": n,
            "pairs_stored": 0,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "dry_run": dry_run,
        }

    sim_matrix = Z @ Z.T
    np.fill_diagonal(sim_matrix, 0.0)

    now = _now_utc()
    inserted = 0
    updated = 0
    unchanged = 0

    for i in range(n):
        scores = sim_matrix[i]
        top_indices = np.argsort(scores)[::-1][:top_k]

        for j in top_indices:
            score = float(scores[j])
            if score < threshold:
                continue

            cid_a = chunk_ids[i]
            cid_b = chunk_ids[j]

            existing = conn.execute(
                "SELECT cosine_score FROM chunk_similarities "
                "WHERE chunk_id_a = ? AND chunk_id_b = ?",
                (cid_a, cid_b),
            ).fetchone()

            if existing is None:
                if not dry_run:
                    conn.execute(
                        "INSERT INTO chunk_similarities "
                        "(chunk_id_a, chunk_id_b, cosine_score, computed_utc) "
                        "VALUES (?, ?, ?, ?)",
                        (cid_a, cid_b, round(score, 4), now),
                    )
                inserted += 1
            elif abs(existing[0] - score) > 0.0001:
                if not dry_run:
                    conn.execute(
                        "UPDATE chunk_similarities "
                        "SET cosine_score = ?, computed_utc = ? "
                        "WHERE chunk_id_a = ? AND chunk_id_b = ?",
                        (round(score, 4), now, cid_a, cid_b),
                    )
                updated += 1
            else:
                unchanged += 1

    if not dry_run:
        conn.commit()

    return {
        "status": "ok",
        "chunks_processed": n,
        "pairs_stored": inserted + updated + unchanged,
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "dry_run": dry_run,
    }


def find_similar(conn, chunk_id: str,
                 limit: int = 10) -> list[dict]:
    """Return chunks most similar to chunk_id, with metadata."""
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT cs.chunk_id_b, cs.cosine_score, cs.computed_utc, "
        "c.source_id, c.kind, c.status, c.word_count, c.heading_path "
        "FROM chunk_similarities cs "
        "JOIN chunks c ON cs.chunk_id_b = c.chunk_id "
        "WHERE cs.chunk_id_a = ? AND c.status != 'superseded' "
        "ORDER BY cs.cosine_score DESC "
        "LIMIT ?",
        (chunk_id, limit),
    ).fetchall()
    return [{
        "chunk_id": r[0],
        "cosine_score": r[1],
        "computed_utc": r[2],
        "source_id": r[3],
        "kind": r[4],
        "status": r[5],
        "word_count": r[6],
        "heading_path": r[7],
    } for r in rows]


def find_mutual(conn, chunk_id: str,
                limit: int = 10) -> list[dict]:
    """Return chunks that are mutually similar (A->B and B->A both stored)."""
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT cs1.chunk_id_b, cs1.cosine_score, cs1.computed_utc, "
        "c.source_id, c.kind, c.status, c.word_count, c.heading_path "
        "FROM chunk_similarities cs1 "
        "JOIN chunk_similarities cs2 "
        "  ON cs1.chunk_id_a = cs2.chunk_id_b "
        "  AND cs1.chunk_id_b = cs2.chunk_id_a "
        "JOIN chunks c ON cs1.chunk_id_b = c.chunk_id "
        "WHERE cs1.chunk_id_a = ? AND c.status != 'superseded' "
        "ORDER BY cs1.cosine_score DESC "
        "LIMIT ?",
        (chunk_id, limit),
    ).fetchall()
    return [{
        "chunk_id": r[0],
        "cosine_score": r[1],
        "computed_utc": r[2],
        "source_id": r[3],
        "kind": r[4],
        "status": r[5],
        "word_count": r[6],
        "heading_path": r[7],
    } for r in rows]


def similarity_stats(conn) -> dict:
    """Summary statistics for the similarity store."""
    _ensure_table(conn)
    total_pairs = conn.execute(
        "SELECT COUNT(*) FROM chunk_similarities"
    ).fetchone()[0]
    distinct_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id_a) FROM chunk_similarities"
    ).fetchone()[0]

    if total_pairs == 0:
        return {
            "total_pairs": 0,
            "distinct_chunks": 0,
            "avg_score": 0,
            "min_score": 0,
            "max_score": 0,
            "mutual_pairs": 0,
        }

    avg_score = conn.execute(
        "SELECT AVG(cosine_score) FROM chunk_similarities"
    ).fetchone()[0]
    min_score = conn.execute(
        "SELECT MIN(cosine_score) FROM chunk_similarities"
    ).fetchone()[0]
    max_score = conn.execute(
        "SELECT MAX(cosine_score) FROM chunk_similarities"
    ).fetchone()[0]

    mutual_pairs = conn.execute(
        "SELECT COUNT(*) FROM chunk_similarities cs1 "
        "JOIN chunk_similarities cs2 "
        "  ON cs1.chunk_id_a = cs2.chunk_id_b "
        "  AND cs1.chunk_id_b = cs2.chunk_id_a"
    ).fetchone()[0] // 2

    return {
        "total_pairs": total_pairs,
        "distinct_chunks": distinct_chunks,
        "avg_score": round(avg_score, 4),
        "min_score": round(min_score, 4),
        "max_score": round(max_score, 4),
        "mutual_pairs": mutual_pairs,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    from embed import fit as embed_fit

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
            ("c9", "src1", 8, "Old", "prose", None,
             "this chunk is superseded and should be ignored.",
             "raw", 8, _sha256("superseded"), 0, 0,
             "superseded", "old", now),
        )
        conn.commit()

        embed_fit(conn, db_path=str(db_path))

        # With only 8 chunks PCA produces 7 components,
        # so cosine similarities are very low (~0.04 max).
        test_threshold = 0.001

        # Check 1: dry run does not persist
        result = persist_similarities(
            conn, threshold=test_threshold, top_k=3,
            dry_run=True, db_path=str(db_path),
        )
        assert result["dry_run"] is True
        _ensure_table(conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_similarities"
        ).fetchone()[0]
        assert count == 0
        checks += 1

        # Check 2: persist creates pairs
        result = persist_similarities(
            conn, threshold=test_threshold, top_k=3,
            dry_run=False, db_path=str(db_path),
        )
        assert result["status"] == "ok"
        assert result["chunks_processed"] == 8
        assert result["inserted"] > 0
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_similarities"
        ).fetchone()[0]
        assert count > 0
        checks += 1

        # Check 3: find_similar returns results for a chunk
        similar = find_similar(conn, "c3")
        assert len(similar) > 0
        assert all("cosine_score" in s for s in similar)
        assert all("chunk_id" in s for s in similar)
        checks += 1

        # Check 4: results sorted by score descending
        scores = [s["cosine_score"] for s in similar]
        assert scores == sorted(scores, reverse=True)
        checks += 1

        # Check 5: c3 and c4 (both testing topics) are similar
        c3_neighbors = [s["chunk_id"] for s in find_similar(conn, "c3")]
        assert "c4" in c3_neighbors
        checks += 1

        # Check 6: find_similar excludes superseded
        all_ids = [s["chunk_id"] for s in find_similar(conn, "c3", limit=100)]
        assert "c9" not in all_ids
        checks += 1

        # Check 7: find_similar for unknown chunk returns empty
        assert find_similar(conn, "nonexistent") == []
        checks += 1

        # Check 8: mutual finds bidirectional pairs
        mutual = find_mutual(conn, "c3")
        for m in mutual:
            reverse = conn.execute(
                "SELECT 1 FROM chunk_similarities "
                "WHERE chunk_id_a = ? AND chunk_id_b = ?",
                (m["chunk_id"], "c3"),
            ).fetchone()
            assert reverse is not None
        checks += 1

        # Check 9: re-persist is idempotent
        result2 = persist_similarities(
            conn, threshold=test_threshold, top_k=3,
            dry_run=False, db_path=str(db_path),
        )
        assert result2["unchanged"] + result2["updated"] == result2["pairs_stored"]
        assert result2["inserted"] == 0
        checks += 1

        # Check 10: stats work
        stats = similarity_stats(conn)
        assert stats["total_pairs"] > 0
        assert stats["distinct_chunks"] > 0
        assert 0 < stats["avg_score"] <= 1.0
        assert stats["min_score"] > 0
        assert stats["max_score"] <= 1.0
        checks += 1

        # Check 11: scores are valid cosine values
        all_scores = conn.execute(
            "SELECT cosine_score FROM chunk_similarities"
        ).fetchall()
        for row in all_scores:
            assert 0 < row[0] <= 1.0
        checks += 1

        # Check 12: primary key prevents duplicates
        existing = conn.execute(
            "SELECT chunk_id_a, chunk_id_b FROM chunk_similarities LIMIT 1"
        ).fetchone()
        try:
            conn.execute(
                "INSERT INTO chunk_similarities VALUES (?, ?, 0.5, ?)",
                (existing[0], existing[1], now),
            )
            assert False, "should have raised IntegrityError"
        except Exception:
            pass
        checks += 1

        # Check 13: empty corpus (separate dir so no stale vectors)
        empty_dir = Path(td) / "empty_sub"
        empty_dir.mkdir()
        empty_conn = connect(str(empty_dir / "empty.db"))
        init_schema(empty_conn)
        result = persist_similarities(
            empty_conn, dry_run=False,
            db_path=str(empty_dir / "empty.db"),
        )
        assert result["status"] == "unavailable"
        stats = similarity_stats(empty_conn)
        assert stats["total_pairs"] == 0
        empty_conn.close()
        checks += 1

        # Check 14: higher threshold yields fewer pairs
        result_low = persist_similarities(
            conn, threshold=test_threshold, top_k=5,
            dry_run=True, db_path=str(db_path),
        )
        result_high = persist_similarities(
            conn, threshold=0.9, top_k=5,
            dry_run=True, db_path=str(db_path),
        )
        assert result_high["pairs_stored"] <= result_low["pairs_stored"]
        checks += 1

        conn.close()

    print(f"PASS similarity_store selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Similarity store")
    sub = parser.add_subparsers(dest="cmd")

    p_persist = sub.add_parser("persist",
                               help="Persist nearest-neighbor pairs")
    p_persist.add_argument("--db", default=str(DEFAULT_DB))
    p_persist.add_argument("--threshold", type=float, default=0.3)
    p_persist.add_argument("--top-k", type=int, default=10)
    p_persist.add_argument("--dry-run", action="store_true")

    p_similar = sub.add_parser("similar",
                               help="Find similar chunks")
    p_similar.add_argument("--chunk-id", required=True)
    p_similar.add_argument("--db", default=str(DEFAULT_DB))
    p_similar.add_argument("--limit", type=int, default=10)
    p_similar.add_argument("--json", action="store_true")

    p_mutual = sub.add_parser("mutual",
                              help="Find mutually similar chunks")
    p_mutual.add_argument("--chunk-id", required=True)
    p_mutual.add_argument("--db", default=str(DEFAULT_DB))
    p_mutual.add_argument("--limit", type=int, default=10)
    p_mutual.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats",
                             help="Similarity store statistics")
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
        result = persist_similarities(
            conn, threshold=args.threshold,
            top_k=args.top_k, dry_run=args.dry_run,
            db_path=args.db,
        )
        if result["status"] == "unavailable":
            print(f"  UNAVAILABLE: {result['reason']}")
        else:
            mode = "DRY RUN" if args.dry_run else "PERSISTED"
            print(f"  {mode}: {result['chunks_processed']} chunk(s), "
                  f"{result['pairs_stored']} pair(s), "
                  f"{result['inserted']} new, {result['updated']} updated, "
                  f"{result['unchanged']} unchanged")
        conn.close()

    elif args.cmd == "similar":
        conn = connect(args.db)
        results = find_similar(conn, args.chunk_id, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"  No similar chunks for {args.chunk_id}")
            else:
                print(f"  {len(results)} similar chunk(s) for {args.chunk_id}:")
                for r in results:
                    print(f"    {r['chunk_id'][:12]}  "
                          f"cos={r['cosine_score']:.3f}  "
                          f"{r['kind']:6s}  w={r['word_count']:4d}")
        conn.close()

    elif args.cmd == "mutual":
        conn = connect(args.db)
        results = find_mutual(conn, args.chunk_id, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"  No mutual similarities for {args.chunk_id}")
            else:
                print(f"  {len(results)} mutual pair(s) for {args.chunk_id}:")
                for r in results:
                    print(f"    {r['chunk_id'][:12]}  "
                          f"cos={r['cosine_score']:.3f}  "
                          f"{r['kind']:6s}  w={r['word_count']:4d}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = similarity_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total pairs:      {stats['total_pairs']}")
            print(f"  Distinct chunks:  {stats['distinct_chunks']}")
            print(f"  Avg score:        {stats['avg_score']:.4f}")
            print(f"  Score range:      {stats['min_score']:.4f} - "
                  f"{stats['max_score']:.4f}")
            print(f"  Mutual pairs:     {stats['mutual_pairs']}")
        conn.close()


if __name__ == "__main__":
    main()
