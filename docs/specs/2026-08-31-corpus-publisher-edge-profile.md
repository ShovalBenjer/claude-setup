# Corpus Publisher Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_edge_profile.py

## Problem

publisher_citation_profile.py profiles publishers by citation
patterns. publisher_domain_profile.py profiles publishers by
semantic domain. No tool joins sources.publisher with claim_edges
to measure which publishers produce the most claim edges, how
edge types distribute across publishers, or which edges cross
publisher boundaries.

## Solution

A new tool `tools/corpus/publisher_edge_profile.py` with four
subcommands:

- `by-publisher [--db PATH] [--json]`: edge distribution per
  publisher (counting edges where the publisher is the source),
  showing total edges, source chunk count, target chunk count,
  and average confidence.
- `by-type [--db PATH] [--json]`: edge type distribution per
  publisher, showing how supports, contradicts, duplicates, and
  other edge types distribute across publishers.
- `cross-publisher [--db PATH] [--json]`: edges that cross
  publisher boundaries, grouped by source publisher, target
  publisher, and edge type, identifying inter-publisher claim
  relationships.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total publishers, publishers with edges, coverage ratio, total
  edges, cross-publisher edge count and rate, average edges per
  publisher, and distinct edge types.
- `selftest`: exercises 14 checks covering per-publisher edge
  counts, edge type counts, cross-publisher detection, null
  publisher handling, summary totals, and empty corpus.

### Design properties

- **Source-based publisher attribution**: edges are attributed to
  the publisher of the source chunk, not the target, matching the
  directionality of claim_edges.
- **Cross-publisher detection**: uses IS NOT comparison to catch
  edges between named publishers and between named and NULL
  publishers.
- **Named publisher counting**: COUNT(DISTINCT publisher) excludes
  NULL publishers from aggregate counts, matching the sources
  table convention.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-edge-profile.md`: this spec

## See also

- [corpus-publisher-citation-profile](2026-08-31-corpus-publisher-citation-profile.md):
  profiles publishers by citation patterns; this tool profiles
  publishers by claim edge patterns.
- [corpus-publisher-domain-profile](2026-08-31-corpus-publisher-domain-profile.md):
  profiles publishers by semantic domain; this tool adds the
  claim edge dimension.

## Non-goals

- Publisher normalisation or deduplication.
- Edge quality scoring beyond confidence averages.
- Cross-publisher edge recommendation or routing.
- Publisher trust scoring based on edge patterns.
