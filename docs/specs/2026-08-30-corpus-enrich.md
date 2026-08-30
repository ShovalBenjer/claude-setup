# Corpus Entity Enrichment

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/enrich.py

## Problem

The artifacts table exists in the corpus schema but is populated only by
manual inserts or ad-hoc scripts.  Chunks that discuss specific libraries,
APIs, commands, and patterns have no automatic linkage to artifact records,
making it impossible to answer "which chunks mention pytorch?" or "is
numpy discussed with actual implementation evidence or only passing
mentions?"

## Solution

A new tool `tools/corpus/enrich.py` that scans chunk text for named
entities and creates artifact table entries with implementation evidence:

- `scan [--db PATH] [--json]`: finds entity mentions across all active
  (non-superseded) chunks.  Returns chunk IDs, entity names, mention
  counts, and whether implementation signals (import statements, install
  commands, code fences) are present.
- `apply [--db PATH] [--dry-run]`: creates artifact table entries for
  discovered entities.  Skips already-existing artifact IDs.  Dry-run
  mode reports what would be created without writing.
- `lookup --name NAME [--db PATH] [--json]`: finds all artifacts for a
  given entity name, joined with chunk metadata.
- `stats [--db PATH] [--json]`: reports entity coverage, unique entity
  count, mention totals, implementation vs discussion ratio, and
  top entities by frequency.
- `selftest`: exercises 16 checks covering entity detection,
  implementation signal classification, scan/apply/lookup/stats
  correctness, superseded-chunk exclusion, and edge cases.

### Entity recognition

31 known entities across five artifact types:

- **library** (14): sqlite, fts5, numpy, pandas, polars, scikit-learn,
  pytorch, tensorflow, react, next.js, tailwind, redis, postgresql
- **api** (5): fastapi, flask, django, express, cloudflare workers,
  graphql
- **command** (6): docker, kubernetes, git, pytest, ruff, pip, cargo, npm
- **pattern** (4): oauth, jwt, rest api, websocket

Each entity carries one or more regex patterns for case-insensitive
matching against chunk norm_text.

### Implementation signals

Four regex patterns distinguish "mentions library X" from "uses library X
in code":

1. Import statements (`import X`, `from X import`)
2. Package installs (`pip install`, `npm install`, `cargo add`)
3. Shell commands (`$ command`)
4. Code fences with language tags

A chunk with at least one matching signal gets `implemented=1` in the
artifact record.

### Design properties

- **Idempotent**: artifact IDs are derived from chunk_id + entity name,
  so re-running apply never creates duplicates.
- **Evidence-based**: the `implemented` flag is grounded in detectable
  code patterns, not keyword proximity.
- **Read-only scan**: scan and stats are pure reads; only apply writes.
- **Respects chunk lifecycle**: superseded chunks are excluded from scan.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/enrich.py`: new tool
- `docs/specs/2026-08-30-corpus-enrich.md`: this spec

## Non-goals

- NER with spaCy or transformer models.
- Dynamic entity discovery from corpus content.
- Version detection or compatibility tracking.
