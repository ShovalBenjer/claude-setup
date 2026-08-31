# Corpus Version-Domain Stability

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_domain_stability.py

## Problem

Zero joins between chunk_versions and chunk_domains existed anywhere
in the codebase.  Understanding whether frequently-revised chunks
cluster in certain domains, or whether domain assignment correlates
with version depth, required a manual multi-table join.

## Solution

A new tool `tools/corpus/version_domain_stability.py` with four
subcommands:

- `churn-by-domain [--db PATH] [--json]`: mean version count per
  domain with chunk count, total versions, mean versions, and max
  version depth.
- `stability [--db PATH] [--json]`: stability classification per
  domain (stable, moderate, active, volatile) based on mean version
  count thresholds.
- `volatile [--db PATH] [--json] [--threshold N]`: chunks with
  high version count and their domain assignments, sorted by version
  depth descending.
- `summary [--db PATH] [--json]`: aggregate stability statistics
  including domains with versions, stability label distribution,
  and most volatile and stable domains.
- `selftest`: exercises 14 checks covering churn-by-domain entries,
  per-domain mean versions, stability labels, volatile chunk
  detection, domain counts on volatile chunks, summary totals, most
  volatile and stable identification, JSON serialisation, and empty
  corpus.

### Design properties

- **Stability labels**: four tiers (stable, moderate, active,
  volatile) based on mean version count per domain, providing a
  quick structural comparison.
- **Per-chunk volatile view**: high-churn chunks are listed with
  their full domain assignments, connecting version instability to
  topical classification.
- **Configurable threshold**: the volatile subcommand accepts a
  version threshold parameter for different sensitivity levels.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_domain_stability.py`: new tool
- `docs/specs/2026-08-31-corpus-version-domain-stability.md`: this spec

## See also

- [corpus-version-timeline](2026-08-31-corpus-version-timeline.md):
  analyses version snapshot timing; this tool crosses versions with
  domain assignments.
- [corpus-classification-timeline](2026-08-31-corpus-classification-timeline.md):
  analyses classification timing; this tool connects domains to
  version churn rather than to classification timing.
- [corpus-domain-analysis](2026-08-31-corpus-domain-analysis.md):
  analyses domain membership; this tool adds the version stability
  dimension to domain analysis.

## Non-goals

- Automatic domain reassignment based on version stability.
- Version content diff analysis across domains.
- Stability prediction or trend forecasting.
- Domain-aware version pruning recommendations.
