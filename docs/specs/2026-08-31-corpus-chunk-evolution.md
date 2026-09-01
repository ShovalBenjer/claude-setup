# Corpus Chunk Evolution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/chunk_evolution.py

## Problem

The chunk_versions table records how chunk content changes across
re-ingestions, but no tool analysed these changes at scale.  Finding
which chunks are most frequently revised, measuring corpus-wide content
drift, or tracing the full edit history of a single chunk required
manual queries.

## Solution

A new tool `tools/corpus/chunk_evolution.py` with three subcommands:

- `most-revised [--db PATH] [--top N] [--json]`: chunks with the most
  version entries, ranked by revision count.  Excludes single-version
  chunks.  Reports revision count, first and last seen timestamps,
  kind, and status.
- `drift [--db PATH] [--json]`: corpus-wide content drift statistics.
  Reports chunks with versions, single vs multi version counts, total
  and average revisions, max revisions, and a list of word count
  changes between consecutive versions.
- `history --chunk-id CID [--db PATH] [--json]`: full version history
  for one chunk.  Reports each version's hash, word count, word count
  delta from previous version, and snapshot timestamp.
- `selftest`: exercises 14 checks covering most-revised ranking,
  single-version exclusion, top-N limiting, drift totals, word count
  change detection, zero-delta filtering, chunk history ordering,
  version deltas, nonexistent chunk handling, JSON serialisation,
  empty corpus, and average revision calculation.

### Design properties

- **Revision ranking**: surfaces the most-edited chunks, which are
  candidates for stability review or content freezing.
- **Word count tracking**: detects growth and shrinkage patterns
  across versions, showing where content is expanding or being trimmed.
- **Zero-delta filtering**: versions with identical word counts are
  excluded from the word count changes list, keeping reports focused
  on actual content size shifts.
- **Graceful degradation**: returns empty results when the
  chunk_versions table does not exist.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/chunk_evolution.py`: new tool
- `docs/specs/2026-08-31-corpus-chunk-evolution.md`: this spec

## See also

- [corpus-citation-analysis](2026-08-31-corpus-citation-analysis.md):
  analyses citation patterns; this tool analyses content change
  patterns over time.
- [corpus-chunk-versions](2026-08-30-corpus-chunk-versions.md):
  the versioning infrastructure this tool reads from.
- [corpus-chunk-profile](2026-08-31-corpus-chunk-profile.md):
  assembles a chunk dossier; this tool traces a chunk's edit lineage.
- [corpus-dashboard](2026-08-31-corpus-dashboard.md): reports corpus
  totals; this tool reports revision dynamics.

- [corpus-artifact-adoption](2026-08-31-corpus-artifact-adoption.md):
  analyses technology artifact patterns; this tool analyses content
  revision patterns.
- [corpus-version-churn](2026-08-31-corpus-version-churn.md):
  measures temporal revision velocity and acceleration; this tool
  counts revisions and measures content drift.

## Non-goals

- Content diffing between version texts.
- Automated version pruning or rollback.
- Cross-chunk correlation of revision patterns.
- Version-level embedding comparison.
