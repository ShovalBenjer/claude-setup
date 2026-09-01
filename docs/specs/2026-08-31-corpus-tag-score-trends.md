# Corpus Tag Score Trends

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_score_trends.py

## Problem

The tag landscape tool reports static score-band distributions, but
no tool tracked how tag classification scores evolve over time.
A tagger whose confidence degrades as the corpus grows may indicate
concept drift or training data staleness, while improving scores
may validate retraining decisions.  Identifying these patterns
required manual temporal aggregation of the chunk_tags table.

## Solution

A new tool `tools/corpus/tag_score_trends.py` with four
subcommands:

- `by-period [--db PATH] [--bucket month|week] [--json]`: mean
  tag score per time period, showing corpus-wide tagging confidence
  evolution.
- `per-tag [--db PATH] [--json]`: score statistics per tag with
  earliest and latest assignment dates, sorted by mean score
  ascending to surface the least confident tags first.
- `drift [--db PATH] [--json]`: tags whose score changed between
  their first and second chronological half of assignments,
  labelled as improving, degrading, or stable, sorted by absolute
  drift descending.
- `summary [--db PATH] [--json]`: aggregate trend statistics
  including total assignments, unique tags, mean score, periods
  covered, and counts of improving, degrading, and stable tags.
- `selftest`: exercises 14 checks covering period count, period
  ordering, score bounds, tag enumeration, mean ordering, earliest
  date, drift detection, improving direction, degrading direction,
  drift sorting, summary totals, drift counts, JSON serialisation,
  and empty corpus.

### Design properties

- **Half-split drift detection**: splits each tag's assignments
  chronologically and compares first-half to second-half mean,
  detecting gradual confidence changes without requiring fixed
  time windows.
- **Per-tag granularity**: different tags may drift independently,
  and this tool surfaces tag-level trends that corpus-wide averages
  hide.
- **Graceful degradation**: returns empty results when the
  chunk_tags table does not exist.
- **Accepted-only scope**: joins through accepted chunks,
  excluding quarantined or rejected content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_score_trends.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-score-trends.md`: this spec

## See also

- [corpus-tag-landscape](2026-08-31-corpus-tag-landscape.md):
  reports static tag distribution and score bands; this tool
  analyses how those scores change over time.
- [corpus-tag-cooccurrence](2026-08-31-corpus-tag-cooccurrence.md):
  analyses which tags appear together; this tool analyses
  individual tag confidence trajectories.
- [corpus-tag-entropy](2026-08-31-corpus-tag-entropy.md):
  measures tag diversity via information entropy; this tool
  measures tag confidence stability.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; tag score drift is a
  complementary classifier health signal.

## Non-goals

- Tagger retraining or parameter adjustment.
- Tag score correction or normalisation.
- Cross-corpus score comparison.
- Automated drift alerting.
