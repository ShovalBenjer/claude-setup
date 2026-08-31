#!/usr/bin/env python3
"""Corpus topic coherence: measures quality of discovered topics.

Computes coherence scores for NMF topics using Normalized Pointwise
Mutual Information (NPMI) between the top terms of each topic,
evaluated against term co-occurrence in the actual corpus.  Higher
coherence indicates more interpretable, semantically tight topics.

Usage:
    python tools/corpus/topic_coherence.py score [--db PATH] [--json]
    python tools/corpus/topic_coherence.py rank [--db PATH] [--json]
    python tools/corpus/topic_coherence.py suggest [--db PATH] [--json]
    python tools/corpus/topic_coherence.py selftest
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
from topic_model import _ensure_table as _ensure_topic_table  # noqa: E402
from topic_model import fit_topics  # noqa: E402


def _load_topic_terms(conn) -> dict[int, list[str]]:
    _ensure_topic_table(conn)
    rows = conn.execute(
        "SELECT topic_label, term FROM topic_terms "
        "ORDER BY topic_label, term_rank"
    ).fetchall()
    topics: dict[int, list[str]] = {}
    for r in rows:
        topics.setdefault(r[0], []).append(r[1])
    return topics


def _load_texts(conn) -> list[str]:
    return [
        r[0] for r in conn.execute(
            "SELECT norm_text FROM chunks WHERE status != 'superseded'"
        ).fetchall()
    ]


def _compute_npmi(texts: list[str], terms: list[str],
                  window: int = 10) -> float:
    """Compute average NPMI across all term pairs in a topic."""
    n_docs = len(texts)
    if n_docs == 0 or len(terms) < 2:
        return 0.0

    term_set = set(terms)
    doc_freq: dict[str, int] = dict.fromkeys(term_set, 0)
    co_freq: dict[tuple[str, str], int] = {}

    for i in range(len(terms)):
        for j in range(i + 1, len(terms)):
            co_freq[(terms[i], terms[j])] = 0

    for text in texts:
        words = text.lower().split()
        present = set()
        for w in words:
            if w in term_set:
                present.add(w)

        for t in present:
            doc_freq[t] += 1

        if window > 0:
            window_co: set[tuple[str, str]] = set()
            for idx, w in enumerate(words):
                if w not in term_set:
                    continue
                end = min(idx + window, len(words))
                for k in range(idx + 1, end):
                    if words[k] in term_set and words[k] != w:
                        a, b = (w, words[k]) if w < words[k] else (words[k], w)
                        key = (terms[terms.index(a) if a in terms else 0],
                               terms[terms.index(b) if b in terms else 0])
                        if a in terms and b in terms:
                            ai = terms.index(a)
                            bi = terms.index(b)
                            if ai < bi:
                                window_co.add((a, b))
                            else:
                                window_co.add((b, a))
            for pair in window_co:
                if pair in co_freq:
                    co_freq[pair] += 1

    eps = 1e-12
    npmis = []
    for (ti, tj), co_count in co_freq.items():
        p_i = doc_freq.get(ti, 0) / n_docs
        p_j = doc_freq.get(tj, 0) / n_docs
        p_ij = co_count / n_docs

        if p_i < eps or p_j < eps or p_ij < eps:
            npmis.append(-1.0)
            continue

        pmi = math.log(p_ij / (p_i * p_j))
        neg_log_pij = -math.log(p_ij)
        if neg_log_pij < eps:
            npmis.append(1.0)
            continue
        npmi = pmi / neg_log_pij
        npmis.append(npmi)

    if not npmis:
        return 0.0
    return sum(npmis) / len(npmis)


def score_coherence(conn) -> list[dict]:
    """Score each topic's coherence using NPMI."""
    topic_terms = _load_topic_terms(conn)
    if not topic_terms:
        return []

    texts = _load_texts(conn)
    if not texts:
        return []

    results = []
    for label in sorted(topic_terms.keys()):
        terms = topic_terms[label]
        npmi = _compute_npmi(texts, terms)

        size = conn.execute(
            "SELECT COUNT(*) FROM chunk_topics WHERE topic_label = ?",
            (label,),
        ).fetchone()[0]

        results.append({
            "topic_label": label,
            "npmi": round(npmi, 4),
            "size": size,
            "top_terms": terms[:5],
        })

    return results


def rank_topics(conn) -> list[dict]:
    """Rank topics by coherence score, best first."""
    scores = score_coherence(conn)
    scores.sort(key=lambda s: s["npmi"], reverse=True)
    for i, s in enumerate(scores):
        s["rank"] = i + 1
    return scores


