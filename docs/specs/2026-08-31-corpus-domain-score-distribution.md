# Corpus Domain Score Distribution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/domain_score_distribution.py

## Problem

The domain analysis tool reports average classification scores per
domain, but no tool analysed the distribution of those scores.
Low-confidence domain assignments may indicate ambiguous content
that the classifier cannot place reliably, while consistently high
scores across a domain may mask a few uncertain assignments.
Identifying calibration issues and low-confidence assignments
required manual SQL queries on the chunk_domains table.

## Solution

A new tool `tools/corpus/domain_score_distribution.py` with four
subcommands:

- `bands [--db PATH] [--json]`: four-band histogram of domain
  classification scores (0.00-0.25, 0.25-0.50, 0.50-0.75,
  0.75-1.00), showing count and share per band.
- `per-domain [--db PATH] [--json]`: score statistics per domain
  (mean, median, min, max, standard deviation), sorted by mean
  score ascending to surface the least confident domains first.
- `low-confidence [--db PATH] [--threshold F] [--json]`:
  assignments with score below a configurable threshold
  (default 0.5), sorted by score ascending.
- `summary [--db PATH] [--json]`: aggregate score statistics
  including total assignments, unique domains, mean, median,
  min, max, standard deviation, and counts of low-confidence
  (<0.5) and high-confidence (>=0.75) assignments.
- `selftest`: exercises 14 checks covering band count, share
  summation, total count, low-band accuracy, domain enumeration,
  mean ordering, mean bounds, low-confidence detection, score
  threshold, sort ordering, summary structure, confidence counts,
  JSON serialisation, and empty corpus.

### Design properties

- **Four-band histogram**: matches the tag_landscape score-band
  convention for consistent cross-tool comparison.
- **Low-confidence surfacing**: ascending sort and threshold
  filtering highlight assignments most in need of review or
  reclassification.
- **Graceful degradation**: returns empty results when the
  chunk_domains table does not exist, allowing safe use before
  domain classification has run.
- **Accepted-only scope**: joins through accepted chunks,
  excluding quarantined or rejected content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/domain_score_distribution.py`: new tool
- `docs/specs/2026-08-31-corpus-domain-score-distribution.md`: this spec

## See also

- [corpus-domain-analysis](2026-08-31-corpus-domain-analysis.md):
  reports per-domain average scores; this tool analyses the full
  score distribution and calibration quality.
- [corpus-domain-balance](2026-08-31-corpus-domain-balance.md):
  measures domain size balance via Gini and entropy; this tool
  measures classification confidence balance.
- [corpus-chunk-kind-profile](2026-08-31-corpus-chunk-kind-profile.md):
  analyses kind distribution per domain; this tool analyses score
  distribution per domain.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; domain classification confidence
  is a complementary quality signal.

## Non-goals

- Domain reclassification or score adjustment.
- Classifier retraining or parameter tuning.
- Cross-corpus calibration comparison.
- Score normalisation or rescaling.
