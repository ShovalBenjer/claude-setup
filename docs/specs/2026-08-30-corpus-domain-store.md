# Corpus Domain Store

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/domain_store.py

## Problem

The semantic classifier (`tools/corpus/semantic.py`) computes ML-based
domain classifications for every chunk using TF-IDF cosine similarity
against 20 domain vocabularies, but discards the results after printing
them.  Downstream tools (retrieval, per-domain chunking, cluster-based
strategies) need persisted domain data for faceted queries and filtering.
Without persistence, every consumer must re-run the classifier from
scratch, and domain-based filtering is impossible in SQL queries.

## Solution

A new table `chunk_domains` in the corpus schema and a companion tool
`tools/corpus/domain_store.py` that bridges the semantic classifier and
the database.

### Schema addition (in research.py)

```sql
CREATE TABLE IF NOT EXISTS chunk_domains (
    chunk_id       TEXT NOT NULL REFERENCES chunks(chunk_id),
    domain         TEXT NOT NULL,
    score          REAL NOT NULL,
    classified_utc TEXT NOT NULL,
    PRIMARY KEY (chunk_id, domain)
);
CREATE INDEX IF NOT EXISTS ix_domains_domain ON chunk_domains(domain);
```

### Tool commands

- `persist [--db PATH] [--top-k N] [--min-score F] [--dry-run]`:
  runs the semantic classifier, then inserts or updates rows in
  `chunk_domains`.  Idempotent: unchanged scores are skipped, changed
  scores are updated.
- `lookup --chunk-id CID [--db PATH] [--json]`: returns domains for a
  specific chunk, sorted by score descending.
- `find --domain DOMAIN [--db PATH] [--min-score F] [--json]`: finds
  chunks classified under a given domain, joins the chunks table for
  metadata, excludes superseded chunks.
- `stats [--db PATH] [--json]`: domain store statistics including total
  rows, distinct chunks classified, distinct domains used, coverage
  ratio, and per-domain counts with average scores.
- `selftest`: exercises 15 checks.

### Design properties

- **ML-based**: uses scikit-learn TF-IDF cosine similarity against
  20 domain vocabulary descriptions, not regex heuristics.
- **Idempotent**: re-persisting with unchanged scores increments the
  `unchanged` counter, not `inserted`.  Score changes are detected
  with a tolerance of 0.0001.
- **Dry-run safe**: `--dry-run` computes and reports without writing.
- **Composable**: `persist_domains()` returns a dict consumable by
  `pipeline.py`.  `find_by_domain()` returns structured results for
  programmatic use.
- **Selective**: `find_by_domain` excludes superseded chunks via the
  `status != 'superseded'` filter on the chunks join.

## Results

- Selftest: 15 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/research.py`: schema addition (chunk_domains table)
- `tools/corpus/domain_store.py`: new tool
- `docs/specs/2026-08-30-corpus-domain-store.md`: this spec

## See also

- [corpus-tag-store](2026-08-30-corpus-tag-store.md): similar persistence
  pattern for auto-tagger results (TF-IDF domain tags).
- [corpus-chunk-versions](2026-08-30-corpus-chunk-versions.md): another
  schema extension tracking chunk content changes over time.

## Non-goals

- Replacing the semantic classifier's scoring algorithm.
- Domain taxonomy management or domain renaming.
- Automatic re-classification on chunk content changes.
- Persisting cluster assignments (separate feature).
