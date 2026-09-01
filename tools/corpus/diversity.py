#!/usr/bin/env python3
"""Corpus diversity analysis: measure topic concentration and coverage gaps.

Evaluates how well-distributed the corpus is across topics and sources.
Uses Shannon entropy and Gini coefficient to quantify concentration,
identifies topics dominated by a single source, and surfaces coverage
gaps where topics have few chunks.

Usage:
    python tools/corpus/diversity.py summary [--db PATH] [--json]
    python tools/corpus/diversity.py topic-sources [--db PATH] [--json]
    python tools/corpus/diversity.py gaps [--db PATH] [--min-chunks N] [--json]
    python tools/corpus/diversity.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _ensure_tables(conn):
    """Create analytical tables if they do not exist."""
    conn.executescript("""
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
        CREATE TABLE IF NOT EXISTS chunk_tags (
            chunk_id  TEXT NOT NULL REFERENCES chunks(chunk_id),
            tag       TEXT NOT NULL,
            score     REAL NOT NULL,
            tagged_utc TEXT NOT NULL,
            PRIMARY KEY (chunk_id, tag)
        );
    """)


def _shannon_entropy(counts: list[int]) -> float:
    """Compute Shannon entropy over a distribution of counts."""
    total = sum(counts)
    if total == 0:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    return -sum(p * math.log2(p) for p in probs)


def _gini_coefficient(counts: list[int]) -> float:
    """Compute Gini coefficient (0 = perfect equality, 1 = total inequality)."""
    n = len(counts)
    if n == 0 or sum(counts) == 0:
        return 0.0
    sorted_counts = sorted(counts)
    total = sum(sorted_counts)
    cumulative = 0.0
    gini_sum = 0.0
    for i, c in enumerate(sorted_counts):
        cumulative += c
        gini_sum += (2 * (i + 1) - n - 1) * c
    return gini_sum / (n * total)


def diversity_summary(conn) -> dict:
    """Compute corpus-wide diversity metrics."""
    _ensure_tables(conn)

    topic_counts = conn.execute("""
        SELECT ct.topic_label, COUNT(*) as cnt
        FROM chunk_topics ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        WHERE c.status != 'superseded'
        GROUP BY ct.topic_label
        ORDER BY ct.topic_label
    """).fetchall()

    if not topic_counts:
        return {"has_topics": False, "total_chunks_with_topics": 0}

    counts = [r[1] for r in topic_counts]
    total_assigned = sum(counts)
    n_topics = len(counts)

    total_active = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    topic_entropy = round(_shannon_entropy(counts), 4)
    max_entropy = round(math.log2(n_topics), 4) if n_topics > 1 else 0.0
    evenness = round(topic_entropy / max_entropy, 4) if max_entropy > 0 else 1.0

    topic_gini = round(_gini_coefficient(counts), 4)

    source_counts = conn.execute("""
        SELECT c.source_id, COUNT(DISTINCT ct.topic_label) as n_topics
        FROM chunk_topics ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        WHERE c.status != 'superseded'
        GROUP BY c.source_id
    """).fetchall()
    avg_topics_per_source = round(
        sum(r[1] for r in source_counts) / len(source_counts), 2
    ) if source_counts else 0

    kind_counts = conn.execute("""
        SELECT c.kind, COUNT(DISTINCT ct.topic_label) as n_topics
        FROM chunk_topics ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        WHERE c.status != 'superseded'
        GROUP BY c.kind
    """).fetchall()

    tag_counts = conn.execute("""
        SELECT tag, COUNT(DISTINCT chunk_id) as cnt
        FROM chunk_tags
        GROUP BY tag
    """).fetchall()
    tag_entropy = round(
        _shannon_entropy([r[1] for r in tag_counts]), 4
    ) if tag_counts else 0.0

    return {
        "has_topics": True,
        "total_active_chunks": total_active,
        "total_chunks_with_topics": total_assigned,
        "topic_coverage_pct": round(100 * total_assigned / total_active, 1)
        if total_active else 0,
        "n_topics": n_topics,
        "topic_entropy": topic_entropy,
        "max_entropy": max_entropy,
        "evenness": evenness,
        "topic_gini": topic_gini,
        "avg_topics_per_source": avg_topics_per_source,
        "kind_topic_spread": {r[0]: r[1] for r in kind_counts},
        "tag_entropy": tag_entropy,
        "n_tags": len(tag_counts),
    }


def topic_source_diversity(conn) -> list[dict]:
    """Per-topic source diversity: how many sources contribute to each topic."""
    _ensure_tables(conn)

    topics = conn.execute("""
        SELECT ct.topic_label, COUNT(*) as chunk_count,
               COUNT(DISTINCT c.source_id) as source_count
        FROM chunk_topics ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        WHERE c.status != 'superseded'
        GROUP BY ct.topic_label
        ORDER BY ct.topic_label
    """).fetchall()

    if not topics:
        return []

    results = []
    for row in topics:
        tl = row[0]
        chunk_count = row[1]
        source_count = row[2]

        terms_rows = conn.execute(
            "SELECT term FROM topic_terms WHERE topic_label = ? "
            "ORDER BY term_rank LIMIT 5", (tl,)
        ).fetchall()
        terms = [r[0] for r in terms_rows]

        source_chunks = conn.execute("""
            SELECT c.source_id, s.title, COUNT(*) as cnt
            FROM chunk_topics ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            WHERE ct.topic_label = ? AND c.status != 'superseded'
            GROUP BY c.source_id
            ORDER BY cnt DESC
        """, (tl,)).fetchall()

        top_source_share = round(
            source_chunks[0][2] / chunk_count, 4
        ) if source_chunks else 0

        results.append({
            "topic_label": tl,
            "topic_terms": terms,
            "chunk_count": chunk_count,
            "source_count": source_count,
            "top_source_share": top_source_share,
            "top_source": source_chunks[0][1] if source_chunks else None,
            "dominated": top_source_share > 0.8,
        })

    results.sort(key=lambda r: r["source_count"])
    return results


def coverage_gaps(conn, min_chunks: int = 5) -> list[dict]:
    """Find topics with few chunks (coverage gaps)."""
    _ensure_tables(conn)

    topics = conn.execute("""
        SELECT ct.topic_label, COUNT(*) as cnt
        FROM chunk_topics ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        WHERE c.status != 'superseded'
        GROUP BY ct.topic_label
        HAVING COUNT(*) < ?
        ORDER BY cnt
    """, (min_chunks,)).fetchall()

    if not topics:
        return []

    results = []
    for row in topics:
        tl = row[0]
        terms_rows = conn.execute(
            "SELECT term FROM topic_terms WHERE topic_label = ? "
            "ORDER BY term_rank LIMIT 5", (tl,)
        ).fetchall()

        results.append({
            "topic_label": tl,
            "topic_terms": [r[0] for r in terms_rows],
            "chunk_count": row[1],
            "below_threshold": min_chunks,
        })

    return results


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)
        _ensure_tables(conn)

        now = "2026-08-31T00:00:00Z"

        for sid, title in [("s1", "Source A"), ("s2", "Source B")]:
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
            ("c1", "s1", 0, "claim", "DB Guide", "sqlite query"),
            ("c2", "s1", 1, "claim", "DB Perf", "database indexing"),
            ("c3", "s1", 2, "claim", "DB Schema", "schema migration"),
            ("c4", "s2", 0, "claim", "Test Guide", "pytest fixtures"),
            ("c5", "s2", 1, "prose", "Test Intro", "testing framework"),
            ("c6", "s1", 3, "prose", "Security", "authentication api"),
        ]

        for cid, sid, ordinal, kind, heading, text in test_chunks:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " citation_count, status, status_reason, ingested_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, ordinal, heading, kind, None,
                 text, text, len(text.split()), _sha256(text),
                 0, 0, "accepted", None, now),
            )

        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c1", 0, 0.8, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c2", 0, 0.7, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c3", 0, 0.6, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c4", 1, 0.9, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c5", 1, 0.5, now))
        conn.execute(
            "INSERT INTO chunk_topics VALUES (?,?,?,?)", ("c6", 2, 0.4, now))

        for tl, terms in [
            (0, [("sqlite", 0.5), ("query", 0.4), ("database", 0.3)]),
            (1, [("pytest", 0.5), ("test", 0.4), ("fixture", 0.3)]),
            (2, [("auth", 0.5), ("api", 0.4), ("security", 0.3)]),
        ]:
            for rank, (term, weight) in enumerate(terms):
                conn.execute(
                    "INSERT INTO topic_terms VALUES (?,?,?,?,?)",
                    (tl, rank, term, weight, now))

        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c1", "database", 0.85, now))
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c4", "testing", 0.90, now))

        conn.commit()

        # Check 1: summary returns valid metrics
        s = diversity_summary(conn)
        assert s["has_topics"] is True
        assert s["total_chunks_with_topics"] == 6
        assert s["n_topics"] == 3
        checks += 1

        # Check 2: entropy is positive (3 topics, not uniform)
        assert s["topic_entropy"] > 0
        checks += 1

        # Check 3: evenness bounded [0, 1]
        assert 0 < s["evenness"] <= 1.0
        checks += 1

        # Check 4: gini bounded [0, 1]
        assert 0 <= s["topic_gini"] <= 1.0
        checks += 1

        # Check 5: topic coverage is 100% (all 6 chunks assigned)
        assert s["topic_coverage_pct"] == 100.0
        checks += 1

        # Check 6: topic_source_diversity returns all topics
        tsd = topic_source_diversity(conn)
        assert len(tsd) == 3
        checks += 1

        # Check 7: topic 0 is dominated by s1 (3/3 chunks from s1)
        t0 = next(t for t in tsd if t["topic_label"] == 0)
        assert t0["source_count"] == 1
        assert t0["top_source_share"] == 1.0
        assert t0["dominated"] is True
        checks += 1

        # Check 8: topic 1 has only source s2
        t1 = next(t for t in tsd if t["topic_label"] == 1)
        assert t1["source_count"] == 1
        checks += 1

        # Check 9: topic 2 has 1 chunk (smallest topic)
        t2 = next(t for t in tsd if t["topic_label"] == 2)
        assert t2["chunk_count"] == 1
        checks += 1

        # Check 10: coverage_gaps finds topic 2 (1 chunk < default 5)
        gaps = coverage_gaps(conn)
        assert len(gaps) > 0
        gap_labels = {g["topic_label"] for g in gaps}
        assert 2 in gap_labels
        checks += 1

        # Check 11: all topics are gaps when min_chunks=10
        gaps_all = coverage_gaps(conn, min_chunks=10)
        assert len(gaps_all) == 3
        checks += 1

        # Check 12: no gaps when min_chunks=1
        gaps_none = coverage_gaps(conn, min_chunks=1)
        assert len(gaps_none) == 0
        checks += 1

        # Check 13: sorted by source_count ascending
        for i in range(len(tsd) - 1):
            assert tsd[i]["source_count"] <= tsd[i + 1]["source_count"]
        checks += 1

        # Check 14: empty corpus
        empty_dir = Path(td) / "empty"
        empty_dir.mkdir()
        ec = connect(str(empty_dir / "e.db"))
        init_schema(ec)
        _ensure_tables(ec)
        es = diversity_summary(ec)
        assert es["has_topics"] is False
        assert topic_source_diversity(ec) == []
        assert coverage_gaps(ec) == []
        ec.close()
        checks += 1

        conn.close()

    print(f"PASS diversity selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus diversity analysis")
    sub = parser.add_subparsers(dest="cmd")

    p_sum = sub.add_parser("summary", help="Corpus-wide diversity metrics")
    p_sum.add_argument("--db", default=str(DEFAULT_DB))
    p_sum.add_argument("--json", action="store_true")

    p_ts = sub.add_parser("topic-sources",
                          help="Per-topic source diversity")
    p_ts.add_argument("--db", default=str(DEFAULT_DB))
    p_ts.add_argument("--json", action="store_true")

    p_gap = sub.add_parser("gaps", help="Topics with few chunks")
    p_gap.add_argument("--db", default=str(DEFAULT_DB))
    p_gap.add_argument("--min-chunks", type=int, default=5)
    p_gap.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "summary":
        conn = connect(args.db)
        result = diversity_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        elif not result["has_topics"]:
            print("  No topic data available")
        else:
            print(f"  {result['n_topics']} topics across "
                  f"{result['total_chunks_with_topics']} chunks "
                  f"({result['topic_coverage_pct']:.0f}% coverage)")
            print(f"  Entropy: {result['topic_entropy']:.2f} / "
                  f"{result['max_entropy']:.2f} "
                  f"(evenness={result['evenness']:.2f})")
            print(f"  Gini: {result['topic_gini']:.3f}")
            print(f"  Avg topics/source: "
                  f"{result['avg_topics_per_source']:.1f}")
            if result["tag_entropy"]:
                print(f"  Tag entropy: {result['tag_entropy']:.2f} "
                      f"({result['n_tags']} tags)")
        conn.close()

    elif args.cmd == "topic-sources":
        conn = connect(args.db)
        results = topic_source_diversity(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  No topic data available")
        else:
            for r in results:
                terms = ", ".join(r["topic_terms"])
                dom = " [dominated]" if r["dominated"] else ""
                print(f"  Topic {r['topic_label']} ({terms}): "
                      f"{r['chunk_count']} chunks from "
                      f"{r['source_count']} sources{dom}")
        conn.close()

    elif args.cmd == "gaps":
        conn = connect(args.db)
        results = coverage_gaps(conn, min_chunks=args.min_chunks)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print(f"  No topics below {args.min_chunks} chunks")
        else:
            for r in results:
                terms = ", ".join(r["topic_terms"])
                print(f"  Topic {r['topic_label']} ({terms}): "
                      f"{r['chunk_count']} chunks "
                      f"(threshold: {r['below_threshold']})")
        conn.close()


if __name__ == "__main__":
    main()
