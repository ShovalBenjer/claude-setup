# Corpus Liveness Citation Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/liveness_citation_profile.py

## Problem

liveness_cross_analysis.py cross-tabulates sources.liveness against
kind, publisher, and license. No tool joins sources.liveness with
citations to measure whether live sources produce more verified
citations than stale or archived ones, or how citation target
diversity varies by liveness state.

## Solution

A new tool `tools/corpus/liveness_citation_profile.py` with four
subcommands:

- `by-liveness [--db PATH] [--json]`: citation distribution per
  source liveness state, showing total citations, citing chunk
  count, verified count, distinct target URIs, and verification
  rate.
- `by-tag [--db PATH] [--json]`: citation tag distribution per
  liveness state, showing how ref, note, and other tags distribute
  across live, stale, and archived sources.
- `verification [--db PATH] [--json]`: per-state verification
  rate, filtered to states with at least two citations, ordered
  from highest to lowest verification rate.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total citations, verified count, overall verification rate,
  liveness states with citations, total states, coverage ratio,
  and average citations per state.
- `selftest`: exercises 14 checks covering per-state citation
  counts, citation tag distribution, verification rates, threshold
  filtering, summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Source-level liveness**: citations are attributed to the
  liveness state of the source that contains the citing chunk.
- **Verification correlation**: reveals whether actively
  maintained (live) sources carry higher verification rates than
  stale or archived ones.
- **Tag distribution**: breaks down citation tags per liveness
  state for style comparison across maintenance states.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/liveness_citation_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-liveness-citation-profile.md`: this spec

## See also

- [corpus-liveness-cross-analysis](2026-08-31-corpus-liveness-cross-analysis.md):
  cross-tabulates liveness against kind, publisher, and license;
  this tool adds the citation dimension.

## Non-goals

- Liveness state transition prediction.
- Automatic staleness detection from citation patterns.
- Citation recommendation based on liveness state.
- Liveness-based source retirement decisions.
