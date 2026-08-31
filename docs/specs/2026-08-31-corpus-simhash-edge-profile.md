# Corpus Simhash Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_edge_profile.py

## Problem

simhash_distribution.py measures hash-space density and collision
patterns. edge_density.py measures edge counts per chunk. No tool
joins simhash proximity with claim_edges to detect whether
structurally similar chunks share edge patterns, whether high-edge
chunks cluster in simhash space, or how edge types distribute
across simhash collision groups.

## Solution

A new tool `tools/corpus/simhash_edge_profile.py` with four
subcommands:

- `by-collision [--db PATH] [--json]`: edge statistics for chunks
  sharing the same simhash value, showing group size, distinct
  edge count, edge type count, and edges per chunk ratio.
- `edge-density [--db PATH] [--json]`: per-chunk edge count with
  simhash value and source, showing whether high-edge chunks
  cluster at particular hash values.
- `type-by-group [--db PATH] [--json]`: edge type distribution
  within simhash collision groups, identifying whether similar
  chunks attract the same or different relationship types.
- `summary [--db PATH] [--json]`: aggregate statistics including
  chunks with simhash, chunks with edges, the overlap count,
  collision group count, and collision-to-edge rates.
- `selftest`: exercises 14 checks covering collision group sizes,
  edge counts, edge type sets, density filtering, summary totals,
  JSON serialisation, and empty corpus.

### Design properties

- **Collision groups as similarity proxy**: chunks sharing exact
  simhash values are treated as a structural similarity group,
  since simhash collision implies high textual overlap.
- **Bidirectional edge counting**: edges are counted against both
  source and target chunks via UNION ALL, then deduplicated with
  COUNT(DISTINCT edge_id) to avoid double-counting.
- **Minimum group size**: collision groups require at least two
  chunks, since a single chunk at a hash value carries no
  similarity signal.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-edge-profile.md`: this spec

## See also

- [corpus-simhash-distribution](2026-08-31-corpus-simhash-distribution.md):
  measures hash-space density and collisions; this tool measures
  how those collisions relate to claim edge patterns.
- [corpus-edge-density](2026-08-31-corpus-edge-density.md):
  measures edge counts per chunk; this tool stratifies those
  counts by simhash similarity groups.

## Non-goals

- Hamming distance computation between non-colliding simhashes.
- Simhash-based edge prediction or recommendation.
- Cross-source simhash comparison.
- Near-duplicate detection (covered by semantic_dedup).
