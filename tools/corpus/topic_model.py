#!/usr/bin/env python3
"""Corpus topic model: unsupervised topic discovery via NMF.

Decomposes the corpus TF-IDF matrix using Non-negative Matrix
Factorization to discover latent topics without predefined vocabularies.
Complements tagger.py (keyword-based) and semantic.py (predefined
domain descriptions) by finding emergent structure in the corpus.

Usage:
    python tools/corpus/topic_model.py fit [--db PATH] [--n-topics N] [--dry-run]
    python tools/corpus/topic_model.py topics [--db PATH] [--json]
    python tools/corpus/topic_model.py lookup --chunk-id CID [--db PATH] [--json]
    python tools/corpus/topic_model.py stats [--db PATH] [--json]
    python tools/corpus/topic_model.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

try:
    import numpy as np
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def _check_sklearn():
    if not HAS_SKLEARN:
        print("ERROR: scikit-learn is required.", file=sys.stderr)
        sys.exit(1)


def _now_utc():
    import datetime
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_table(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunk_topics (
            chunk_id      TEXT NOT NULL REFERENCES chunks(chunk_id),
            topic_label   INTEGER NOT NULL,
            topic_weight  REAL NOT NULL,
            fitted_utc    TEXT NOT NULL,
            PRIMARY KEY (chunk_id)
        );
        CREATE INDEX IF NOT EXISTS idx_chunk_topics_label
            ON chunk_topics(topic_label);

        CREATE TABLE IF NOT EXISTS topic_terms (
            topic_label   INTEGER NOT NULL,
            term_rank     INTEGER NOT NULL,
            term          TEXT NOT NULL,
            term_weight   REAL NOT NULL,
            fitted_utc    TEXT NOT NULL,
            PRIMARY KEY (topic_label, term_rank)
        );
    """)


def _load_chunks(conn):
    return conn.execute(
        "SELECT chunk_id, norm_text FROM chunks "
        "WHERE status != 'superseded'"
    ).fetchall()


def fit_topics(conn, n_topics: int = 10, dry_run: bool = False,
               top_terms: int = 8) -> dict:
    _check_sklearn()
    _ensure_table(conn)

    rows = _load_chunks(conn)
    if not rows:
        return {"chunk_count": 0, "n_topics": 0, "dry_run": dry_run}

    chunk_ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]

    actual_k = min(n_topics, len(rows))
    if actual_k < 2:
        return {"chunk_count": len(rows), "n_topics": 0,
                "reason": "too_few_chunks", "dry_run": dry_run}

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=2 if len(texts) > 20 else 1,
        max_df=0.95,
        sublinear_tf=True,
    )
    tfidf = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    model = NMF(
        n_components=actual_k,
        random_state=42,
        max_iter=300,
        init="nndsvda",
    )
    W = model.fit_transform(tfidf)
    H = model.components_

    assignments = np.argmax(W, axis=1)
    weights = np.max(W, axis=1)

    topic_terms_data = []
    for t in range(actual_k):
        top_idx = np.argsort(H[t])[::-1][:top_terms]
        for rank, idx in enumerate(top_idx):
            if H[t][idx] > 0:
                topic_terms_data.append({
                    "topic_label": int(t),
                    "term_rank": rank,
                    "term": str(feature_names[idx]),
                    "term_weight": round(float(H[t][idx]), 4),
                })

    topic_sizes = {}
    for label in assignments:
        topic_sizes[int(label)] = topic_sizes.get(int(label), 0) + 1

    if dry_run:
        return {
            "chunk_count": len(rows),
            "n_topics": actual_k,
            "topic_sizes": topic_sizes,
            "dry_run": True,
        }

    now = _now_utc()
    conn.execute("DELETE FROM chunk_topics")
    conn.execute("DELETE FROM topic_terms")

    for i, cid in enumerate(chunk_ids):
        conn.execute(
            "INSERT INTO chunk_topics "
            "(chunk_id, topic_label, topic_weight, fitted_utc) "
            "VALUES (?, ?, ?, ?)",
            (cid, int(assignments[i]), round(float(weights[i]), 4), now),
        )

    for td in topic_terms_data:
        conn.execute(
            "INSERT INTO topic_terms "
            "(topic_label, term_rank, term, term_weight, fitted_utc) "
            "VALUES (?, ?, ?, ?, ?)",
            (td["topic_label"], td["term_rank"],
             td["term"], td["term_weight"], now),
        )

    conn.commit()

    return {
        "chunk_count": len(rows),
        "n_topics": actual_k,
        "topic_sizes": topic_sizes,
        "dry_run": False,
    }


def list_topics(conn) -> list[dict]:
    _ensure_table(conn)

    topics = conn.execute(
        "SELECT topic_label, COUNT(*) as size "
        "FROM chunk_topics GROUP BY topic_label "
        "ORDER BY size DESC"
    ).fetchall()

    results = []
    for t in topics:
        label = t[0]
        terms = conn.execute(
            "SELECT term, term_weight FROM topic_terms "
            "WHERE topic_label = ? ORDER BY term_rank ASC",
            (label,),
        ).fetchall()
        results.append({
            "topic_label": label,
            "size": t[1],
            "terms": [{"term": r[0], "weight": r[1]} for r in terms],
        })

    return results


