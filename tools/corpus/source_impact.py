#!/usr/bin/env python3
"""Corpus source impact: rank sources by their downstream footprint.

Scores each source by how its chunks participate in the analytical
tables: topic assignments, cluster memberships, citation counts,
claim edges, and quality signals.  Surfaces which sources drive the
most corpus value and which contribute little.

Usage:
    python tools/corpus/source_impact.py rank [--db PATH] [--top N] [--json]
    python tools/corpus/source_impact.py detail --source SOURCE_ID [--db PATH] [--json]
    python tools/corpus/source_impact.py deadweight [--db PATH] [--json]
    python tools/corpus/source_impact.py selftest
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


def _source_scores(conn) -> list[dict]:
    """Compute per-source impact scores."""
    _ensure_tables(conn)

    sources = conn.execute("""
        SELECT s.source_id, s.title, s.kind, s.liveness,
               COUNT(c.chunk_id) as chunk_count,
               SUM(c.word_count) as total_words
        FROM sources s
        LEFT JOIN chunks c ON c.source_id = s.source_id
            AND c.status != 'superseded'
        GROUP BY s.source_id
    """).fetchall()

    if not sources:
        return []

    results = []
    for row in sources:
        sid = row[0]
        chunk_count = row[4] or 0
        total_words = row[5] or 0

        if chunk_count == 0:
            results.append({
                "source_id": sid,
                "title": row[1],
                "kind": row[2],
                "liveness": row[3],
                "chunk_count": 0,
                "total_words": 0,
                "cited_chunks": 0,
                "total_citations": 0,
                "edge_chunks": 0,
                "topic_chunks": 0,
                "cluster_chunks": 0,
                "tag_chunks": 0,
                "impact_score": 0.0,
            })
            continue

        cited = conn.execute("""
            SELECT COUNT(DISTINCT c.chunk_id), SUM(c.citation_count)
            FROM chunks c
            WHERE c.source_id = ? AND c.status != 'superseded'
            AND c.citation_count > 0
        """, (sid,)).fetchone()
        cited_chunks = cited[0] or 0
        total_citations = cited[1] or 0

        edge_chunks = conn.execute("""
            SELECT COUNT(DISTINCT chunk_id) FROM (
                SELECT source_chunk as chunk_id FROM claim_edges ce
                JOIN chunks c ON c.chunk_id = ce.source_chunk
                WHERE c.source_id = ? AND c.status != 'superseded'
                AND ce.resolution IS NULL
                UNION
                SELECT target_chunk as chunk_id FROM claim_edges ce
                JOIN chunks c ON c.chunk_id = ce.target_chunk
                WHERE c.source_id = ? AND c.status != 'superseded'
                AND ce.resolution IS NULL
            )
        """, (sid, sid)).fetchone()[0]

        topic_chunks = conn.execute("""
            SELECT COUNT(*) FROM chunk_topics ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            WHERE c.source_id = ? AND c.status != 'superseded'
        """, (sid,)).fetchone()[0]

        cluster_chunks = conn.execute("""
            SELECT COUNT(*) FROM chunk_clusters cc
            JOIN chunks c ON c.chunk_id = cc.chunk_id
            WHERE c.source_id = ? AND c.status != 'superseded'
        """, (sid,)).fetchone()[0]

        tag_chunks = conn.execute("""
            SELECT COUNT(DISTINCT ct.chunk_id) FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            WHERE c.source_id = ? AND c.status != 'superseded'
        """, (sid,)).fetchone()[0]

        citation_rate = cited_chunks / chunk_count if chunk_count else 0
        edge_rate = edge_chunks / chunk_count if chunk_count else 0
        topic_rate = topic_chunks / chunk_count if chunk_count else 0
        cluster_rate = cluster_chunks / chunk_count if chunk_count else 0
        tag_rate = tag_chunks / chunk_count if chunk_count else 0

        impact = round(
            (citation_rate * 0.3)
            + (edge_rate * 0.2)
            + (topic_rate * 0.2)
            + (cluster_rate * 0.15)
            + (tag_rate * 0.15),
            4,
        )

        results.append({
            "source_id": sid,
            "title": row[1],
            "kind": row[2],
            "liveness": row[3],
            "chunk_count": chunk_count,
            "total_words": total_words,
            "cited_chunks": cited_chunks,
            "total_citations": total_citations,
            "edge_chunks": edge_chunks,
            "topic_chunks": topic_chunks,
            "cluster_chunks": cluster_chunks,
            "tag_chunks": tag_chunks,
            "impact_score": impact,
        })

    return results


def rank_sources(conn, top_n: int = 20) -> list[dict]:
    """Rank sources by impact score descending."""
    scores = _source_scores(conn)
    scores.sort(key=lambda s: s["impact_score"], reverse=True)
    return scores[:top_n]


def source_detail(conn, source_id: str) -> dict | None:
    """Detailed impact breakdown for one source."""
    _ensure_tables(conn)

    src = conn.execute(
        "SELECT source_id, title, kind, liveness, canonical_uri "
        "FROM sources WHERE source_id = ?",
        (source_id,),
    ).fetchone()

    if not src:
        return None

    chunks = conn.execute("""
        SELECT chunk_id, kind, word_count, heading_path, citation_count
        FROM chunks
        WHERE source_id = ? AND status != 'superseded'
        ORDER BY ordinal
    """, (source_id,)).fetchall()

    chunk_details = []
    for row in chunks:
        cid = row[0]

        has_topic = conn.execute(
            "SELECT topic_label FROM chunk_topics WHERE chunk_id = ?",
            (cid,),
        ).fetchone()

        has_cluster = conn.execute(
            "SELECT cluster_label FROM chunk_clusters WHERE chunk_id = ?",
            (cid,),
        ).fetchone()

        edge_count = conn.execute("""
            SELECT COUNT(*) FROM claim_edges
            WHERE (source_chunk = ? OR target_chunk = ?)
            AND resolution IS NULL
        """, (cid, cid)).fetchone()[0]

        tags = conn.execute(
            "SELECT tag, score FROM chunk_tags WHERE chunk_id = ? "
            "ORDER BY score DESC LIMIT 3",
            (cid,),
        ).fetchall()

        chunk_details.append({
            "chunk_id": cid,
            "kind": row[1],
            "word_count": row[2],
            "heading": row[3],
            "citation_count": row[4],
            "topic_label": has_topic[0] if has_topic else None,
            "cluster_label": has_cluster[0] if has_cluster else None,
            "edge_count": edge_count,
            "top_tags": [{"tag": t[0], "score": round(t[1], 4)} for t in tags],
        })

    return {
        "source_id": src[0],
        "title": src[1],
        "kind": src[2],
        "liveness": src[3],
        "uri": src[4],
        "chunk_count": len(chunk_details),
        "chunks": chunk_details,
    }


def deadweight(conn) -> list[dict]:
    """Find sources whose chunks have zero analytical footprint."""
    scores = _source_scores(conn)
    dead = [
        s for s in scores
        if s["chunk_count"] > 0
        and s["cited_chunks"] == 0
        and s["edge_chunks"] == 0
        and s["topic_chunks"] == 0
        and s["cluster_chunks"] == 0
        and s["tag_chunks"] == 0
    ]
    dead.sort(key=lambda s: s["total_words"], reverse=True)
    return dead


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)
        _ensure_tables(conn)

        now = "2026-08-31T00:00:00Z"

        for sid, title in [("s1", "Active Source"), ("s2", "Quiet Source")]:
            conn.execute(
                "INSERT INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, publisher, published_utc, "
                " fetched_utc, upstream_rev, upstream_mtime, liveness, "
                " content_sha256, bytes, supersedes) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, f"file:///{sid}.md", "local_md", title,
                 "CC-BY-4.0", "vendor", "LICENSE", "test", None,
                 now, None, None, "live", _sha256(sid), 100, None),
            )

        test_chunks = [
            ("c1", "s1", 0, "claim", "Database Guide",
             "sqlite provides sql query capabilities", 2),
            ("c2", "s1", 1, "claim", "Perf Guide",
             "database indexing improves performance", 3),
            ("c3", "s1", 2, "prose", "Code Guide",
             "python code examples for beginners", 0),
            ("c4", "s2", 0, "prose", "Filler",
             "this chunk has no analytical presence", 0),
            ("c5", "s2", 1, "prose", "More Filler",
             "another chunk with zero engagement", 0),
        ]

        for cid, sid, ordinal, kind, heading, text, cites in test_chunks:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " citation_count, status, status_reason, ingested_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, ordinal, heading, kind, None,
                 text, text, len(text.split()), _sha256(text),
                 0, cites, "accepted", None, now),
            )

        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c1", 0, 0.8, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c2", 0, 0.7, now))

        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c1", 0, "sqlite, query", now))
        conn.execute(
            "INSERT INTO chunk_clusters VALUES (?,?,?,?)",
            ("c2", 0, "database, index", now))

        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c1", "database", 0.85, now))
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c2", "database", 0.72, now))

        conn.execute(
            "INSERT INTO claim_edges "
            "(edge_id, source_chunk, target_chunk, edge_type, basis, "
            " confidence, detected_utc, resolution, resolved_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (_sha256("e1"), "c1", "c2", "supports", "negation",
             0.9, now, None, None))

        conn.commit()

        # Check 1: rank returns both sources
        ranked = rank_sources(conn)
        assert len(ranked) == 2
        checks += 1

        # Check 2: s1 ranks higher than s2
        assert ranked[0]["source_id"] == "s1"
        assert ranked[1]["source_id"] == "s2"
        checks += 1

        # Check 3: s1 has positive impact score
        assert ranked[0]["impact_score"] > 0
        checks += 1

        # Check 4: s2 has zero impact score
        assert ranked[1]["impact_score"] == 0
        checks += 1

        # Check 5: s1 counts are correct
        s1 = ranked[0]
        assert s1["chunk_count"] == 3
        assert s1["cited_chunks"] == 2
        assert s1["topic_chunks"] == 2
        assert s1["cluster_chunks"] == 2
        assert s1["tag_chunks"] == 2
        checks += 1

        # Check 6: s1 edge_chunks > 0
        assert s1["edge_chunks"] >= 1
        checks += 1

        # Check 7: detail returns chunk-level breakdown
        det = source_detail(conn, "s1")
        assert det is not None
        assert det["chunk_count"] == 3
        assert len(det["chunks"]) == 3
        checks += 1

        # Check 8: detail chunk has topic and cluster
        c1_detail = next(c for c in det["chunks"] if c["chunk_id"] == "c1")
        assert c1_detail["topic_label"] == 0
        assert c1_detail["cluster_label"] == 0
        assert c1_detail["citation_count"] == 2
        checks += 1

        # Check 9: detail chunk c3 has no analytical footprint
        c3_detail = next(c for c in det["chunks"] if c["chunk_id"] == "c3")
        assert c3_detail["topic_label"] is None
        assert c3_detail["cluster_label"] is None
        assert c3_detail["edge_count"] == 0
        checks += 1

        # Check 10: detail for nonexistent source
        assert source_detail(conn, "nosuch") is None
        checks += 1

        # Check 11: deadweight returns s2
        dw = deadweight(conn)
        assert len(dw) == 1
        assert dw[0]["source_id"] == "s2"
        checks += 1

        # Check 12: deadweight excludes s1
        assert all(d["source_id"] != "s1" for d in dw)
        checks += 1

        # Check 13: empty corpus
        empty_dir = Path(td) / "empty"
        empty_dir.mkdir()
        ec = connect(str(empty_dir / "e.db"))
        init_schema(ec)
        _ensure_tables(ec)
        assert rank_sources(ec) == []
        assert deadweight(ec) == []
        assert source_detail(ec, "any") is None
        ec.close()
        checks += 1

        # Check 14: top_n limits results
        small = rank_sources(conn, top_n=1)
        assert len(small) == 1
        checks += 1

        conn.close()

    print(f"PASS source_impact selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus source impact analysis")
    sub = parser.add_subparsers(dest="cmd")

    p_rank = sub.add_parser("rank", help="Rank sources by impact score")
    p_rank.add_argument("--db", default=str(DEFAULT_DB))
    p_rank.add_argument("--top", type=int, default=20)
    p_rank.add_argument("--json", action="store_true")

    p_det = sub.add_parser("detail", help="Detailed breakdown for one source")
    p_det.add_argument("--source", required=True)
    p_det.add_argument("--db", default=str(DEFAULT_DB))
    p_det.add_argument("--json", action="store_true")

    p_dw = sub.add_parser("deadweight",
                          help="Sources with zero analytical footprint")
    p_dw.add_argument("--db", default=str(DEFAULT_DB))
    p_dw.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "rank":
        conn = connect(args.db)
        results = rank_sources(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No sources found")
        else:
            for r in results:
                print(f"  {r['impact_score']:.3f}  {r['title'][:40]:40s}  "
                      f"chunks={r['chunk_count']}  "
                      f"cited={r['cited_chunks']}  "
                      f"topics={r['topic_chunks']}  "
                      f"edges={r['edge_chunks']}")
        conn.close()

    elif args.cmd == "detail":
        conn = connect(args.db)
        result = source_detail(conn, args.source)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result is None:
            print(f"  Source {args.source!r} not found")
        else:
            print(f"  {result['title']} ({result['kind']}, "
                  f"{result['liveness']})")
            print(f"  {result['chunk_count']} chunks")
            for c in result["chunks"]:
                tags = ", ".join(t["tag"] for t in c["top_tags"])
                print(f"    {c['chunk_id']} ({c['kind']}): "
                      f"cites={c['citation_count']} "
                      f"edges={c['edge_count']} "
                      f"topic={c['topic_label']} "
                      f"cluster={c['cluster_label']} "
                      f"tags=[{tags}]")
        conn.close()

    elif args.cmd == "deadweight":
        conn = connect(args.db)
        results = deadweight(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No deadweight sources found")
        else:
            print(f"  {len(results)} sources with zero analytical footprint:")
            for r in results:
                print(f"    {r['title'][:50]:50s}  "
                      f"chunks={r['chunk_count']}  "
                      f"words={r['total_words']}")
        conn.close()


if __name__ == "__main__":
    main()
