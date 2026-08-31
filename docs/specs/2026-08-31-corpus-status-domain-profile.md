# Corpus Status Domain Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/status_domain_profile.py

## Problem

status_tag_profile.py profiles statuses by chunk tag patterns.
status_edge_profile.py profiles statuses by claim edge patterns.
No tool joins chunks.status with chunk_domains to measure whether
accepted chunks span different knowledge domains than quarantined
or rejected ones, or how domain scores vary across chunk statuses.

## Solution

A new tool `tools/corpus/status_domain_profile.py` with four
subcommands:

- `by-status [--db PATH] [--json]`: domain distribution per chunk
  status, showing distinct domains, domain assignments, classified
  chunk count, and average score.
- `by-domain [--db PATH] [--json]`: status distribution per domain,
  showing how many statuses each domain spans, with assignment
  counts and average score.
- `concentration [--db PATH] [--json]`: per-status domain
  concentration, filtered to statuses with at least two domain
  assignments, ordered by diversity ratio (distinct domains divided
  by total assignments).
- `summary [--db PATH] [--json]`: aggregate statistics including
  total statuses, statuses with domains, coverage ratio, distinct
  domains, total assignments, average domains per status,
  single-status domain count, and single-status domain rate.
- `selftest`: exercises 14 checks covering per-status domain counts,
  domain-to-status distributions, concentration filtering, summary
  totals, JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level status attribution**: domains are attributed directly
  to the chunk's own status, not the source's liveness.
- **Knowledge breadth**: concentration subcommand reveals whether
  accepted chunks cover broader knowledge domains than quarantined
  or rejected ones.
- **Single-status exclusivity**: summary tracks domains that appear
  in only one status, indicating quality-tier-specific knowledge
  coverage.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/status_domain_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-status-domain-profile.md`: this spec

## See also

- [corpus-status-tag-profile](2026-08-31-corpus-status-tag-profile.md):
  profiles statuses by chunk tag patterns; this tool profiles
  statuses by chunk domain patterns.
- [corpus-liveness-domain-profile](2026-08-31-corpus-liveness-domain-profile.md):
  profiles domains by source liveness; this tool profiles domains
  by chunk status.

## Non-goals

- Status prediction from domain patterns.
- Automatic domain recommendation based on chunk status.
- Domain-based chunk promotion or demotion decisions.
- Status-driven domain pruning or expansion.
