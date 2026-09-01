#!/usr/bin/env python3
"""Domain store: persists semantic domain classifications into the database.

Bridges the gap between the in-memory semantic classifier (which computes
domain scores but discards them) and downstream tools that need persisted
domain data for faceted queries, per-domain retrieval, and cluster-based
chunking strategies.

Usage:
    python tools/corpus/domain_store.py persist [--db PATH] [--top-k N] [--min-score F] [--dry-run]
    python tools/corpus/domain_store.py lookup --chunk-id CID [--db PATH] [--json]
    python tools/corpus/domain_store.py find --domain DOMAIN [--db PATH] [--min-score F] [--json]
    python tools/corpus/domain_store.py stats [--db PATH] [--json]
    python tools/corpus/domain_store.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402
from semantic import classify_chunks  # noqa: E402


def _now_utc():
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def persist_domains(conn, top_k: int = 3, min_score: float = 0.01,
                    dry_run: bool = False) -> dict:
    """Run semantic classification and persist results to chunk_domains."""
    classified = classify_chunks(conn)
    now = _now_utc()

    inserted = 0
    updated = 0
    unchanged = 0

    for result in classified:
        chunk_id = result["chunk_id"]
        domains = result["domains"][:top_k]

        for entry in domains:
            domain = entry["domain"]
            score = entry["score"]

            if score < min_score:
                continue

            existing = conn.execute(
                "SELECT score FROM chunk_domains "
                "WHERE chunk_id = ? AND domain = ?",
                (chunk_id, domain),
            ).fetchone()

            if existing is None:
                if not dry_run:
                    conn.execute(
                        "INSERT INTO chunk_domains "
                        "(chunk_id, domain, score, classified_utc) "
                        "VALUES (?, ?, ?, ?)",
                        (chunk_id, domain, score, now),
                    )
                inserted += 1
            elif abs(existing[0] - score) > 0.0001:
                if not dry_run:
                    conn.execute(
                        "UPDATE chunk_domains SET score = ?, classified_utc = ? "
                        "WHERE chunk_id = ? AND domain = ?",
                        (score, now, chunk_id, domain),
                    )
                updated += 1
            else:
                unchanged += 1

    if not dry_run:
        conn.commit()

    return {
        "chunks_classified": len(classified),
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "dry_run": dry_run,
    }


def lookup_chunk_domains(conn, chunk_id: str) -> list[dict]:
    """Return domains for a chunk, sorted by score descending."""
    rows = conn.execute(
        "SELECT domain, score, classified_utc FROM chunk_domains "
        "WHERE chunk_id = ? ORDER BY score DESC",
        (chunk_id,),
    ).fetchall()
    return [{"domain": r[0], "score": r[1], "classified_utc": r[2]}
            for r in rows]


def find_by_domain(conn, domain: str, min_score: float = 0.0) -> list[dict]:
    """Find chunks classified under a domain, excluding superseded."""
    rows = conn.execute(
        "SELECT cd.chunk_id, cd.score, cd.classified_utc, "
        "c.source_id, c.kind, c.status, c.heading_path "
        "FROM chunk_domains cd "
        "JOIN chunks c ON cd.chunk_id = c.chunk_id "
        "WHERE cd.domain = ? AND cd.score >= ? AND c.status != 'superseded' "
        "ORDER BY cd.score DESC",
        (domain, min_score),
    ).fetchall()
    return [{
        "chunk_id": r[0], "score": r[1], "classified_utc": r[2],
        "source_id": r[3], "kind": r[4], "status": r[5],
        "heading_path": r[6],
    } for r in rows]


def domain_store_stats(conn) -> dict:
    """Summary statistics for domain classifications."""
    total_rows = conn.execute(
        "SELECT COUNT(*) FROM chunk_domains"
    ).fetchone()[0]
    distinct_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_domains"
    ).fetchone()[0]
    distinct_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]

    by_domain = conn.execute(
        "SELECT domain, COUNT(*), ROUND(AVG(score), 4) "
        "FROM chunk_domains GROUP BY domain ORDER BY COUNT(*) DESC"
    ).fetchall()

    active_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    return {
        "total_domain_rows": total_rows,
        "distinct_chunks_classified": distinct_chunks,
        "distinct_domains_used": distinct_domains,
        "active_chunks": active_chunks,
        "coverage": round(distinct_chunks / active_chunks, 3)
        if active_chunks else 0,
        "by_domain": [{"domain": r[0], "count": r[1], "avg_score": r[2]}
                      for r in by_domain],
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    try:
        from semantic import HAS_SKLEARN
        if not HAS_SKLEARN:
            print("SKIP domain_store selftest (scikit-learn not installed)")
            return True
    except ImportError:
        print("SKIP domain_store selftest (semantic.py import failed)")
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

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "Database", "prose", None,
             "sqlite database provides powerful sql query capabilities with "
             "schema migrations and index management. table constraints ensure "
             "data integrity through foreign key relationships and unique indexes.",
             "raw", 25, _sha256("c1"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "Testing", "prose", None,
             "python pytest framework provides test fixtures and assertions. "
             "coverage reports measure code quality. unittest mock objects "
             "help isolate components during regression testing.",
             "raw", 22, _sha256("c2"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 2, "Security", "prose", None,
             "oauth authentication with jwt tokens provides secure api access. "
             "tls encryption protects credentials and secrets in transit. "
             "authorization middleware validates each api request.",
             "raw", 24, _sha256("c3"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src1", 3, "Old", "prose", None,
             "this chunk is superseded and should be ignored completely.",
             "raw", 9, _sha256("c4"), 0, 0, "superseded", "old", now),
        )
        conn.commit()

        # Check 1: dry run does not persist
        result = persist_domains(conn, dry_run=True)
        assert result["dry_run"] is True
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_domains"
        ).fetchone()[0]
        assert count == 0
        checks += 1

        # Check 2: persist creates rows
        result = persist_domains(conn, dry_run=False)
        assert result["chunks_classified"] >= 3
        assert result["inserted"] > 0
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_domains"
        ).fetchone()[0]
        assert count > 0
        checks += 1

        # Check 3: lookup returns domains for a chunk
        domains = lookup_chunk_domains(conn, "c1")
        assert len(domains) > 0
        assert all("domain" in d and "score" in d for d in domains)
        checks += 1

        # Check 4: domains sorted by score descending
        scores = [d["score"] for d in domains]
        assert scores == sorted(scores, reverse=True)
        checks += 1

        # Check 5: lookup for unknown chunk returns empty
        assert lookup_chunk_domains(conn, "nonexistent") == []
        checks += 1

        # Check 6: find_by_domain returns matching chunks
        domain_name = domains[0]["domain"]
        found = find_by_domain(conn, domain_name)
        assert len(found) > 0
        assert any(f["chunk_id"] == "c1" for f in found)
        checks += 1

        # Check 7: find_by_domain excludes superseded
        all_found_ids = [f["chunk_id"] for f in find_by_domain(conn, domain_name)]
        assert "c4" not in all_found_ids
        checks += 1

        # Check 8: find_by_domain min_score filter
        high_score = find_by_domain(conn, domain_name, min_score=999.0)
        assert len(high_score) == 0
        checks += 1

        # Check 9: re-persist is idempotent (unchanged count)
        result2 = persist_domains(conn, dry_run=False)
        assert result2["unchanged"] > 0
        assert result2["inserted"] == 0
        checks += 1

        # Check 10: stats work
        stats = domain_store_stats(conn)
        assert stats["total_domain_rows"] > 0
        assert stats["distinct_chunks_classified"] >= 3
        assert stats["distinct_domains_used"] > 0
        assert stats["coverage"] > 0
        assert len(stats["by_domain"]) > 0
        checks += 1

        # Check 11: chunk_domains table has correct schema
        row = conn.execute(
            "SELECT chunk_id, domain, score, classified_utc "
            "FROM chunk_domains LIMIT 1"
        ).fetchone()
        assert row is not None
        assert isinstance(row[2], float)
        checks += 1

        # Check 12: primary key prevents duplicate (chunk_id, domain)
        existing_row = conn.execute(
            "SELECT chunk_id, domain FROM chunk_domains LIMIT 1"
        ).fetchone()
        try:
            conn.execute(
                "INSERT INTO chunk_domains VALUES (?, ?, 0.5, ?)",
                (existing_row[0], existing_row[1], now),
            )
            assert False, "should have raised IntegrityError"
        except Exception:
            pass
        checks += 1

        # Check 13: database chunk gets database domain
        c1_domains = [d["domain"] for d in lookup_chunk_domains(conn, "c1")]
        assert "database" in c1_domains, \
            f"database chunk should classify as database, got {c1_domains}"
        checks += 1

        # Check 14: top_k limits number of domains per chunk
        result3 = persist_domains(conn, top_k=1, dry_run=True)
        assert result3["dry_run"] is True
        checks += 1

        # Check 15: empty corpus
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        result = persist_domains(empty_conn, dry_run=False)
        assert result["chunks_classified"] == 0
        assert result["inserted"] == 0
        stats = domain_store_stats(empty_conn)
        assert stats["total_domain_rows"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS domain_store selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Domain store")
    sub = parser.add_subparsers(dest="cmd")

    p_persist = sub.add_parser("persist",
                               help="Persist domain classifications to DB")
    p_persist.add_argument("--db", default=str(DEFAULT_DB))
    p_persist.add_argument("--top-k", type=int, default=3)
    p_persist.add_argument("--min-score", type=float, default=0.01)
    p_persist.add_argument("--dry-run", action="store_true")

    p_lookup = sub.add_parser("lookup", help="Look up domains for a chunk")
    p_lookup.add_argument("--chunk-id", required=True)
    p_lookup.add_argument("--db", default=str(DEFAULT_DB))
    p_lookup.add_argument("--json", action="store_true")

    p_find = sub.add_parser("find", help="Find chunks by domain")
    p_find.add_argument("--domain", required=True)
    p_find.add_argument("--db", default=str(DEFAULT_DB))
    p_find.add_argument("--min-score", type=float, default=0.0)
    p_find.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats", help="Domain store statistics")
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
        result = persist_domains(conn, top_k=args.top_k,
                                 min_score=args.min_score,
                                 dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "PERSISTED"
        print(f"  {mode}: {result['chunks_classified']} chunk(s) classified, "
              f"{result['inserted']} new, {result['updated']} updated, "
              f"{result['unchanged']} unchanged")
        conn.close()

    elif args.cmd == "lookup":
        conn = connect(args.db)
        domains = lookup_chunk_domains(conn, args.chunk_id)
        if args.json:
            print(json.dumps(domains, indent=2))
        else:
            if not domains:
                print(f"  No domains for chunk {args.chunk_id}")
            else:
                print(f"  Domains for {args.chunk_id}:")
                for d in domains:
                    print(f"    {d['domain']:16s}  score={d['score']:.4f}")
        conn.close()

    elif args.cmd == "find":
        conn = connect(args.db)
        results = find_by_domain(conn, args.domain, min_score=args.min_score)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"  No chunks for domain '{args.domain}'")
            else:
                print(f"  {len(results)} chunk(s) for '{args.domain}':")
                for r in results[:50]:
                    print(f"    {r['chunk_id'][:12]}  {r['kind']:6s}  "
                          f"score={r['score']:.4f}  {r['status']}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = domain_store_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total domain rows:    {stats['total_domain_rows']}")
            print(f"  Chunks classified:    {stats['distinct_chunks_classified']}")
            print(f"  Domains used:         {stats['distinct_domains_used']}")
            print(f"  Active chunks:        {stats['active_chunks']}")
            print(f"  Coverage:             {stats['coverage']:.1%}")
            print("  By domain:")
            for d in stats["by_domain"]:
                print(f"    {d['domain']:16s}: {d['count']:5d}  "
                      f"avg={d['avg_score']:.4f}")
        conn.close()


if __name__ == "__main__":
    main()
