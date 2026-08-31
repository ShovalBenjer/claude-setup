# Corpus Domain Coverage Balance

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/domain_balance.py

## Problem

The domain analysis tool reports chunk counts per domain, but no tool
measured whether content is distributed evenly or concentrated in a
few domains.  A corpus dominated by one domain has blind spots that
simple counts do not surface.  Quantifying evenness required manually
computing statistical measures over the distribution.

## Solution

A new tool `tools/corpus/domain_balance.py` with three subcommands:

- `balance [--db PATH] [--json]`: per-domain chunk counts and share
  of total.  Includes each domain's deviation from a uniform
  distribution.  Sorted by chunk count descending.
- `skew [--db PATH] [--threshold F] [--json]`: domains whose share
  deviates from uniform by more than the threshold (default 0.05).
  Sorted by absolute deviation descending to surface the most
  imbalanced domains first.
- `summary [--db PATH] [--json]`: aggregate balance statistics
  including Shannon entropy (bits), maximum entropy, normalised
  entropy (0 to 1), Gini coefficient, most and least covered
  domains, and over/under-represented counts.
- `selftest`: exercises 14 checks covering domain enumeration, sort
  order, count accuracy, share summation, deviation signs, skew
  filtering, threshold sensitivity, summary structure, entropy
  bounds, normalised entropy range, Gini bounds, most/least
  identification, JSON serialisation, and empty corpus.

### Balance metrics

Two complementary measures quantify distribution evenness:

1. **Shannon entropy** (bits): information-theoretic diversity.
   Maximum entropy (log2 of domain count) indicates perfectly
   uniform distribution.  Normalised entropy divides by the
   maximum, giving a 0 to 1 scale where 1 is perfectly even.
2. **Gini coefficient** (0 to 1): inequality measure.  Zero
   indicates perfect equality; higher values indicate concentration.
   Computed from the sorted cumulative distribution.

### Design properties

- **Accepted-only scope**: joins chunk_domains through accepted
  chunks, excluding quarantined or rejected content.
- **Deviation from uniform**: per-domain deviation shows which
  domains are over or under their fair share.
- **Configurable threshold**: the skew subcommand accepts a custom
  deviation threshold for different balance requirements.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/domain_balance.py`: new tool
- `docs/specs/2026-08-31-corpus-domain-balance.md`: this spec

## See also

- [corpus-domain-analysis](2026-08-30-corpus-domain-analysis.md):
  reports domain distribution and per-source coverage; this tool
  adds statistical evenness metrics over that distribution.
- [corpus-domain-tag-affinity](2026-08-31-corpus-domain-tag-affinity.md):
  analyses domain-tag relationships; this tool analyses domain-level
  content concentration.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; domain balance adds a coverage
  evenness dimension.
- [corpus-diversity](2026-08-30-corpus-diversity.md):
  measures vocabulary and content diversity; this tool measures
  domain-level distribution diversity.
- [corpus-readability](2026-08-31-corpus-readability.md):
  measures text complexity per chunk; this tool measures content
  distribution across domains.

## Non-goals

- Domain creation or reassignment suggestions.
- Minimum balance enforcement or gating.
- Temporal balance tracking over time.
- Cross-source domain balance comparison.
