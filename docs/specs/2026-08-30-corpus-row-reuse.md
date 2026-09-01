# Corpus Row-Reuse Write-Back

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/rowreuse.py

## Problem

The research corpus serves retrieval queries but never learns from the
answers it produces. When a synthesis draws on multiple stored chunks to
answer a question, the synthesized answer is discarded after delivery.
Repeating the same or a similar query re-derives the same answer from
scratch. Step 9 (section 5.1) of the research corpus spec calls for
writing the synthesis back as a derived source and chunk with citation
edges to every row it consumed, so the cache both serves and grows.

## Solution

A new tool `tools/corpus/rowreuse.py` with three subcommands:

- `write --query TEXT --answer TEXT --sources ID,ID,...`: creates a
  derived source + chunk + citation edges from a synthesis. Idempotent
  via content hash check. Returns the new (or existing) chunk_id.
- `check [--db PATH]`: scans all derived chunks for provenance
  violations and reports them.
- `selftest`: exercises 9 checks covering write, kind validation,
  citation creation, idempotency, provenance cap enforcement, mixed
  sources, and edge cases.

### Provenance guard

A derived row is capped at one hop of provenance depth. The
`validate_sources` function rejects a write when ALL source chunks are
themselves derived (the sole-citation rule from the spec). Mixed sources
(some derived, some primary) are allowed.

`check_provenance` scans the entire corpus for violations of this
invariant: any derived chunk whose citations all point to other derived
sources is flagged.

### Write mechanics

Each write creates three artifacts in a single transaction:

1. A `sources` row with `kind='derived'`, a deterministic `source_id`,
   and a `derived://` URI keyed on the query hash.
2. A `chunks` row with `kind='claim'`, the answer as both `norm_text`
   and `raw_text`, and a heading path from the query.
3. One `citations` row per source chunk, linking the derived chunk to
   each source's `source_id` and `canonical_uri`, with `tag='derived'`
   and a locator from the query.

Idempotency: if a chunk with the same `norm_sha256` and `kind='derived'`
already exists, the existing `chunk_id` is returned without inserting
duplicates.

## Results

First run against the real corpus (5936 chunks from 365 sources):
- Provenance check: 0 violations (clean baseline before any derived rows)
- Test write: 1 derived chunk created with 3 citations, provenance clean

## Design decisions

- Source and chunk IDs are deterministic (sha256-based), so re-runs
  produce identical rows via INSERT OR IGNORE.
- The one-hop cap is enforced at write time, not retroactively. The
  `check` subcommand is a secondary audit for data that bypassed the
  write path.
- Citation `tag` is set to `'derived'` and `verified` to 1 since the
  provenance relationship is known at write time, not inferred.

## Scope

- `tools/corpus/rowreuse.py`: new tool
- `docs/specs/2026-08-30-corpus-row-reuse.md`: this spec

## Non-goals

- Automatic triggering from retrieval queries (requires integration
  with a retrieval pipeline that does not yet exist).
- Embedding or reranking derived chunks (spec step 5, separate feature).
- Executing derived content as actions (cache2action, spec step 10).
