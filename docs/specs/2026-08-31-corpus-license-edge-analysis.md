# Corpus License Edge Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/license_edge_analysis.py

## Problem

No tool joins sources.license_verdict with chunks and claim_edges to
show whether claim relationships cross license boundaries or involve
blocked sources.  publisher_license_distribution.py analyses source
licensing alone.  liveness_cross_analysis.py and source_provenance.py
touch license_verdict but never cross-reference with claim_edges.
Understanding how the claim network relates to licensing required a
manual three-way join.

## Solution

A new tool `tools/corpus/license_edge_analysis.py` with four
subcommands:

- `by-verdict [--db PATH] [--json]`: edge counts per source/target
  license verdict pair with edge_type, mean confidence, and
  cross-boundary flag.
- `cross-boundary [--db PATH] [--json]`: edges where source and
  target chunks come from sources with different license verdicts.
- `blocked-edges [--db PATH] [--json]`: individual edges involving
  at least one blocked source, with per-endpoint blocked flags.
- `summary [--db PATH] [--json]`: aggregate statistics including
  cross-boundary count and rate, blocked edge count and rate, verdict
  pair count, and dominant verdict pair.
- `selftest`: exercises 14 checks covering verdict pair counts,
  same-boundary detection, cross-boundary filtering, blocked edge
  identification, per-endpoint blocked flags, summary totals, rates,
  dominant pair, JSON serialisation, and empty corpus.

### Design properties

- **Four-way join**: joins claim_edges to chunks (twice) to sources
  (twice) to get license verdicts at both endpoints per edge.
- **Cross-boundary detection**: flags edges spanning different
  license regimes, which may require different handling if content
  from one side must be removed.
- **Blocked source surfacing**: specifically identifies edges
  involving blocked sources, since those edges may reference content
  that cannot be retained.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/license_edge_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-license-edge-analysis.md`: this spec

## See also

- [corpus-publisher-license-distribution](2026-08-31-corpus-publisher-license-distribution.md):
  analyses source licensing alone; this tool crosses license verdicts
  with the claim edge network.
- [corpus-supersession-edge-orphans](2026-08-31-corpus-supersession-edge-orphans.md):
  finds edges stranded by supersession; this tool finds edges
  stranded by licensing constraints.

## Non-goals

- Automatic edge removal based on blocked source status.
- License compatibility analysis between source and target.
- Content redaction or replacement for blocked source chunks.
- License change tracking over time.
