# Corpus Domain Edge Flow

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/domain_edge_flow.py

## Problem

domain_edge_profile.py profiles edges per domain but treats source
and target sides symmetrically. domain_edge_depth.py measures edge
density within each domain. No tool maps directional flow between
domains, measuring whether domain X supports domain Y but contradicts
domain Z, revealing inter-field tension and reinforcement patterns.

## Solution

A new tool `tools/corpus/domain_edge_flow.py` with four subcommands:

- `flow [--db PATH] [--json]`: directional edge-type counts between
  domain pairs, showing total edges, type breakdown, dominant type,
  and whether the pair is cross-domain or self-domain.
- `tension [--db PATH] [--json]`: cross-domain pairs that carry both
  supports and contradicts edges, with a tension ratio measuring how
  balanced the opposing signals are.
- `balance [--db PATH] [--json]`: per-domain net support balance
  across all cross-domain edges, separating outbound and inbound
  supports/contradicts counts.
- `summary [--db PATH] [--json]`: aggregate statistics including
  cross-domain pair count, self-domain pair count, edge totals per
  category, tension pair count, and average net support.
- `selftest`: exercises 14 checks covering flow detection, tension
  identification, balance computation, summary totals, JSON
  round-trip, and empty corpus.

### Design properties

- **Directional domain mapping**: tracks which domains argue about
  which other domains and in what tone, distinguishing the direction
  of argumentation flow.
- **Tension detection**: identifies domain pairs where both support
  and contradiction coexist, a structural signal for unresolved
  inter-field disagreement.
- **Multi-domain chunk handling**: a chunk in multiple domains
  produces multiple domain-pair records per edge, correctly
  reflecting cross-classification.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/domain_edge_flow.py`: new tool
- `docs/specs/2026-08-31-corpus-domain-edge-flow.md`: this spec

## See also

- domain_edge_profile.py: profiles edges per domain symmetrically;
  this tool adds directionality and cross-domain flow.
- domain_edge_depth.py: measures density within domains; this tool
  measures flow between domains.
- source_argumentation_balance.py: per-source inbound vs outbound
  tone; this tool lifts that pattern to the domain level.

## Non-goals

- Domain-level Markov transition modeling.
- Temporal tracking of inter-domain tension shifts.
- Automatic domain boundary detection from edge patterns.
- Domain hierarchy or subsumption inference.
