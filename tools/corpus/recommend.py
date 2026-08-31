#!/usr/bin/env python3
"""Corpus chunk recommender: find related chunks by multi-signal relevance.

Given a chunk, ranks all other active chunks by a weighted combination
of topic overlap, cluster co-membership, cosine similarity, shared tags,
and citation links.  Surfaces the most related content across all
available analytical signals.

Usage:
    python tools/corpus/recommend.py related --chunk-id CID [--db PATH] [--top N] [--json]
    python tools/corpus/recommend.py explain --chunk-id CID --target TID [--db PATH] [--json]
    python tools/corpus/recommend.py selftest
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
        CREATE TABLE IF NOT EXISTS chunk_similarities (
            chunk_id_a     TEXT NOT NULL REFERENCES chunks(chunk_id),
            chunk_id_b     TEXT NOT NULL REFERENCES chunks(chunk_id),
            cosine_score   REAL NOT NULL,
            computed_utc   TEXT NOT NULL,
            PRIMARY KEY (chunk_id_a, chunk_id_b)
        );
        CREATE TABLE IF NOT EXISTS chunk_tags (
            chunk_id  TEXT NOT NULL REFERENCES chunks(chunk_id),
            tag       TEXT NOT NULL,
            score     REAL NOT NULL,
            tagged_utc TEXT NOT NULL,
            PRIMARY KEY (chunk_id, tag)
        );
    """)


