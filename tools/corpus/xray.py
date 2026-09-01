#!/usr/bin/env python3
"""Corpus cross-table analysis: joins analytical tables to surface insights.

Joins chunk_clusters, chunk_topics, topic_terms, chunk_similarities,
and claim_edges against each other and against chunks to answer questions
no single-table tool can.

Usage:
    python tools/corpus/xray.py topic-clusters [--db PATH] [--topic N] [--json]
    python tools/corpus/xray.py cluster-health [--db PATH] [--cluster N] [--json]
    python tools/corpus/xray.py hotspots [--db PATH] [--top N] [--json]
    python tools/corpus/xray.py isolation [--db PATH] [--top N] [--json]
    python tools/corpus/xray.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _ensure_tables(conn):
    """Create analytical tables if they do not exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunk_clusters (
            chunk_id       TEXT NOT NULL REFERENCES chunks(chunk_id),
            cluster_label  INTEGER NOT NULL,
            top_terms      TEXT NOT NULL,
            clustered_utc  TEXT NOT NULL,
            PRIMARY KEY (chunk_id)
        );
        CREATE TABLE IF NOT EXISTS chunk_topics (
            chunk_id      TEXT NOT NULL REFERENCES chunks(chunk_id),
            topic_label   INTEGER NOT NULL,
            topic_weight  REAL NOT NULL,
            fitted_utc    TEXT NOT NULL,
            PRIMARY KEY (chunk_id)
        );
        CREATE TABLE IF NOT EXISTS topic_terms (
            topic_label   INTEGER NOT NULL,
            term_rank     INTEGER NOT NULL,
            term          TEXT NOT NULL,
            term_weight   REAL NOT NULL,
            fitted_utc    TEXT NOT NULL,
            PRIMARY KEY (topic_label, term_rank)
        );
        CREATE TABLE IF NOT EXISTS chunk_similarities (
            chunk_id_a     TEXT NOT NULL REFERENCES chunks(chunk_id),
            chunk_id_b     TEXT NOT NULL REFERENCES chunks(chunk_id),
            cosine_score   REAL NOT NULL,
            computed_utc   TEXT NOT NULL,
            PRIMARY KEY (chunk_id_a, chunk_id_b)
        );
    """)


def topic_clusters(conn, topic_label: int | None = None) -> list[dict]:
    """Show which clusters each topic spans, or drill into one topic."""
    _ensure_tables(conn)

    if topic_label is not None:
        rows = conn.execute("""
            SELECT cc.cluster_label, cc.top_terms, COUNT(*) as cnt
            FROM chunk_topics ct
            JOIN chunk_clusters cc ON cc.chunk_id = ct.chunk_id
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            WHERE ct.topic_label = ? AND c.status != 'superseded'
            GROUP BY cc.cluster_label, cc.top_terms
            ORDER BY cnt DESC
        """, (topic_label,)).fetchall()

        terms_rows = conn.execute(
            "SELECT term FROM topic_terms WHERE topic_label = ? "
            "ORDER BY term_rank LIMIT 5", (topic_label,)
        ).fetchall()
        topic_terms_list = [r[0] for r in terms_rows]

        total = conn.execute("""
            SELECT COUNT(*) FROM chunk_topics ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            WHERE ct.topic_label = ? AND c.status != 'superseded'
        """, (topic_label,)).fetchone()[0]

        clusters = [
            {"cluster_label": r[0], "top_terms": r[1], "chunk_count": r[2]}
            for r in rows
        ]
        return [{
            "topic_label": topic_label,
            "topic_terms": topic_terms_list,
            "total_chunks": total,
            "cluster_count": len(clusters),
            "clusters": clusters,
        }]

    rows = conn.execute("""
        SELECT ct.topic_label, cc.cluster_label, COUNT(*) as cnt
        FROM chunk_topics ct
        JOIN chunk_clusters cc ON cc.chunk_id = ct.chunk_id
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        WHERE c.status != 'superseded'
        GROUP BY ct.topic_label, cc.cluster_label
        ORDER BY ct.topic_label, cnt DESC
    """).fetchall()

    if not rows:
        return []

    by_topic: dict[int, list[dict]] = {}
    for tl, cl, cnt in rows:
        by_topic.setdefault(tl, []).append(
            {"cluster_label": cl, "chunk_count": cnt}
        )

    results = []
    for tl, clusters in sorted(by_topic.items()):
        total = sum(c["chunk_count"] for c in clusters)
        results.append({
            "topic_label": tl,
            "total_chunks": total,
            "cluster_count": len(clusters),
            "spread": round(len(clusters) / max(total, 1), 4),
        })

    results.sort(key=lambda r: r["spread"], reverse=True)
    return results


def cluster_health(conn, cluster_label: int | None = None) -> list[dict]:
    """Measure contradiction density, citation density, and similarity within clusters."""
    _ensure_tables(conn)

    if cluster_label is not None:
        labels = [cluster_label]
    else:
        label_rows = conn.execute("""
            SELECT DISTINCT cc.cluster_label
            FROM chunk_clusters cc
            JOIN chunks c ON c.chunk_id = cc.chunk_id
            WHERE c.status != 'superseded'
            ORDER BY cc.cluster_label
        """).fetchall()
        labels = [r[0] for r in label_rows]

    if not labels:
        return []

    results = []
    for lab in labels:
        chunk_ids = conn.execute("""
            SELECT cc.chunk_id FROM chunk_clusters cc
            JOIN chunks c ON c.chunk_id = cc.chunk_id
            WHERE cc.cluster_label = ? AND c.status != 'superseded'
        """, (lab,)).fetchall()
        cids = [r[0] for r in chunk_ids]
        n = len(cids)
        if n == 0:
            continue

        placeholders = ",".join("?" * n)

        contradiction_count = conn.execute(f"""
            SELECT COUNT(*) FROM claim_edges
            WHERE edge_type = 'contradicts' AND resolution IS NULL
            AND source_chunk IN ({placeholders})
            AND target_chunk IN ({placeholders})
        """, cids + cids).fetchone()[0]

        edge_count = conn.execute(f"""
            SELECT COUNT(*) FROM claim_edges
            WHERE resolution IS NULL
            AND (source_chunk IN ({placeholders})
                 OR target_chunk IN ({placeholders}))
        """, cids + cids).fetchone()[0]

        sim_row = conn.execute(f"""
            SELECT AVG(cosine_score), MIN(cosine_score), MAX(cosine_score)
            FROM chunk_similarities
            WHERE chunk_id_a IN ({placeholders})
            AND chunk_id_b IN ({placeholders})
        """, cids + cids).fetchone()

        avg_sim = round(sim_row[0], 4) if sim_row[0] is not None else None
        min_sim = round(sim_row[1], 4) if sim_row[1] is not None else None
        max_sim = round(sim_row[2], 4) if sim_row[2] is not None else None

        top_terms_row = conn.execute(
            "SELECT top_terms FROM chunk_clusters WHERE cluster_label = ? LIMIT 1",
            (lab,)
        ).fetchone()

        results.append({
            "cluster_label": lab,
            "top_terms": top_terms_row[0] if top_terms_row else "",
            "chunk_count": n,
            "contradiction_count": contradiction_count,
            "contradiction_density": round(contradiction_count / n, 4),
            "edge_count": edge_count,
            "avg_similarity": avg_sim,
            "min_similarity": min_sim,
            "max_similarity": max_sim,
        })

    results.sort(key=lambda r: r["contradiction_density"], reverse=True)
    return results


def hotspots(conn, top_n: int = 10) -> list[dict]:
    """Rank topics by open-contradiction density within their chunks."""
    _ensure_tables(conn)

    topic_rows = conn.execute("""
        SELECT DISTINCT ct.topic_label FROM chunk_topics ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        WHERE c.status != 'superseded'
    """).fetchall()

    if not topic_rows:
        return []

    results = []
    for (tl,) in topic_rows:
        chunk_ids = conn.execute("""
            SELECT ct.chunk_id FROM chunk_topics ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            WHERE ct.topic_label = ? AND c.status != 'superseded'
        """, (tl,)).fetchall()
        cids = [r[0] for r in chunk_ids]
        n = len(cids)
        if n == 0:
            continue

        placeholders = ",".join("?" * n)

        contras = conn.execute(f"""
            SELECT COUNT(*) FROM claim_edges
            WHERE edge_type = 'contradicts' AND resolution IS NULL
            AND source_chunk IN ({placeholders})
        """, cids).fetchone()[0]

        terms_rows = conn.execute(
            "SELECT term FROM topic_terms WHERE topic_label = ? "
            "ORDER BY term_rank LIMIT 5", (tl,)
        ).fetchall()
        terms = [r[0] for r in terms_rows]

        results.append({
            "topic_label": tl,
            "topic_terms": terms,
            "chunk_count": n,
            "contradiction_count": contras,
            "contradiction_density": round(contras / n, 4),
        })

    results.sort(key=lambda r: r["contradiction_density"], reverse=True)
    return results[:top_n]


def isolation(conn, top_n: int = 20) -> list[dict]:
    """Find chunks with low similarity and small/singleton topics."""
    _ensure_tables(conn)

    rows = conn.execute("""
        SELECT c.chunk_id, c.kind, c.word_count, c.heading_path,
               ct.topic_label, ct.topic_weight
        FROM chunks c
        JOIN chunk_topics ct ON ct.chunk_id = c.chunk_id
        WHERE c.status != 'superseded'
    """).fetchall()

    if not rows:
        return []

    topic_sizes: dict[int, int] = {}
    for r in rows:
        topic_sizes[r[4]] = topic_sizes.get(r[4], 0) + 1

    results = []
    for r in rows:
        chunk_id = r[0]

        max_sim_row = conn.execute("""
            SELECT MAX(cosine_score) FROM chunk_similarities
            WHERE chunk_id_a = ? OR chunk_id_b = ?
        """, (chunk_id, chunk_id)).fetchone()
        max_sim = max_sim_row[0] if max_sim_row and max_sim_row[0] is not None else 0.0

        topic_size = topic_sizes[r[4]]

        results.append({
            "chunk_id": chunk_id,
            "kind": r[1],
            "word_count": r[2],
            "heading": r[3],
            "topic_label": r[4],
            "topic_weight": round(r[5], 4),
            "topic_size": topic_size,
            "max_similarity": round(max_sim, 4),
            "isolation_score": round((1.0 - max_sim) / max(topic_size, 1), 4),
        })

    results.sort(key=lambda r: r["isolation_score"], reverse=True)
    return results[:top_n]


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)
        _ensure_tables(conn)

        now = "2026-08-31T00:00:00Z"

        conn.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, publisher, published_utc, "
            " fetched_utc, upstream_rev, upstream_mtime, liveness, "
            " content_sha256, bytes, supersedes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Test Doc",
             "CC-BY-4.0", "vendor", "LICENSE", "test", None,
             now, None, None, "live", _sha256("a"), 100, None),
        )

        test_chunks = [
            ("c1", 0, "claim", "Database Guide",
             "sqlite provides sql query capabilities with schema"),
            ("c2", 1, "claim", "Database Perf",
             "database indexing improves query performance significantly"),
            ("c3", 2, "claim", "Testing Guide",
             "pytest framework provides fixtures and assertions"),
            ("c4", 3, "claim", "Testing Claim",
             "test driven development improves code quality always"),
            ("c5", 4, "prose", "Security Guide",
             "authentication and authorization protect api endpoints"),
            ("c6", 5, "claim", "Security Claim",
             "encryption ensures data confidentiality at rest"),
        ]

        for cid, ordinal, kind, heading, text in test_chunks:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " citation_count, status, status_reason, ingested_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "src1", ordinal, heading, kind, None,
                 text, text, len(text.split()), _sha256(text),
                 0, 0, "accepted", None, now),
            )

        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c1", 0, 0.8, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c2", 0, 0.7, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c3", 1, 0.9, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c4", 1, 0.6, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c5", 2, 0.5, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c6", 2, 0.4, now))

        for rank, (term, weight) in enumerate([
            ("sqlite", 0.5), ("query", 0.4), ("schema", 0.3),
            ("database", 0.2), ("index", 0.1),
        ]):
            conn.execute(
                "INSERT INTO topic_terms VALUES (?,?,?,?,?)",
                (0, rank, term, weight, now))
        for rank, (term, weight) in enumerate([
            ("pytest", 0.5), ("test", 0.4), ("fixture", 0.3),
            ("assert", 0.2), ("coverage", 0.1),
        ]):
            conn.execute(
                "INSERT INTO topic_terms VALUES (?,?,?,?,?)",
                (1, rank, term, weight, now))
        for rank, (term, weight) in enumerate([
            ("auth", 0.5), ("encrypt", 0.4), ("api", 0.3),
        ]):
            conn.execute(
                "INSERT INTO topic_terms VALUES (?,?,?,?,?)",
                (2, rank, term, weight, now))

        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c1", 0, "sqlite, query", now))
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c2", 0, "sqlite, query", now))
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c3", 1, "pytest, test", now))
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c4", 1, "pytest, test", now))
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c5", 2, "auth, encrypt", now))
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c6", 0, "sqlite, query", now))

        conn.execute(
            "INSERT INTO chunk_similarities VALUES (?,?,?,?)",
            ("c1", "c2", 0.85, now))
        conn.execute(
            "INSERT INTO chunk_similarities VALUES (?,?,?,?)",
            ("c3", "c4", 0.72, now))
        conn.execute(
            "INSERT INTO chunk_similarities VALUES (?,?,?,?)",
            ("c5", "c6", 0.30, now))

        conn.execute(
            "INSERT INTO claim_edges "
            "(edge_id, source_chunk, target_chunk, edge_type, basis, "
            " confidence, detected_utc, resolution, resolved_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (_sha256("e1"), "c1", "c2", "contradicts", "numeric",
             0.8, now, None, None))
        conn.execute(
            "INSERT INTO claim_edges "
            "(edge_id, source_chunk, target_chunk, edge_type, basis, "
            " confidence, detected_utc, resolution, resolved_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (_sha256("e2"), "c3", "c4", "supports", "negation",
             0.9, now, None, None))
        conn.execute(
            "INSERT INTO claim_edges "
            "(edge_id, source_chunk, target_chunk, edge_type, basis, "
            " confidence, detected_utc, resolution, resolved_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (_sha256("e3"), "c5", "c6", "contradicts", "recommendation",
             0.7, now, None, None))

        conn.commit()

        # Check 1: topic_clusters returns all topics
        tc = topic_clusters(conn)
        assert len(tc) == 3, f"expected 3 topics, got {len(tc)}"
        checks += 1

        # Check 2: each topic has spread > 0
        for t in tc:
            assert t["spread"] > 0
            assert t["cluster_count"] >= 1
        checks += 1

        # Check 3: topic 2 spans two clusters (c5 in cluster 2, c6 in cluster 0)
        tc_detail = topic_clusters(conn, topic_label=2)
        assert len(tc_detail) == 1
        assert tc_detail[0]["cluster_count"] == 2
        assert tc_detail[0]["total_chunks"] == 2
        checks += 1

        # Check 4: topic_clusters with topic_label returns topic_terms
        assert len(tc_detail[0]["topic_terms"]) == 3
        assert "auth" in tc_detail[0]["topic_terms"]
        checks += 1

        # Check 5: cluster_health returns all clusters
        ch = cluster_health(conn)
        assert len(ch) == 3
        checks += 1

        # Check 6: cluster 0 has a contradiction (c1 vs c2)
        cl0 = next(c for c in ch if c["cluster_label"] == 0)
        assert cl0["contradiction_count"] >= 1
        assert cl0["chunk_count"] == 3
        checks += 1

        # Check 7: cluster 0 has similarity data
        assert cl0["avg_similarity"] is not None
        assert cl0["avg_similarity"] > 0
        checks += 1

        # Check 8: single cluster query works
        ch_single = cluster_health(conn, cluster_label=1)
        assert len(ch_single) == 1
        assert ch_single[0]["cluster_label"] == 1
        checks += 1

        # Check 9: hotspots returns ranked results
        hs = hotspots(conn)
        assert len(hs) > 0
        checks += 1

        # Check 10: hotspots sorted by contradiction_density descending
        densities = [h["contradiction_density"] for h in hs]
        for i in range(len(densities) - 1):
            assert densities[i] >= densities[i + 1]
        checks += 1

        # Check 11: topic 0 has contradiction density > 0
        t0 = next(h for h in hs if h["topic_label"] == 0)
        assert t0["contradiction_count"] >= 1
        assert t0["contradiction_density"] > 0
        checks += 1

        # Check 12: isolation returns results
        iso = isolation(conn)
        assert len(iso) > 0
        checks += 1

        # Check 13: isolation scores are bounded [0, 1]
        for item in iso:
            assert 0 <= item["isolation_score"] <= 1.0
            assert 0 <= item["max_similarity"] <= 1.0
        checks += 1

        # Check 14: empty corpus returns empty
        empty_dir = Path(td) / "empty"
        empty_dir.mkdir()
        ec = connect(str(empty_dir / "e.db"))
        init_schema(ec)
        _ensure_tables(ec)
        assert topic_clusters(ec) == []
        assert cluster_health(ec) == []
        assert hotspots(ec) == []
        assert isolation(ec) == []
        ec.close()
        checks += 1

        conn.close()

    print(f"PASS xray selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus cross-table analysis")
    sub = parser.add_subparsers(dest="cmd")

    p_tc = sub.add_parser("topic-clusters",
                          help="Which clusters each topic spans")
    p_tc.add_argument("--db", default=str(DEFAULT_DB))
    p_tc.add_argument("--topic", type=int, default=None)
    p_tc.add_argument("--json", action="store_true")

    p_ch = sub.add_parser("cluster-health",
                          help="Contradiction and similarity within clusters")
    p_ch.add_argument("--db", default=str(DEFAULT_DB))
    p_ch.add_argument("--cluster", type=int, default=None)
    p_ch.add_argument("--json", action="store_true")

    p_hs = sub.add_parser("hotspots",
                          help="Topics ranked by contradiction density")
    p_hs.add_argument("--db", default=str(DEFAULT_DB))
    p_hs.add_argument("--top", type=int, default=10)
    p_hs.add_argument("--json", action="store_true")

    p_iso = sub.add_parser("isolation",
                           help="Chunks with low similarity and small topics")
    p_iso.add_argument("--db", default=str(DEFAULT_DB))
    p_iso.add_argument("--top", type=int, default=20)
    p_iso.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "topic-clusters":
        conn = connect(args.db)
        results = topic_clusters(conn, topic_label=args.topic)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No topic-cluster data")
        else:
            for r in results:
                if "clusters" in r:
                    terms = ", ".join(r.get("topic_terms", []))
                    print(f"  Topic {r['topic_label']} ({terms}): "
                          f"{r['total_chunks']} chunks across "
                          f"{r['cluster_count']} clusters")
                    for cl in r["clusters"]:
                        print(f"    cluster {cl['cluster_label']}: "
                              f"{cl['chunk_count']} chunks "
                              f"({cl.get('top_terms', '')})")
                else:
                    print(f"  Topic {r['topic_label']}: "
                          f"{r['total_chunks']} chunks, "
                          f"{r['cluster_count']} clusters, "
                          f"spread={r['spread']:.2f}")
        conn.close()

    elif args.cmd == "cluster-health":
        conn = connect(args.db)
        results = cluster_health(conn, cluster_label=args.cluster)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No cluster data")
        else:
            for r in results:
                sim = (f"sim={r['avg_similarity']:.2f}"
                       if r["avg_similarity"] is not None else "no sim")
                print(f"  Cluster {r['cluster_label']} "
                      f"({r['top_terms']}): "
                      f"{r['chunk_count']} chunks, "
                      f"{r['contradiction_count']} contradictions, "
                      f"{sim}")
        conn.close()

    elif args.cmd == "hotspots":
        conn = connect(args.db)
        results = hotspots(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No hotspots found")
        else:
            for r in results:
                terms = ", ".join(r.get("topic_terms", []))
                print(f"  Topic {r['topic_label']} ({terms}): "
                      f"{r['contradiction_count']} contradictions / "
                      f"{r['chunk_count']} chunks = "
                      f"{r['contradiction_density']:.2f}")
        conn.close()

    elif args.cmd == "isolation":
        conn = connect(args.db)
        results = isolation(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No isolated chunks found")
        else:
            for r in results:
                print(f"  {r['chunk_id']} ({r['kind']}): "
                      f"isolation={r['isolation_score']:.3f}, "
                      f"max_sim={r['max_similarity']:.2f}, "
                      f"topic_size={r['topic_size']}")
        conn.close()


if __name__ == "__main__":
    main()
