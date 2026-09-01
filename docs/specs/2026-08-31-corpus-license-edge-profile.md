# Corpus License Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/license_edge_profile.py

## Problem

license_citation_profile.py profiles licenses by citation counts.
publisher_edge_profile.py profiles publishers by claim edges.
No tool cross-tabulates sources.license_spdx with claim_edges to measure
which licenses carry the most claim edges, or how edge types distribute
across licenses.

## Solution

A new tool `tools/corpus/license_edge_profile.py` with four subcommands:

- `by-license [--db PATH] [--json]`: edge statistics per license, showing
  chunks with edges, total edges, edge types, and edges per chunk.
- `by-type [--db PATH] [--json]`: license distribution per edge type,
  showing distinct licenses, chunks involved, and edge count per type.
- `concentration [--db PATH] [--json]`: per-license edge type diversity,
  ordered by edge type count to surface licenses with the broadest
  range of edge types.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  licenses, licenses with edges, license edge rate, total edges,
  edge types, multi-type licenses, and multi-type rate.
- `selftest`: exercises 14 checks covering per-license edge counts,
  per-type license counts, concentration ordering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Source-chunk-edge join**: joins sources to chunks to claim_edges via
  UNION ALL of source_chunk and target_chunk to count each license's
  participation in edges regardless of direction.
- **License edge mapping**: reveals which licenses carry the densest
  claim-edge networks, useful for understanding argumentative density
  by licensing regime.
- **Cross-license edges**: edge types spanning multiple licenses indicate
  argumentative connections across licensing boundaries.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/license_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-license-edge-profile.md`: this spec

## See also

- [corpus-license-citation-profile](2026-08-31-corpus-license-citation-profile.md):
  profiles licenses by citation counts; this tool profiles licenses by
  claim edges.
- [corpus-publisher-edge-profile](2026-08-31-corpus-publisher-edge-profile.md):
  profiles publishers by claim edges; this tool uses licenses instead.

## Non-goals

- Automatic edge prediction from license type.
- Cross-license edge merging or deduplication.
- Edge weight normalization across licenses.
- License reorganization from edge density.
