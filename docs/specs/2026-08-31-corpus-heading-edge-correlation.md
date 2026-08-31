# Corpus Heading Edge Correlation

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_edge_correlation.py

## Problem

heading_tag_correlation.py measures heading paths against chunk tags.
heading_domain_correlation.py measures heading paths against domains.
No tool measures which heading paths concentrate which claim edge
types, whether deeper headings produce more contradictions or
supports, or how edge type diversity varies across heading
structures.

## Solution

A new tool `tools/corpus/heading_edge_correlation.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: edge distribution per heading
  path (source chunk heading), showing total edges, distinct edge
  types, source chunk count, and average confidence.
- `by-depth [--db PATH] [--json]`: edge statistics grouped by
  heading depth (separator count plus one), showing how edge
  density and type variety vary with structural depth.
- `diversity [--db PATH] [--json]`: per-heading edge type diversity
  as the ratio of distinct types to total edges, filtered to
  headings with at least two edges, ordered from most concentrated
  to most diverse.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total edges, headings with edges, heading count, coverage ratio,
  max edge depth, average edges per heading, and distinct edge
  types.
- `selftest`: exercises 14 checks covering per-heading edge
  counts, per-depth edge counts, diversity ratios, threshold
  filtering, summary totals, and empty corpus.

### Design properties

- **Source-based heading attribution**: edges are attributed to
  the heading of the source chunk, not the target, matching the
  directionality of claim_edges.
- **Depth computation**: counts separator characters plus one,
  matching the heading_tag_correlation convention.
- **Diversity threshold**: only headings with at least two edges
  appear in the diversity view.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_edge_correlation.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-edge-correlation.md`: this spec

## See also

- [corpus-heading-tag-correlation](2026-08-31-corpus-heading-tag-correlation.md):
  measures heading paths against tags; this tool measures heading
  paths against claim edges.
- [corpus-heading-domain-correlation](2026-08-31-corpus-heading-domain-correlation.md):
  measures heading paths against domains; this tool adds the
  claim edge dimension.

## Non-goals

- Heading path normalisation or canonicalisation.
- Edge recommendation based on heading structure.
- Heading quality scoring beyond edge diversity.
- Cross-heading edge routing or conflict detection.
