#!/usr/bin/env python3
"""Similarity analysis: chunk relatedness patterns and outlier review.

Analyses chunk_similarities, chunk_outliers, and chunk_clusters to
report similarity distribution, closest pairs, outlier characteristics,
and cluster cohesion.

Usage:
    python tools/corpus/similarity_analysis.py distribution [--db PATH] [--json]
    python tools/corpus/similarity_analysis.py closest [--db PATH] [--top N] [--json]
    python tools/corpus/similarity_analysis.py outliers [--db PATH] [--json]
    python tools/corpus/similarity_analysis.py cluster-cohesion [--db PATH] [--json]
    python tools/corpus/similarity_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
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


def similarity_distribution(conn) -> dict:
    """Distribution of cosine similarity scores across all chunk pairs."""
    if not _table_exists(conn, "chunk_similarities"):
        return {"total_pairs": 0, "avg_score": 0.0,
                "min_score": 0.0, "max_score": 0.0, "bands": []}

    stats = conn.execute(
        "SELECT count(*), round(avg(cosine_score), 4), "
        "round(min(cosine_score), 4), round(max(cosine_score), 4) "
        "FROM chunk_similarities"
    ).fetchone()

    total = stats[0]
    if total == 0:
        return {"total_pairs": 0, "avg_score": 0.0,
                "min_score": 0.0, "max_score": 0.0, "bands": []}

    band_defs = [
        ("0.0-0.2", 0.0, 0.2),
        ("0.2-0.4", 0.2, 0.4),
        ("0.4-0.6", 0.4, 0.6),
        ("0.6-0.8", 0.6, 0.8),
        ("0.8-1.0", 0.8, 1.01),
    ]

    bands = []
    for label, lo, hi in band_defs:
        count = conn.execute(
            "SELECT count(*) FROM chunk_similarities "
            "WHERE cosine_score >= ? AND cosine_score < ?",
            (lo, hi),
        ).fetchone()[0]
        bands.append({"band": label, "count": count})

    return {
        "total_pairs": total,
        "avg_score": stats[1],
        "min_score": stats[2],
        "max_score": stats[3],
        "bands": bands,
    }


def closest_pairs(conn, top_n: int = 20) -> list[dict]:
    """Most similar chunk pairs, ranked by cosine score descending."""
    if not _table_exists(conn, "chunk_similarities"):
        return []

    rows = conn.execute(
        "SELECT cs.chunk_id_a, cs.chunk_id_b, cs.cosine_score, "
        "ca.kind AS kind_a, cb.kind AS kind_b, "
        "ca.source_id AS source_a, cb.source_id AS source_b "
        "FROM chunk_similarities cs "
        "JOIN chunks ca ON ca.chunk_id = cs.chunk_id_a "
        "JOIN chunks cb ON cb.chunk_id = cs.chunk_id_b "
        "ORDER BY cs.cosine_score DESC "
        "LIMIT ?",
        (top_n,),
    ).fetchall()

    return [
        {"chunk_id_a": r[0], "chunk_id_b": r[1],
         "cosine_score": r[2], "kind_a": r[3], "kind_b": r[4],
         "source_a": r[5], "source_b": r[6],
         "cross_source": r[5] != r[6]}
        for r in rows
    ]


def outlier_report(conn) -> dict:
    """Outlier chunk analysis with source and kind distribution."""
    if not _table_exists(conn, "chunk_outliers"):
        return {"total_outliers": 0, "avg_max_similarity": 0.0,
                "by_kind": {}, "outliers": []}

    total = conn.execute(
        "SELECT count(*) FROM chunk_outliers"
    ).fetchone()[0]

    if total == 0:
        return {"total_outliers": 0, "avg_max_similarity": 0.0,
                "by_kind": {}, "outliers": []}

    avg_sim = conn.execute(
        "SELECT round(avg(max_similarity), 4) FROM chunk_outliers"
    ).fetchone()[0]

    kind_rows = conn.execute(
        "SELECT c.kind, count(*) AS cnt "
        "FROM chunk_outliers co "
        "JOIN chunks c ON c.chunk_id = co.chunk_id "
        "GROUP BY c.kind ORDER BY cnt DESC"
    ).fetchall()

    by_kind = {r[0]: r[1] for r in kind_rows}

    rows = conn.execute(
        "SELECT co.chunk_id, co.max_similarity, co.threshold_used, "
        "c.kind, c.source_id, c.heading_path "
        "FROM chunk_outliers co "
        "JOIN chunks c ON c.chunk_id = co.chunk_id "
        "ORDER BY co.max_similarity ASC "
        "LIMIT 50"
    ).fetchall()

    outliers = [
        {"chunk_id": r[0], "max_similarity": r[1],
         "threshold_used": r[2], "kind": r[3],
         "source_id": r[4], "heading_path": r[5]}
        for r in rows
    ]

    return {
        "total_outliers": total,
        "avg_max_similarity": avg_sim,
        "by_kind": by_kind,
        "outliers": outliers,
    }


def cluster_cohesion(conn) -> list[dict]:
    """Per-cluster cohesion based on intra-cluster similarity scores."""
    if not _table_exists(conn, "chunk_clusters"):
        return []
    if not _table_exists(conn, "chunk_similarities"):
        return []

    clusters = conn.execute(
        "SELECT cluster_label, count(*) AS size "
        "FROM chunk_clusters "
        "GROUP BY cluster_label "
        "ORDER BY size DESC"
    ).fetchall()

    result = []
    for cl_label, cl_size in clusters:
        if cl_size < 2:
            result.append({
                "cluster_label": cl_label, "size": cl_size,
                "avg_intra_similarity": None, "pair_count": 0,
            })
            continue

        row = conn.execute(
            "SELECT round(avg(cs.cosine_score), 4), count(*) "
            "FROM chunk_similarities cs "
            "JOIN chunk_clusters cca ON cca.chunk_id = cs.chunk_id_a "
            "JOIN chunk_clusters ccb ON ccb.chunk_id = cs.chunk_id_b "
            "WHERE cca.cluster_label = ? AND ccb.cluster_label = ?",
            (cl_label, cl_label),
        ).fetchone()

        result.append({
            "cluster_label": cl_label, "size": cl_size,
            "avg_intra_similarity": row[0], "pair_count": row[1],
        })

    return result


# -- selftest ----------------------------------------------------------------


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

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(1, 5):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (f"c{i}", "s1", i - 1, f"H{i}",
                 "claim" if i <= 3 else "prose", "en",
                 f"text{i}", f"text{i}", 10 * i, f"n{i}", now),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_similarities ("
            "  chunk_id_a TEXT NOT NULL, chunk_id_b TEXT NOT NULL, "
            "  cosine_score REAL NOT NULL, computed_utc TEXT NOT NULL, "
            "  PRIMARY KEY (chunk_id_a, chunk_id_b))"
        )

        sim_data = [
            ("c1", "c2", 0.92, now),
            ("c1", "c3", 0.45, now),
            ("c2", "c3", 0.55, now),
            ("c1", "c4", 0.15, now),
            ("c3", "c4", 0.35, now),
        ]
        for sd in sim_data:
            conn.execute(
                "INSERT INTO chunk_similarities "
                "(chunk_id_a, chunk_id_b, cosine_score, computed_utc) "
                "VALUES (?, ?, ?, ?)", sd,
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_outliers ("
            "  chunk_id TEXT PRIMARY KEY, max_similarity REAL NOT NULL, "
            "  threshold_used REAL NOT NULL, detected_utc TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO chunk_outliers VALUES (?, ?, ?, ?)",
            ("c4", 0.35, 0.4, now),
        )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_clusters ("
            "  chunk_id TEXT PRIMARY KEY, cluster_label INTEGER NOT NULL, "
            "  top_terms TEXT, clustered_utc TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?, ?, ?, ?)",
            ("c1", 0, "ml,neural", now),
        )
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?, ?, ?, ?)",
            ("c2", 0, "ml,neural", now),
        )
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?, ?, ?, ?)",
            ("c3", 1, "systems,db", now),
        )
        conn.commit()

        # 1: similarity distribution totals
        dist = similarity_distribution(conn)
        assert dist["total_pairs"] == 5
        checks += 1

        # 2: score stats
        assert dist["min_score"] == 0.15
        assert dist["max_score"] == 0.92
        checks += 1

        # 3: band distribution
        band_map = {b["band"]: b["count"] for b in dist["bands"]}
        assert band_map["0.0-0.2"] == 1
        assert band_map["0.8-1.0"] == 1
        checks += 1

        # 4: closest pairs ordering
        cp = closest_pairs(conn, top_n=10)
        assert cp[0]["cosine_score"] == 0.92
        assert cp[0]["chunk_id_a"] == "c1"
        assert cp[0]["chunk_id_b"] == "c2"
        checks += 1

        # 5: cross_source flag
        assert cp[0]["cross_source"] is False
        checks += 1

        # 6: top_n limit
        cp2 = closest_pairs(conn, top_n=1)
        assert len(cp2) == 1
        checks += 1

        # 7: outlier report
        orep = outlier_report(conn)
        assert orep["total_outliers"] == 1
        assert orep["outliers"][0]["chunk_id"] == "c4"
        checks += 1

        # 8: outlier kind distribution
        assert orep["by_kind"]["prose"] == 1
        checks += 1

        # 9: outlier max similarity
        assert orep["avg_max_similarity"] == 0.35
        checks += 1

        # 10: cluster cohesion
        cc = cluster_cohesion(conn)
        assert len(cc) == 2
        checks += 1

        # 11: cluster 0 has intra-similarity from c1-c2 pair
        cl0 = [c for c in cc if c["cluster_label"] == 0][0]
        assert cl0["size"] == 2
        assert cl0["pair_count"] == 1
        assert cl0["avg_intra_similarity"] == 0.92
        checks += 1

        # 12: cluster 1 (single member) has no pairs
        cl1 = [c for c in cc if c["cluster_label"] == 1][0]
        assert cl1["size"] == 1
        assert cl1["pair_count"] == 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dist)
        _ = json.dumps(cp)
        _ = json.dumps(orep)
        _ = json.dumps(cc)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert similarity_distribution(conn2)["total_pairs"] == 0
        assert closest_pairs(conn2) == []
        assert outlier_report(conn2)["total_outliers"] == 0
        assert cluster_cohesion(conn2) == []
        checks += 1

    print(f"PASS similarity_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Similarity analysis: chunk relatedness patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dist = sub.add_parser("distribution",
                            help="Similarity score distribution")
    p_dist.add_argument("--db", default=DEFAULT_DB)
    p_dist.add_argument("--json", action="store_true")

    p_cp = sub.add_parser("closest",
                          help="Most similar chunk pairs")
    p_cp.add_argument("--db", default=DEFAULT_DB)
    p_cp.add_argument("--top", type=int, default=20)
    p_cp.add_argument("--json", action="store_true")

    p_out = sub.add_parser("outliers",
                           help="Outlier chunk analysis")
    p_out.add_argument("--db", default=DEFAULT_DB)
    p_out.add_argument("--json", action="store_true")

    p_cc = sub.add_parser("cluster-cohesion",
                          help="Per-cluster cohesion scores")
    p_cc.add_argument("--db", default=DEFAULT_DB)
    p_cc.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "distribution":
        result = similarity_distribution(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Similarity pairs: {result['total_pairs']}, "
                  f"avg {result['avg_score']:.3f} "
                  f"(range {result['min_score']:.3f}-"
                  f"{result['max_score']:.3f})")
            for b in result["bands"]:
                print(f"  {b['band']}: {b['count']} pairs")

    elif args.cmd == "closest":
        result = closest_pairs(conn, top_n=args.top)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Closest pairs: {len(result)}")
            for r in result:
                cross = " [cross-source]" if r["cross_source"] else ""
                print(f"  {r['chunk_id_a']} <-> {r['chunk_id_b']}: "
                      f"{r['cosine_score']:.3f}{cross}")

    elif args.cmd == "outliers":
        result = outlier_report(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Outliers: {result['total_outliers']} "
                  f"(avg max sim {result['avg_max_similarity']:.3f})")
            for k, v in result["by_kind"].items():
                print(f"  {k}: {v}")
            for o in result["outliers"]:
                print(f"  {o['chunk_id']}: max_sim {o['max_similarity']:.3f} "
                      f"({o['kind']})")

    elif args.cmd == "cluster-cohesion":
        result = cluster_cohesion(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Clusters: {len(result)}")
            for c in result:
                sim = (f"{c['avg_intra_similarity']:.3f}"
                       if c["avg_intra_similarity"] is not None
                       else "n/a")
                print(f"  cluster {c['cluster_label']}: "
                      f"size {c['size']}, cohesion {sim} "
                      f"({c['pair_count']} pairs)")

    conn.close()


if __name__ == "__main__":
    main()
