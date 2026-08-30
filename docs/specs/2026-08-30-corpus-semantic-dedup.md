# Corpus Semantic Deduplication

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/semantic_dedup.py

## Problem

The existing dedup tool (`tools/corpus/dedup.py`) detects exact-hash (Class A)
and simhash near-match (Class B) duplicates, but misses paraphrase-level
duplicates: chunks that convey the same information using different wording.
These rephrased passages survive hash-based detection because their byte
representations differ, yet they inflate the corpus and skew retrieval results.

The dedup spec explicitly lists "Semantic deduplication using embeddings" as a
non-goal. This tool fills that gap using the dense vectors already produced by
`tools/corpus/embed.py`.

## Solution

A new tool `tools/corpus/semantic_dedup.py` that uses the PCA-reduced TF-IDF
vectors from `embed.py` to find chunk pairs with high cosine similarity.

### How it works

1. Loads the L2-normalised vectors from `corpus-vec.npy` (produced by
   `embed.py fit`). Because the vectors are unit-length, cosine similarity
   reduces to a dot product.
2. Checks that the vector generation matches the corpus generation counter,
   refusing to operate on stale vectors.
3. Computes the full pairwise similarity matrix and extracts pairs above the
   configurable threshold (default 0.85).
4. Excludes pairs already linked by existing `duplicates` edges in
   `claim_edges`, preventing double-marking.
5. Excludes superseded chunks from both scan and apply.

### Tool commands

- `scan [--db PATH] [--threshold F] [--json]`: reports semantic duplicate
  pairs above the cosine similarity threshold, sorted by similarity descending.
- `apply [--db PATH] [--threshold F] [--dry-run]`: marks the shorter chunk in
  each pair as superseded (longer chunks carry more information). Creates
  `duplicates` edges in `claim_edges` with `basis='embedding_cosine'` and the
  actual cosine similarity as confidence.
- `stats [--db PATH] [--json]`: statistics on semantic dedup activity including
  edge counts, superseded counts, and average cosine similarity.
- `selftest`: exercises 14 checks.

### Design properties

- **Embedding-based**: uses dense PCA-reduced TF-IDF vectors, not hash-based
  comparison, catching paraphrases that simhash misses.
- **Generation-aware**: refuses to scan or apply when vectors are stale
  (generation mismatch), returning `vectors_unavailable` rather than producing
  incorrect results.
- **Non-destructive by default**: apply defaults to dry-run mode.
- **Auditable**: every action creates a `claim_edges` row with
  `edge_type='duplicates'` and `basis='embedding_cosine'`, distinguishing
  semantic dedup from hash-based dedup (`basis='norm_sha256'`).
- **Keeper selection**: the longer chunk (by word count) is kept, preserving
  the more informative version. Ties break by alphabetical chunk_id.
- **Incremental**: re-running scan after apply excludes already-linked pairs.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/semantic_dedup.py`: new tool
- `docs/specs/2026-08-30-corpus-semantic-dedup.md`: this spec

## See also

- [corpus-dedup](2026-08-30-corpus-dedup.md): hash-based deduplication
  (Class A/B/C) that this tool extends with semantic matching.
- [corpus-embedding-rerank](2026-08-30-corpus-embedding-rerank.md): produces
  the dense vectors this tool consumes.

## Non-goals

- Replacing the hash-based dedup pipeline.
- Training a dedicated deduplication model.
- Cross-corpus semantic dedup between separate databases.
- Automatic re-scanning on chunk content changes.
