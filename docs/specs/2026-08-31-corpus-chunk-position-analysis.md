# Corpus Chunk Position Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/chunk_position_analysis.py

## Problem

The chunks.ordinal column had zero GROUP BY queries anywhere in the
codebase.  Every reference to ordinal was either an INSERT populating
the column or an ORDER BY for display sorting.  No tool revealed how
many chunks a typical source produces, whether chunk kinds vary by
document position, or whether citation density correlates with where
a chunk sits within its source.

## Solution

A new tool `tools/corpus/chunk_position_analysis.py` with four
subcommands:

- `depth [--db PATH] [--json]`: distribution of document depths
  (max ordinal + 1 per source) in buckets (1, 2-3, 4-5, 6-10,
  11-20, >20), showing how many sources fall into each length tier.
- `kind-by-position [--db PATH] [--json]`: chunk kind distribution
  by document position (only, first, early, middle, late, last),
  revealing whether code chunks cluster at certain positions while
  prose or claim chunks dominate others.
- `citation-by-position [--db PATH] [--json]`: citation density by
  document position with total citations, mean citations, and cited
  rate per position bucket.
- `summary [--db PATH] [--json]`: aggregate positional statistics
  including depth mean/max/min, single-chunk source count and rate,
  and the dominant chunk kind for first and last positions.
- `selftest`: exercises 14 checks covering depth entries, bucket
  counts, share summation, kind-by-position entries, only/first/last
  position counts, citation entries, citation totals, cited rate,
  summary counts, depth stats, JSON serialisation, and empty corpus.

### Design properties

- **Relative position bucketing**: positions are classified relative
  to each source's own depth rather than using absolute ordinals,
  making the analysis meaningful regardless of document length.
- **Single-chunk awareness**: the "only" position bucket separates
  single-chunk sources from multi-chunk documents, since a chunk
  that is both first and last in a one-chunk source has different
  structural meaning than a leading or trailing chunk.
- **Citation correlation**: connecting citation density to position
  reveals whether leading chunks (often abstracts or introductions)
  are more cited than trailing chunks (often appendices).
- **Accepted-only scope**: all analyses filter to accepted chunks,
  matching the corpus downstream consumers use.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/chunk_position_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-chunk-position-analysis.md`: this spec

## See also

- [corpus-chunk-kind-profile](2026-08-31-corpus-chunk-kind-profile.md):
  analyses chunk kind distribution per source and per domain; this
  tool adds the positional dimension to chunk kind analysis.
- [corpus-citation-analysis](2026-08-31-corpus-citation-analysis.md):
  analyses citation targets and verification; this tool correlates
  citation density with document position.
- [corpus-word-count-distribution](2026-08-31-corpus-word-count-distribution.md):
  analyses chunk size in words; this tool analyses chunk count per
  source (document depth).
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; positional patterns are a
  complementary structural signal.

## Non-goals

- Automatic chunk reordering or position-based filtering.
- Heading hierarchy analysis (see heading-depth-analysis).
- Position-aware chunk quality scoring.
- Cross-source positional alignment.
