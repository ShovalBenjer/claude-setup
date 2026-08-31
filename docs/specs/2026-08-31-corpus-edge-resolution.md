# Corpus Edge Resolution Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_resolution.py

## Problem

The claim_edges table records resolution status and timestamps, but no
tool analysed resolution patterns.  Knowing which edge types get
resolved fastest, which resolution values are most common, or which
edges have been pending longest required manual SQL queries.

## Solution

A new tool `tools/corpus/edge_resolution.py` with three subcommands:

- `summary [--db PATH] [--json]`: resolution rates broken down by edge
  type.  Reports total, resolved, and unresolved counts with
  resolution rate for each type.  Also reports the distribution of
  resolution values (accepted, rejected, etc.).
- `pending [--db PATH] [--top N] [--json]`: longest-pending unresolved
  edges ordered by detection date (oldest first).  Reports edge type,
  confidence, and detection timestamp.
- `velocity [--db PATH] [--bucket month|week] [--json]`: resolution
  count per time bucket based on resolved_utc.  Shows how fast the
  corpus is processing its dispute backlog.
- `selftest`: exercises 14 checks covering summary totals, per-type
  breakdown, resolution value distribution, pending edge ordering,
  top-N limiting, velocity bucketing by month and week, sorted periods,
  JSON serialisation, empty corpus, and all-resolved scenario.

### Design properties

- **Per-type granularity**: each edge type (contradicts, supports,
  supersedes, duplicates, refines) gets its own resolution rate.
- **Resolution value tracking**: reports which resolution outcomes are
  most common across the corpus.
- **Temporal velocity**: measures how fast edges are being resolved,
  supporting both monthly and weekly bucketing.
- **Graceful degradation**: returns empty results when claim_edges
  table does not exist.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/edge_resolution.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-resolution.md`: this spec

## See also

- [corpus-audit](2026-08-31-corpus-audit.md): identifies unresolved
  intra-cluster contradictions; this tool analyses resolution patterns
  across all edge types.
- [corpus-claim-network](2026-08-31-corpus-claim-network.md): analyses
  network structure of edges; this tool analyses their lifecycle.
- [corpus-dashboard](2026-08-31-corpus-dashboard.md): reports aggregate
  edge counts; this tool breaks down resolution rates by type.
- [corpus-source-chain](2026-08-31-corpus-source-chain.md): traces
  source supersession lifecycle; this tool traces edge resolution
  lifecycle.

## Non-goals

- Automated edge resolution or recommendation.
- Resolution time distribution (median, percentile) analysis.
- Per-reviewer or per-session resolution attribution.
- Cross-corpus resolution comparison.
