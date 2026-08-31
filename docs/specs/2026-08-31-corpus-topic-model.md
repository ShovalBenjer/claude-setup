# Corpus Topic Model

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/topic_model.py

## Problem

The existing tagging and classification tools use predefined vocabularies
(`tagger.py` with 20 keyword lists, `semantic.py` with 20 domain
descriptions).  They cannot discover emergent topics that the vocabulary
does not anticipate.  When the corpus grows into an area with no matching
domain, chunks in that area receive low scores across all domains and no
meaningful label.  The semantic spec lists "Topic modeling or LDA-style
unsupervised clustering" as a non-goal; this tool implements it.

## Solution

A new tool `tools/corpus/topic_model.py` that decomposes the corpus
TF-IDF matrix using Non-negative Matrix Factorization (NMF) to discover
latent topics without predefined vocabularies.

### Schema (created dynamically via `_ensure_table`)

```sql
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
```

### Tool commands

- `fit [--db PATH] [--n-topics N] [--dry-run]`: builds a TF-IDF matrix
  (unigram + bigram, sublinear TF, English stop words), decomposes it
  via NMF into N topics, and persists per-chunk topic assignments and
  per-topic top terms.  Re-fitting replaces all previous assignments.
- `topics [--db PATH] [--json]`: lists discovered topics with their
  sizes and top terms, ordered by size descending.
- `lookup --chunk-id CID [--db PATH] [--json]`: returns the topic
  assignment for a specific chunk, including topic weight and the
  topic's top terms.
- `stats [--db PATH] [--json]`: summary including topic count, total
  chunks, average topic weight, and topic size range.
- `selftest`: exercises 14 checks.

### ML approach

- **NMF over LDA**: NMF tends to produce more coherent topics on
  shorter documents and TF-IDF inputs.  LDA expects raw term counts
  and a generative model that is less natural for the mixed-kind
  corpus (code, prose, claims).
- **scikit-learn NMF** with `init="nndsvda"` (SVD-based non-negative
  initialization) for deterministic, stable decomposition.
- **TF-IDF with bigrams**: captures multi-word concepts (e.g.
  "foreign key", "token rotation") that unigrams miss.
- **Two tables**: `chunk_topics` stores per-chunk assignments (one
  topic per chunk, the dominant one by NMF weight); `topic_terms`
  stores the top terms per topic for interpretability.

### Design properties

- **Unsupervised**: no predefined domains or seed terms required.
- **Idempotent re-fit**: each fit deletes all previous assignments
  before inserting, so the tables always reflect the latest model.
- **Composable**: `fit_topics()` returns a dict consumable by
  `pipeline.py`.  `list_topics()` and `lookup_chunk_topic()` return
  structured results for programmatic use.
- **Superseded-aware**: only non-superseded chunks are modeled.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/topic_model.py`: new tool
- `docs/specs/2026-08-31-corpus-topic-model.md`: this spec

## See also

- [corpus-semantic](2026-08-30-corpus-semantic.md): TF-IDF
  classification against predefined domain descriptions; NMF topic
  modeling complements it with unsupervised discovery.
- [corpus-tagger](2026-08-30-corpus-tagger.md): keyword-based domain
  tagging with predefined vocabularies.
- [corpus-cluster-store](2026-08-30-corpus-cluster-store.md): KMeans
  clustering persistence (groups by similarity, no term decomposition).

## Non-goals

- Hierarchical topic modeling (flat topic assignments only).
- Dynamic topic count selection (the caller chooses n-topics).
- Topic coherence scoring (future work).
- Streaming or incremental topic updates.