def _chunk_signals(conn, chunk_id: str) -> dict | None:
    """Gather all analytical signals for a chunk."""
    row = conn.execute(
        "SELECT chunk_id, kind, heading_path FROM chunks "
        "WHERE chunk_id = ? AND status != 'superseded'",
        (chunk_id,),
    ).fetchone()
    if not row:
        return None

    topic_row = conn.execute(
        "SELECT topic_label FROM chunk_topics WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchone()

    cluster_row = conn.execute(
        "SELECT cluster_label FROM chunk_clusters WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchone()

    tags = conn.execute(
        "SELECT tag FROM chunk_tags WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchall()

    return {
        "chunk_id": chunk_id,
        "kind": row[1],
        "heading": row[2],
        "topic_label": topic_row[0] if topic_row else None,
        "cluster_label": cluster_row[0] if cluster_row else None,
        "tags": {r[0] for r in tags},
    }


def _score_pair(conn, source_signals: dict, target_id: str) -> dict:
    """Score relatedness between source chunk and a target chunk."""
    scores = {}

    t_topic = conn.execute(
        "SELECT topic_label FROM chunk_topics WHERE chunk_id = ?",
        (target_id,),
    ).fetchone()
    t_cluster = conn.execute(
        "SELECT cluster_label FROM chunk_clusters WHERE chunk_id = ?",
        (target_id,),
    ).fetchone()
    t_tags = conn.execute(
        "SELECT tag FROM chunk_tags WHERE chunk_id = ?",
        (target_id,),
    ).fetchall()
    t_tag_set = {r[0] for r in t_tags}

    if source_signals["topic_label"] is not None and t_topic is not None:
        scores["topic"] = 1.0 if source_signals["topic_label"] == t_topic[0] else 0.0
    else:
        scores["topic"] = 0.0

    if source_signals["cluster_label"] is not None and t_cluster is not None:
        scores["cluster"] = 1.0 if source_signals["cluster_label"] == t_cluster[0] else 0.0
    else:
        scores["cluster"] = 0.0

    src_tags = source_signals["tags"]
    if src_tags and t_tag_set:
        overlap = len(src_tags & t_tag_set)
        union = len(src_tags | t_tag_set)
        scores["tags"] = overlap / union if union else 0.0
    else:
        scores["tags"] = 0.0

    sim_row = conn.execute("""
        SELECT cosine_score FROM chunk_similarities
        WHERE (chunk_id_a = ? AND chunk_id_b = ?)
        OR (chunk_id_a = ? AND chunk_id_b = ?)
    """, (source_signals["chunk_id"], target_id,
          target_id, source_signals["chunk_id"])).fetchone()
    scores["similarity"] = sim_row[0] if sim_row else 0.0

    edge_row = conn.execute("""
        SELECT COUNT(*) FROM claim_edges
        WHERE resolution IS NULL
        AND ((source_chunk = ? AND target_chunk = ?)
             OR (source_chunk = ? AND target_chunk = ?))
    """, (source_signals["chunk_id"], target_id,
          target_id, source_signals["chunk_id"])).fetchone()
    scores["citation"] = min(1.0, (edge_row[0] if edge_row else 0) * 0.5)

    composite = round(
        scores["topic"] * 0.25
        + scores["cluster"] * 0.20
        + scores["similarity"] * 0.25
        + scores["tags"] * 0.15
        + scores["citation"] * 0.15,
        4,
    )

    return {
        "signals": {k: round(v, 4) for k, v in scores.items()},
        "composite": composite,
    }


def related_chunks(conn, chunk_id: str, top_n: int = 10) -> dict:
    """Find the most related chunks to a given chunk."""
    _ensure_tables(conn)

    signals = _chunk_signals(conn, chunk_id)
    if signals is None:
        return {"chunk_id": chunk_id, "found": False, "related": []}

    candidates = conn.execute(
        "SELECT chunk_id, kind, heading_path, word_count "
        "FROM chunks WHERE chunk_id != ? AND status != 'superseded'",
        (chunk_id,),
    ).fetchall()

    results = []
    for row in candidates:
        tid = row[0]
        pair_score = _score_pair(conn, signals, tid)
        if pair_score["composite"] > 0:
            results.append({
                "chunk_id": tid,
                "kind": row[1],
                "heading": row[2],
                "word_count": row[3],
                **pair_score,
            })

    results.sort(key=lambda r: r["composite"], reverse=True)

    return {
        "chunk_id": chunk_id,
        "found": True,
        "kind": signals["kind"],
        "heading": signals["heading"],
        "related": results[:top_n],
    }


def explain_relation(conn, chunk_id: str, target_id: str) -> dict:
    """Explain the relationship between two specific chunks."""
    _ensure_tables(conn)

    signals = _chunk_signals(conn, chunk_id)
    if signals is None:
        return {"chunk_id": chunk_id, "found": False}

    target_row = conn.execute(
        "SELECT chunk_id, kind, heading_path FROM chunks "
        "WHERE chunk_id = ? AND status != 'superseded'",
        (target_id,),
    ).fetchone()
    if not target_row:
        return {"chunk_id": chunk_id, "target_id": target_id,
                "target_found": False}

    pair_score = _score_pair(conn, signals, target_id)

    edges = conn.execute("""
        SELECT edge_type, confidence, basis FROM claim_edges
        WHERE resolution IS NULL
        AND ((source_chunk = ? AND target_chunk = ?)
             OR (source_chunk = ? AND target_chunk = ?))
    """, (chunk_id, target_id, target_id, chunk_id)).fetchall()

    return {
        "chunk_id": chunk_id,
        "target_id": target_id,
        "source_heading": signals["heading"],
        "target_heading": target_row[2],
        "source_kind": signals["kind"],
        "target_kind": target_row[1],
        **pair_score,
        "edges": [
            {"edge_type": e[0], "confidence": round(e[1], 4), "basis": e[2]}
            for e in edges
        ],
    }


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
             "sqlite provides sql query capabilities"),
            ("c2", 1, "claim", "Database Perf",
             "database indexing improves query performance"),
            ("c3", 2, "claim", "Testing Guide",
             "pytest framework provides fixtures and assertions"),
            ("c4", 3, "prose", "Security Guide",
             "authentication and authorization protect api endpoints"),
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
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c1", 0, "sqlite, query", now))
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c2", 0, "database, index", now))
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c3", 1, "pytest, test", now))

        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c1", "database", 0.85, now))
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c2", "database", 0.72, now))
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c1", "search", 0.60, now))

        conn.execute(
            "INSERT INTO chunk_similarities VALUES (?,?,?,?)",
            ("c1", "c2", 0.82, now))

        conn.execute(
            "INSERT INTO claim_edges "
            "(edge_id, source_chunk, target_chunk, edge_type, basis, "
            " confidence, detected_utc, resolution, resolved_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (_sha256("e1"), "c1", "c2", "supports", "negation",
             0.9, now, None, None))

        conn.commit()

        # Check 1: related_chunks returns results for c1
        rel = related_chunks(conn, "c1")
        assert rel["found"] is True
        assert len(rel["related"]) > 0
        checks += 1

        # Check 2: c2 is the top related chunk to c1
        assert rel["related"][0]["chunk_id"] == "c2"
        checks += 1

        # Check 3: c2 has high composite score (same topic, cluster, similarity, tags, edge)
        assert rel["related"][0]["composite"] > 0.5
        checks += 1

        # Check 4: c3 has lower score than c2
        c3_entry = next(
            (r for r in rel["related"] if r["chunk_id"] == "c3"), None)
        if c3_entry:
            assert c3_entry["composite"] < rel["related"][0]["composite"]
        checks += 1

        # Check 5: signals breakdown is present
        top = rel["related"][0]
        assert "signals" in top
        assert "topic" in top["signals"]
        assert "cluster" in top["signals"]
        assert "similarity" in top["signals"]
        assert "tags" in top["signals"]
        assert "citation" in top["signals"]
        checks += 1

        # Check 6: topic signal is 1.0 (c1 and c2 share topic 0)
        assert top["signals"]["topic"] == 1.0
        checks += 1

        # Check 7: cluster signal is 1.0 (both in cluster 0)
        assert top["signals"]["cluster"] == 1.0
        checks += 1

        # Check 8: similarity signal matches stored value
        assert top["signals"]["similarity"] == 0.82
        checks += 1

        # Check 9: explain_relation returns detailed breakdown
        expl = explain_relation(conn, "c1", "c2")
        assert expl["composite"] > 0.5
        assert len(expl["edges"]) == 1
        assert expl["edges"][0]["edge_type"] == "supports"
        checks += 1

        # Check 10: explain_relation for unrelated pair
        expl2 = explain_relation(conn, "c1", "c4")
        assert expl2["composite"] == 0.0
        assert len(expl2["edges"]) == 0
        checks += 1

        # Check 11: nonexistent chunk
        rel_none = related_chunks(conn, "nosuch")
        assert rel_none["found"] is False
        checks += 1

        # Check 12: explain with nonexistent target
        expl_none = explain_relation(conn, "c1", "nosuch")
        assert expl_none.get("target_found") is False
        checks += 1

        # Check 13: top_n limits results
        small = related_chunks(conn, "c1", top_n=1)
        assert len(small["related"]) <= 1
        checks += 1

        # Check 14: empty corpus
        empty_dir = Path(td) / "empty"
        empty_dir.mkdir()
        ec = connect(str(empty_dir / "e.db"))
        init_schema(ec)
        _ensure_tables(ec)
        assert related_chunks(ec, "any")["found"] is False
        ec.close()
        checks += 1

        conn.close()

    print(f"PASS recommend selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus chunk recommender")
    sub = parser.add_subparsers(dest="cmd")

    p_rel = sub.add_parser("related",
                           help="Find related chunks by multi-signal relevance")
    p_rel.add_argument("--chunk-id", required=True)
    p_rel.add_argument("--db", default=str(DEFAULT_DB))
    p_rel.add_argument("--top", type=int, default=10)
    p_rel.add_argument("--json", action="store_true")

    p_expl = sub.add_parser("explain",
                            help="Explain relationship between two chunks")
    p_expl.add_argument("--chunk-id", required=True)
    p_expl.add_argument("--target", required=True)
    p_expl.add_argument("--db", default=str(DEFAULT_DB))
    p_expl.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "related":
        conn = connect(args.db)
        result = related_chunks(conn, args.chunk_id, top_n=args.top)
        if args.json:
            print(json.dumps(result, indent=2))
        elif not result["found"]:
            print(f"  Chunk {args.chunk_id!r} not found")
        elif not result["related"]:
            print(f"  No related chunks found for {args.chunk_id}")
        else:
            print(f"  Related to {args.chunk_id} ({result['heading']}):")
            for r in result["related"]:
                sigs = r["signals"]
                print(f"    {r['composite']:.3f}  {r['chunk_id']}  "
                      f"({r['kind']})  {r['heading'][:30]}")
                print(f"           topic={sigs['topic']:.1f} "
                      f"cluster={sigs['cluster']:.1f} "
                      f"sim={sigs['similarity']:.2f} "
                      f"tags={sigs['tags']:.2f} "
                      f"cite={sigs['citation']:.1f}")
        conn.close()

    elif args.cmd == "explain":
        conn = connect(args.db)
        result = explain_relation(conn, args.chunk_id, args.target)
        if args.json:
            print(json.dumps(result, indent=2))
        elif not result.get("found", True):
            print(f"  Chunk {args.chunk_id!r} not found")
        elif result.get("target_found") is False:
            print(f"  Target {args.target!r} not found")
        else:
            print(f"  {result['chunk_id']} -> {result['target_id']}")
            print(f"  Composite: {result['composite']:.3f}")
            for k, v in result["signals"].items():
                print(f"    {k}: {v:.3f}")
            if result["edges"]:
                for e in result["edges"]:
                    print(f"    edge: {e['edge_type']} "
                          f"(conf={e['confidence']:.2f}, {e['basis']})")
        conn.close()


if __name__ == "__main__":
    main()
