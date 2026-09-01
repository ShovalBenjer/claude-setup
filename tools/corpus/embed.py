#!/usr/bin/env python3
"""Corpus embedding and rerank (spec step 5, section 4.5).

Fits a hashed char-ngram TF-IDF + PCA embedding over corpus chunks,
stores the vectors as a .npy sidecar with a generation counter. Rerank
uses cosine similarity to reorder FTS5 results.

A generation mismatch between the vectors and corpus_meta produces
rerank_unavailable rather than silent degradation.

Usage:
    python tools/corpus/embed.py fit [--db PATH]
    python tools/corpus/embed.py rerank --query TEXT [--top N] [--db PATH]
    python tools/corpus/embed.py info [--db PATH]
    python tools/corpus/embed.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    SCHEMA_SQL,
    _sha256,
    connect,
    init_schema,
)

DIM = 2048
NGRAMS = (3, 4)
COMPONENTS = 256

_VEC_NPY = "corpus-vec.npy"
_VEC_META = "corpus-vec.json"

_ELONG = re.compile(r"(.)\1{2,}")
_DIGIT = re.compile(r"\d")
_WS = re.compile(r"\s+")
_HCACHE = {}


def _normalize(t):
    t = _ELONG.sub(r"\1\1", t)
    t = _DIGIT.sub("#", t)
    t = _WS.sub(" ", t).strip()
    return t.lower()


def _ngrams(t):
    t = f" {_normalize(t)} "
    for n in NGRAMS:
        for i in range(len(t) - n + 1):
            yield t[i : i + n]


def _hash(s):
    h = _HCACHE.get(s)
    if h is None:
        h = int.from_bytes(
            hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "little"
        )
        _HCACHE[s] = h
    return h


def _counts(docs, dim=DIM):
    X = np.zeros((len(docs), dim), dtype=np.float32)
    for i, d in enumerate(docs):
        row = X[i]
        for g in _ngrams(d):
            h = _hash(g)
            row[h % dim] += 1.0 if (h >> 32) & 1 else -1.0
    return X


def _tfidf(X, idf):
    X = np.sign(X) * np.log1p(np.abs(X))
    X *= idf
    n = np.linalg.norm(X, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return X / n


def _get_generation(conn):
    row = conn.execute(
        "SELECT value FROM corpus_meta WHERE key = 'generation'"
    ).fetchone()
    if row:
        return int(row[0])
    return 0


def _bump_generation(conn):
    gen = _get_generation(conn) + 1
    conn.execute(
        "INSERT OR REPLACE INTO corpus_meta (key, value) VALUES ('generation', ?)",
        (str(gen),),
    )
    conn.commit()
    return gen


def _vec_paths(db_path):
    if db_path is None:
        db_dir = Path(DEFAULT_DB).parent
    else:
        db_dir = Path(db_path).parent
    return db_dir / _VEC_NPY, db_dir / _VEC_META


def fit(conn, db_path=None):
    """Fit embedding over all accepted chunks. Returns (n_chunks, generation)."""
    chunks = conn.execute(
        "SELECT chunk_id, norm_text FROM chunks "
        "WHERE status = 'accepted' ORDER BY rowid"
    ).fetchall()

    if not chunks:
        return 0, 0

    chunk_ids = [r[0] for r in chunks]
    texts = [r[1] for r in chunks]

    X = _counts(texts)
    df = (X != 0).sum(axis=0).astype(np.float32)
    idf = np.log((1.0 + len(texts)) / (1.0 + df)) + 1.0
    X = _tfidf(X, idf)
    mean = X.mean(axis=0)
    Xc = X - mean

    n_components = min(COMPONENTS, len(texts), DIM)
    cov = (Xc.T @ Xc) / max(1, len(texts) - 1)
    vals, vecs = np.linalg.eigh(cov.astype(np.float64))
    order = np.argsort(vals)[::-1][:n_components]
    proj = vecs[:, order].astype(np.float32)
    explained = float(vals[order].sum() / max(1e-12, vals.sum()))

    Z = (Xc) @ proj
    n = np.linalg.norm(Z, axis=1, keepdims=True)
    n[n == 0] = 1.0
    Z = Z / n

    gen = _bump_generation(conn)

    npy_path, meta_path = _vec_paths(db_path)
    np.save(npy_path, Z)

    meta = {
        "generation": gen,
        "n_chunks": len(chunks),
        "components": n_components,
        "explained_variance": round(explained, 4),
        "dim": DIM,
        "ngrams": list(NGRAMS),
        "chunk_ids": chunk_ids,
        "idf": idf.tolist(),
        "mean": mean.tolist(),
        "proj_shape": list(proj.shape),
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    np.save(npy_path.with_suffix(".proj.npy"), proj)
    np.save(npy_path.with_suffix(".mean.npy"), mean)
    np.save(npy_path.with_suffix(".idf.npy"), idf)

    return len(chunks), gen


def _load_vectors(db_path=None):
    """Load vectors and metadata. Returns (Z, meta, error_str)."""
    npy_path, meta_path = _vec_paths(db_path)

    if not npy_path.exists() or not meta_path.exists():
        return None, None, "vectors not fitted (run 'fit' first)"

    meta = json.loads(meta_path.read_text())
    Z = np.load(npy_path)

    return Z, meta, None


def rerank(conn, query_text, top_n=10, db_path=None):
    """Rerank FTS5 results using vector similarity.

    Returns list of (chunk_id, fts_snippet, cosine_score, rerank_status).
    rerank_status is 'reranked' or 'rerank_unavailable'.
    """
    Z, meta, err = _load_vectors(db_path)

    current_gen = _get_generation(conn)

    if err:
        return _fts_only(conn, query_text, top_n), "rerank_unavailable"

    if meta["generation"] != current_gen:
        return _fts_only(conn, query_text, top_n), "rerank_unavailable"

    words = query_text.lower().split()
    if not words:
        return [], "reranked"

    fts_query = " OR ".join(words)
    fts_results = conn.execute(
        "SELECT c.chunk_id, substr(c.norm_text, 1, 120) "
        "FROM chunks_fts f JOIN chunks c ON f.rowid = c.rowid "
        "WHERE f.norm_text MATCH ? AND c.status = 'accepted' LIMIT 100",
        (fts_query,),
    ).fetchall()

    if not fts_results:
        return [], "reranked"

    chunk_id_to_idx = {cid: i for i, cid in enumerate(meta["chunk_ids"])}

    idf_path = _vec_paths(db_path)[0].with_suffix(".idf.npy")
    mean_path = _vec_paths(db_path)[0].with_suffix(".mean.npy")
    proj_path = _vec_paths(db_path)[0].with_suffix(".proj.npy")

    idf = np.load(idf_path)
    mean = np.load(mean_path)
    proj = np.load(proj_path)

    q_counts = _counts([query_text])
    q_tfidf = _tfidf(q_counts, idf)
    q_vec = ((q_tfidf - mean) @ proj)
    q_norm = np.linalg.norm(q_vec)
    if q_norm > 0:
        q_vec = q_vec / q_norm
    q_vec = q_vec.flatten()

    scored = []
    for chunk_id, snippet in fts_results:
        idx = chunk_id_to_idx.get(chunk_id)
        if idx is not None and idx < len(Z):
            score = float(Z[idx] @ q_vec)
        else:
            score = 0.0
        scored.append((chunk_id, snippet, score))

    scored.sort(key=lambda x: -x[2])
    return scored[:top_n], "reranked"


def _fts_only(conn, query_text, top_n):
    """Fallback: FTS5 results without reranking."""
    words = query_text.lower().split()
    if not words:
        return []

    fts_query = " OR ".join(words)
    results = conn.execute(
        "SELECT c.chunk_id, substr(c.norm_text, 1, 120) "
        "FROM chunks_fts f JOIN chunks c ON f.rowid = c.rowid "
        "WHERE f.norm_text MATCH ? AND c.status = 'accepted' LIMIT ?",
        (fts_query, top_n),
    ).fetchall()

    return [(r[0], r[1], 0.0) for r in results]


def info(conn, db_path=None):
    """Report embedding state."""
    Z, meta, err = _load_vectors(db_path)
    current_gen = _get_generation(conn)

    result = {"corpus_generation": current_gen}

    if err:
        result["status"] = "not_fitted"
        result["error"] = err
        return result

    result["vec_generation"] = meta["generation"]
    result["n_chunks"] = meta["n_chunks"]
    result["components"] = meta["components"]
    result["explained_variance"] = meta["explained_variance"]

    if meta["generation"] != current_gen:
        result["status"] = "stale"
    else:
        result["status"] = "current"

    return result


def selftest():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        def add_chunk(cid, sid, text):
            conn.execute(
                "INSERT OR IGNORE INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " content_sha256, bytes) "
                "VALUES (?, ?, 'local_md', 'Test', 'MIT', 'vendor', "
                " 'test', ?, 'live', ?, 100)",
                (sid, f"/test/{sid}", now, _sha256(sid)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, 0, 'Test', 'prose', ?, ?, ?, ?, 0, "
                " 'accepted', ?)",
                (cid, sid, text, text, len(text.split()), _sha256(text), now),
            )
            conn.commit()

        add_chunk("c1", "s1", "numpy provides fast matrix multiplication")
        add_chunk("c2", "s2", "polars handles dataframe operations efficiently")
        add_chunk("c3", "s3", "duckdb enables fast SQL analytics on files")
        add_chunk("c4", "s4", "sqlite is the embedded database for this project")
        add_chunk("c5", "s5", "FTS5 full text search indexes the corpus chunks")

        # Test 1: fit produces vectors
        n_chunks, gen = fit(conn, db_path=db_path)
        if n_chunks != 5:
            failures.append(f"fit returned {n_chunks} chunks, expected 5")
        if gen != 1:
            failures.append(f"generation is {gen}, expected 1")

        # Test 2: .npy file exists with correct shape
        npy_path, meta_path = _vec_paths(db_path)
        if not npy_path.exists():
            failures.append("corpus-vec.npy not created")
        else:
            Z = np.load(npy_path)
            if Z.shape[0] != 5:
                failures.append(f"vectors have {Z.shape[0]} rows, expected 5")
            if Z.shape[1] > COMPONENTS:
                failures.append(f"vectors have {Z.shape[1]} dims, expected <= {COMPONENTS}")

        # Test 3: meta file has correct generation
        if not meta_path.exists():
            failures.append("corpus-vec.json not created")
        else:
            meta = json.loads(meta_path.read_text())
            if meta["generation"] != 1:
                failures.append(f"meta generation is {meta['generation']}, expected 1")

        # Test 4: info reports current status
        status = info(conn, db_path=db_path)
        if status["status"] != "current":
            failures.append(f"info status is {status['status']}, expected current")

        # Test 5: rerank returns reranked results
        results, rstatus = rerank(conn, "numpy matrix", top_n=3, db_path=db_path)
        if rstatus != "reranked":
            failures.append(f"rerank status is {rstatus}, expected reranked")
        if not results:
            failures.append("rerank returned no results")

        # Test 6: top result should be the numpy chunk
        if results and results[0][0] != "c1":
            failures.append(f"top reranked result is {results[0][0]}, expected c1")

        # Test 7: generation mismatch produces rerank_unavailable
        _bump_generation(conn)
        results2, rstatus2 = rerank(
            conn, "numpy matrix", top_n=3, db_path=db_path
        )
        if rstatus2 != "rerank_unavailable":
            failures.append(
                f"stale generation should give rerank_unavailable, got {rstatus2}"
            )

        # Test 8: info reports stale after generation bump
        status2 = info(conn, db_path=db_path)
        if status2["status"] != "stale":
            failures.append(f"info should report stale, got {status2['status']}")

        # Test 9: re-fit updates vectors and generation
        n2, gen2 = fit(conn, db_path=db_path)
        if gen2 != 3:
            failures.append(f"re-fit generation is {gen2}, expected 3")
        status3 = info(conn, db_path=db_path)
        if status3["status"] != "current":
            failures.append(f"re-fit should be current, got {status3['status']}")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print("PASS embed selftest (9 checks)")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_fit = sub.add_parser("fit", help="Fit embedding over corpus")
    p_fit.add_argument("--db", default=None)

    p_rerank = sub.add_parser("rerank", help="Rerank FTS5 results")
    p_rerank.add_argument("--query", required=True)
    p_rerank.add_argument("--top", type=int, default=10)
    p_rerank.add_argument("--db", default=None)

    p_info = sub.add_parser("info", help="Show embedding status")
    p_info.add_argument("--db", default=None)

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    db = getattr(args, "db", None)
    conn = connect(db)

    if args.command == "fit":
        n_chunks, gen = fit(conn, db_path=db)
        print(f"  fitted: {n_chunks} chunks")
        print(f"  generation: {gen}")
        npy_path, _ = _vec_paths(db)
        size_mb = npy_path.stat().st_size / (1024 * 1024)
        print(f"  vector file: {size_mb:.1f} MB")
        conn.close()
        return 0

    if args.command == "rerank":
        results, rstatus = rerank(conn, args.query, top_n=args.top, db_path=db)
        print(f"  status: {rstatus}")
        if not results:
            print("  no results")
        else:
            for i, (cid, snippet, score) in enumerate(results, 1):
                print(f"  {i:2d}. [{score:.3f}] {cid}")
                print(f"      {snippet}")
        conn.close()
        return 0

    if args.command == "info":
        result = info(conn, db_path=db)
        for k, v in result.items():
            print(f"  {k}: {v}")
        conn.close()
        return 0

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
