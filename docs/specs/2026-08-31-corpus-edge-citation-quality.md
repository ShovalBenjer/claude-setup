# Corpus Edge Citation Quality

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_citation_quality.py

## Problem

No tool joins claim_edges with individual citation rows from the
citations table via their shared chunk_id on chunks.  A "supports"
edge between two well-cited chunks is far more trustworthy than one
between chunks with zero citations.  health_scorecard.py counts
citations and edges separately; corpus_audit.py finds unverified
citations but never correlates them with edge endpoints.
Understanding which edges are citation-backed at both endpoints
required a manual three-way join.

## Solution

A new tool `tools/corpus/edge_citation_quality.py` with four
subcommands:

- `by-edge [--db PATH] [--json]`: per-edge citation quality showing
  source and target chunk citation counts (total and verified) with
  both_backed and both_verified flags.
- `unbacked [--db PATH] [--json]`: edges where at least one endpoint
  has zero citations.
- `quality-distribution [--db PATH] [--json]`: distribution of edges
  across five quality tiers (both_verified, both_backed_partial_verified,
  both_backed_none_verified, one_backed, neither_backed) with counts
  and rates.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total edges, both-backed count, both-verified count, unbacked count,
  backing and verification rates, mean citation counts per endpoint.
- `selftest`: exercises 14 checks covering per-edge citation counts,
  backed/verified flags, unbacked detection, quality tier distribution,
  rate summation, summary totals, backing rate, mean citation counts,
  JSON serialisation, and empty corpus.

### Design properties

- **Three-way join**: joins claim_edges to citations twice (once per
  endpoint) via source_chunk and target_chunk, giving per-endpoint
  citation quality in a single query.
- **Distinct counting**: uses DISTINCT citation_id to avoid inflating
  counts when multiple LEFT JOINs produce cross-products.
- **Quality tiers**: classifies edges into five tiers based on the
  citation backing and verification status of both endpoints, enabling
  prioritised review of low-quality edges.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/edge_citation_quality.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-citation-quality.md`: this spec

## See also

- [corpus-artifact-edge-profile](2026-08-31-corpus-artifact-edge-profile.md):
  cross-tabulates artifact_type with edge_type; this tool crosses
  individual citation records with edge endpoints.
- [corpus-evidence-coverage](2026-08-31-corpus-evidence-coverage.md):
  analyses evidence_path coverage on artifacts; this tool measures
  citation backing on claim_edge endpoints.

## Non-goals

- Automatic edge confidence adjustment based on citation quality.
- Edge removal or resolution based on backing status.
- Citation quality weighting by tag or verification lag.
- Transitive citation backing through edge chains.
