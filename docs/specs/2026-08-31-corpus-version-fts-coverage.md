# Corpus Version FTS Coverage

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_fts_coverage.py

## Problem

version_source_profile.py measures revision activity per source.
fts_edge_reachability.py correlates edges with FTS word count.
No tool measures how word count changes across chunk versions,
which sources gain or lose searchable content through revisions,
or how much total churn revisions produce relative to final word
count.

## Solution

A new tool `tools/corpus/version_fts_coverage.py` with four
subcommands:

- `by-source [--db PATH] [--json]`: per-source version word count
  statistics, including initial and latest aggregate word counts
  and net change.
- `word-delta [--db PATH] [--json]`: per-chunk word count delta
  between first and latest version, with growth direction flag.
- `churn-rate [--db PATH] [--json]`: total word count churn per
  source from consecutive version deltas, counting transitions
  that grew, shrank, or stayed unchanged.
- `summary [--db PATH] [--json]`: aggregate statistics including
  versioned chunk count, initial and latest word totals, net
  change, total churn, version coverage rate, and churn ratio.
- `selftest`: exercises 14 checks covering per-source aggregation,
  word delta computation, growth direction, churn calculation,
  transition counts, summary totals, JSON serialisation, and
  empty corpus.

### Design properties

- **Consecutive-version churn**: measures total churn as the sum
  of absolute word count differences between consecutive version
  numbers (v1 to v2, v2 to v3), not just first-to-last delta,
  capturing oscillations that net change hides.
- **Growth direction tracking**: flags each chunk as grew or not
  based on first-to-last version delta, enabling quick filtering
  of expanding versus contracting content.
- **Churn ratio**: normalises total churn against latest word
  count, showing how much rewriting a source underwent relative
  to its final size.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_fts_coverage.py`: new tool
- `docs/specs/2026-08-31-corpus-version-fts-coverage.md`: this spec

## See also

- [corpus-version-source-profile](2026-08-31-corpus-version-source-profile.md):
  measures revision activity per source; this tool measures word
  count evolution across revisions.
- [corpus-fts-edge-reachability](2026-08-31-corpus-fts-edge-reachability.md):
  correlates edges with FTS word count; this tool correlates
  version history with FTS word count.

## Non-goals

- Diffing actual text content between versions.
- Predicting future word count trends.
- FTS ranking or relevance tuning based on version history.
- Version-weighted search result boosting.
