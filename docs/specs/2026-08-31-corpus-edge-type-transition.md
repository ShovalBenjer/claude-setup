# Corpus Edge Type Transition Patterns

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_type_transition.py

## Problem

edge_chain_analysis.py walks directed multi-hop paths through the
claim_edges graph. edge_reciprocity_analysis.py measures mutual vs
one-way edges. No tool analyzes the sequence of edge types along
multi-hop paths, measuring how argumentation tone changes step-by-step
(e.g. supports-then-contradicts vs supports-then-supports), surfacing
rhetorical escalation and argumentation flow patterns.

## Solution

A new tool `tools/corpus/edge_type_transition.py` with four
subcommands:

- `bigrams [--db PATH] [--json]`: consecutive edge-type pairs
  across all 2-hop paths, counting how often each type pair
  occurs (e.g. supports followed by contradicts).
- `paths [--db PATH] [--json] [--max-hops N]`: distinct edge-type
  sequences across multi-hop paths with occurrence counts and
  path lengths.
- `flow [--db PATH] [--json]`: per edge-type, what types tend to
  follow in the next hop, with dominant successor and dominance
  rate.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total bigrams, reinforcing bigrams (same type repeated),
  shifting bigrams (type changes), and reinforcement rate.
- `selftest`: exercises 14 checks covering bigram detection,
  path sequence enumeration, flow analysis, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Bigram counting**: counts consecutive edge-type pairs to reveal
  which argumentative transitions are most common in the corpus.
- **Reinforcement vs shift detection**: distinguishes paths that
  maintain tone (supports-supports) from those that shift
  (supports-contradicts), a structural signal for rhetorical
  escalation.
- **Flow profiling**: for each edge type, reports what types
  typically follow, revealing whether supports tends to lead to
  more supports or to contradiction.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/edge_type_transition.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-type-transition.md`: this spec

## See also

- edge_chain_analysis.py: walks multi-hop paths; this tool analyzes
  the type sequence along those paths.
- edge_reciprocity_analysis.py: measures mutual edges; this tool
  measures sequential type patterns.
- source_argumentation_balance.py: per-source tone balance; this
  tool measures tone transitions across the graph.

## Non-goals

- Weighted transition probabilities by confidence.
- Markov chain modeling of type transitions.
- Visualization of transition graphs.
- Path-specific transition recommendations.
