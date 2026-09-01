# Corpus Status Citation Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/status_citation_profile.py

## Problem

status_enrichment_profile.py profiles chunk statuses by enrichment
depth. status_reason_trends.py tracks status reason evolution. No
tool joins chunks.status with citations to measure whether accepted
chunks carry more citations than quarantined or rejected ones, or how
verification rates vary across chunk statuses.

## Solution

A new tool `tools/corpus/status_citation_profile.py` with four
subcommands:

- `by-status [--db PATH] [--json]`: citation distribution per
  chunk status, showing total citations, citing chunk count,
  verified count, distinct target URIs, and verification rate.
- `by-tag [--db PATH] [--json]`: citation tag distribution per
  chunk status, showing how ref, note, and other tags distribute
  across accepted, quarantined, and rejected chunks.
- `verification [--db PATH] [--json]`: per-status verification
  rate, filtered to statuses with at least two citations, ordered
  from highest to lowest verification rate.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total citations, verified count, overall verification rate,
  statuses with citations, total statuses, coverage ratio, and
  average citations per status.
- `selftest`: exercises 14 checks covering per-status citation
  counts, citation tag distribution, verification rates, threshold
  filtering, summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level status**: citations are attributed to the status
  of the chunk that contains the citation.
- **Quality correlation**: reveals whether accepted chunks carry
  higher verification rates than quarantined or rejected ones.
- **Tag distribution**: breaks down citation tags per status for
  style comparison across quality tiers.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/status_citation_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-status-citation-profile.md`: this spec

## See also

- [corpus-status-enrichment-profile](2026-08-31-corpus-status-enrichment-profile.md):
  profiles statuses by enrichment depth; this tool profiles
  statuses by citation patterns.

## Non-goals

- Status transition prediction from citation patterns.
- Automatic quality scoring based on citation density.
- Citation recommendation based on chunk status.
- Status-based chunk promotion or demotion decisions.
