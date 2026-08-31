# Corpus Artifact Citation Provenance

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_citation_provenance.py

## Problem

No tool joins artifacts with citations via their shared chunk_id to
show which technology references have evidentiary backing.
artifact_adoption.py joins artifacts with chunks and sources but never
touches citations.  artifact_edge_profile.py joins artifacts with
claim_edges but never touches citations.  Understanding which artifacts
are mentioned in well-cited chunks versus chunks with zero citations
required a manual three-way join.

## Solution

A new tool `tools/corpus/artifact_citation_provenance.py` with four
subcommands:

- `by-artifact [--db PATH] [--json]`: per-artifact citation backing
  showing citation count, verified count, and backed flag via chunk_id
  join.
- `unbacked [--db PATH] [--json]`: artifacts on chunks with zero
  citations, surfacing unsubstantiated technology mentions.
- `by-type [--db PATH] [--json]`: citation backing rates per
  artifact_type with total and backed counts, backing rate, and
  citation totals.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total artifacts, backed and unbacked counts, backing rate, citation
  totals, and best and worst backed artifact types.
- `selftest`: exercises 14 checks covering per-artifact citation
  counts, backed flags, shared-chunk citation inheritance, unbacked
  detection, per-type rates, summary totals, backing rate, citation
  sums, best and worst type identification, JSON serialisation, and
  empty corpus.

### Design properties

- **Three-way join**: joins artifacts to citations via their shared
  chunk_id, giving per-artifact citation quality in a single query.
- **Distinct counting**: uses DISTINCT citation_id to avoid inflating
  counts from the LEFT JOIN.
- **Shared-chunk inheritance**: multiple artifacts on the same chunk
  each see that chunk's full citation set, correctly reflecting that
  the evidence backs all mentions in the chunk.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_citation_provenance.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-citation-provenance.md`:
  this spec

## See also

- [corpus-artifact-edge-profile](2026-08-31-corpus-artifact-edge-profile.md):
  cross-tabulates artifact_type with edge_type; this tool crosses
  artifacts with citations instead of edges.
- [corpus-edge-citation-quality](2026-08-31-corpus-edge-citation-quality.md):
  measures citation backing at claim_edge endpoints; this tool
  measures citation backing at artifact chunk locations.

## Non-goals

- Automatic artifact credibility scoring based on citation quality.
- Citation-weighted artifact ranking or recommendation.
- Artifact removal or flagging based on citation absence.
- Cross-source artifact citation deduplication.