def lookup_chunk_topic(conn, chunk_id: str) -> dict | None:
    _ensure_table(conn)

    row = conn.execute(
        "SELECT topic_label, topic_weight, fitted_utc "
        "FROM chunk_topics WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchone()
    if not row:
        return None

    terms = conn.execute(
        "SELECT term, term_weight FROM topic_terms "
        "WHERE topic_label = ? ORDER BY term_rank ASC",
        (row[0],),
    ).fetchall()

    return {
        "chunk_id": chunk_id,
        "topic_label": row[0],
        "topic_weight": row[1],
        "fitted_utc": row[2],
        "terms": [{"term": r[0], "weight": r[1]} for r in terms],
    }


def topic_stats(conn) -> dict:
    _ensure_table(conn)

    total = conn.execute(
        "SELECT COUNT(*) FROM chunk_topics"
    ).fetchone()[0]

    if total == 0:
        return {"fitted": False}

    n_topics = conn.execute(
        "SELECT COUNT(DISTINCT topic_label) FROM chunk_topics"
    ).fetchone()[0]

    avg_weight = conn.execute(
        "SELECT AVG(topic_weight) FROM chunk_topics"
    ).fetchone()[0]

    sizes = conn.execute(
        "SELECT COUNT(*) FROM chunk_topics GROUP BY topic_label"
    ).fetchall()
    size_list = [r[0] for r in sizes]

    fitted_utc = conn.execute(
        "SELECT fitted_utc FROM chunk_topics LIMIT 1"
    ).fetchone()[0]

    return {
        "fitted": True,
        "n_topics": n_topics,
        "total_chunks": total,
        "avg_topic_weight": round(float(avg_weight), 4),
        "min_topic_size": min(size_list),
        "max_topic_size": max(size_list),
        "fitted_utc": fitted_utc,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    _check_sklearn()
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

        test_chunks = [
            ("c1", 0, "prose", "SQL Databases",
             "sqlite provides sql query capabilities with schema migrations "
             "and index management for data storage retrieval join constraint"),
            ("c2", 1, "prose", "More SQL",
             "postgresql database table query select insert update delete "
             "index constraint foreign key transaction isolation level"),
            ("c3", 2, "prose", "Python Testing",
             "pytest framework provides fixtures assertions parametrize "
             "coverage report unittest mock patching test runner suite"),
            ("c4", 3, "prose", "Unit Tests",
             "test driven development unit integration testing assert "
             "fixture setup teardown parameterized tests coverage report"),
            ("c5", 4, "prose", "Security Auth",
             "oauth2 authentication jwt bearer tokens authorization "
             "api security tls encryption credential management secret"),
            ("c6", 5, "prose", "API Security",
             "api key rotation security headers cors policy authentication "
             "rate limiting token validation jwt verification endpoint"),
            ("c7", 6, "prose", "Deployment",
             "docker container kubernetes helm chart deployment pipeline "
             "ci cd continuous integration delivery artifact registry"),
            ("c8", 7, "prose", "Cloud Infra",
             "cloudflare workers serverless edge computing lambda function "
             "cdn deploy container orchestration scaling load balancer"),
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
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " citation_count, status, status_reason, ingested_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c9", "src1", 8, "Old", "prose", None,
             "superseded content", "superseded content", 2,
             _sha256("superseded"), 0, 0, "superseded", "old", now),
        )
        conn.commit()

        # Check 1: dry run does not persist
        result = fit_topics(conn, n_topics=3, dry_run=True)
        assert result["dry_run"] is True
        assert result["chunk_count"] == 8
        assert result["n_topics"] == 3
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_topics"
        ).fetchone()[0]
        assert count == 0, f"dry run persisted {count} rows"
        checks += 1

        # Check 2: fit persists assignments
        result = fit_topics(conn, n_topics=3, dry_run=False)
        assert result["chunk_count"] == 8
        assert result["n_topics"] == 3
        assert result["dry_run"] is False
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_topics"
        ).fetchone()[0]
        assert count == 8, f"expected 8 rows, got {count}"
        checks += 1

        # Check 3: every chunk has exactly one topic
        distinct = conn.execute(
            "SELECT COUNT(DISTINCT chunk_id) FROM chunk_topics"
        ).fetchone()[0]
        assert distinct == 8
        checks += 1

        # Check 4: topic labels are in [0, n_topics)
        labels = conn.execute(
            "SELECT DISTINCT topic_label FROM chunk_topics"
        ).fetchall()
        for row in labels:
            assert 0 <= row[0] < 3, f"label {row[0]} out of range"
        checks += 1

        # Check 5: topic_terms populated
        term_count = conn.execute(
            "SELECT COUNT(*) FROM topic_terms"
        ).fetchone()[0]
        assert term_count > 0, "no topic terms stored"
        checks += 1

        # Check 6: list_topics returns all topics with terms
        topics = list_topics(conn)
        assert len(topics) == 3
        for t in topics:
            assert t["size"] > 0
            assert len(t["terms"]) > 0
        checks += 1

        # Check 7: topic sizes sum to chunk count
        total_size = sum(t["size"] for t in topics)
        assert total_size == 8, f"sizes sum to {total_size}, expected 8"
        checks += 1

        # Check 8: lookup returns assignment for known chunk
        info = lookup_chunk_topic(conn, "c1")
        assert info is not None
        assert info["topic_label"] >= 0
        assert info["topic_weight"] > 0
        assert len(info["terms"]) > 0
        checks += 1

        # Check 9: lookup returns None for unknown chunk
        info = lookup_chunk_topic(conn, "nonexistent")
        assert info is None
        checks += 1

        # Check 10: superseded chunks excluded
        info = lookup_chunk_topic(conn, "c9")
        assert info is None
        checks += 1

        # Check 11: stats reports correctly
        stats = topic_stats(conn)
        assert stats["fitted"] is True
        assert stats["n_topics"] == 3
        assert stats["total_chunks"] == 8
        assert stats["avg_topic_weight"] > 0
        checks += 1

        # Check 12: re-fit replaces previous assignments
        result2 = fit_topics(conn, n_topics=4, dry_run=False)
        assert result2["n_topics"] == 4
        count = conn.execute(
            "SELECT COUNT(*) FROM chunk_topics"
        ).fetchone()[0]
        assert count == 8
        labels2 = conn.execute(
            "SELECT DISTINCT topic_label FROM chunk_topics"
        ).fetchall()
        for row in labels2:
            assert 0 <= row[0] < 4
        checks += 1

        # Check 13: empty corpus
        empty_dir = Path(td) / "empty_sub"
        empty_dir.mkdir()
        empty_conn = connect(str(empty_dir / "empty.db"))
        init_schema(empty_conn)
        result = fit_topics(empty_conn, n_topics=5, dry_run=False)
        assert result["chunk_count"] == 0
        assert result["n_topics"] == 0
        stats = topic_stats(empty_conn)
        assert stats["fitted"] is False
        empty_conn.close()
        checks += 1

        # Check 14: term weights are positive
        terms = conn.execute(
            "SELECT term_weight FROM topic_terms"
        ).fetchall()
        for row in terms:
            assert row[0] > 0, f"non-positive weight: {row[0]}"
        checks += 1

        conn.close()

    print(f"PASS topic_model selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus topic model")
    sub = parser.add_subparsers(dest="cmd")

    p_fit = sub.add_parser("fit", help="Fit NMF topic model")
    p_fit.add_argument("--db", default=str(DEFAULT_DB))
    p_fit.add_argument("--n-topics", type=int, default=10)
    p_fit.add_argument("--dry-run", action="store_true")

    p_topics = sub.add_parser("topics", help="List discovered topics")
    p_topics.add_argument("--db", default=str(DEFAULT_DB))
    p_topics.add_argument("--json", action="store_true")

    p_lookup = sub.add_parser("lookup",
                              help="Look up topic for a chunk")
    p_lookup.add_argument("--chunk-id", required=True)
    p_lookup.add_argument("--db", default=str(DEFAULT_DB))
    p_lookup.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats", help="Topic model statistics")
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

    if args.cmd == "fit":
        _check_sklearn()
        conn = connect(args.db)
        result = fit_topics(conn, n_topics=args.n_topics,
                            dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "FIT"
        print(f"  {mode}: {result['chunk_count']} chunks, "
              f"{result['n_topics']} topics")
        if "topic_sizes" in result:
            for label, size in sorted(result["topic_sizes"].items()):
                print(f"    topic {label}: {size} chunks")
        conn.close()

    elif args.cmd == "topics":
        conn = connect(args.db)
        topics = list_topics(conn)
        if args.json:
            print(json.dumps(topics, indent=2))
        else:
            if not topics:
                print("  No topics fitted yet")
            else:
                for t in topics:
                    terms_str = ", ".join(
                        d["term"] for d in t["terms"][:5]
                    )
                    print(f"  Topic {t['topic_label']} "
                          f"({t['size']} chunks): {terms_str}")
        conn.close()

    elif args.cmd == "lookup":
        conn = connect(args.db)
        info = lookup_chunk_topic(conn, args.chunk_id)
        if args.json:
            print(json.dumps(info, indent=2))
        elif info is None:
            print(f"  Chunk {args.chunk_id}: no topic assignment")
        else:
            terms_str = ", ".join(
                d["term"] for d in info["terms"][:5]
            )
            print(f"  Chunk {args.chunk_id}: topic {info['topic_label']} "
                  f"(weight={info['topic_weight']:.3f})")
            print(f"    Terms: {terms_str}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = topic_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        elif not stats["fitted"]:
            print("  No topic model fitted yet")
        else:
            print(f"  {stats['n_topics']} topics across "
                  f"{stats['total_chunks']} chunks")
            print(f"  Avg weight: {stats['avg_topic_weight']:.3f}")
            print(f"  Topic sizes: {stats['min_topic_size']}"
                  f"--{stats['max_topic_size']}")
            print(f"  Fitted: {stats['fitted_utc']}")
        conn.close()


if __name__ == "__main__":
    main()
