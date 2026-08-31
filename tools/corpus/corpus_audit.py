#!/usr/bin/env python3
"""Corpus audit: cross-signal issue detection.

Identifies actionable issues by cross-referencing analytical signals:
contradictions within the same cluster, unverified citations on accepted
chunks, low-confidence tags, orphan accepted chunks, and sources whose
chunks are mostly superseded.

Usage:
    python tools/corpus/corpus_audit.py contradictions [--db PATH] [--json]
    python tools/corpus/corpus_audit.py citations [--db PATH] [--json]
    python tools/corpus/corpus_audit.py weak-tags [--db PATH] [--threshold F] [--json]
    python tools/corpus/corpus_audit.py orphans [--db PATH] [--json]
    python tools/corpus/corpus_audit.py stale-sources [--db PATH] [--threshold F] [--json]
    python tools/corpus/corpus_audit.py full [--db PATH] [--json]
    python tools/corpus/corpus_audit.py selftest
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


def intra_cluster_contradictions(conn) -> list[dict]:
    """Find unresolved contradictions where both chunks share a cluster."""
    if not _table_exists(conn, "claim_edges"):
        return []
    if not _table_exists(conn, "chunk_clusters"):
        return []
    rows = conn.execute(
        "SELECT e.edge_id, e.source_chunk, e.target_chunk, "
        "e.confidence, cc1.cluster_label "
        "FROM claim_edges e "
        "JOIN chunk_clusters cc1 ON cc1.chunk_id = e.source_chunk "
        "JOIN chunk_clusters cc2 ON cc2.chunk_id = e.target_chunk "
        "WHERE e.edge_type = 'contradicts' "
        "AND e.resolution IS NULL "
        "AND cc1.cluster_label = cc2.cluster_label "
        "ORDER BY e.confidence DESC"
    ).fetchall()
    return [
        {"edge_id": r[0], "source_chunk": r[1], "target_chunk": r[2],
         "confidence": round(r[3], 4), "cluster": r[4]}
        for r in rows
    ]


def unverified_citations(conn) -> list[dict]:
    """Find unverified citations on accepted chunks."""
    if not _table_exists(conn, "citations"):
        return []
    rows = conn.execute(
        "SELECT ci.citation_id, ci.chunk_id, ci.target_uri, ci.tag "
        "FROM citations ci "
        "JOIN chunks c ON c.chunk_id = ci.chunk_id "
        "WHERE ci.verified = 0 AND c.status = 'accepted' "
        "ORDER BY ci.chunk_id"
    ).fetchall()
    return [
        {"citation_id": r[0], "chunk_id": r[1],
         "target_uri": r[2], "tag": r[3]}
        for r in rows
    ]


def weak_tags(conn, threshold: float = 0.5) -> list[dict]:
    """Find tags assigned with confidence below threshold."""
    if not _table_exists(conn, "chunk_tags"):
        return []
    rows = conn.execute(
        "SELECT ct.chunk_id, ct.tag, ct.score "
        "FROM chunk_tags ct "
        "JOIN chunks c ON c.chunk_id = ct.chunk_id "
        "WHERE ct.score < ? AND c.status != 'superseded' "
        "ORDER BY ct.score ASC",
        (threshold,),
    ).fetchall()
    return [
        {"chunk_id": r[0], "tag": r[1], "score": round(r[2], 4)}
        for r in rows
    ]


def orphan_accepted(conn) -> list[dict]:
    """Find accepted chunks with no edges, citations, tags, or topic."""
    has_edges = _table_exists(conn, "claim_edges")
    has_citations = _table_exists(conn, "citations")
    has_tags = _table_exists(conn, "chunk_tags")
    has_topics = _table_exists(conn, "chunk_topics")

    rows = conn.execute(
        "SELECT chunk_id, source_id, kind, word_count "
        "FROM chunks WHERE status = 'accepted'"
    ).fetchall()

    orphans = []
    for r in rows:
        cid = r[0]
        if has_edges and conn.execute(
            "SELECT 1 FROM claim_edges "
            "WHERE source_chunk = ? OR target_chunk = ? LIMIT 1",
            (cid, cid),
        ).fetchone():
            continue
        if has_citations and conn.execute(
            "SELECT 1 FROM citations WHERE chunk_id = ? LIMIT 1",
            (cid,),
        ).fetchone():
            continue
        if has_tags and conn.execute(
            "SELECT 1 FROM chunk_tags WHERE chunk_id = ? LIMIT 1",
            (cid,),
        ).fetchone():
            continue
        if has_topics and conn.execute(
            "SELECT 1 FROM chunk_topics WHERE chunk_id = ? LIMIT 1",
            (cid,),
        ).fetchone():
            continue
        orphans.append({
            "chunk_id": cid, "source_id": r[1],
            "kind": r[2], "word_count": r[3],
        })
    return orphans


def stale_sources(conn, threshold: float = 0.5) -> list[dict]:
    """Find sources where more than threshold fraction of chunks are superseded."""
    if not _table_exists(conn, "chunks") or not _table_exists(conn, "sources"):
        return []
    rows = conn.execute(
        "SELECT s.source_id, s.title, "
        "count(*) AS total, "
        "sum(CASE WHEN c.status = 'superseded' THEN 1 ELSE 0 END) AS sup "
        "FROM sources s "
        "JOIN chunks c ON c.source_id = s.source_id "
        "GROUP BY s.source_id "
        "HAVING total > 0"
    ).fetchall()
    results = []
    for r in rows:
        ratio = r[3] / r[2]
        if ratio >= threshold:
            results.append({
                "source_id": r[0], "title": r[1],
                "total_chunks": r[2], "superseded_chunks": r[3],
                "superseded_ratio": round(ratio, 4),
            })
    results.sort(key=lambda x: x["superseded_ratio"], reverse=True)
    return results


def full_audit(conn) -> dict:
    return {
        "intra_cluster_contradictions": intra_cluster_contradictions(conn),
        "unverified_citations": unverified_citations(conn),
        "weak_tags": weak_tags(conn),
        "orphan_accepted": orphan_accepted(conn),
        "stale_sources": stale_sources(conn),
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

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chunk_clusters (
                chunk_id       TEXT NOT NULL REFERENCES chunks(chunk_id),
                cluster_label  INTEGER NOT NULL,
                top_terms      TEXT NOT NULL,
                clustered_utc  TEXT NOT NULL,
                PRIMARY KEY (chunk_id)
            );
        """)

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
            ("c1", "s1", 0, "H1", "claim", "en", "alpha", "alpha", 10, "n1"),
            ("c2", "s1", 1, "H2", "claim", "en", "beta", "beta", 10, "n2"),
            ("c3", "s1", 2, "H3", "claim", "en", "gamma", "gamma", 10, "n3"),
            ("c4", "s2", 0, "H4", "prose", "en", "delta", "delta", 10, "n4"),
            ("c5", "s2", 1, "H5", "claim", "en", "epsilon", "epsilon", 10, "n5"),
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
            "INSERT INTO chunk_clusters (chunk_id, cluster_label, "
            "top_terms, clustered_utc) VALUES (?, ?, ?, ?)",
            ("c1", "cluster-A", "term1,term2", now),
        )
        conn.execute(
            "INSERT INTO chunk_clusters (chunk_id, cluster_label, "
            "top_terms, clustered_utc) VALUES (?, ?, ?, ?)",
            ("c2", "cluster-A", "term1,term2", now),
        )

        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e1", "c1", "c2", "contradicts", "semantic", 0.85, now),
        )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES (?, ?, ?, ?, ?, ?)",
            ("ci1", "c1", "https://ref.com", "primary", "p.5", 0),
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES (?, ?, ?, ?, ?, ?)",
            ("ci2", "c2", "https://ref2.com", "primary", "p.10", 1),
        )

        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c1", "ml", 0.3, now),
        )
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c2", "ml", 0.8, now),
        )
        conn.execute(
            "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
            "VALUES (?, ?, ?, ?)",
            ("c3", "nlp", 0.4, now),
        )
        conn.commit()

        # 1: intra-cluster contradictions detected
        ic = intra_cluster_contradictions(conn)
        assert len(ic) == 1
        assert ic[0]["cluster"] == "cluster-A"
        assert ic[0]["confidence"] == 0.85
        checks += 1

        # 2: resolved contradictions excluded
        conn.execute(
            "UPDATE claim_edges SET resolution = 'accepted' "
            "WHERE edge_id = 'e1'"
        )
        conn.commit()
        ic2 = intra_cluster_contradictions(conn)
        assert len(ic2) == 0
        checks += 1

        # 3: restore and check cross-cluster contradictions excluded
        conn.execute(
            "UPDATE claim_edges SET resolution = NULL "
            "WHERE edge_id = 'e1'"
        )
        conn.execute(
            "INSERT INTO chunk_clusters (chunk_id, cluster_label, "
            "top_terms, clustered_utc) VALUES (?, ?, ?, ?)",
            ("c3", "cluster-B", "term3,term4", now),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e2", "c1", "c3", "contradicts", "semantic", 0.7, now),
        )
        conn.commit()
        ic3 = intra_cluster_contradictions(conn)
        assert len(ic3) == 1
        assert ic3[0]["edge_id"] == "e1"
        checks += 1

        # 4: unverified citations on accepted chunks
        uv = unverified_citations(conn)
        assert len(uv) == 1
        assert uv[0]["citation_id"] == "ci1"
        assert uv[0]["target_uri"] == "https://ref.com"
        checks += 1

        # 5: verified citation excluded
        assert all(u["citation_id"] != "ci2" for u in uv)
        checks += 1

        # 6: weak tags below threshold
        wt = weak_tags(conn, threshold=0.5)
        assert len(wt) == 2
        assert wt[0]["score"] <= wt[1]["score"]
        checks += 1

        # 7: strong tags excluded
        assert all(t["tag"] != "ml" or t["score"] < 0.5 for t in wt)
        checks += 1

        # 8: orphan accepted chunks (c4 and c5 have no signals)
        orph = orphan_accepted(conn)
        orphan_ids = {o["chunk_id"] for o in orph}
        assert "c4" in orphan_ids
        assert "c5" in orphan_ids
        checks += 1

        # 9: connected chunks not orphans
        assert "c1" not in orphan_ids
        assert "c2" not in orphan_ids
        checks += 1

        # 10: stale sources
        conn.execute(
            "UPDATE chunks SET status = 'superseded' WHERE chunk_id IN ('c4', 'c5')"
        )
        conn.commit()
        ss = stale_sources(conn, threshold=0.5)
        assert len(ss) == 1
        assert ss[0]["source_id"] == "s2"
        assert ss[0]["superseded_ratio"] == 1.0
        checks += 1

        # 11: non-stale source excluded
        assert all(s["source_id"] != "s1" for s in ss)
        checks += 1

        # 12: full audit combines all checks
        fa = full_audit(conn)
        assert "intra_cluster_contradictions" in fa
        assert "unverified_citations" in fa
        assert "weak_tags" in fa
        assert "orphan_accepted" in fa
        assert "stale_sources" in fa
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(fa)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        fa2 = full_audit(conn2)
        assert fa2["intra_cluster_contradictions"] == []
        assert fa2["unverified_citations"] == []
        assert fa2["weak_tags"] == []
        assert fa2["orphan_accepted"] == []
        assert fa2["stale_sources"] == []
        checks += 1

    print(f"PASS corpus_audit selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Corpus audit: cross-signal issue detection"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ic = sub.add_parser("contradictions",
                          help="Intra-cluster contradictions")
    p_ic.add_argument("--db", default=DEFAULT_DB)
    p_ic.add_argument("--json", action="store_true")

    p_ci = sub.add_parser("citations",
                          help="Unverified citations on accepted chunks")
    p_ci.add_argument("--db", default=DEFAULT_DB)
    p_ci.add_argument("--json", action="store_true")

    p_wt = sub.add_parser("weak-tags",
                          help="Tags below confidence threshold")
    p_wt.add_argument("--db", default=DEFAULT_DB)
    p_wt.add_argument("--threshold", type=float, default=0.5)
    p_wt.add_argument("--json", action="store_true")

    p_or = sub.add_parser("orphans",
                          help="Accepted chunks with no signals")
    p_or.add_argument("--db", default=DEFAULT_DB)
    p_or.add_argument("--json", action="store_true")

    p_ss = sub.add_parser("stale-sources",
                          help="Sources with high superseded ratio")
    p_ss.add_argument("--db", default=DEFAULT_DB)
    p_ss.add_argument("--threshold", type=float, default=0.5)
    p_ss.add_argument("--json", action="store_true")

    p_fa = sub.add_parser("full", help="Full audit across all checks")
    p_fa.add_argument("--db", default=DEFAULT_DB)
    p_fa.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "contradictions":
        result = intra_cluster_contradictions(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Intra-cluster contradictions: {len(result)}")
            for r in result:
                print(f"  {r['source_chunk']} <-> {r['target_chunk']} "
                      f"in {r['cluster']} (conf {r['confidence']})")

    elif args.cmd == "citations":
        result = unverified_citations(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Unverified citations on accepted chunks: {len(result)}")
            for r in result:
                print(f"  {r['chunk_id']}: {r['target_uri']} ({r['tag']})")

    elif args.cmd == "weak-tags":
        threshold = args.threshold
        result = weak_tags(conn, threshold=threshold)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Weak tags (score < {threshold}): {len(result)}")
            for r in result:
                print(f"  {r['chunk_id']}: {r['tag']} ({r['score']})")

    elif args.cmd == "orphans":
        result = orphan_accepted(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Orphan accepted chunks: {len(result)}")
            for r in result:
                print(f"  {r['chunk_id']}: {r['kind']} "
                      f"({r['word_count']} words)")

    elif args.cmd == "stale-sources":
        threshold = args.threshold
        result = stale_sources(conn, threshold=threshold)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Stale sources (>= {threshold:.0%} superseded): "
                  f"{len(result)}")
            for r in result:
                print(f"  {r['source_id']}: {r['title']} "
                      f"({r['superseded_chunks']}/{r['total_chunks']} "
                      f"superseded)")

    elif args.cmd == "full":
        result = full_audit(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            ic = result["intra_cluster_contradictions"]
            print(f"Intra-cluster contradictions: {len(ic)}")
            uv = result["unverified_citations"]
            print(f"Unverified citations: {len(uv)}")
            wt = result["weak_tags"]
            print(f"Weak tags: {len(wt)}")
            orph = result["orphan_accepted"]
            print(f"Orphan accepted chunks: {len(orph)}")
            ss = result["stale_sources"]
            print(f"Stale sources: {len(ss)}")

    conn.close()


if __name__ == "__main__":
    main()
