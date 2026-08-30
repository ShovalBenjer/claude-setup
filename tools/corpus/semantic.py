#!/usr/bin/env python3
"""Corpus semantic analysis: ML-based chunk classification and similarity.

Uses scikit-learn TF-IDF vectorizer and cosine similarity for:
  - Semantic chunk classification beyond regex heuristics
  - Finding semantically similar chunks across the corpus
  - Topic clustering using k-means on TF-IDF vectors
  - Outlier detection for chunks that don't fit any cluster

Requires: scikit-learn (pip install scikit-learn)

Usage:
    python tools/corpus/semantic.py classify [--db PATH] [--json]
    python tools/corpus/semantic.py similar --chunk CHUNK_ID [--db PATH] [--top-k N] [--json]
    python tools/corpus/semantic.py clusters [--db PATH] [--n-clusters N] [--json]
    python tools/corpus/semantic.py outliers [--db PATH] [--threshold F] [--json]
    python tools/corpus/semantic.py selftest
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
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


DOMAIN_DESCRIPTIONS = {
    "database": "sql database query schema migration index table join constraint transaction sqlite",
    "search": "search retrieval ranking fts5 fulltext tokenizer stemming porter bm25 rerank",
    "embedding": "embedding vector cosine similarity pca tfidf dense projection dimension neural",
    "dedup": "deduplication duplicate simhash hamming fingerprint shingle jaccard minhash collision",
    "citation": "citation reference provenance source bibliography footnote attribution lineage",
    "testing": "test pytest assert unittest coverage fixture mock selftest regression validation",
    "security": "security encryption authentication authorization oauth jwt token credential tls secret",
    "ml": "machine learning neural network model training inference classification transformer attention",
    "python": "python pip import def class decorator generator asyncio comprehension typing",
    "typescript": "typescript javascript npm node react next tailwind component jsx tsx",
    "rust": "rust cargo crate borrow ownership lifetime trait enum match unsafe memory",
    "devops": "docker kubernetes ci cd pipeline deploy container helm registry artifact",
    "api": "api rest graphql endpoint request response payload middleware route handler",
    "prompt": "prompt context token completion instruction few-shot chain-of-thought reasoning system",
    "agent": "agent skill persona autonomy tool orchestration swarm delegation planning workflow",
    "observability": "logging metrics tracing observability monitor alert dashboard span telemetry",
    "data": "csv json yaml toml xml parquet arrow serialization schema validation format",
    "git": "git commit branch merge rebase pull request diff stash hook worktree",
    "cloud": "cloudflare worker d1 r2 kv edge serverless lambda cdn wasm cloud",
    "quality": "quality lint format style convention review gate check standard compliance",
}


def _check_sklearn():
    if not HAS_SKLEARN:
        print("ERROR: scikit-learn is required. Install with: pip install scikit-learn",
              file=sys.stderr)
        sys.exit(1)


def _build_vectorizer(texts: list[str]) -> tuple:
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    return vectorizer, tfidf_matrix


def classify_chunks(conn) -> list[dict]:
    _check_sklearn()

    rows = conn.execute(
        "SELECT chunk_id, source_id, norm_text, kind, status "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()

    if not rows:
        return []

    chunk_texts = [row[2] for row in rows]
    domain_texts = list(DOMAIN_DESCRIPTIONS.values())
    domain_names = list(DOMAIN_DESCRIPTIONS.keys())

    all_texts = chunk_texts + domain_texts
    vectorizer, tfidf_matrix = _build_vectorizer(all_texts)

    chunk_vectors = tfidf_matrix[:len(chunk_texts)]
    domain_vectors = tfidf_matrix[len(chunk_texts):]

    similarities = cosine_similarity(chunk_vectors, domain_vectors)

    results = []
    for i, row in enumerate(rows):
        scores = similarities[i]
        top_indices = np.argsort(scores)[::-1][:3]
        top_domains = [
            {"domain": domain_names[idx], "score": round(float(scores[idx]), 4)}
            for idx in top_indices
            if scores[idx] > 0.01
        ]

        results.append({
            "chunk_id": row[0],
            "source_id": row[1],
            "kind": row[3],
            "status": row[4],
            "domains": top_domains,
        })

    results.sort(
        key=lambda r: r["domains"][0]["score"] if r["domains"] else 0,
        reverse=True,
    )
    return results


def find_similar(conn, chunk_id: str, top_k: int = 10) -> list[dict]:
    _check_sklearn()

    rows = conn.execute(
        "SELECT chunk_id, source_id, norm_text, kind, status "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()

    target_idx = None
    texts = []
    for i, row in enumerate(rows):
        texts.append(row[2])
        if row[0] == chunk_id:
            target_idx = i

    if target_idx is None:
        return []

    _, tfidf_matrix = _build_vectorizer(texts)
    target_vector = tfidf_matrix[target_idx]
    similarities = cosine_similarity(target_vector, tfidf_matrix).flatten()

    indices = np.argsort(similarities)[::-1]
    results = []
    for idx in indices:
        if idx == target_idx:
            continue
        if len(results) >= top_k:
            break
        row = rows[idx]
        results.append({
            "chunk_id": row[0],
            "source_id": row[1],
            "kind": row[3],
            "status": row[4],
            "similarity": round(float(similarities[idx]), 4),
        })

    return results


def cluster_chunks(conn, n_clusters: int = 8) -> list[dict]:
    _check_sklearn()

    rows = conn.execute(
        "SELECT chunk_id, source_id, norm_text, kind, status "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()

    if not rows:
        return []

    texts = [row[2] for row in rows]
    _, tfidf_matrix = _build_vectorizer(texts)

    actual_k = min(n_clusters, len(rows))
    if actual_k < 2:
        return [{"cluster": 0, "size": len(rows),
                 "members": [{"chunk_id": r[0], "kind": r[3]} for r in rows]}]

    kmeans = MiniBatchKMeans(n_clusters=actual_k, random_state=42, n_init=3)
    labels = kmeans.fit_predict(tfidf_matrix)

    clusters: dict[int, list[dict]] = {}
    for i, row in enumerate(rows):
        label = int(labels[i])
        clusters.setdefault(label, [])
        clusters[label].append({
            "chunk_id": row[0],
            "source_id": row[1],
            "kind": row[3],
            "status": row[4],
        })

    feature_names = _build_vectorizer(texts)[0].get_feature_names_out()
    results = []
    for label in sorted(clusters.keys()):
        center = kmeans.cluster_centers_[label]
        top_term_indices = np.argsort(center)[::-1][:5]
        top_terms = [feature_names[idx] for idx in top_term_indices
                     if center[idx] > 0]

        results.append({
            "cluster": label,
            "size": len(clusters[label]),
            "top_terms": top_terms,
            "members": clusters[label],
        })

    results.sort(key=lambda c: c["size"], reverse=True)
    return results


def find_outliers(conn, threshold: float = 0.15) -> list[dict]:
    _check_sklearn()

    rows = conn.execute(
        "SELECT chunk_id, source_id, norm_text, kind, status "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()

    if len(rows) < 3:
        return []

    texts = [row[2] for row in rows]
    _, tfidf_matrix = _build_vectorizer(texts)

    similarities = cosine_similarity(tfidf_matrix)
    np.fill_diagonal(similarities, 0)
    max_similarities = similarities.max(axis=1)

    outliers = []
    for i, row in enumerate(rows):
        max_sim = float(max_similarities[i])
        if max_sim < threshold:
            outliers.append({
                "chunk_id": row[0],
                "source_id": row[1],
                "kind": row[3],
                "status": row[4],
                "max_similarity": round(max_sim, 4),
            })

    outliers.sort(key=lambda o: o["max_similarity"])
    return outliers


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
            ("src1", "file:///a.md", "local_md", "Database Guide",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src2", "file:///b.md", "local_md", "Security Manual",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("b"), 200, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "SQLite", "prose", None,
             "sqlite database provides powerful sql query capabilities with "
             "schema migrations and index management. table constraints ensure "
             "data integrity through foreign key relationships and unique indexes.",
             "raw", 25, _sha256("c1"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "FTS5", "prose", None,
             "fts5 full text search engine with porter stemming tokenizer "
             "provides bm25 ranking for search results. retrieval performance "
             "is optimised through reranking with vector similarity.",
             "raw", 22, _sha256("c2"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src2", 0, "Auth", "prose", None,
             "oauth authentication with jwt tokens provides secure api access. "
             "tls encryption protects credentials and secrets in transit. "
             "authorization middleware validates each api request.",
             "raw", 24, _sha256("c3"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src2", 1, "ML", "prose", None,
             "machine learning model training uses neural network transformer "
             "architecture with attention mechanism. classification inference "
             "runs through the trained model for prediction.",
             "raw", 20, _sha256("c4"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "src1", 2, "Similar DB", "prose", None,
             "database query optimisation uses sql index hints and schema "
             "analysis. table scan performance depends on constraint evaluation "
             "and join strategy selection.",
             "raw", 20, _sha256("c5"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "src2", 2, "Old", "prose", None,
             "this chunk is superseded and should be ignored completely.",
             "raw", 9, _sha256("c6"), 0, 0, "superseded", "old", now),
        )
        conn.commit()

        # Check 1: classify returns results for active chunks
        classified = classify_chunks(conn)
        assert len(classified) == 5, f"expected 5 classified, got {len(classified)}"
        checks += 1

        # Check 2: database chunk gets database domain
        c1_result = next(r for r in classified if r["chunk_id"] == "c1")
        c1_domains = [d["domain"] for d in c1_result["domains"]]
        assert "database" in c1_domains, \
            f"database chunk should classify as database, got {c1_domains}"
        checks += 1

        # Check 3: security chunk gets security domain
        c3_result = next(r for r in classified if r["chunk_id"] == "c3")
        c3_domains = [d["domain"] for d in c3_result["domains"]]
        assert "security" in c3_domains or "api" in c3_domains, \
            f"security chunk should classify as security or api, got {c3_domains}"
        checks += 1

        # Check 4: superseded chunk excluded
        superseded_ids = [r["chunk_id"] for r in classified]
        assert "c6" not in superseded_ids
        checks += 1

        # Check 5: domains sorted by score descending
        for r in classified:
            if len(r["domains"]) > 1:
                scores = [d["score"] for d in r["domains"]]
                assert scores == sorted(scores, reverse=True)
        checks += 1

        # Check 6: find_similar returns results
        similar = find_similar(conn, "c1", top_k=3)
        assert len(similar) > 0
        checks += 1

        # Check 7: most similar to c1 should be c5 (both database topics)
        assert similar[0]["chunk_id"] == "c5", \
            f"expected c5 most similar to c1, got {similar[0]['chunk_id']}"
        checks += 1

        # Check 8: target chunk not in similar results
        similar_ids = [s["chunk_id"] for s in similar]
        assert "c1" not in similar_ids
        checks += 1

        # Check 9: similarity scores in [0, 1]
        for s in similar:
            assert 0 <= s["similarity"] <= 1.0
        checks += 1

        # Check 10: find_similar for nonexistent chunk returns empty
        assert find_similar(conn, "nonexistent") == []
        checks += 1

        # Check 11: cluster_chunks returns clusters
        clusters = cluster_chunks(conn, n_clusters=3)
        assert len(clusters) > 0
        total_members = sum(c["size"] for c in clusters)
        assert total_members == 5
        checks += 1

        # Check 12: clusters have top_terms
        for c in clusters:
            assert "top_terms" in c
            assert isinstance(c["top_terms"], list)
        checks += 1

        # Check 13: find_outliers returns a list
        outliers = find_outliers(conn, threshold=0.05)
        assert isinstance(outliers, list)
        checks += 1

        # Check 14: outlier max_similarity below threshold
        for o in outliers:
            assert o["max_similarity"] < 0.05
        checks += 1

        # Check 15: JSON serialization works
        j = json.dumps(classified, indent=2)
        parsed = json.loads(j)
        assert len(parsed) == 5
        checks += 1

        # Check 16: empty corpus returns empty results
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert classify_chunks(empty_conn) == []
        assert cluster_chunks(empty_conn) == []
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS semantic selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus semantic analysis (ML-based)")
    sub = parser.add_subparsers(dest="cmd")

    p_cls = sub.add_parser("classify", help="Classify chunks by domain")
    p_cls.add_argument("--db", default=str(DEFAULT_DB))
    p_cls.add_argument("--json", action="store_true")

    p_sim = sub.add_parser("similar", help="Find similar chunks")
    p_sim.add_argument("--chunk", required=True, dest="chunk_id")
    p_sim.add_argument("--db", default=str(DEFAULT_DB))
    p_sim.add_argument("--top-k", type=int, default=10)
    p_sim.add_argument("--json", action="store_true")

    p_clu = sub.add_parser("clusters", help="Cluster chunks by topic")
    p_clu.add_argument("--db", default=str(DEFAULT_DB))
    p_clu.add_argument("--n-clusters", type=int, default=8)
    p_clu.add_argument("--json", action="store_true")

    p_out = sub.add_parser("outliers", help="Find topic outliers")
    p_out.add_argument("--db", default=str(DEFAULT_DB))
    p_out.add_argument("--threshold", type=float, default=0.15)
    p_out.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _check_sklearn()
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    _check_sklearn()
    conn = connect(args.db)

    if args.cmd == "classify":
        results = classify_chunks(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  No chunks to classify.")
            else:
                print(f"  {len(results)} chunk(s) classified:")
                for r in results[:50]:
                    domains_str = ", ".join(
                        f"{d['domain']}={d['score']:.3f}"
                        for d in r["domains"]
                    )
                    print(f"    {r['chunk_id'][:12]}  {r['kind']:6s}  "
                          f"[{domains_str}]")

    elif args.cmd == "similar":
        results = find_similar(conn, args.chunk_id, top_k=args.top_k)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"  No similar chunks found for '{args.chunk_id}'.")
            else:
                print(f"  {len(results)} similar chunk(s):")
                for r in results:
                    print(f"    {r['chunk_id'][:12]}  sim={r['similarity']:.3f}  "
                          f"{r['kind']:6s}  {r['status']}")

    elif args.cmd == "clusters":
        results = cluster_chunks(conn, n_clusters=args.n_clusters)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for c in results:
                terms = ", ".join(c["top_terms"][:5])
                print(f"  Cluster {c['cluster']:2d}  "
                      f"size={c['size']:3d}  [{terms}]")

    elif args.cmd == "outliers":
        results = find_outliers(conn, threshold=args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  No outliers found.")
            else:
                print(f"  {len(results)} outlier(s):")
                for o in results:
                    print(f"    {o['chunk_id'][:12]}  "
                          f"max_sim={o['max_similarity']:.3f}  "
                          f"{o['kind']:6s}  {o['status']}")

    conn.close()


if __name__ == "__main__":
    main()
