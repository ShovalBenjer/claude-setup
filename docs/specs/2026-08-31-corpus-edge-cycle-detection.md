# Corpus Edge Cycle Detection

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_cycle_detection.py

## Problem

edge_chain_analysis.py walks acyclic multi-hop paths through the
claim_edges graph. No tool detects cycles where argumentation circles
back on itself (A supports B, B supports C, C contradicts A), measuring
how many chunks participate in circular reasoning and which edge types
appear in cycles.

## Solution

A new tool `tools/corpus/edge_cycle_detection.py` with four subcommands:

- `cycles [--db PATH] [--json] [--max-length N]`: enumerate all simple
  cycles up to max_length in the claim_edges directed graph, reporting
  path, edge types, tension, and uniformity. Cycles are normalized by
  rotating to the lexicographically smallest node to prevent duplicates.
- `by-type [--db PATH] [--json]`: edge type distribution across cycles,
  showing which edge types participate in circular argumentation and how
  many distinct chunks each type involves.
- `members [--db PATH] [--json]`: chunks participating in cycles, ranked
  by cycle count, with min and max cycle lengths and edge type diversity
  per member.
- `summary [--db PATH] [--json] [--max-length N]`: aggregate cycle
  statistics including total cycles, max cycle length, tension cycles,
  uniform cycles, average cycle length, chunks in cycles, and cycle
  participation rate.
- `selftest`: exercises 14 checks covering triangle detection, tension
  and uniformity flags, shared-node cycle counting, edge type distribution,
  member analysis, summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Cycle normalization**: rotates each cycle so the lexicographically
  smallest node appears first, preventing the same cycle from being
  reported multiple times with different starting nodes.
- **Tension in cycles**: detects cycles containing both contradicts and
  non-contradicts edges, indicating circular argumentation with polarity
  shifts.
- **Participation rate**: measures what fraction of graph nodes
  participate in at least one cycle, quantifying how much of the
  argumentative structure is circular.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/edge_cycle_detection.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-cycle-detection.md`: this spec

## See also

- [corpus-edge-chain-analysis](2026-08-31-corpus-edge-chain-analysis.md):
  walks acyclic multi-hop paths; this tool finds closed loops.

## Non-goals

- Strongly connected component decomposition.
- Cycle breaking or resolution suggestions.
- Edge weight accumulation around cycles.
- Minimum cycle basis computation.
