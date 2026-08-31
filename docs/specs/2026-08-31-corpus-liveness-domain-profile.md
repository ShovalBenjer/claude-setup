# Corpus Liveness Domain Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/liveness_domain_profile.py

## Problem

publisher_domain_profile.py profiles domains by publisher.
liveness_tag_profile.py correlates liveness with chunk tags.
No tool joins sources.liveness with chunk_domains to measure whether
live sources span different knowledge domains than stale or archived
ones, or how domain scores vary across liveness states.

## Solution

A new tool `tools/corpus/liveness_domain_profile.py` with four
subcommands:

- `by-liveness [--db PATH] [--json]`: domain distribution per
  source liveness state, showing distinct domains, domain
  assignments, classified chunk count, and average score.
- `by-domain [--db PATH] [--json]`: liveness distribution per
  domain, showing how many liveness states each domain spans,
  with assignment counts and average score.
- `concentration [--db PATH] [--json]`: per-liveness domain
  concentration, filtered to states with at least two domain
  assignments, ordered by diversity ratio (distinct domains
  divided by total assignments).
- `summary [--db PATH] [--json]`: aggregate statistics including
  total liveness states, states with domains, coverage ratio,
  distinct domains, total assignments, average domains per state,
  single-state domain count, and single-state domain rate.
- `selftest`: exercises 14 checks covering per-state domain counts,
  domain-to-state distributions, concentration filtering, summary
  totals, JSON round-trip, and empty corpus.

### Design properties

- **Source-based liveness attribution**: domains are attributed to
  the liveness state of the source that contains the classified
  chunk.
- **Knowledge breadth**: concentration subcommand reveals whether
  actively maintained sources cover broader knowledge domains than
  stale or archived ones.
- **Single-state exclusivity**: summary tracks domains that appear
  in only one liveness state, indicating liveness-specific
  knowledge coverage.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/liveness_domain_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-liveness-domain-profile.md`: this spec

## See also

- [corpus-liveness-tag-profile](2026-08-31-corpus-liveness-tag-profile.md):
  correlates liveness with chunk tags; this tool correlates liveness
  with chunk domains.
- [corpus-publisher-domain-profile](2026-08-31-corpus-publisher-domain-profile.md):
  profiles domains by publisher; this tool profiles domains by
  source liveness.

## Non-goals

- Liveness state prediction from domain patterns.
- Automatic domain recommendation based on source liveness.
- Domain-based staleness detection.
- Liveness-driven domain pruning or expansion.
