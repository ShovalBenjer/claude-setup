#!/usr/bin/env python3
"""Corpus auto-tagger: assign topic tags to chunks using TF-IDF scoring.

Builds a vocabulary of domain terms and scores each chunk against them,
assigning the top-matching tags. Uses numpy-only TF-IDF (no sklearn
dependency) to rank term relevance per chunk.

Designed to bridge regex-based reclassification and full semantic
classification by providing a lightweight, transparent tagging layer.

Usage:
    python tools/corpus/tagger.py tag [--db PATH] [--top-k N] [--min-score F] [--json]
    python tools/corpus/tagger.py vocab [--json]
    python tools/corpus/tagger.py chunks --tag TAG [--db PATH] [--json]
    python tools/corpus/tagger.py stats [--db PATH] [--json]
    python tools/corpus/tagger.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

DOMAIN_VOCAB: dict[str, list[str]] = {
    "database": ["sqlite", "sql", "database", "query", "index", "table", "schema",
                  "migration", "transaction", "constraint"],
    "search": ["fts5", "search", "retrieval", "ranking", "rerank", "tokenizer",
               "stemming", "porter", "fulltext", "bm25"],
    "embedding": ["embedding", "vector", "cosine", "similarity", "pca", "tfidf",
                   "ngram", "dimension", "projection", "dense"],
    "dedup": ["dedup", "deduplication", "duplicate", "simhash", "hamming",
              "fingerprint", "shingle", "jaccard", "minhash", "collision"],
    "citation": ["citation", "cite", "reference", "provenance", "source",
                  "bibliography", "footnote"],
    "testing": ["test", "testing", "pytest", "assert", "unittest", "coverage",
                "fixture", "mock", "selftest", "regression"],
    "security": ["security", "encryption", "authentication", "authorization",
                 "oauth", "jwt", "token", "credential", "secret", "tls"],
    "ml": ["machine learning", "neural", "model", "training", "inference",
           "classification", "regression", "transformer", "attention", "gradient"],
    "python": ["python", "pip", "venv", "import", "def", "class", "decorator",
               "comprehension", "generator", "asyncio"],
    "typescript": ["typescript", "javascript", "npm", "node", "react", "next",
                   "tailwind", "component", "jsx", "tsx"],
    "rust": ["rust", "cargo", "crate", "borrow", "ownership", "lifetime",
             "trait", "enum", "match", "unsafe"],
    "devops": ["docker", "kubernetes", "ci", "cd", "pipeline", "deploy",
               "container", "helm", "registry", "artifact"],
    "api": ["api", "rest", "graphql", "endpoint", "request", "response",
            "payload", "middleware", "route", "handler"],
    "prompt": ["prompt", "context", "token", "completion", "system",
               "instruction", "few-shot", "chain-of-thought", "reasoning"],
    "agent": ["agent", "skill", "persona", "autonomy", "tool",
              "orchestration", "swarm", "delegation", "planning"],
    "observability": ["logging", "metrics", "tracing", "observability",
                      "monitor", "alert", "dashboard", "span", "telemetry"],
    "data": ["csv", "json", "yaml", "toml", "xml", "parquet", "arrow",
             "serialization", "schema", "validation"],
    "git": ["git", "commit", "branch", "merge", "rebase", "pull request",
            "diff", "stash", "hook", "worktree"],
    "cloud": ["cloudflare", "worker", "d1", "r2", "kv", "edge",
              "serverless", "lambda", "cdn", "wasm"],
    "quality": ["quality", "lint", "format", "style", "convention",
                "review", "gate", "check", "standard", "compliance"],
}

_WORD_RE = re.compile(r"[a-z][a-z0-9._-]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _compute_idf(docs: list[list[str]], vocab_terms: set[str]) -> dict[str, float]:
    n = len(docs)
    if n == 0:
        return {}
    df: Counter[str] = Counter()
    for doc in docs:
        unique = set(doc) & vocab_terms
        for term in unique:
            df[term] += 1
    return {term: math.log((n + 1) / (count + 1)) + 1
            for term, count in df.items()}


def _score_chunk(tokens: list[str], domain: str, terms: list[str],
                 idf: dict[str, float]) -> float:
    if not tokens:
        return 0.0
    tf = Counter(tokens)
    total = len(tokens)
    score = 0.0
    for term in terms:
        term_tokens = term.lower().split()
        if len(term_tokens) == 1:
            t = term_tokens[0]
            if t in tf:
                term_tf = tf[t] / total
                term_idf = idf.get(t, 1.0)
                score += term_tf * term_idf
        else:
            text_joined = " ".join(tokens)
            if term.lower() in text_joined:
                score += idf.get(term_tokens[0], 1.0) * 0.5
    return round(score, 4)


def tag_chunks(conn, top_k: int = 3,
               min_score: float = 0.01) -> list[dict]:
    rows = conn.execute(
        "SELECT chunk_id, source_id, norm_text, kind, status "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()

    all_vocab_terms: set[str] = set()
    for terms in DOMAIN_VOCAB.values():
        for term in terms:
            for t in term.lower().split():
                all_vocab_terms.add(t)

    all_docs = [_tokenize(row[2]) for row in rows]
    idf = _compute_idf(all_docs, all_vocab_terms)

    results = []
    for i, row in enumerate(rows):
        tokens = all_docs[i]
        scores: list[tuple[str, float]] = []
        for domain, terms in DOMAIN_VOCAB.items():
            s = _score_chunk(tokens, domain, terms, idf)
            if s >= min_score:
                scores.append((domain, s))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_tags = scores[:top_k]

        if top_tags:
            results.append({
                "chunk_id": row[0],
                "source_id": row[1],
                "kind": row[3],
                "status": row[4],
                "tags": [{"tag": t[0], "score": t[1]} for t in top_tags],
            })

    results.sort(key=lambda r: r["tags"][0]["score"] if r["tags"] else 0,
                 reverse=True)
    return results


def chunks_by_tag(conn, tag: str) -> list[dict]:
    if tag not in DOMAIN_VOCAB:
        return []

    rows = conn.execute(
        "SELECT chunk_id, source_id, norm_text, kind, status "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()

    all_vocab_terms: set[str] = set()
    for terms in DOMAIN_VOCAB.values():
        for term in terms:
            for t in term.lower().split():
                all_vocab_terms.add(t)

    all_docs = [_tokenize(row[2]) for row in rows]
    idf = _compute_idf(all_docs, all_vocab_terms)

    terms = DOMAIN_VOCAB[tag]
    results = []
    for i, row in enumerate(rows):
        tokens = all_docs[i]
        score = _score_chunk(tokens, tag, terms, idf)
        if score > 0:
            results.append({
                "chunk_id": row[0],
                "source_id": row[1],
                "kind": row[3],
                "status": row[4],
                "score": score,
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def tag_stats(conn) -> dict:
    tagged = tag_chunks(conn, top_k=3, min_score=0.01)

    tag_counts: Counter[str] = Counter()
    for r in tagged:
        for t in r["tags"]:
            tag_counts[t["tag"]] += 1

    total = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status != 'superseded'"
    ).fetchone()[0]

    untagged = total - len(tagged)

    return {
        "total_active_chunks": total,
        "tagged_chunks": len(tagged),
        "untagged_chunks": untagged,
        "tag_coverage": round(len(tagged) / total, 3) if total else 0,
        "tag_distribution": dict(tag_counts.most_common()),
        "vocab_domains": len(DOMAIN_VOCAB),
        "vocab_total_terms": sum(len(v) for v in DOMAIN_VOCAB.values()),
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "SQLite Guide",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src2", "file:///b.md", "local_md", "Python Testing",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("b"), 200, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "SQLite", "prose", None,
             "sqlite database uses fts5 for full text search with porter "
             "stemming tokenizer. the query engine supports bm25 ranking "
             "and reranking with vector similarity scores.",
             "raw", 25, _sha256("c1"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src2", 0, "Testing", "prose", None,
             "python pytest framework provides test fixtures and assertions. "
             "coverage reports measure code quality. unittest mock objects "
             "help isolate components during regression testing.",
             "raw", 22, _sha256("c2"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 1, "Embedding", "claim", None,
             "embedding vectors use cosine similarity for nearest neighbor "
             "retrieval. pca projection reduces dimensionality from 768 to "
             "256. tfidf ngram features provide a baseline without neural models.",
             "raw", 28, _sha256("c3"), 0, 1, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src2", 1, "Security", "prose", None,
             "oauth authentication with jwt tokens provides secure api access. "
             "tls encryption protects credentials in transit. authorization "
             "middleware validates each request.",
             "raw", 20, _sha256("c4"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "src1", 2, "Old", "prose", None,
             "this chunk is superseded and should be ignored.",
             "raw", 9, _sha256("c5"), 0, 0, "superseded", "old", now),
        )
        conn.commit()

        # Check 1: tag_chunks returns results
        tagged = tag_chunks(conn, top_k=3, min_score=0.001)
        assert len(tagged) > 0, "should tag at least some chunks"
        checks += 1

        # Check 2: sqlite chunk gets database/search tags
        c1_tags = next((r for r in tagged if r["chunk_id"] == "c1"), None)
        assert c1_tags is not None
        tag_names = [t["tag"] for t in c1_tags["tags"]]
        assert "database" in tag_names or "search" in tag_names, \
            f"sqlite chunk should get database or search tag, got {tag_names}"
        checks += 1

        # Check 3: testing chunk gets testing tag
        c2_tags = next((r for r in tagged if r["chunk_id"] == "c2"), None)
        assert c2_tags is not None
        tag_names = [t["tag"] for t in c2_tags["tags"]]
        assert "testing" in tag_names, \
            f"testing chunk should get testing tag, got {tag_names}"
        checks += 1

        # Check 4: embedding chunk gets embedding tag
        c3_tags = next((r for r in tagged if r["chunk_id"] == "c3"), None)
        assert c3_tags is not None
        tag_names = [t["tag"] for t in c3_tags["tags"]]
        assert "embedding" in tag_names, \
            f"embedding chunk should get embedding tag, got {tag_names}"
        checks += 1

        # Check 5: security chunk gets security tag
        c4_tags = next((r for r in tagged if r["chunk_id"] == "c4"), None)
        assert c4_tags is not None
        tag_names = [t["tag"] for t in c4_tags["tags"]]
        assert "security" in tag_names, \
            f"security chunk should get security tag, got {tag_names}"
        checks += 1

        # Check 6: superseded chunk excluded
        c5_result = [r for r in tagged if r["chunk_id"] == "c5"]
        assert len(c5_result) == 0, "superseded chunk should be excluded"
        checks += 1

        # Check 7: tags are sorted by score descending within each chunk
        for r in tagged:
            scores = [t["score"] for t in r["tags"]]
            assert scores == sorted(scores, reverse=True), \
                f"tags should be sorted by score desc: {scores}"
        checks += 1

        # Check 8: top_k limits tag count
        tagged_k1 = tag_chunks(conn, top_k=1, min_score=0.001)
        for r in tagged_k1:
            assert len(r["tags"]) <= 1
        checks += 1

        # Check 9: min_score filters low-scoring tags
        tagged_high = tag_chunks(conn, top_k=10, min_score=100.0)
        assert len(tagged_high) == 0, "very high min_score should filter everything"
        checks += 1

        # Check 10: chunks_by_tag finds database chunks
        db_chunks = chunks_by_tag(conn, "database")
        assert len(db_chunks) > 0
        assert any(c["chunk_id"] == "c1" for c in db_chunks)
        checks += 1

        # Check 11: chunks_by_tag for unknown tag returns empty
        unknown = chunks_by_tag(conn, "nonexistent_tag")
        assert unknown == []
        checks += 1

        # Check 12: chunks_by_tag sorted by score descending
        if len(db_chunks) > 1:
            scores = [c["score"] for c in db_chunks]
            assert scores == sorted(scores, reverse=True)
        checks += 1

        # Check 13: tag_stats returns expected structure
        stats = tag_stats(conn)
        assert "total_active_chunks" in stats
        assert "tagged_chunks" in stats
        assert "tag_distribution" in stats
        assert stats["total_active_chunks"] == 4
        checks += 1

        # Check 14: vocab command returns all domains
        assert len(DOMAIN_VOCAB) == 20
        checks += 1

        # Check 15: JSON serialization works
        j = json.dumps(tagged, indent=2)
        parsed = json.loads(j)
        assert len(parsed) > 0
        checks += 1

        # Check 16: empty corpus returns empty results
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert tag_chunks(empty_conn) == []
        empty_stats = tag_stats(empty_conn)
        assert empty_stats["total_active_chunks"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS tagger selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus auto-tagger")
    sub = parser.add_subparsers(dest="cmd")

    p_tag = sub.add_parser("tag", help="Auto-tag chunks with topic labels")
    p_tag.add_argument("--db", default=str(DEFAULT_DB))
    p_tag.add_argument("--top-k", type=int, default=3)
    p_tag.add_argument("--min-score", type=float, default=0.01)
    p_tag.add_argument("--json", action="store_true")

    p_vocab = sub.add_parser("vocab", help="Show domain vocabulary")
    p_vocab.add_argument("--json", action="store_true")

    p_chunks = sub.add_parser("chunks", help="Find chunks by tag")
    p_chunks.add_argument("--tag", required=True)
    p_chunks.add_argument("--db", default=str(DEFAULT_DB))
    p_chunks.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats", help="Tagging statistics")
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

    if args.cmd == "vocab":
        if args.json:
            print(json.dumps(DOMAIN_VOCAB, indent=2))
        else:
            for domain, terms in sorted(DOMAIN_VOCAB.items()):
                print(f"  {domain:16s}  ({len(terms)} terms)  "
                      f"{', '.join(terms[:5])}...")
        return

    conn = connect(args.db)

    if args.cmd == "tag":
        results = tag_chunks(conn, top_k=args.top_k,
                             min_score=args.min_score)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  No chunks tagged.")
            else:
                print(f"  {len(results)} chunk(s) tagged:")
                for r in results[:50]:
                    tags_str = ", ".join(
                        f"{t['tag']}={t['score']:.3f}" for t in r["tags"]
                    )
                    print(f"    {r['chunk_id'][:12]}  {r['kind']:6s}  "
                          f"[{tags_str}]")

    elif args.cmd == "chunks":
        results = chunks_by_tag(conn, tag=args.tag)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"  No chunks found for tag '{args.tag}'.")
            else:
                print(f"  {len(results)} chunk(s) for '{args.tag}':")
                for r in results[:50]:
                    print(f"    {r['chunk_id'][:12]}  {r['kind']:6s}  "
                          f"score={r['score']:.3f}  {r['status']}")

    elif args.cmd == "stats":
        stats = tag_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Active chunks:    {stats['total_active_chunks']}")
            print(f"  Tagged chunks:    {stats['tagged_chunks']}")
            print(f"  Untagged:         {stats['untagged_chunks']}")
            print(f"  Tag coverage:     {stats['tag_coverage']:.1%}")
            print(f"  Vocab domains:    {stats['vocab_domains']}")
            print(f"  Vocab terms:      {stats['vocab_total_terms']}")
            print("  Tag distribution:")
            for tag, count in sorted(stats["tag_distribution"].items(),
                                     key=lambda x: x[1], reverse=True):
                print(f"    {tag:16s}: {count:5d}")

    conn.close()


if __name__ == "__main__":
    main()
