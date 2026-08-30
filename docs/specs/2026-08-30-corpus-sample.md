# Corpus Sample

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/sample.py

## Problem

Reviewing corpus quality requires inspecting representative chunks, but
the corpus has 5937 chunks across 366 sources. Manual SQL queries are
tedious, and without stratification the reviewer over-samples large
sources and misses edge cases in smaller ones.

## Solution

A new tool `tools/corpus/sample.py` with two subcommands:

- `draw [--db PATH] [--n N] [--kind KIND] [--status STATUS]
  [--source SOURCE_ID] [--min-words N] [--max-words N] [--seed SEED]
  [--json]`: draws a random sample of chunks with optional filters.
- `stratified [--db PATH] [--per-stratum N] [--by {kind,status,source}]
  [--json]`: draws stratified samples, N per stratum, grouped by kind,
  status, or source.
- `selftest`: exercises 16 checks covering both draw modes, filters,
  reproducibility, result shape, and JSON serialization.

### Design properties

- **Filtered sampling**: draw with kind, status, source, and word count
  filters to target specific review needs.
- **Reproducible**: `--seed` produces deterministic samples for audit
  trails and regression comparisons.
- **Stratified**: the stratified subcommand ensures every kind, status, or
  source gets equal representation regardless of population size.
- **Truncated text**: sample text is capped at 500 characters to keep
  output scannable while showing enough context.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/sample.py`: new tool
- `docs/specs/2026-08-30-corpus-sample.md`: this spec

## Non-goals

- Statistical significance testing (the tool draws samples, the operator
  interprets them).
- Weighted sampling by source size or word count (uniform random within
  each stratum is the right default for quality review).
- Automatic quality scoring of sampled chunks.
