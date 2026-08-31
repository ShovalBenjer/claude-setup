# Corpus Heading Depth Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_depth_analysis.py

## Problem

The chunks table stores heading_path for every chunk, encoding the
document hierarchy as a slash-separated path (e.g. /methods/data).
No tool analysed the depth distribution, section organization, or
structural patterns encoded in these paths.  Identifying flat
documents that lack subsections or deeply nested ones that may
indicate over-segmentation required manual parsing.

## Solution

A new tool `tools/corpus/heading_depth_analysis.py` with four
subcommands:

- `depth-distribution [--db PATH] [--json]`: distribution of
  heading depths across accepted chunks, showing count and share
  per depth level.
- `per-source [--db PATH] [--json]`: heading depth statistics per
  source including chunk count, mean/min/max depth, and distinct
  depth levels.  Sorted by max depth descending to surface the
  most structurally complex sources first.
- `top-sections [--db PATH] [--top N] [--json]`: most common
  top-level heading sections across the corpus, showing which
  organizational patterns recur.
- `summary [--db PATH] [--json]`: aggregate heading statistics
  including total chunks, mean/median/max depth, distinct top
  sections, distinct depth levels, and counts of shallow (depth
  at most 1) and deep (depth at least 4) chunks.
- `selftest`: exercises 14 checks covering depth distribution,
  depth level presence, share summation, depth-1 accuracy,
  per-source results, max depth per source, sort order, top
  section counts, summary totals, shallow count, JSON
  serialisation, and empty corpus.

### Design properties

- **Path parsing**: splits heading_path on "/" to derive depth,
  treating each non-empty segment as one heading level.
- **Top-level section extraction**: identifies the first path
  component as the organizational section, enabling corpus-wide
  section pattern analysis.
- **Shallow/deep classification**: fixed thresholds (depth at
  most 1 for shallow, at least 4 for deep) flag structural
  extremes.
- **Accepted-only scope**: analyses only accepted chunks.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_depth_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-depth-analysis.md`: this spec

## See also

- [corpus-chunk-profile](2026-08-30-corpus-chunk-profile.md):
  analyses chunk structure and segmentation; this tool analyses
  the heading hierarchy that defines that structure.
- [corpus-word-count-distribution](2026-08-31-corpus-word-count-distribution.md):
  analyses chunk length; heading depth is a complementary
  structural dimension.
- [corpus-readability](2026-08-30-corpus-readability.md):
  measures prose complexity; document structure depth may
  correlate with readability.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; heading depth uniformity
  is a complementary structural signal.

## Non-goals

- Heading text content analysis or normalisation.
- Automatic document restructuring or heading correction.
- Cross-source heading hierarchy alignment.
- Heading-based chunk splitting or merging.
