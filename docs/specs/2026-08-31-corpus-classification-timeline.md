# Corpus Classification Timeline

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/classification_timeline.py

## Problem

The chunk_domains.classified_utc column had no temporal distribution
analysis.  Existing tools (domain_analysis, domain_balance,
domain_score_distribution) analyse domain membership and scores but
never when classification activity happens over time, how it varies
by domain, or how classification scores evolve across periods.

## Solution

A new tool `tools/corpus/classification_timeline.py` with four
subcommands:

- `timeline [--db PATH] [--json]`: distribution of classification
  times by month, with count and share per month.
- `by-domain [--db PATH] [--json]`: classification activity per
  domain with total classifications and distinct months of activity.
- `score-trend [--db PATH] [--json]`: mean classification score per
  month with min and max, revealing whether classification confidence
  changes over time.
- `summary [--db PATH] [--json]`: aggregate classification statistics
  including total classifications, distinct domains, distinct months,
  classification range, and overall mean score.
- `selftest`: exercises 14 checks covering timeline entry count,
  monthly counts, share summation, by-domain entries, ml domain
  totals and month span, systems count, score trend entries, June
  and August mean scores, summary totals, JSON serialisation, and
  empty corpus.

### Design properties

- **Monthly granularity**: classification times grouped by month
  reveal whether domain assignment happens in bursts or continuously.
- **Domain stratification**: per-domain breakdown reveals whether
  certain domains get classified in narrow windows or across many
  months.
- **Score trend**: tracking mean score per month reveals whether
  classification confidence improves, degrades, or stays stable as
  the corpus grows.
- **Non-base-schema awareness**: the selftest creates the
  chunk_domains table with CREATE TABLE IF NOT EXISTS since it is
  not part of the base init_schema.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/classification_timeline.py`: new tool
- `docs/specs/2026-08-31-corpus-classification-timeline.md`: this spec

## See also

- [corpus-domain-analysis](2026-08-31-corpus-domain-analysis.md):
  analyses domain membership and coverage; this tool adds the
  temporal dimension.
- [corpus-domain-score-distribution](2026-08-31-corpus-domain-score-distribution.md):
  analyses score distributions per domain; this tool tracks how
  scores evolve over time.
- [corpus-temporal-distribution](2026-08-31-corpus-temporal-distribution.md):
  analyses ingestion, publication, and fetch timestamps; this tool
  analyses the domain classification timestamp.

## Non-goals

- Automatic domain reclassification scheduling.
- Classification quality assessment or drift detection.
- Domain taxonomy evolution tracking.
- Score threshold optimisation over time.
