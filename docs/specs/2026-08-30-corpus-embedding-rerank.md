# Corpus Embedding and Rerank

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/embed.py

## Problem

The research corpus had 5936 chunks indexed via FTS5 full-text search,
but FTS5 returns results ranked by term frequency alone. For queries
where multiple chunks contain the same keywords, relevance depends on
semantic similarity that bag-of-words matching cannot capture. Step 5
of the research corpus spec called for an embedding layer that can
rerank FTS5 results by vector similarity.

## Solution

A new tool `tools/corpus/embed.py` with four subcommands:

- `fit [--db PATH]`: fits a hashed char-ngram TF-IDF + PCA embedding
  over all accepted corpus chunks, stores vectors as `.npy` sidecar
  files alongside the corpus database, with a generation counter that
  tracks corpus mutations.
- `rerank --query TEXT [--top N] [--db PATH]`: reorders FTS5 results
  using cosine similarity between the query vector and stored chunk
  vectors. Returns `rerank_unavailable` on generation mismatch rather
  than silently degrading.
- `info [--db PATH]`: reports embedding status (current, stale, or
  not_fitted) and metadata (chunk count, component count, explained
  variance).
- `selftest`: exercises 9 checks covering fit, vector shape, metadata,
  info status, rerank ordering, generation mismatch, stale detection,
  and re-fit.

### Embedding approach

Uses the IdiolectEmbedding pattern: hashed character n-grams (3 and
4-grams) projected into a 2048-dimensional space via signed random
hashing (feature hashing with alternating signs from the high bits of
a blake2b hash). The raw counts are converted to sublinear TF-IDF,
then reduced to 256 dimensions via PCA (eigendecomposition of the
covariance matrix). Final vectors are L2-normalized for cosine
similarity.

This approach requires no external model, no network access, and no
GPU. The entire pipeline runs in numpy and fits 1362 chunks in under
a second.

### Generation tracking

Each `fit` call bumps a `generation` counter in the `corpus_meta`
table and records it in the vector metadata JSON. On `rerank`, if the
stored generation does not match the current corpus generation, the
tool returns `rerank_unavailable` and falls back to FTS5-only results.
This prevents silent degradation when the corpus has been modified
since the last fit.

### Storage

Five files are written alongside the corpus database:
- `corpus-vec.npy`: the chunk embedding matrix (n_chunks x components)
- `corpus-vec.json`: metadata (generation, chunk IDs, explained
  variance, dimensions, n-gram sizes)
- `corpus-vec.proj.npy`: PCA projection matrix
- `corpus-vec.mean.npy`: mean vector for centering
- `corpus-vec.idf.npy`: IDF weights

## Results

First run against the real corpus:
- 1362 accepted chunks embedded
- 256 PCA components, 61.6% explained variance
- Vector file: 1.3 MB
- Rerank query "deploy script service": top result is the Azure DevOps
  dormancy audit chunk, which is the most deployment-specific content
  in the corpus

## Design decisions

- PCA over random projection: PCA captures more variance per component
  and the corpus is small enough that eigendecomposition is instant.
- Character n-grams over word tokens: handles typos, camelCase, and
  code identifiers without a tokenizer.
- 256 components: balances dimensionality reduction against information
  loss; 61.6% explained variance is adequate for reranking (not
  retrieval from scratch).
- Generation counter over content hashing: cheaper to check and
  sufficient since every corpus mutation goes through `research.py`
  which can bump the counter.

## Scope

- `tools/corpus/embed.py`: new tool
- `docs/specs/2026-08-30-corpus-embedding-rerank.md`: this spec

## Non-goals

- Replacing FTS5 for initial retrieval (embedding reranks FTS5 results,
  does not replace them).
- GPU or external model dependencies.
- Incremental updates (re-fit is fast enough to run from scratch).
