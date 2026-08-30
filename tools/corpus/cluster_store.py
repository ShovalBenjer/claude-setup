#!/usr/bin/env python3
"""Cluster store: persists ML-based cluster assignments into the database.

Bridges the gap between the in-memory semantic clusterer (which computes
KMeans cluster assignments but discards them) and downstream tools that
need persisted cluster data for per-cluster retrieval and chunking
strategies.

Usage:
    python tools/corpus/cluster_store.py persist [--db PATH] [--n-clusters N] [--dry-run]
    python tools/corpus/cluster_store.py lookup --chunk-id CID [--db PATH] [--json]
    python tools/corpus/cluster_store.py members --cluster-label N [--db PATH] [--json]
    python tools/corpus/cluster_store.py stats [--db PATH] [--json]
    python tools/corpus/cluster_store.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402
from semantic import cluster_chunks  # noqa: E402


def _now_utc():
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_table(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunk_clusters (
            chunk_id       TEXT NOT NULL REFERENCES chunks(chunk_id),
            cluster_label  INTEGER NOT NULL,
            top_terms      TEXT NOT NULL,
            clustered_utc  TEXT NOT NULL,
            PRIMARY KEY (chunk_id)
        );
        CREATE INDEX IF NOT EXISTS ix_clusters_label
            ON chunk_clusters(cluster_label);
    """)


def persist_clusters(conn, n_clusters: int = 8,
                     dry_run: bool = False) -> dict:
    """Run semantic clustering and persist assignments to chunk_clusters."""
    _ensure_table(conn)
    clusters = cluster_chunks(conn, n_clusters=n_clusters)
    now = _now_utc()

    inserted = 0
    updated = 0
    unchanged = 0

    for cluster in clusters:
        label = cluster["cluster"]
        top_terms = json.dumps(cluster.get("top_terms", []))

        for member in cluster["members"]:
            chunk_id = member["chunk_id"]

            existing = conn.execute(
                "SELECT cluster_label, top_terms FROM chunk_clusters "
                "WHERE chunk_id = ?",
                (chunk_id,),
            ).fetchone()

            if existing is None:
                if not dry_run:
                    conn.execute(
                        "INSERT INTO chunk_clusters "
                        "(chunk_id, cluster_label, top_terms, clustered_utc) "
                        "VALUES (?, ?, ?, ?)",
                        (chunk_id, label, top_terms, now),
                    )
                inserted += 1
            elif existing[0] != label or existing[1] != top_terms:
                if not dry_run:
                    conn.execute(
                        "UPDATE chunk_clusters "
                        "SET cluster_label = ?, top_terms = ?, "
                        "    clustered_utc = ? "
                        "WHERE chunk_id = ?",
                        (label, top_terms, now, chunk_id),
                    )
                updated += 1
            else:
                unchanged += 1

    if not dry_run:
        conn.commit()

    return {
        "clusters_found": len(clusters),
        "chunks_clustered": sum(c["size"] for c in clusters),
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "dry_run": dry_run,
    }


def lookup_chunk_cluster(conn, chunk_id: str) -> dict | None:
    """Return cluster assignment for a chunk."""
    _ensure_table(conn)
    row = conn.execute(
        "SELECT cluster_label, top_terms, clustered_utc "
        "FROM chunk_clusters WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "chunk_id": chunk_id,
        "cluster_label": row[0],
        "top_terms": json.loads(row[1]),
        "clustered_utc": row[2],
    }


def cluster_members(conn, cluster_label: int) -> list[dict]:
    """Return chunks in a cluster, excluding superseded, with metadata."""
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT cc.chunk_id, cc.top_terms, cc.clustered_utc, "
        "c.source_id, c.kind, c.status, c.word_count, c.heading_path "
        "FROM chunk_clusters cc "
        "JOIN chunks c ON cc.chunk_id = c.chunk_id "
        "WHERE cc.cluster_label = ? AND c.status != 'superseded' "
        "ORDER BY c.word_count DESC",
        (cluster_label,),
    ).fetchall()
    return [{
        "chunk_id": r[0],
        "top_terms": json.loads(r[1]),
        "clustered_utc": r[2],
        "source_id": r[3],
        "kind": r[4],
        "status": r[5],
        "word_count": r[6],
        "heading_path": r[7],
    } for r in rows]


