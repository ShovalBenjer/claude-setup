# Corpus Cluster

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/cluster.py

## Problem

The research corpus has 5937 chunks across 366 sources with no way to
discover topical relationships between chunks or sources. Near-duplicate
chunks that escaped dedup, chunks sharing citations, and sources covering
the same topics are invisible without manual SQL queries.

## Solution

A new tool `tools/corpus/cluster.py` with three subcommands:

- `simhash [--db PATH] [--threshold N] [--status STATUS] [--json]`:
  groups chunks by simhash Hamming distance, finding near-duplicates
  and topically similar content.
- `citation [--db PATH] [--min-shared N] [--json]`: finds pairs of
  chunks that cite the same URIs, revealing content overlap through
  shared references.
- `source-overlap [--db PATH] [--min-overlap N] [--json]`: finds pairs
  of sources whose chunks cite the same URIs, revealing topical
  relationships at the source level.
- `selftest`: exercises 16 checks covering all three clustering modes,
  filters, result shapes, edge cases, and JSON serialization.

### Design properties

- **Three complementary views**: simhash catches textual similarity,
  citation catches referential overlap, and source-overlap catches
  topical relationships at the document level.
- **Tunable thresholds**: each mode has a sensitivity parameter so the
  operator can tighten or loosen the clustering.
- **Status filtering**: simhash clustering can be restricted to accepted
  or quarantined chunks.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/cluster.py`: new tool
- `docs/specs/2026-08-30-corpus-cluster.md`: this spec

## Non-goals

- Dense vector clustering (handled by embed.py's cosine reranking).
- Automatic merge of clustered chunks.
- Topic modeling or LDA-style unsupervised clustering.
