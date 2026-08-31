# Corpus Heading Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_edge_profile.py

## Problem

heading_citation_profile.py profiles headings by citation counts.
simhash_edge_profile.py profiles simhash collision groups by claim edges.
No tool cross-tabulates chunks.heading_path with claim_edges to measure
which document sections carry the most claim edges, or how edge types
distribute across heading paths.

## Solution

A new tool `tools/corpus/heading_edge_profile.py` with four subcommands:

- `by-heading [--db PATH] [--json]`: edge statistics per heading path,
  showing chunks with edges, total edges, edge types, and edges per chunk.
- `by-type [--db PATH] [--json]`: heading distribution per edge type,
  showing distinct headings, chunks involved, and edge count per type.
- `concentration [--db PATH] [--json]`: per-heading edge type diversity,
  ordered by edge type count descending to surface headings with the
  broadest range of edge types.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  headings, headings with edges, heading edge rate, total edges,
  edge types, multi-type headings, and multi-type rate.
- `selftest`: exercises 14 checks covering per-heading edge counts,
  per-type heading counts, concentration ordering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Chunk-edge join**: joins chunks with claim_edges via UNION ALL of
  source_chunk and target_chunk to count each chunk's participation in
  edges regardless of direction.
- **Section edge mapping**: reveals which document sections carry the
  densest claim-edge networks, useful for identifying argumentative
  hotspots.
- **Edge type diversity**: concentration view surfaces headings with
  multiple edge types, indicating sections with complex argumentative
  structure.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-edge-profile.md`: this spec

## See also

- [corpus-heading-citation-profile](2026-08-31-corpus-heading-citation-profile.md):
  profiles headings by citation counts; this tool profiles headings by
  claim edges.
- [corpus-simhash-edge-profile](2026-08-31-corpus-simhash-edge-profile.md):
  profiles simhash collision groups by claim edges; this tool uses
  heading paths instead.

## Non-goals

- Automatic edge prediction from heading structure.
- Cross-heading edge merging or deduplication.
- Edge weight normalization across sections.
- Heading reorganization from edge density.
