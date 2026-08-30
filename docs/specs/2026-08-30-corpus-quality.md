# Corpus Quality Scoring

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/quality.py

## Problem

With 4507 quarantined chunks awaiting review, there was no way to
prioritise which chunks or sources to examine first.  Quality was
assessed manually by reading samples, with no repeatable metric across
the corpus.

## Solution

A new tool `tools/corpus/quality.py` with three subcommands:

- `score [--db PATH] [--status STATUS] [--source SOURCE_ID] [--min-score N]
  [--max-score N] [--n N] [--json]`: scores individual chunks on five
  weighted signals: word count adequacy (0.25), citation density (0.30),
  heading structure (0.10), artifact extraction (0.15), and contradiction
  involvement (0.20).  Filters by status, source, and score range.
- `sources [--db PATH] [--n N] [--json]`: scores sources by aggregate
  quality: acceptance rate, citation density, artifact density,
  contradiction count, and word count distribution.
- `distribution [--db PATH] [--json]`: quality score distribution across
  the entire corpus with five-bucket histogram, mean/median/min/max,
  and per-status breakdown.
- `selftest`: exercises 16 checks covering all three subcommands,
  filter combinations, sort ordering, edge cases, and JSON serialization.

### Design properties

- **Measurable signals only**: every quality dimension is computed from
  existing DB columns, no subjective ratings.
- **Weighted composite score**: the five signals combine into a 0-to-1
  score with tunable weights.
- **Promotion prioritisation**: scoring quarantined chunks by quality
  identifies the best candidates for `promote.py` review.
- **Structured output**: `--json` on every subcommand for machine
  consumption and downstream tooling.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/quality.py`: new tool
- `docs/specs/2026-08-30-corpus-quality.md`: this spec

## Non-goals

- Subjective or LLM-based quality assessment.
- Automatic promotion based on score thresholds.
- Quality trend tracking over time.
