#!/usr/bin/env python3
"""Corpus vocabulary analysis: term frequency and coverage profiling.

Computes corpus-wide term statistics using TF-IDF to identify the
most distinctive terms, domain-specific vocabulary density, and
under-represented terminology areas.  Complements the tagger (which
scores against fixed vocabularies) by discovering what the corpus
actually talks about.

Usage:
    python tools/corpus/vocab_analysis.py profile [--db PATH] [--top N] [--json]
    python tools/corpus/vocab_analysis.py distinctive [--db PATH] [--top N] [--json]
    python tools/corpus/vocab_analysis.py coverage [--db PATH] [--json]
    python tools/corpus/vocab_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def _check_sklearn():
    if not HAS_SKLEARN:
        print("ERROR: scikit-learn is required.", file=sys.stderr)
        sys.exit(1)


def _load_texts(conn) -> tuple[list[str], list[dict]]:
    """Load active chunk texts and metadata."""
    rows = conn.execute(
        "SELECT chunk_id, kind, norm_text FROM chunks "
        "WHERE status != 'superseded'"
    ).fetchall()
    meta = [{"chunk_id": r[0], "kind": r[1]} for r in rows]
    texts = [r[2] for r in rows]
    return texts, meta


def term_profile(conn, top_n: int = 50) -> dict:
    """Compute corpus-wide term frequency profile."""
    texts, meta = _load_texts(conn)
    if not texts:
        return {"total_chunks": 0, "terms": []}

    word_counts = Counter()
    doc_counts = Counter()
    total_words = 0

    for text in texts:
        words = text.lower().split()
        total_words += len(words)
        word_counts.update(words)
        doc_counts.update(set(words))

    n_docs = len(texts)
    vocab_size = len(word_counts)

    terms = []
    for word, count in word_counts.most_common(top_n):
        terms.append({
            "term": word,
            "frequency": count,
            "doc_frequency": doc_counts[word],
            "doc_fraction": round(doc_counts[word] / n_docs, 4),
        })

    kind_counts = Counter(m["kind"] for m in meta)

    return {
        "total_chunks": n_docs,
        "total_words": total_words,
        "vocab_size": vocab_size,
        "avg_words_per_chunk": round(total_words / n_docs, 1),
        "kind_distribution": dict(kind_counts),
        "terms": terms,
    }


def distinctive_terms(conn, top_n: int = 30) -> list[dict]:
    """Find the most distinctive terms per chunk kind using TF-IDF."""
    _check_sklearn()
    texts, meta = _load_texts(conn)
    if not texts:
        return []

    kinds = sorted({m["kind"] for m in meta})
    if len(kinds) < 2:
        return []

    kind_texts: dict[str, list[str]] = {}
    for text, m in zip(texts, meta):
        kind_texts.setdefault(m["kind"], []).append(text)

    merged = {k: " ".join(ts) for k, ts in kind_texts.items()}
    kind_labels = sorted(merged.keys())
    kind_docs = [merged[k] for k in kind_labels]

    vectorizer = TfidfVectorizer(
        max_features=3000,
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
    )
    tfidf = vectorizer.fit_transform(kind_docs)
    feature_names = vectorizer.get_feature_names_out()

    results = []
    for i, kind in enumerate(kind_labels):
        row = tfidf[i].toarray().flatten()
        top_idx = np.argsort(row)[::-1][:top_n]
        terms = [
            {"term": str(feature_names[idx]),
             "tfidf": round(float(row[idx]), 4)}
            for idx in top_idx
            if row[idx] > 0
        ]
        results.append({
            "kind": kind,
            "chunk_count": len(kind_texts[kind]),
            "distinctive_terms": terms[:top_n],
        })

    results.sort(key=lambda r: r["chunk_count"], reverse=True)
    return results


def vocabulary_coverage(conn) -> dict:
    """Measure vocabulary coverage against domain vocabularies."""
    texts, _ = _load_texts(conn)
    if not texts:
        return {"total_chunks": 0, "coverage": []}

    from tagger import DOMAIN_VOCAB  # noqa: E402

    corpus_words = set()
    for text in texts:
        corpus_words.update(text.lower().split())

    coverage = []
    for domain, vocab_list in sorted(DOMAIN_VOCAB.items()):
        domain_terms = set(vocab_list)
        matched = domain_terms & corpus_words
        coverage.append({
            "domain": domain,
            "vocab_size": len(domain_terms),
            "matched": len(matched),
            "coverage_pct": round(
                100 * len(matched) / len(domain_terms), 1
            ) if domain_terms else 0,
            "missing": sorted(domain_terms - corpus_words)[:10],
        })

    coverage.sort(key=lambda c: c["coverage_pct"], reverse=True)

    total_vocab = sum(len(v) for v in DOMAIN_VOCAB.values())
    total_matched = sum(c["matched"] for c in coverage)

    return {
        "total_chunks": len(texts),
        "corpus_vocab_size": len(corpus_words),
        "domain_vocab_total": total_vocab,
        "overall_coverage_pct": round(
            100 * total_matched / total_vocab, 1
        ) if total_vocab else 0,
        "coverage": coverage,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    _check_sklearn()
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-31T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Test Doc",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )

        test_chunks = [
            ("c1", 0, "prose", "Database Guide",
             "sqlite provides sql query capabilities with schema migrations "
             "and index management for data storage and retrieval with "
             "foreign key constraints and triggers for referential integrity"),
            ("c2", 1, "claim", "Performance Claim",
             "database indexing improves query performance by reducing "
             "table scan operations and enabling faster lookups through "
             "balanced tree structures and hash indexes"),
            ("c3", 2, "code", "Example Code",
             "def create_table(): conn.execute('CREATE TABLE users') "
             "def insert_row(): conn.execute('INSERT INTO users VALUES')"),
            ("c4", 3, "prose", "Testing Guide",
             "pytest framework provides fixtures and assertions for "
             "writing unit tests with parameterized test cases and "
             "coverage reporting and integration testing support"),
            ("c5", 4, "claim", "Test Claim",
             "test driven development improves code quality by ensuring "
             "every function has corresponding unit tests and assertions"),
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
        conn.commit()

        # Check 1: term_profile returns results
        profile = term_profile(conn)
        assert profile["total_chunks"] == 5
        assert profile["total_words"] > 0
        assert profile["vocab_size"] > 0
        assert len(profile["terms"]) > 0
        checks += 1

        # Check 2: terms are sorted by frequency
        freqs = [t["frequency"] for t in profile["terms"]]
        for i in range(len(freqs) - 1):
            assert freqs[i] >= freqs[i + 1]
        checks += 1

        # Check 3: doc_fraction bounded [0, 1]
        for t in profile["terms"]:
            assert 0 < t["doc_fraction"] <= 1.0
        checks += 1

        # Check 4: kind_distribution sums to chunk count
        kind_sum = sum(profile["kind_distribution"].values())
        assert kind_sum == 5
        checks += 1

        # Check 5: distinctive_terms returns per-kind results
        distinct = distinctive_terms(conn)
        assert len(distinct) > 0
        kinds = {d["kind"] for d in distinct}
        assert "prose" in kinds
        assert "claim" in kinds
        checks += 1

        # Check 6: each kind has distinctive terms
        for d in distinct:
            assert d["chunk_count"] > 0
            assert len(d["distinctive_terms"]) > 0
        checks += 1

        # Check 7: tfidf scores are positive
        for d in distinct:
            for t in d["distinctive_terms"]:
                assert t["tfidf"] > 0
        checks += 1

        # Check 8: vocabulary_coverage returns domains
        cov = vocabulary_coverage(conn)
        assert cov["total_chunks"] == 5
        assert cov["corpus_vocab_size"] > 0
        assert len(cov["coverage"]) > 0
        checks += 1

        # Check 9: coverage percentages bounded [0, 100]
        for c in cov["coverage"]:
            assert 0 <= c["coverage_pct"] <= 100
        checks += 1

        # Check 10: database domain has some coverage
        db_cov = next(
            (c for c in cov["coverage"] if c["domain"] == "database"),
            None,
        )
        assert db_cov is not None
        assert db_cov["matched"] > 0
        checks += 1

        # Check 11: overall_coverage_pct is bounded
        assert 0 <= cov["overall_coverage_pct"] <= 100
        checks += 1

        # Check 12: empty corpus
        empty_dir = Path(td) / "empty_sub"
        empty_dir.mkdir()
        empty_conn = connect(str(empty_dir / "empty.db"))
        init_schema(empty_conn)
        assert term_profile(empty_conn)["total_chunks"] == 0
        assert distinctive_terms(empty_conn) == []
        assert vocabulary_coverage(empty_conn)["total_chunks"] == 0
        empty_conn.close()
        checks += 1

        # Check 13: top_n limits profile terms
        small_profile = term_profile(conn, top_n=3)
        assert len(small_profile["terms"]) <= 3
        checks += 1

        # Check 14: missing terms are actual vocab terms not in corpus
        for c in cov["coverage"]:
            if c["missing"]:
                for m in c["missing"]:
                    assert isinstance(m, str)
                    assert len(m) > 0
        checks += 1

        conn.close()

    print(f"PASS vocab_analysis selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus vocabulary analysis")
    sub = parser.add_subparsers(dest="cmd")

    p_prof = sub.add_parser("profile",
                            help="Corpus term frequency profile")
    p_prof.add_argument("--db", default=str(DEFAULT_DB))
    p_prof.add_argument("--top", type=int, default=50)
    p_prof.add_argument("--json", action="store_true")

    p_dist = sub.add_parser("distinctive",
                            help="Distinctive terms per chunk kind")
    p_dist.add_argument("--db", default=str(DEFAULT_DB))
    p_dist.add_argument("--top", type=int, default=30)
    p_dist.add_argument("--json", action="store_true")

    p_cov = sub.add_parser("coverage",
                           help="Vocabulary coverage against domains")
    p_cov.add_argument("--db", default=str(DEFAULT_DB))
    p_cov.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "profile":
        conn = connect(args.db)
        result = term_profile(conn, top_n=args.top)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"  {result['total_chunks']} chunks, "
                  f"{result['total_words']} words, "
                  f"{result['vocab_size']} unique terms")
            print(f"  Avg {result['avg_words_per_chunk']} words/chunk")
            for t in result["terms"][:20]:
                print(f"    {t['term']:20s}  "
                      f"freq={t['frequency']:5d}  "
                      f"docs={t['doc_fraction']:.1%}")
        conn.close()

    elif args.cmd == "distinctive":
        conn = connect(args.db)
        results = distinctive_terms(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        elif not results:
            print("  Not enough chunk kinds for comparison")
        else:
            for d in results:
                terms = ", ".join(
                    t["term"] for t in d["distinctive_terms"][:5]
                )
                print(f"  {d['kind']} ({d['chunk_count']} chunks): "
                      f"{terms}")
        conn.close()

    elif args.cmd == "coverage":
        conn = connect(args.db)
        result = vocabulary_coverage(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"  Corpus vocab: {result['corpus_vocab_size']} terms")
            print(f"  Overall coverage: "
                  f"{result['overall_coverage_pct']:.1f}%")
            for c in result["coverage"]:
                print(f"    {c['domain']:15s}  "
                      f"{c['coverage_pct']:5.1f}%  "
                      f"({c['matched']}/{c['vocab_size']})")
        conn.close()


if __name__ == "__main__":
    main()
