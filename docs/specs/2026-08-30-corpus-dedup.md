# Corpus Deduplication

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/dedup.py

## Problem

The corpus contains duplicate chunks from directory-level copy events,
versioned drafts, and encoding damage (spec section 2.1, classes A/B/C).
No tool existed to detect duplicates at scale or mark them superseded with
proper claim_edges recording the relationship.

## Solution

A new tool `tools/corpus/dedup.py` with four subcommands:

- `exact [--db PATH] [--json]`: finds groups of chunks sharing the same
  `norm_sha256`, excluding already-superseded chunks.  Reports group
  membership with source titles and statuses.
- `near [--db PATH] [--threshold N] [--json]`: finds chunk pairs within
  a simhash hamming distance threshold (default 5), for detecting
  near-duplicates from versioned drafts or encoding damage.
- `apply [--db PATH] [--dry-run]`: marks exact duplicates as superseded,
  keeping the earliest-ingested chunk as the keeper.  Creates `duplicates`
  edges in `claim_edges` with `basis='norm_sha256'` and `confidence=1.0`.
- `stats [--db PATH] [--json]`: reports total, active, and superseded
  chunk counts, duplicate group counts, unique hash counts, and the
  dedup rate.
- `selftest`: exercises 16 checks covering exact and near detection,
  apply with dry-run, edge creation, and empty corpus handling.

### Design properties

- **Three-class coverage**: exact matching (class A), simhash near-match
  (class B), with normalisation preceding hashing (class C) handled by
  the existing `norm_text` column.
- **Keeper selection**: earliest-ingested chunk wins, preserving temporal
  ordering and provenance.
- **Auditable**: every dedup action creates a `claim_edges` row with
  `edge_type='duplicates'`, so the relationship is queryable and
  reversible.
- **Non-destructive by default**: apply defaults to dry-run mode.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/dedup.py`: new tool
- `docs/specs/2026-08-30-corpus-dedup.md`: this spec

## See also

- [corpus-semantic-dedup](2026-08-30-corpus-semantic-dedup.md): extends
  this tool with embedding-based semantic deduplication for paraphrases.
- [corpus-simhash-distribution](2026-08-31-corpus-simhash-distribution.md):
  analyses the quality of simhash distribution underlying this tool's
  near-duplicate detection.

## Non-goals

- ~~Semantic deduplication using embeddings.~~ Shipped as
  [corpus-semantic-dedup](2026-08-30-corpus-semantic-dedup.md).
- Automatic dedup on ingestion.
- Cross-corpus dedup between separate databases.
