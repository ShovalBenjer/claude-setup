# Corpus Domain Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/domain_edge_profile.py

## Problem

domain_citation_profile.py profiles domains by citation counts.
tag_edge_profile.py profiles tags by claim edges.
No tool cross-tabulates chunk_domains.domain with claim_edges to measure
which domains carry the most claim edges, or how edge types distribute
across domains.

## Solution

A new tool `tools/corpus/domain_edge_profile.py` with four subcommands:

- `by-domain [--db PATH] [--json]`: edge statistics per domain, showing
  classified chunks with edges, total edges, edge types, and edges per
  chunk.
- `by-type [--db PATH] [--json]`: domain distribution per edge type,
  showing distinct domains, classified chunks, and edge count per type.
- `concentration [--db PATH] [--json]`: per-domain edge type diversity,
  ordered by edge type count to surface domains with the broadest
  range of argumentative connections.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  domains, domains with edges, domain edge rate, total edges, edge
  types, multi-type domains, and multi-type rate.
- `selftest`: exercises 14 checks covering per-domain edge counts,
  per-type domain counts, concentration ordering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Domain-edge join**: joins chunk_domains with claim_edges via
  UNION ALL of source_chunk and target_chunk to count each domain's
  participation in edges regardless of direction.
- **Domain edge mapping**: reveals which semantic domains carry the
  densest claim-edge networks, useful for identifying which knowledge
  areas have the most argumentative structure.
- **Cross-domain edges**: edge types spanning multiple domains indicate
  argumentative connections across semantic boundaries.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/domain_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-domain-edge-profile.md`: this spec

## See also

- [corpus-domain-citation-profile](2026-08-31-corpus-domain-citation-profile.md):
  profiles domains by citation counts; this tool profiles domains by
  claim edges.
- [corpus-tag-edge-profile](2026-08-31-corpus-tag-edge-profile.md):
  profiles tags by claim edges; this tool uses domains instead.

## Non-goals

- Automatic edge prediction from domain classifications.
- Cross-domain edge merging or deduplication.
- Edge weight normalization across domains.
- Domain reorganization from edge density.
