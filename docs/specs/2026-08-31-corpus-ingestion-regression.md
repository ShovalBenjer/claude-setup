# Corpus Ingestion Regression Detector

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/ingestion_regression.py

## Problem

The chunk_versions table records content snapshots across re-ingestion
cycles, but no tool compared consecutive versions to detect quality
regressions.  A re-ingestion that silently drops 60% of a chunk's
content, changes its hash while shrinking it, or produces fewer words
went unnoticed until someone manually inspected the version history.

## Solution

A new tool `tools/corpus/ingestion_regression.py` with three
subcommands:

- `detect [--db PATH] [--json]`: finds chunks where a newer version
  is worse than its predecessor.  Detects word count drops exceeding
  20% and content hash changes that shrink the chunk.  Reports the
  from/to version numbers, snapshot timestamp, and issue details.
  Sorted by worst drop percentage first.
- `history [--db PATH] [--chunk CHUNK_ID] [--json]`: version history
  for a single chunk with change annotations (initial, unchanged,
  grew, shrank, rewritten).  Enables manual inspection of a
  flagged regression.
- `summary [--db PATH] [--json]`: aggregate regression statistics
  including total versioned chunks, multi-version chunks, regressed
  chunk count, issue type breakdown, and worst drop percentage.
- `selftest`: exercises 14 checks covering regression detection,
  stable exclusion, growth exclusion, regression details, drop
  percentage accuracy, sort order, history annotations, growing
  history, stable history, summary structure, issue types, worst
  drop, JSON serialisation, and empty corpus.

### Regression criteria

A version transition is flagged as a regression when either:

1. **word_count_drop**: the new version has more than 20% fewer
   words than the previous version.
2. **content_shrink**: the content hash changed (norm_sha256 differs)
   and word count decreased, even if below the 20% threshold.

### Design properties

- **Version-pair comparison**: examines each consecutive version pair
  independently, catching regressions at any point in the history.
- **Severity ordering**: results sort by worst drop percentage,
  putting the most severe regressions at the top.
- **Change annotations**: the history subcommand labels each version
  transition (grew, shrank, rewritten, unchanged) for visual
  inspection.
- **Graceful degradation**: returns empty results when the
  chunk_versions table does not exist.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/ingestion_regression.py`: new tool
- `docs/specs/2026-08-31-corpus-ingestion-regression.md`: this spec

## See also

- [corpus-claim-consensus](2026-08-31-corpus-claim-consensus.md):
  measures cross-source agreement; this tool detects within-chunk
  quality regressions across versions.
- [corpus-chunk-versions](2026-08-30-corpus-chunk-versions.md):
  the versioning infrastructure this tool reads from.
- [corpus-freshness-scorer](2026-08-31-corpus-freshness-scorer.md):
  temporal freshness scoring; this tool detects version-level
  regressions rather than age-based staleness.
- [corpus-artifact-graph](2026-08-31-corpus-artifact-graph.md):
  maps relationships between artifacts; this tool detects quality
  regressions within individual chunks across versions.

## Non-goals

- Automatic rollback to previous versions.
- Content diff or text-level change tracking.
- Regression alerting or threshold configuration.
- Cross-chunk regression correlation.
