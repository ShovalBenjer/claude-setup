# Corpus Source Argumentation Balance

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_argumentation_balance.py

## Problem

source_edge_stance.py profiles outgoing edge-type distribution.
edge_reciprocity_analysis.py measures mutual vs one-way edges.
No tool compares inbound and outbound argumentation tone per source,
measuring whether a source is predominantly cited in support or
contradiction, and whether its own outgoing edges agree with how
others reference it.

## Solution

A new tool `tools/corpus/source_argumentation_balance.py` with four
subcommands:

- `balance [--db PATH] [--json]`: per-source inbound vs outbound
  edge-type counts with supports/contradicts breakdown and a
  net_support metric combining both directions.
- `inbound [--db PATH] [--json]`: how each source is referenced by
  others, showing inbound edge counts, type distribution, average
  confidence, and dominant inbound type.
- `contrast [--db PATH] [--json]`: sources where the dominant
  outbound edge type differs from the dominant inbound edge type,
  surfacing sources whose own argumentation tone disagrees with how
  others cite them.
- `summary [--db PATH] [--json]`: aggregate statistics including
  net supportive source count, net adversarial source count,
  contrast source count, and average net support.
- `selftest`: exercises 14 checks covering balance computation,
  inbound profiling, stance contrast detection, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Bidirectional tone comparison**: separates how a source argues
  (outbound edges) from how others argue about it (inbound edges),
  distinguishing sources that support from those that are supported.
- **Net support metric**: single scalar combining all four
  directional counts (out_supports + in_supports - out_contradicts
  - in_contradicts), ranking sources on the support-contradiction
  spectrum.
- **Stance contrast detection**: identifies sources whose outbound
  dominant type disagrees with their inbound dominant type, a
  structural signal for sources that are cited differently than
  they cite others.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/source_argumentation_balance.py`: new tool
- `docs/specs/2026-08-31-corpus-source-argumentation-balance.md`: this spec

## See also

- source_edge_stance.py: profiles outgoing edge-type distribution;
  this tool adds the inbound dimension and compares directions.
- edge_reciprocity_analysis.py: measures mutual vs one-way edges;
  this tool aggregates reciprocity effects at source level.
- chunk_connectivity_profile.py: measures degree; this tool
  decomposes connectivity into argumentation tone per direction.

## Non-goals

- Weighted balance scoring by confidence or edge count.
- Temporal tracking of balance shifts over time.
- Automatic edge suggestion to rebalance argumentation.
- Cross-source argumentation flow analysis.
