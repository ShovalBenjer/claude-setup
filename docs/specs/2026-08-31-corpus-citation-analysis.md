# Corpus Citation Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/citation_analysis.py

## Problem

The citations table records which chunks cite which external URIs, but
no tool analysed citation patterns across the corpus.  Finding the most
referenced sources, measuring how well each source's claims are backed
by citations, or tracking verification progress required manual queries.

## Solution

A new tool `tools/corpus/citation_analysis.py` with four subcommands:

- `top-targets [--db PATH] [--top N] [--json]`: most frequently cited
  target URIs across all chunks.  Reports citation count, distinct
  chunk count, and how many citations are verified.
- `coverage [--db PATH] [--json]`: per-source citation coverage for
  accepted claim chunks.  Reports how many claims in each source have
  at least one citation, with an overall coverage rate.
- `verification [--db PATH] [--json]`: verification rates across all
  citations, broken down by tag (primary, secondary, etc.).  Reports
  total, verified, unverified counts and rates.
- `uncited-claims [--db PATH] [--limit N] [--json]`: accepted claim
  chunks with zero citations.  These are claims the corpus treats as
  valid but that cite no evidence.
- `selftest`: exercises 14 checks covering top target ranking, chunk
  counts, top-N limiting, per-source coverage, verification rates,
  by-tag breakdown, uncited claim detection, prose exclusion, JSON
  serialisation, empty corpus, and coverage rate calculation.

### Design properties

- **Target-level aggregation**: citations to the same URI from
  different chunks are counted together, showing which references
  anchor the most claims.
- **Per-source granularity**: coverage reports let operators see which
  sources need more citations versus which are well-evidenced.
- **Verification tracking**: by-tag verification rates show where
  verification effort should be directed.
- **Claim-only scoping**: coverage and uncited-claims focus on claim
  chunks, excluding prose, code, and other non-assertive kinds.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/citation_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-citation-analysis.md`: this spec

## See also

- [corpus-source-chain](2026-08-31-corpus-source-chain.md): traces
  source supersession; this tool traces citation relationships.
- [corpus-audit](2026-08-31-corpus-audit.md): identifies unverified
  citations as issues; this tool provides the full verification
  breakdown.
- [corpus-dashboard](2026-08-31-corpus-dashboard.md): reports total
  citation count; this tool analyses citation patterns and coverage.

- [corpus-chunk-evolution](2026-08-31-corpus-chunk-evolution.md):
  analyses content change patterns; this tool analyses citation
  relationships.
- [corpus-source-citation-net](2026-08-31-corpus-source-citation-net.md):
  aggregates citations to source-to-source topology; this tool
  analyses citation density and patterns at chunk level.
- [corpus-cross-ref-density](2026-08-31-corpus-cross-ref-density.md):
  measures internal vs external citation patterns per source;
  this tool analyses citation patterns at the chunk level.

## Non-goals

- Citation graph visualisation.
- Automated citation verification or link checking.
- Citation style or format validation.
- Cross-corpus citation comparison.
