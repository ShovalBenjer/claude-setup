#!/usr/bin/env python3
"""Corpus dashboard: single-command overview of all analytical signals.

Aggregates key metrics from across the corpus into one report rather
than requiring the operator to run each tool individually.

Usage:
    python tools/corpus/dashboard.py overview [--db PATH] [--json]
    python tools/corpus/dashboard.py health [--db PATH] [--json]
    python tools/corpus/dashboard.py signals [--db PATH] [--json]
    python tools/corpus/dashboard.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

# ── helpers ──────────────────────────────────────────────────────────


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _count(conn, table: str, where: str = "") -> int:
    if not _table_exists(conn, table):
        return 0
    q = f"SELECT count(*) FROM {table}"
    if where:
        q += f" WHERE {where}"
    return conn.execute(q).fetchone()[0]


# ── subcommands ──────────────────────────────────────────────────────


def overview(conn) -> dict:
    total_chunks = _count(conn, "chunks")
    active_chunks = _count(conn, "chunks", "status != 'superseded'")
    superseded = _count(conn, "chunks", "status = 'superseded'")
    accepted = _count(conn, "chunks", "status = 'accepted'")
    quarantined = _count(conn, "chunks", "status = 'quarantined'")

    by_kind: dict[str, int] = {}
    if _table_exists(conn, "chunks"):
        rows = conn.execute(
            "SELECT kind, count(*) FROM chunks "
            "WHERE status != 'superseded' GROUP BY kind"
        ).fetchall()
        by_kind = {r[0]: r[1] for r in rows}

    total_sources = _count(conn, "sources")
    live_sources = _count(conn, "sources", "liveness = 'live'")

    return {
        "chunks": {
            "total": total_chunks,
            "active": active_chunks,
            "superseded": superseded,
            "accepted": accepted,
            "quarantined": quarantined,
            "by_kind": by_kind,
        },
        "sources": {
            "total": total_sources,
            "live": live_sources,
        },
    }


def health(conn) -> dict:
    total_edges = _count(conn, "claim_edges")
    unresolved = _count(conn, "claim_edges", "resolution IS NULL")
    contradictions = _count(conn, "claim_edges",
                            "edge_type = 'contradicts' AND resolution IS NULL")

    edge_types: dict[str, int] = {}
    if _table_exists(conn, "claim_edges"):
        rows = conn.execute(
            "SELECT edge_type, count(*) FROM claim_edges GROUP BY edge_type"
        ).fetchall()
        edge_types = {r[0]: r[1] for r in rows}

    total_citations = _count(conn, "citations")
    total_artifacts = _count(conn, "artifacts")

    orphan_chunks = 0
    if _table_exists(conn, "chunks") and _table_exists(conn, "citations"):
        orphan_chunks = conn.execute(
            "SELECT count(*) FROM chunks c "
            "WHERE c.status = 'accepted' AND c.kind = 'claim' "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM citations ci WHERE ci.chunk_id = c.chunk_id"
            ") AND NOT EXISTS ("
            "  SELECT 1 FROM claim_edges e "
            "  WHERE e.source_chunk = c.chunk_id "
            "     OR e.target_chunk = c.chunk_id"
            ")"
        ).fetchone()[0]

    return {
        "edges": {
            "total": total_edges,
            "unresolved": unresolved,
            "open_contradictions": contradictions,
            "by_type": edge_types,
        },
        "citations": total_citations,
        "artifacts": total_artifacts,
        "orphan_claim_chunks": orphan_chunks,
    }


def signal_coverage(conn) -> dict:
    active = _count(conn, "chunks", "status != 'superseded'")
    if active == 0:
        return {
            "active_chunks": 0,
            "topics": {"chunks_covered": 0, "topic_count": 0, "coverage": 0.0},
            "clusters": {"chunks_covered": 0, "cluster_count": 0, "coverage": 0.0},
            "tags": {"chunks_covered": 0, "tag_count": 0, "coverage": 0.0},
            "similarities": {"pairs": 0, "chunks_with_pairs": 0, "coverage": 0.0},
            "domains": {"chunks_covered": 0, "domain_count": 0, "coverage": 0.0},
        }

    def _signal(table: str, chunk_col: str = "chunk_id",
                label_col: str | None = None) -> dict:
        if not _table_exists(conn, table):
            return {"chunks_covered": 0,
                    **({"count": 0} if not label_col else {f"{label_col}_count": 0}),
                    "coverage": 0.0}
        covered = conn.execute(
            f"SELECT count(DISTINCT t.{chunk_col}) FROM {table} t "
            f"JOIN chunks c ON c.chunk_id = t.{chunk_col} "
            f"WHERE c.status != 'superseded'"
        ).fetchone()[0]
        label_count = 0
        if label_col:
            label_count = conn.execute(
                f"SELECT count(DISTINCT {label_col}) FROM {table}"
            ).fetchone()[0]
        result = {
            "chunks_covered": covered,
            "coverage": round(covered / active, 4) if active else 0.0,
        }
        if label_col:
            result[f"{label_col}_count"] = label_count
        return result

    topics = _signal("chunk_topics", label_col="topic_label")
    clusters = _signal("chunk_clusters", label_col="cluster_label")
    tags = _signal("chunk_tags", label_col="tag")

    sim_pairs = 0
    sim_chunks = 0
    if _table_exists(conn, "chunk_similarities"):
        sim_pairs = _count(conn, "chunk_similarities")
        sim_chunks = conn.execute(
            "SELECT count(DISTINCT x.cid) FROM ("
            "  SELECT chunk_id_a AS cid FROM chunk_similarities "
            "  UNION SELECT chunk_id_b FROM chunk_similarities"
            ") x JOIN chunks c ON c.chunk_id = x.cid "
            "WHERE c.status != 'superseded'"
        ).fetchone()[0]

    domains = _signal("chunk_domains", label_col="domain")

    return {
        "active_chunks": active,
        "topics": topics,
        "clusters": clusters,
        "tags": tags,
        "similarities": {
            "pairs": sim_pairs,
            "chunks_with_pairs": sim_chunks,
            "coverage": round(sim_chunks / active, 4) if active else 0.0,
        },
        "domains": domains,
    }


# ── selftest ─────────────────────────────────────────────────────────


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        for sid, uri in [("s1", "https://a.com"), ("s2", "https://b.com")]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunk_rows = [
            ("c1", "s1", 0, "H1", "claim", "en", "alpha", "alpha", 1, "n1"),
            ("c2", "s1", 1, "H2", "claim", "en", "beta", "beta", 1, "n2"),
            ("c3", "s2", 0, "H3", "prose", "en", "gamma", "gamma", 1, "n3"),
            ("c4", "s1", 2, "H4", "claim", "en", "delta", "delta", 1, "n4"),
        ]
        for cr in chunk_rows:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (*cr, now),
            )

        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e1", "c1", "c2", "contradicts", "semantic", 0.9, now),
        )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("ci1", "c1", "https://ref.com", "primary", "p.5", 0),
        )

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c1", "ml", 0.9, now),
        )
        conn.commit()

        # 1: overview returns correct chunk counts
        ov = overview(conn)
        assert ov["chunks"]["total"] == 4
        assert ov["chunks"]["active"] == 4
        checks += 1

        # 2: by_kind breakdown
        assert "claim" in ov["chunks"]["by_kind"]
        assert ov["chunks"]["by_kind"]["claim"] == 3
        assert ov["chunks"]["by_kind"]["prose"] == 1
        checks += 1

        # 3: source counts
        assert ov["sources"]["total"] == 2
        assert ov["sources"]["live"] == 2
        checks += 1

        # 4: health edge stats
        h = health(conn)
        assert h["edges"]["total"] == 1
        assert h["edges"]["unresolved"] == 1
        assert h["edges"]["open_contradictions"] == 1
        checks += 1

        # 5: health citations and artifacts
        assert h["citations"] == 1
        assert h["artifacts"] == 0
        checks += 1

        # 6: orphan detection (c4 has no citations or edges)
        assert h["orphan_claim_chunks"] >= 1
        checks += 1

        # 7: signal coverage
        sig = signal_coverage(conn)
        assert sig["active_chunks"] == 4
        checks += 1

        # 8: tag coverage
        assert sig["tags"]["chunks_covered"] == 1
        assert sig["tags"]["coverage"] == 0.25
        checks += 1

        # 9: missing analytical tables handled
        assert sig["topics"]["chunks_covered"] == 0
        assert sig["clusters"]["chunks_covered"] == 0
        checks += 1

        # 10: JSON output for all
        _ = json.dumps(ov)
        _ = json.dumps(h)
        _ = json.dumps(sig)
        checks += 1

        # 11: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        ov2 = overview(conn2)
        assert ov2["chunks"]["total"] == 0
        h2 = health(conn2)
        assert h2["edges"]["total"] == 0
        sig2 = signal_coverage(conn2)
        assert sig2["active_chunks"] == 0
        checks += 1

        # 12: superseded chunks excluded from overview
        conn.execute(
            "UPDATE chunks SET status = 'superseded' WHERE chunk_id = 'c1'"
        )
        conn.commit()
        ov3 = overview(conn)
        assert ov3["chunks"]["active"] == 3
        assert ov3["chunks"]["superseded"] == 1
        checks += 1

        # 13: signal coverage updates with superseded
        sig3 = signal_coverage(conn)
        assert sig3["active_chunks"] == 3
        assert sig3["tags"]["chunks_covered"] == 0
        checks += 1

        # 14: edge types breakdown
        assert "contradicts" in h["edges"]["by_type"]
        assert h["edges"]["by_type"]["contradicts"] == 1
        checks += 1

    print(f"PASS dashboard selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Corpus dashboard: single-command overview"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ov = sub.add_parser("overview", help="Chunk and source counts")
    p_ov.add_argument("--db", default=DEFAULT_DB)
    p_ov.add_argument("--json", action="store_true")

    p_h = sub.add_parser("health", help="Edge, citation, and orphan stats")
    p_h.add_argument("--db", default=DEFAULT_DB)
    p_h.add_argument("--json", action="store_true")

    p_sig = sub.add_parser("signals",
                           help="Analytical signal coverage")
    p_sig.add_argument("--db", default=DEFAULT_DB)
    p_sig.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "overview":
        result = overview(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            c = result["chunks"]
            print(f"Chunks: {c['total']} total, {c['active']} active, "
                  f"{c['superseded']} superseded")
            print(f"  Accepted: {c['accepted']}, "
                  f"Quarantined: {c['quarantined']}")
            if c["by_kind"]:
                kinds = ", ".join(f"{k}: {v}"
                                 for k, v in sorted(c["by_kind"].items()))
                print(f"  By kind: {kinds}")
            s = result["sources"]
            print(f"Sources: {s['total']} total, {s['live']} live")

    elif args.cmd == "health":
        result = health(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            e = result["edges"]
            print(f"Edges: {e['total']} total, {e['unresolved']} unresolved")
            print(f"  Open contradictions: {e['open_contradictions']}")
            if e["by_type"]:
                types = ", ".join(f"{k}: {v}"
                                 for k, v in sorted(e["by_type"].items()))
                print(f"  By type: {types}")
            print(f"Citations: {result['citations']}")
            print(f"Artifacts: {result['artifacts']}")
            print(f"Orphan claim chunks: {result['orphan_claim_chunks']}")

    elif args.cmd == "signals":
        result = signal_coverage(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            a = result["active_chunks"]
            print(f"Active chunks: {a}")
            for name in ["topics", "clusters", "tags", "domains"]:
                sig = result[name]
                cov = sig["coverage"]
                covered = sig["chunks_covered"]
                print(f"  {name}: {covered}/{a} chunks "
                      f"({cov:.1%} coverage)")
            sim = result["similarities"]
            print(f"  similarities: {sim['pairs']} pairs, "
                  f"{sim['chunks_with_pairs']}/{a} chunks "
                  f"({sim['coverage']:.1%} coverage)")

    conn.close()


if __name__ == "__main__":
    main()
