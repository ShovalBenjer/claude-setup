#!/usr/bin/env python3
"""Chunk profile: complete dossier for a single chunk.

Assembles provenance, analytical signals, and relationships into
one report.  Combines what lineage, recommend, and dashboard each
show partially.

Usage:
    python tools/corpus/chunk_profile.py show --chunk-id CID [--db PATH] [--json]
    python tools/corpus/chunk_profile.py compare --chunk-id CID1 --chunk-id CID2 [--db PATH] [--json]
    python tools/corpus/chunk_profile.py batch [--db PATH] [--status STATUS] [--limit N] [--json]
    python tools/corpus/chunk_profile.py selftest
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


def _get_chunk(conn, chunk_id: str) -> dict | None:
    row = conn.execute(
        "SELECT chunk_id, source_id, ordinal, heading_path, kind, lang, "
        "word_count, status, status_reason, ingested_utc "
        "FROM chunks WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchone()
    if not row:
        return None
    cols = ["chunk_id", "source_id", "ordinal", "heading_path", "kind",
            "lang", "word_count", "status", "status_reason", "ingested_utc"]
    return dict(zip(cols, row))


def _get_source(conn, source_id: str) -> dict | None:
    row = conn.execute(
        "SELECT source_id, canonical_uri, kind, title, publisher, "
        "published_utc, liveness "
        "FROM sources WHERE source_id = ?",
        (source_id,),
    ).fetchone()
    if not row:
        return None
    cols = ["source_id", "canonical_uri", "kind", "title", "publisher",
            "published_utc", "liveness"]
    return dict(zip(cols, row))


# ── subcommands ──────────────────────────────────────────────────────


def chunk_profile(conn, chunk_id: str) -> dict:
    chunk = _get_chunk(conn, chunk_id)
    if not chunk:
        return {"chunk_id": chunk_id, "error": "not found"}

    source = _get_source(conn, chunk["source_id"])

    edges = []
    if _table_exists(conn, "claim_edges"):
        rows = conn.execute(
            "SELECT edge_id, source_chunk, target_chunk, edge_type, "
            "confidence, resolution "
            "FROM claim_edges "
            "WHERE source_chunk = ? OR target_chunk = ?",
            (chunk_id, chunk_id),
        ).fetchall()
        for r in rows:
            direction = "outbound" if r[1] == chunk_id else "inbound"
            other = r[2] if r[1] == chunk_id else r[1]
            edges.append({
                "edge_id": r[0], "direction": direction,
                "other_chunk": other, "edge_type": r[3],
                "confidence": round(r[4], 4),
                "resolution": r[5],
            })

    tags = []
    if _table_exists(conn, "chunk_tags"):
        rows = conn.execute(
            "SELECT tag, score FROM chunk_tags WHERE chunk_id = ? "
            "ORDER BY score DESC",
            (chunk_id,),
        ).fetchall()
        tags = [{"tag": r[0], "score": round(r[1], 4)} for r in rows]

    topic = None
    if _table_exists(conn, "chunk_topics"):
        row = conn.execute(
            "SELECT topic_label, topic_weight FROM chunk_topics "
            "WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if row:
            topic = {"label": row[0], "weight": round(row[1], 4)}

    cluster = None
    if _table_exists(conn, "chunk_clusters"):
        row = conn.execute(
            "SELECT cluster_label, top_terms FROM chunk_clusters "
            "WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if row:
            cluster = {"label": row[0], "top_terms": row[1]}

    similar = []
    if _table_exists(conn, "chunk_similarities"):
        rows = conn.execute(
            "SELECT chunk_id_b, cosine_score FROM chunk_similarities "
            "WHERE chunk_id_a = ? "
            "UNION ALL "
            "SELECT chunk_id_a, cosine_score FROM chunk_similarities "
            "WHERE chunk_id_b = ? "
            "ORDER BY cosine_score DESC LIMIT 5",
            (chunk_id, chunk_id),
        ).fetchall()
        similar = [{"chunk_id": r[0], "score": round(r[1], 4)}
                   for r in rows]

    citations = []
    if _table_exists(conn, "citations"):
        rows = conn.execute(
            "SELECT citation_id, target_uri, tag, verified "
            "FROM citations WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchall()
        citations = [{"citation_id": r[0], "target_uri": r[1],
                       "tag": r[2], "verified": bool(r[3])}
                     for r in rows]

    return {
        "chunk": chunk,
        "source": source,
        "edges": edges,
        "tags": tags,
        "topic": topic,
        "cluster": cluster,
        "similar_chunks": similar,
        "citations": citations,
    }


def compare_chunks(conn, cid1: str, cid2: str) -> dict:
    p1 = chunk_profile(conn, cid1)
    p2 = chunk_profile(conn, cid2)

    shared_tags = set()
    if p1.get("tags") and p2.get("tags"):
        tags1 = {t["tag"] for t in p1["tags"]}
        tags2 = {t["tag"] for t in p2["tags"]}
        shared_tags = tags1 & tags2

    same_topic = False
    if p1.get("topic") and p2.get("topic"):
        same_topic = p1["topic"]["label"] == p2["topic"]["label"]

    same_cluster = False
    if p1.get("cluster") and p2.get("cluster"):
        same_cluster = p1["cluster"]["label"] == p2["cluster"]["label"]

    direct_edge = None
    for e in p1.get("edges", []):
        if e["other_chunk"] == cid2:
            direct_edge = e
            break

    similarity = None
    for s in p1.get("similar_chunks", []):
        if s["chunk_id"] == cid2:
            similarity = s["score"]
            break

    return {
        "chunk_1": p1,
        "chunk_2": p2,
        "shared_tags": sorted(shared_tags),
        "same_topic": same_topic,
        "same_cluster": same_cluster,
        "direct_edge": direct_edge,
        "similarity_score": similarity,
    }


def batch_profiles(conn, status: str = "accepted",
                   limit: int = 10) -> list[dict]:
    rows = conn.execute(
        "SELECT chunk_id FROM chunks WHERE status = ? LIMIT ?",
        (status, limit),
    ).fetchall()
    return [chunk_profile(conn, r[0]) for r in rows]


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

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Test Paper",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha1", 1000, None),
        )

        for i in range(1, 4):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (f"c{i}", "s1", i - 1, f"H{i}", "claim", "en",
                 f"text{i}", f"text{i}", 10, f"n{i}", now),
            )

        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e1", "c1", "c2", "contradicts", "semantic", 0.9, now),
        )

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c1", "ml", 0.9, now),
        )
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c2", "ml", 0.7, now),
        )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES (?, ?, ?, ?, ?, ?)",
            ("ci1", "c1", "https://ref.com", "primary", "p.5", 0),
        )
        conn.commit()

        # 1: profile returns chunk data
        p = chunk_profile(conn, "c1")
        assert p["chunk"]["chunk_id"] == "c1"
        assert p["chunk"]["kind"] == "claim"
        checks += 1

        # 2: source included
        assert p["source"]["title"] == "Test Paper"
        assert p["source"]["liveness"] == "live"
        checks += 1

        # 3: edges present
        assert len(p["edges"]) == 1
        assert p["edges"][0]["edge_type"] == "contradicts"
        assert p["edges"][0]["direction"] == "outbound"
        checks += 1

        # 4: tags present
        assert len(p["tags"]) == 1
        assert p["tags"][0]["tag"] == "ml"
        checks += 1

        # 5: citations present
        assert len(p["citations"]) == 1
        assert p["citations"][0]["target_uri"] == "https://ref.com"
        checks += 1

        # 6: missing analytical tables handled
        assert p["topic"] is None
        assert p["cluster"] is None
        assert p["similar_chunks"] == []
        checks += 1

        # 7: nonexistent chunk
        p_none = chunk_profile(conn, "nonexistent")
        assert "error" in p_none
        checks += 1

        # 8: compare chunks
        cmp = compare_chunks(conn, "c1", "c2")
        assert "ml" in cmp["shared_tags"]
        checks += 1

        # 9: direct edge in comparison
        assert cmp["direct_edge"] is not None
        assert cmp["direct_edge"]["edge_type"] == "contradicts"
        checks += 1

        # 10: batch profiles
        batch = batch_profiles(conn, status="accepted", limit=5)
        assert len(batch) == 3
        checks += 1

        # 11: JSON output
        _ = json.dumps(p)
        _ = json.dumps(cmp)
        _ = json.dumps(batch)
        checks += 1

        # 12: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        p2 = chunk_profile(conn2, "c1")
        assert "error" in p2
        b2 = batch_profiles(conn2)
        assert b2 == []
        checks += 1

        # 13: inbound edge direction
        p_c2 = chunk_profile(conn, "c2")
        assert len(p_c2["edges"]) == 1
        assert p_c2["edges"][0]["direction"] == "inbound"
        checks += 1

        # 14: compare with no shared tags
        p_c3 = compare_chunks(conn, "c1", "c3")
        assert p_c3["shared_tags"] == []
        assert p_c3["direct_edge"] is None
        checks += 1

    print(f"PASS chunk_profile selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk profile: complete dossier for a single chunk"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_show = sub.add_parser("show", help="Full profile for one chunk")
    p_show.add_argument("--chunk-id", required=True)
    p_show.add_argument("--db", default=DEFAULT_DB)
    p_show.add_argument("--json", action="store_true")

    p_cmp = sub.add_parser("compare", help="Compare two chunks")
    p_cmp.add_argument("--chunk-id", required=True, nargs=2)
    p_cmp.add_argument("--db", default=DEFAULT_DB)
    p_cmp.add_argument("--json", action="store_true")

    p_batch = sub.add_parser("batch", help="Batch profiles by status")
    p_batch.add_argument("--db", default=DEFAULT_DB)
    p_batch.add_argument("--status", default="accepted")
    p_batch.add_argument("--limit", type=int, default=10)
    p_batch.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "show":
        result = chunk_profile(conn, args.chunk_id)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if "error" in result:
                print(f"Chunk {args.chunk_id}: {result['error']}")
                return
            c = result["chunk"]
            print(f"Chunk: {c['chunk_id']} ({c['kind']}, {c['status']})")
            print(f"  Source: {result['source']['title']} "
                  f"({result['source']['source_id']})")
            print(f"  Words: {c['word_count']}, "
                  f"Heading: {c['heading_path']}")
            if result["tags"]:
                tags = ", ".join(f"{t['tag']}({t['score']})"
                                for t in result["tags"])
                print(f"  Tags: {tags}")
            if result["topic"]:
                print(f"  Topic: {result['topic']['label']} "
                      f"({result['topic']['weight']})")
            if result["cluster"]:
                print(f"  Cluster: {result['cluster']['label']}")
            if result["edges"]:
                print(f"  Edges: {len(result['edges'])}")
                for e in result["edges"]:
                    print(f"    {e['direction']} {e['edge_type']} "
                          f"-> {e['other_chunk']} "
                          f"(conf {e['confidence']})")
            if result["similar_chunks"]:
                print(f"  Similar: {len(result['similar_chunks'])}")
            if result["citations"]:
                print(f"  Citations: {len(result['citations'])}")

    elif args.cmd == "compare":
        result = compare_chunks(conn, args.chunk_id[0], args.chunk_id[1])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Comparing {args.chunk_id[0]} vs {args.chunk_id[1]}")
            if result["shared_tags"]:
                print(f"  Shared tags: {', '.join(result['shared_tags'])}")
            print(f"  Same topic: {result['same_topic']}")
            print(f"  Same cluster: {result['same_cluster']}")
            if result["direct_edge"]:
                e = result["direct_edge"]
                print(f"  Direct edge: {e['edge_type']} "
                      f"(conf {e['confidence']})")
            if result["similarity_score"] is not None:
                print(f"  Similarity: {result['similarity_score']}")

    elif args.cmd == "batch":
        results = batch_profiles(conn, status=args.status,
                                 limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                if "error" in r:
                    continue
                c = r["chunk"]
                tags = len(r["tags"])
                edges = len(r["edges"])
                print(f"{c['chunk_id']}: {c['kind']} | "
                      f"{tags} tags, {edges} edges")

    conn.close()


if __name__ == "__main__":
    main()
