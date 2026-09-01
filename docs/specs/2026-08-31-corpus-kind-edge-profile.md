# Corpus Kind Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/kind_edge_profile.py

## Problem

chunk_kind_profile.py profiles kinds per source.
kind_citation_profile.py profiles kinds by citation patterns.
No tool joins chunks.kind with claim_edges to measure which chunk
kinds produce the most edges, how edge types distribute across kinds,
or which edges cross kind boundaries.

## Solution

A new tool `tools/corpus/kind_edge_profile.py` with four
subcommands:

- `by-kind [--db PATH] [--json]`: edge distribution per source
  chunk kind, showing total edges, distinct edge types, source
  chunk count, and average confidence.
- `by-type [--db PATH] [--json]`: edge type distribution per
  source chunk kind, showing how supports, contradicts, and other
  edge types distribute across chunk kinds.
- `cross-kind [--db PATH] [--json]`: edges that cross chunk kind
  boundaries, grouped by source kind, target kind, and edge type,
  identifying inter-kind claim relationships.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total edges, kinds with edges, total kinds, coverage ratio,
  cross-kind edge count and rate, average edges per kind, and
  distinct edge types.
- `selftest`: exercises 14 checks covering per-kind edge counts,
  edge type distribution, cross-kind detection, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Source-based kind attribution**: edges are attributed to the
  kind of the source chunk, not the target, matching the
  directionality of claim_edges.
- **Cross-kind detection**: uses IS NOT comparison to catch edges
  between different chunk kinds.
- **Kind coverage**: measures which kinds participate in claim
  relationships versus which exist but produce no edges.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/kind_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-kind-edge-profile.md`: this spec

## See also

- [corpus-kind-citation-profile](2026-08-31-corpus-kind-citation-profile.md):
  profiles kinds by citation patterns; this tool profiles kinds by
  claim edge patterns.
- [corpus-publisher-edge-profile](2026-08-31-corpus-publisher-edge-profile.md):
  profiles publishers by claim edges; this tool does the same
  grouping by chunk kind instead.

## Non-goals

- Kind normalisation or canonicalisation.
- Edge recommendation based on chunk kind.
- Kind quality scoring beyond edge type distribution.
- Cross-kind edge routing or conflict resolution.