def suggest_n_topics(conn) -> dict:
    """Suggest whether to increase or decrease n_topics.

    Heuristic: if most topics have low coherence (NPMI < 0), the model
    is over-specified and should use fewer topics.  If all topics have
    high coherence (NPMI > 0.1), the model may be under-specified.
    """
    scores = score_coherence(conn)
    if not scores:
        return {"suggestion": "no_data", "reason": "no topics fitted"}

    npmis = [s["npmi"] for s in scores]
    avg = sum(npmis) / len(npmis)
    low_count = sum(1 for n in npmis if n < 0)
    high_count = sum(1 for n in npmis if n > 0.1)

    n_topics = len(scores)

    if low_count > len(scores) * 0.5:
        suggestion = "decrease"
        reason = (f"{low_count}/{n_topics} topics have negative NPMI; "
                  f"try {max(2, n_topics - 2)} topics")
    elif high_count == len(scores) and n_topics < 20:
        suggestion = "increase"
        reason = (f"all {n_topics} topics have NPMI > 0.1; "
                  f"try {n_topics + 3} topics")
    else:
        suggestion = "keep"
        reason = f"average NPMI {avg:.3f} across {n_topics} topics"

    return {
        "suggestion": suggestion,
        "reason": reason,
        "n_topics": n_topics,
        "avg_npmi": round(avg, 4),
        "low_coherence_count": low_count,
        "high_coherence_count": high_count,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
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
            ("c1", 0, "SQL Databases",
             "sqlite provides sql query capabilities with schema migrations "
             "and index management for data storage retrieval join constraint "
             "table column primary key foreign key referential integrity"),
            ("c2", 1, "More SQL",
             "postgresql database table query select insert update delete "
             "index constraint foreign key transaction isolation level "
             "sql schema migration alter table create drop truncate"),
            ("c3", 2, "SQL Tuning",
             "database query optimization index scan table scan explain plan "
             "sql performance tuning join strategy hash sort merge nested"),
            ("c4", 3, "Python Testing",
             "pytest framework provides fixtures assertions parametrize "
             "coverage report unittest mock patching test runner suite "
             "test driven development tdd integration testing"),
            ("c5", 4, "Unit Tests",
             "test driven development unit integration testing assert "
             "fixture setup teardown parameterized tests coverage report "
             "pytest markers skip xfail conftest plugin"),
            ("c6", 5, "Test Patterns",
             "testing patterns arrange act assert given when then test "
             "doubles mock stub spy fake fixture factory builder pattern"),
            ("c7", 6, "Security Auth",
             "oauth2 authentication jwt bearer tokens authorization "
             "api security tls encryption credential management secret "
             "openid connect saml sso identity provider"),
            ("c8", 7, "API Security",
             "api key rotation security headers cors policy authentication "
             "rate limiting token validation jwt verification endpoint "
             "oauth2 authorization server resource protected"),
            ("c9", 8, "Crypto",
             "cryptography aes rsa elliptic curve encryption decryption "
             "digital signature hash function sha256 hmac key exchange "
             "tls certificate x509 public private key pair"),
        ]

        for cid, ordinal, heading, text in test_chunks:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " citation_count, status, status_reason, ingested_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "src1", ordinal, heading, "prose", None,
                 text, text, len(text.split()), _sha256(text),
                 0, 0, "accepted", None, now),
            )
        conn.commit()

        fit_topics(conn, n_topics=3, dry_run=False)

        # Check 1: score_coherence returns results for each topic
        scores = score_coherence(conn)
        assert len(scores) == 3, f"expected 3, got {len(scores)}"
        checks += 1

        # Check 2: each score has required fields
        for s in scores:
            assert "topic_label" in s
            assert "npmi" in s
            assert "size" in s
            assert "top_terms" in s
        checks += 1

        # Check 3: NPMI is bounded [-1, 1]
        for s in scores:
            assert -1.0 <= s["npmi"] <= 1.0, f"NPMI {s['npmi']} out of range"
        checks += 1

        # Check 4: sizes sum to chunk count
        total = sum(s["size"] for s in scores)
        assert total == 9, f"sizes sum to {total}, expected 9"
        checks += 1

        # Check 5: rank_topics returns ranked results
        ranked = rank_topics(conn)
        assert len(ranked) == 3
        for i in range(len(ranked) - 1):
            assert ranked[i]["npmi"] >= ranked[i + 1]["npmi"]
        checks += 1

        # Check 6: rank numbers are sequential
        ranks = [r["rank"] for r in ranked]
        assert ranks == [1, 2, 3]
        checks += 1

        # Check 7: suggest returns valid suggestion
        suggestion = suggest_n_topics(conn)
        assert suggestion["suggestion"] in ("increase", "decrease", "keep")
        assert "reason" in suggestion
        assert suggestion["n_topics"] == 3
        checks += 1

        # Check 8: suggest avg_npmi matches scores
        avg = sum(s["npmi"] for s in scores) / len(scores)
        assert abs(suggestion["avg_npmi"] - round(avg, 4)) < 0.001
        checks += 1

        # Check 9: empty corpus returns empty
        empty_dir = Path(td) / "empty_sub"
        empty_dir.mkdir()
        empty_conn = connect(str(empty_dir / "empty.db"))
        init_schema(empty_conn)
        _ensure_topic_table(empty_conn)
        result = score_coherence(empty_conn)
        assert result == []
        suggestion = suggest_n_topics(empty_conn)
        assert suggestion["suggestion"] == "no_data"
        empty_conn.close()
        checks += 1

        # Check 10: NPMI computation with known data
        test_texts = [
            "cat dog cat dog",
            "cat dog pet",
            "cat dog animal pet",
        ]
        npmi = _compute_npmi(test_texts, ["cat", "dog"])
        assert npmi > 0, f"co-occurring terms should have positive NPMI, got {npmi}"
        checks += 1

        # Check 11: NPMI for non-co-occurring terms
        test_texts2 = [
            "alpha bravo charlie",
            "delta echo foxtrot",
            "alpha bravo charlie",
        ]
        npmi2 = _compute_npmi(test_texts2, ["alpha", "delta"])
        assert npmi2 <= 0, f"non-co-occurring terms should have non-positive NPMI, got {npmi2}"
        checks += 1

        # Check 12: top_terms limited to 5
        for s in scores:
            assert len(s["top_terms"]) <= 5
        checks += 1

        # Check 13: topic_label matches fitted topics
        fitted_labels = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT topic_label FROM chunk_topics"
            ).fetchall()
        }
        score_labels = {s["topic_label"] for s in scores}
        assert score_labels == fitted_labels
        checks += 1

        # Check 14: coherence with single-term topic is zero
        npmi_single = _compute_npmi(test_texts, ["cat"])
        assert npmi_single == 0.0
        checks += 1

        conn.close()

    print(f"PASS topic_coherence selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Corpus topic coherence scorer")
    sub = parser.add_subparsers(dest="cmd")

    p_score = sub.add_parser("score",
                             help="Score topic coherence via NPMI")
    p_score.add_argument("--db", default=str(DEFAULT_DB))
    p_score.add_argument("--json", action="store_true")

    p_rank = sub.add_parser("rank",
                            help="Rank topics by coherence")
    p_rank.add_argument("--db", default=str(DEFAULT_DB))
    p_rank.add_argument("--json", action="store_true")

    p_suggest = sub.add_parser("suggest",
                               help="Suggest n_topics adjustment")
    p_suggest.add_argument("--db", default=str(DEFAULT_DB))
    p_suggest.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "score":
        conn = connect(args.db)
        scores = score_coherence(conn)
        if args.json:
            print(json.dumps(scores, indent=2))
        elif not scores:
            print("  No topics fitted yet")
        else:
            for s in scores:
                terms = ", ".join(s["top_terms"])
                print(f"  Topic {s['topic_label']} "
                      f"(NPMI={s['npmi']:+.3f}, "
                      f"{s['size']} chunks): {terms}")
        conn.close()

    elif args.cmd == "rank":
        conn = connect(args.db)
        ranked = rank_topics(conn)
        if args.json:
            print(json.dumps(ranked, indent=2))
        elif not ranked:
            print("  No topics fitted yet")
        else:
            for r in ranked:
                terms = ", ".join(r["top_terms"])
                print(f"  #{r['rank']} Topic {r['topic_label']} "
                      f"(NPMI={r['npmi']:+.3f}, "
                      f"{r['size']} chunks): {terms}")
        conn.close()

    elif args.cmd == "suggest":
        conn = connect(args.db)
        result = suggest_n_topics(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"  Suggestion: {result['suggestion']}")
            print(f"  Reason: {result['reason']}")
            if "avg_npmi" in result:
                print(f"  Avg NPMI: {result['avg_npmi']:+.3f}")
        conn.close()


if __name__ == "__main__":
    main()
