# Corpus Heading Simhash Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_simhash_profile.py

## Problem

heading_edge_profile.py profiles headings by claim edges.
simhash_publisher_profile.py profiles simhash groups by publisher.
No tool cross-tabulates chunks.heading_path with chunks.simhash to measure
whether structurally similar chunks cluster under the same headings, or how
simhash collision groups distribute across heading paths.

## Solution

A new tool `tools/corpus/heading_simhash_profile.py` with four subcommands:

- `by-heading [--db PATH] [--json]`: simhash collision statistics per heading
  path, showing total chunks, distinct simhashes, collision chunks, and
  collision rate.
- `by-group [--db PATH] [--json]`: heading distribution per simhash collision
  group, showing distinct headings, group size, and whether the group spans
  multiple headings.
- `concentration [--db PATH] [--json]`: per-heading simhash collision
  concentration with simhash ratio, ordered by collision chunks to surface
  headings with the most structural duplication.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  headings, chunks, collision groups, cross-heading groups, cross-heading
  rate, and headings with collisions.
- `selftest`: exercises 14 checks covering per-heading collision counts,
  per-group heading distribution, concentration ratios, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Single-table analysis**: queries chunks table directly since both
  heading_path and simhash are chunk-level attributes.
- **Cross-heading duplication**: by-group view reveals whether structurally
  similar chunks appear under different document sections.
- **Collision density**: concentration view surfaces headings where chunks
  reuse the same structure, indicating potential redundancy.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_simhash_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-simhash-profile.md`: this spec

## See also

- [corpus-heading-edge-profile](2026-08-31-corpus-heading-edge-profile.md):
  profiles headings by claim edges; this tool profiles headings by simhash.
- [corpus-simhash-publisher-profile](2026-08-31-corpus-simhash-publisher-profile.md):
  profiles simhash groups by publisher; this tool uses heading paths instead.

## Non-goals

- Automatic deduplication based on heading-simhash patterns.
- Simhash prediction from heading structure.
- Heading reorganization from simhash clustering.
- Cross-heading simhash merging.