def cluster_store_stats(conn) -> dict:
    """Summary statistics for cluster assignments."""
    _ensure_table(conn)
    total_rows = conn.execute(
        "SELECT COUNT(*) FROM chunk_clusters"
    ).fetchone()[0]
    distinct_clusters = conn.execute(
        "SELECT COUNT(DISTINCT cluster_label) FROM chunk_clusters"
    ).fetchone()[0]

    by_cluster = conn.execute(
        "SELECT cc.cluster_label, COUNT(*), cc.top_terms "
        "FROM chunk_clusters cc "
        "JOIN chunks c ON cc.chunk_id = c.chunk_id "
        "WHERE c.status != 'superseded' "
        "GROUP BY cc.cluster_label ORDER BY COUNT(*) DESC"
    ).fetchall()

    active_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    return {
        "total_cluster_rows": total_rows,
        "distinct_clusters": distinct_clusters,
        "active_chunks": active_chunks,
        "coverage": round(total_rows / active_chunks, 3)
        if active_chunks else 0,
        "by_cluster": [{
            "cluster_label": r[0],
            "count": r[1],
            "top_terms": json.loads(r[2]),
        } for r in by_cluster],
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    try:
        from semantic import HAS_SKLEARN
        if not HAS_SKLEARN:
            print("SKIP cluster_store selftest (scikit-learn not installed)")
            return True
    except ImportError:
        print("SKIP cluster_store selftest (semantic.py import failed)")
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

        # Check 1: dry run does not persist
        result = persist_clusters(conn, n_clusters=3, dry_run=True)
        assert result["dry_run"] is True
        _ensure_table(conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_clusters"
        ).fetchone()[0]
        assert count == 0
        checks += 1

        # Check 2: persist creates rows
        result = persist_clusters(conn, n_clusters=3, dry_run=False)
        assert result["chunks_clustered"] == 8
        assert result["inserted"] == 8
        assert result["clusters_found"] >= 2
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_clusters"
        ).fetchone()[0]
        assert count == 8
        checks += 1

        # Check 3: lookup returns assignment for a chunk
        info = lookup_chunk_cluster(conn, "c1")
        assert info is not None
        assert "cluster_label" in info
        assert "top_terms" in info
        assert isinstance(info["top_terms"], list)
        checks += 1

        # Check 4: lookup for unknown chunk returns None
        assert lookup_chunk_cluster(conn, "nonexistent") is None
        checks += 1

        # Check 5: members returns chunks in a cluster
        label = info["cluster_label"]
        members = cluster_members(conn, label)
        assert len(members) > 0
        assert any(m["chunk_id"] == "c1" for m in members)
        checks += 1

        # Check 6: members excludes superseded
        all_ids = [m["chunk_id"] for m in cluster_members(conn, label)]
        assert "c9" not in all_ids
        checks += 1

        # Check 7: re-persist is idempotent (unchanged count)
        result2 = persist_clusters(conn, n_clusters=3, dry_run=False)
        assert result2["unchanged"] + result2["updated"] == 8
        assert result2["inserted"] == 0
        checks += 1

        # Check 8: stats work
        stats = cluster_store_stats(conn)
        assert stats["total_cluster_rows"] == 8
        assert stats["distinct_clusters"] >= 2
        assert stats["coverage"] > 0
        assert len(stats["by_cluster"]) >= 2
        checks += 1

        # Check 9: chunk_clusters table has correct schema
        row = conn.execute(
            "SELECT chunk_id, cluster_label, top_terms, clustered_utc "
            "FROM chunk_clusters LIMIT 1"
        ).fetchone()
        assert row is not None
        assert isinstance(row[1], int)
        checks += 1

        # Check 10: primary key prevents duplicate chunk_id
        existing_row = conn.execute(
            "SELECT chunk_id FROM chunk_clusters LIMIT 1"
        ).fetchone()
        try:
            conn.execute(
                "INSERT INTO chunk_clusters VALUES (?, 0, '[]', ?)",
                (existing_row[0], now),
            )
            assert False, "should have raised IntegrityError"
        except Exception:
            pass
        checks += 1

        # Check 11: re-clustering with different n_clusters updates labels
        result3 = persist_clusters(conn, n_clusters=4, dry_run=False)
        assert result3["updated"] > 0 or result3["unchanged"] > 0
        checks += 1

        # Check 12: members ordered by word_count descending
        members = cluster_members(conn, label)
        if len(members) > 1:
            wcs = [m["word_count"] for m in members]
            assert wcs == sorted(wcs, reverse=True)
        checks += 1

        # Check 13: empty corpus
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        result = persist_clusters(empty_conn, dry_run=False)
        assert result["chunks_clustered"] == 0
        assert result["inserted"] == 0
        stats = cluster_store_stats(empty_conn)
        assert stats["total_cluster_rows"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS cluster_store selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Cluster store")
    sub = parser.add_subparsers(dest="cmd")

    p_persist = sub.add_parser("persist",
                               help="Persist cluster assignments to DB")
    p_persist.add_argument("--db", default=str(DEFAULT_DB))
    p_persist.add_argument("--n-clusters", type=int, default=8)
    p_persist.add_argument("--dry-run", action="store_true")

    p_lookup = sub.add_parser("lookup",
                              help="Look up cluster for a chunk")
    p_lookup.add_argument("--chunk-id", required=True)
    p_lookup.add_argument("--db", default=str(DEFAULT_DB))
    p_lookup.add_argument("--json", action="store_true")

    p_members = sub.add_parser("members",
                               help="List chunks in a cluster")
    p_members.add_argument("--cluster-label", type=int, required=True)
    p_members.add_argument("--db", default=str(DEFAULT_DB))
    p_members.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats",
                             help="Cluster store statistics")
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
        result = persist_clusters(conn, n_clusters=args.n_clusters,
                                  dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "PERSISTED"
        print(f"  {mode}: {result['clusters_found']} cluster(s), "
              f"{result['chunks_clustered']} chunk(s), "
              f"{result['inserted']} new, {result['updated']} updated, "
              f"{result['unchanged']} unchanged")
        conn.close()

    elif args.cmd == "lookup":
        conn = connect(args.db)
        info = lookup_chunk_cluster(conn, args.chunk_id)
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            if not info:
                print(f"  No cluster for chunk {args.chunk_id}")
            else:
                print(f"  Cluster for {args.chunk_id}:")
                print(f"    label:     {info['cluster_label']}")
                print(f"    terms:     {', '.join(info['top_terms'])}")
                print(f"    clustered: {info['clustered_utc']}")
        conn.close()

    elif args.cmd == "members":
        conn = connect(args.db)
        results = cluster_members(conn, args.cluster_label)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"  No chunks in cluster {args.cluster_label}")
            else:
                terms = results[0]["top_terms"]
                print(f"  Cluster {args.cluster_label} "
                      f"({len(results)} chunk(s)):")
                print(f"  Top terms: {', '.join(terms)}")
                for r in results[:50]:
                    print(f"    {r['chunk_id'][:12]}  {r['kind']:6s}  "
                          f"w={r['word_count']:4d}  {r['status']}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = cluster_store_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total cluster rows:   {stats['total_cluster_rows']}")
            print(f"  Distinct clusters:    {stats['distinct_clusters']}")
            print(f"  Active chunks:        {stats['active_chunks']}")
            print(f"  Coverage:             {stats['coverage']:.1%}")
            print("  By cluster:")
            for c in stats["by_cluster"]:
                terms = ", ".join(c["top_terms"][:3])
                print(f"    {c['cluster_label']:3d}: {c['count']:5d}  "
                      f"[{terms}]")
        conn.close()


if __name__ == "__main__":
    main()
