# Corpus Tag Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_edge_profile.py

## Problem

tag_domain_profile.py profiles tags by semantic domains.
license_edge_profile.py profiles licenses by claim edges.
No tool cross-tabulates chunk_tags.tag with claim_edges to measure
which tags carry the most claim edges, or how edge types distribute
across tags.

## Solution

A new tool `tools/corpus/tag_edge_profile.py` with four subcommands:

- `by-tag [--db PATH] [--json]`: edge statistics per tag, showing tagged
  chunks with edges, total edges, edge types, and edges per chunk.
- `by-type [--db PATH] [--json]`: tag distribution per edge type, showing
  distinct tags, tagged chunks, and edge count per type.
- `concentration [--db PATH] [--json]`: per-tag edge type diversity,
  ordered by edge type count to surface tags with the broadest range
  of argumentative connections.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  tags, tags with edges, tag edge rate, total edges, edge types,
  multi-type tags, and multi-type rate.
- `selftest`: exercises 14 checks covering per-tag edge counts,
  per-type tag counts, concentration ordering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Tag-edge join**: joins chunk_tags with claim_edges via UNION ALL of
  source_chunk and target_chunk to count each tag's participation in
  edges regardless of direction.
- **Tag edge mapping**: reveals which tags carry the densest claim-edge
  networks, useful for identifying which content categories have the
  most argumentative structure.
- **Edge type diversity**: concentration view surfaces tags with
  multiple edge types, indicating content categories with complex
  argumentation.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-edge-profile.md`: this spec

## See also

- [corpus-tag-domain-profile](2026-08-31-corpus-tag-domain-profile.md):
  profiles tags by semantic domains; this tool profiles tags by claim
  edges.
- [corpus-license-edge-profile](2026-08-31-corpus-license-edge-profile.md):
  profiles licenses by claim edges; this tool uses tags instead.

## Non-goals

- Automatic edge prediction from tag assignments.
- Cross-tag edge merging or deduplication.
- Edge weight normalization across tags.
- Tag reorganization from edge density.
