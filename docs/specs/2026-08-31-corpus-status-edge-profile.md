# Corpus Status Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/status_edge_profile.py

## Problem

status_enrichment_profile.py profiles statuses by enrichment depth.
status_citation_profile.py profiles statuses by citation patterns.
No tool joins chunks.status with claim_edges to measure whether
accepted chunks produce more edges than quarantined ones, how edge
types distribute across statuses, or which edges cross status
boundaries.

## Solution

A new tool `tools/corpus/status_edge_profile.py` with four
subcommands:

- `by-status [--db PATH] [--json]`: edge distribution per source
  chunk status, showing total edges, distinct edge types, source
  chunk count, and average confidence.
- `by-type [--db PATH] [--json]`: edge type distribution per
  status, showing how supports, contradicts, and other edge types
  distribute across accepted, quarantined, and rejected chunks.
- `cross-status [--db PATH] [--json]`: edges that cross chunk
  status boundaries, grouped by source status, target status, and
  edge type, identifying inter-status claim relationships.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total edges, statuses with edges, total statuses, coverage ratio,
  cross-status edge count and rate, average edges per status, and
  distinct edge types.
- `selftest`: exercises 14 checks covering per-status edge counts,
  edge type distribution, cross-status detection, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level status attribution**: edges are attributed to the
  status of the source chunk, not the target.
- **Cross-status detection**: uses IS NOT comparison to catch edges
  between chunks with different statuses.
- **Quality correlation**: reveals whether accepted chunks
  participate in more claim relationships than quarantined or
  rejected ones.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/status_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-status-edge-profile.md`: this spec

## See also

- [corpus-status-citation-profile](2026-08-31-corpus-status-citation-profile.md):
  profiles statuses by citation patterns; this tool profiles
  statuses by claim edge patterns.

## Non-goals

- Status transition prediction from edge patterns.
- Automatic quality scoring based on edge density.
- Edge recommendation based on chunk status.
- Status-based chunk promotion or demotion decisions.
