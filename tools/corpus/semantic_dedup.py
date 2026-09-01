#!/usr/bin/env python3
"""Semantic deduplication: find paraphrase-level duplicates via embeddings.

Extends the dedup pipeline beyond exact-hash (Class A) and simhash
(Class B) to find chunks that are semantically equivalent but lexically
different -- rephrased passages, reorganised tables, or rewritten prose
that escape hash-based detection.

Uses the PCA-reduced TF-IDF vectors from embed.py, where L2-normalised
vectors make cosine similarity a simple dot product.

Usage:
    python tools/corpus/semantic_dedup.py scan [--db PATH] [--threshold F] [--json]
    python tools/corpus/semantic_dedup.py apply [--db PATH] [--threshold F] [--dry-run]
    python tools/corpus/semantic_dedup.py stats [--db PATH] [--json]
    python tools/corpus/semantic_dedup.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed import _get_generation, _load_vectors  # noqa: E402
from embed import fit as embed_fit  # noqa: E402
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _now_utc():
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _existing_dup_pairs(conn) -> set[tuple[str, str]]:
    """Return chunk pairs already linked by a 'duplicates' edge."""
    rows = conn.execute(
        "SELECT source_chunk, target_chunk FROM claim_edges "
        "WHERE edge_type = 'duplicates'"
    ).fetchall()
    pairs = set()
    for r in rows:
        pairs.add(tuple(sorted([r[0], r[1]])))
    return pairs


def scan_semantic_dups(conn, threshold: float = 0.85,
                       db_path=None) -> tuple[list[dict], str]:
    """Find semantically similar chunk pairs above threshold.

    Returns (pairs, status) where status is 'scanned' or 'vectors_unavailable'.
    Each pair dict has chunk_a, chunk_b, cosine_similarity, and metadata.
    """
    Z, meta, err = _load_vectors(db_path)
    if err:
        return [], "vectors_unavailable"

    current_gen = _get_generation(conn)
    if meta["generation"] != current_gen:
        return [], "vectors_unavailable"

    chunk_ids = meta["chunk_ids"]
    n = len(chunk_ids)

    if n < 2:
        return [], "scanned"

    existing_pairs = _existing_dup_pairs(conn)

    status_map = {}
    rows = conn.execute(
        "SELECT chunk_id, status, source_id, kind, word_count "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()
    for r in rows:
        status_map[r[0]] = {
            "status": r[1], "source_id": r[2],
            "kind": r[3], "word_count": r[4],
        }

    # Z is L2-normalised, so cosine similarity = dot product
    sim_matrix = Z @ Z.T

    pairs = []
    for i in range(n):
        cid_a = chunk_ids[i]
        if cid_a not in status_map:
            continue
        for j in range(i + 1, n):
            cid_b = chunk_ids[j]
            if cid_b not in status_map:
                continue

            score = float(sim_matrix[i, j])
            if score < threshold:
                continue

            pair_key = tuple(sorted([cid_a, cid_b]))
            if pair_key in existing_pairs:
                continue

            meta_a = status_map[cid_a]
            meta_b = status_map[cid_b]

            pairs.append({
                "chunk_a": cid_a,
                "chunk_b": cid_b,
                "cosine_similarity": round(score, 4),
                "source_a": meta_a["source_id"],
                "source_b": meta_b["source_id"],
                "kind_a": meta_a["kind"],
                "kind_b": meta_b["kind"],
                "word_count_a": meta_a["word_count"],
                "word_count_b": meta_b["word_count"],
            })

    pairs.sort(key=lambda p: -p["cosine_similarity"])
    return pairs, "scanned"


def apply_semantic_dedup(conn, threshold: float = 0.85,
                         dry_run: bool = True,
                         db_path=None) -> dict:
    """Mark semantic duplicates as superseded.

    For each pair above threshold, the shorter chunk is superseded
    (the longer one is assumed to carry more information). Ties break
    by chunk_id alphabetical order (earlier id kept).
    """
    pairs, status = scan_semantic_dups(conn, threshold=threshold,
                                       db_path=db_path)
    if status != "scanned":
        return {
            "status": status,
            "pairs_found": 0,
            "applied": 0,
            "skipped": 0,
            "dry_run": dry_run,
        }

    now = _now_utc()
    applied = 0
    skipped = 0
    already_superseded = set()

    for pair in pairs:
        cid_a = pair["chunk_a"]
        cid_b = pair["chunk_b"]

        if cid_a in already_superseded or cid_b in already_superseded:
            skipped += 1
            continue

        wc_a = pair["word_count_a"]
        wc_b = pair["word_count_b"]
        if wc_a > wc_b:
            keeper, duplicate = cid_a, cid_b
        elif wc_b > wc_a:
            keeper, duplicate = cid_b, cid_a
        else:
            keeper, duplicate = sorted([cid_a, cid_b])

        edge_id = "e" + _sha256(keeper + duplicate)[:15]

        if not dry_run:
            conn.execute(
                "UPDATE chunks SET status = 'superseded', "
                "status_reason = 'semantic_duplicate' "
                "WHERE chunk_id = ?",
                (duplicate,),
            )
            existing = conn.execute(
                "SELECT edge_id FROM claim_edges WHERE edge_id = ?",
                (edge_id,),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
                    (edge_id, duplicate, keeper,
                     "duplicates", "embedding_cosine",
                     pair["cosine_similarity"], now, None, None),
                )

        already_superseded.add(duplicate)
        applied += 1

    if not dry_run:
        conn.commit()

    return {
        "status": "applied" if not dry_run else "dry_run",
        "pairs_found": len(pairs),
        "applied": applied,
        "skipped": skipped,
        "dry_run": dry_run,
        "threshold": threshold,
    }


def semantic_dedup_stats(conn) -> dict:
    """Statistics on semantic dedup activity."""
    sem_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges "
        "WHERE edge_type = 'duplicates' AND basis = 'embedding_cosine'"
    ).fetchone()[0]

    sem_superseded = conn.execute(
        "SELECT COUNT(*) FROM chunks "
        "WHERE status = 'superseded' AND status_reason = 'semantic_duplicate'"
    ).fetchone()[0]

    all_dup_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges WHERE edge_type = 'duplicates'"
    ).fetchone()[0]

    all_superseded = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'superseded'"
    ).fetchone()[0]

    active = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    avg_sim = conn.execute(
        "SELECT ROUND(AVG(confidence), 4) FROM claim_edges "
        "WHERE edge_type = 'duplicates' AND basis = 'embedding_cosine'"
    ).fetchone()[0]

    return {
        "semantic_dup_edges": sem_edges,
        "semantic_superseded": sem_superseded,
        "total_dup_edges": all_dup_edges,
        "total_superseded": all_superseded,
        "active_chunks": active,
        "total_chunks": total,
        "avg_cosine_similarity": avg_sim or 0.0,
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
            ("src1", "file:///a.md", "local_md", "Source A",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src2", "file:///b.md", "local_md", "Source B",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("b"), 200, None),
        )

        # Near-identical pair (minor word swaps, high char-ngram overlap)
        text_a = (
            "sqlite database provides efficient btree indexing for fast "
            "lookups on primary keys and unique constraints in relational "
            "tables with support for covering indexes and partial indexes "
            "the query planner optimizes joins using cost based analysis"
        )
        text_b = (
            "sqlite database provides efficient btree indexing for fast "
            "lookups on primary keys and unique constraints in relational "
            "tables with support for covering indexes and partial indexes "
            "the query optimizer selects joins using cost based analysis"
        )
        # Distinct topics to separate from the db pair
        text_c = (
            "python pytest framework provides test fixtures parametrize "
            "decorators for automated testing with coverage reports and "
            "assertion introspection for debugging test failures unittest "
            "mock objects help isolate components during regression testing"
        )
        text_d = (
            "oauth2 authentication flow uses jwt bearer tokens for "
            "stateless api authorization with refresh token rotation "
            "and scope based access control for microservices security "
            "tls encryption protects credentials secrets in transit"
        )
        text_e = (
            "react components use jsx syntax for declarative ui rendering "
            "with virtual dom diffing and reconciliation for efficient "
            "updates hooks provide state management and side effects "
            "context api enables prop drilling avoidance patterns"
        )
        text_f = (
            "kubernetes orchestrates container workloads across clusters "
            "with pod scheduling resource limits and health checks "
            "services expose network endpoints with load balancing "
            "ingress controllers route external traffic to pods"
        )
        text_g = (
            "git version control tracks file changes with commits branches "
            "and merges providing distributed collaboration workflows "
            "rebasing enables linear history while cherry pick applies "
            "individual commits across branches selectively"
        )
        # Superseded chunk (should be excluded)
        text_h = (
            "this chunk was superseded and should be excluded from "
            "all semantic deduplication analysis entirely ignored"
        )

        for cid, sid, ordinal, text, status, reason in [
            ("c1", "src1", 0, text_a, "accepted", None),
            ("c2", "src2", 0, text_b, "accepted", None),
            ("c3", "src1", 1, text_c, "accepted", None),
            ("c4", "src2", 1, text_d, "accepted", None),
            ("c5", "src1", 2, text_e, "accepted", None),
            ("c6", "src2", 2, text_f, "accepted", None),
            ("c7", "src1", 3, text_g, "accepted", None),
            ("c8", "src2", 3, text_h, "superseded", "old"),
        ]:
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, ordinal, "Test", "prose", None,
                 text, "raw", len(text.split()), _sha256(text),
                 0, 0, status, reason, now),
            )
        conn.commit()

        # Fit vectors
        n_chunks, gen = embed_fit(conn, db_path=db_path)

        # Check 1: vectors fitted for accepted chunks (c1-c7, not c8)
        assert n_chunks == 7, f"expected 7 chunks fitted, got {n_chunks}"
        checks += 1

        # Check 2: scan finds the similar pair
        pairs, status = scan_semantic_dups(conn, threshold=0.5,
                                           db_path=db_path)
        assert status == "scanned"
        checks += 1

        # Check 3: the paraphrase pair (c1, c2) appears
        c1c2 = [p for p in pairs
                if {p["chunk_a"], p["chunk_b"]} == {"c1", "c2"}]
        assert len(c1c2) == 1, \
            f"expected c1-c2 pair, found {len(c1c2)} matches in {pairs}"
        checks += 1

        # Check 4: the paraphrase pair has highest similarity
        if pairs:
            top_pair = pairs[0]
            assert {top_pair["chunk_a"], top_pair["chunk_b"]} == {"c1", "c2"}
        checks += 1

        # Check 5: superseded chunk c8 is excluded
        all_ids = set()
        for p in pairs:
            all_ids.add(p["chunk_a"])
            all_ids.add(p["chunk_b"])
        assert "c8" not in all_ids
        checks += 1

        # Check 6: dry run does not modify DB
        result = apply_semantic_dedup(conn, threshold=0.5,
                                      dry_run=True, db_path=db_path)
        assert result["dry_run"] is True
        assert result["applied"] >= 1
        status_c2 = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()[0]
        assert status_c2 == "accepted"
        checks += 1

        # Check 7: apply marks the shorter chunk as superseded
        result = apply_semantic_dedup(conn, threshold=0.5,
                                      dry_run=False, db_path=db_path)
        assert result["applied"] >= 1
        checks += 1

        # Check 8: claim_edge created with basis 'embedding_cosine'
        edges = conn.execute(
            "SELECT edge_type, basis FROM claim_edges "
            "WHERE basis = 'embedding_cosine'"
        ).fetchall()
        assert len(edges) >= 1
        assert edges[0][0] == "duplicates"
        checks += 1

        # Check 9: keeper is not superseded
        keeper_rows = conn.execute(
            "SELECT chunk_id, status FROM chunks "
            "WHERE status = 'accepted' AND chunk_id IN ('c1', 'c2')"
        ).fetchall()
        assert len(keeper_rows) >= 1
        checks += 1

        # Check 10: stats reflect the semantic dedup
        stats = semantic_dedup_stats(conn)
        assert stats["semantic_dup_edges"] >= 1
        assert stats["semantic_superseded"] >= 1
        assert stats["avg_cosine_similarity"] > 0
        checks += 1

        # Check 11: re-scan excludes already-linked pairs
        pairs2, _ = scan_semantic_dups(conn, threshold=0.5,
                                       db_path=db_path)
        linked = [p for p in pairs2
                  if {p["chunk_a"], p["chunk_b"]} == {"c1", "c2"}]
        assert len(linked) == 0
        checks += 1

        # Check 12: high threshold returns no pairs
        pairs3, st3 = scan_semantic_dups(conn, threshold=0.999,
                                         db_path=db_path)
        assert st3 == "scanned"
        assert len(pairs3) == 0
        checks += 1

        # Check 13: vectors_unavailable when generation mismatched
        conn.execute(
            "INSERT OR REPLACE INTO corpus_meta (key, value) "
            "VALUES ('generation', '999')"
        )
        conn.commit()
        pairs4, st4 = scan_semantic_dups(conn, threshold=0.5,
                                         db_path=db_path)
        assert st4 == "vectors_unavailable"
        checks += 1

        # Check 14: empty corpus
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        stats_empty = semantic_dedup_stats(empty_conn)
        assert stats_empty["semantic_dup_edges"] == 0
        assert stats_empty["total_chunks"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS semantic_dedup selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Semantic deduplication")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan",
                            help="Scan for semantic duplicates")
    p_scan.add_argument("--db", default=str(DEFAULT_DB))
    p_scan.add_argument("--threshold", type=float, default=0.85,
                        help="Cosine similarity threshold (default: 0.85)")
    p_scan.add_argument("--json", action="store_true")

    p_apply = sub.add_parser("apply",
                             help="Mark semantic duplicates as superseded")
    p_apply.add_argument("--db", default=str(DEFAULT_DB))
    p_apply.add_argument("--threshold", type=float, default=0.85)
    p_apply.add_argument("--dry-run", action="store_true")

    p_stats = sub.add_parser("stats",
                             help="Semantic dedup statistics")
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

    if args.cmd == "scan":
        conn = connect(args.db)
        pairs, status = scan_semantic_dups(conn, threshold=args.threshold)
        if status != "scanned":
            print(f"  {status}: run 'embed.py fit' first")
        elif args.json:
            print(json.dumps(pairs, indent=2))
        else:
            if not pairs:
                print("  No semantic duplicates found above threshold "
                      f"{args.threshold}")
            else:
                print(f"  {len(pairs)} semantic duplicate pair(s) "
                      f"(threshold={args.threshold}):")
                for p in pairs[:50]:
                    print(f"    sim={p['cosine_similarity']:.4f}  "
                          f"{p['chunk_a'][:12]} <-> {p['chunk_b'][:12]}  "
                          f"w={p['word_count_a']}/{p['word_count_b']}")
        conn.close()

    elif args.cmd == "apply":
        conn = connect(args.db)
        result = apply_semantic_dedup(conn, threshold=args.threshold,
                                      dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        if result["status"] == "vectors_unavailable":
            print("  vectors unavailable: run 'embed.py fit' first")
        else:
            print(f"  {mode}: {result['pairs_found']} pair(s) found, "
                  f"{result['applied']} applied, "
                  f"{result['skipped']} skipped")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = semantic_dedup_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Semantic dup edges:    {stats['semantic_dup_edges']}")
            print(f"  Semantic superseded:   {stats['semantic_superseded']}")
            print(f"  Total dup edges:       {stats['total_dup_edges']}")
            print(f"  Total superseded:      {stats['total_superseded']}")
            print(f"  Active chunks:         {stats['active_chunks']}")
            print(f"  Total chunks:          {stats['total_chunks']}")
            print(f"  Avg cosine similarity: "
                  f"{stats['avg_cosine_similarity']:.4f}")
        conn.close()


if __name__ == "__main__":
    main()
