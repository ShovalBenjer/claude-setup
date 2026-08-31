# Corpus Word Count Distribution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/word_count_distribution.py

## Problem

The corpus tracks word counts per chunk, but no tool analysed the
distribution of those counts across the corpus.  Unusually short
chunks may indicate extraction failures (headings captured without
body text), while unusually long chunks may indicate missing
segmentation.  Identifying these patterns required manual SQL
queries and ad-hoc statistics.

## Solution

A new tool `tools/corpus/word_count_distribution.py` with four
subcommands:

- `histogram [--db PATH] [--json]`: seven-bin histogram of word
  counts across accepted chunks (0-10, 11-50, 51-100, 101-250,
  251-500, 501-1000, 1001+), showing count and share per bin.
- `per-kind [--db PATH] [--json]`: word count statistics per chunk
  kind (mean, median, min, max, standard deviation), sorted by
  mean word count descending.
- `outliers [--db PATH] [--threshold F] [--json]`: chunks whose
  word count deviates beyond a configurable number of standard
  deviations (default 2.0) from the corpus mean, reporting z-score
  and direction (short or long).
- `summary [--db PATH] [--json]`: aggregate word count statistics
  including total chunks and words, mean, median, min, max,
  standard deviation, and counts of short (<=10 words) and long
  (>500 words) chunks.
- `selftest`: exercises 14 checks covering bin count, share
  summation, total count, short-bin accuracy, kind enumeration,
  kind ordering, mean bounds, outlier detection, long-outlier
  identification, z-score sorting, summary structure, mean range,
  JSON serialisation, and empty corpus.

### Design properties

- **Fixed bins**: the seven histogram bins are chosen to separate
  common chunk length ranges for research text, making the output
  directly comparable across corpus snapshots.
- **Z-score outlier detection**: uses population standard deviation
  for outlier identification, with a configurable threshold for
  different sensitivity requirements.
- **Per-kind breakdown**: different chunk kinds (claim, prose, code,
  table, config, link) have different expected lengths, and this
  tool surfaces those differences.
- **Accepted-only scope**: analyses only accepted chunks, excluding
  quarantined or rejected content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/word_count_distribution.py`: new tool
- `docs/specs/2026-08-31-corpus-word-count-distribution.md`: this spec

## See also

- [corpus-chunk-profile](2026-08-30-corpus-chunk-profile.md):
  analyses chunk structure and segmentation; this tool analyses
  word count patterns specifically.
- [corpus-readability](2026-08-30-corpus-readability.md):
  measures prose complexity; word count distribution is a
  complementary length dimension.
- [corpus-chunk-kind-profile](2026-08-31-corpus-chunk-kind-profile.md):
  analyses kind distribution per source and domain; this tool
  analyses word count distribution per kind.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; word count distribution adds a
  length uniformity signal.
- [corpus-domain-analysis](2026-08-30-corpus-domain-analysis.md):
  analyses domain coverage; word count patterns may vary by domain.

## Non-goals

- Automatic chunk splitting or merging.
- Word count normalisation or correction.
- Per-source word count aggregation.
- Language-specific tokenisation differences.
