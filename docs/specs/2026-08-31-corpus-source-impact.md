# Corpus Source Impact Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_impact.py

## Problem

The corpus has 365+ sources producing thousands of chunks, but there
was no way to assess which sources drive the most analytical value and
which contribute dead weight.  Without impact scoring, source curation
decisions (which to refresh, which to retire) rely on chunk counts alone,
missing whether those chunks participate in topics, clusters, citations,
or contradiction edges.

## Solution

A new tool `tools/corpus/source_impact.py` with three subcommands:

- `rank [--db PATH] [--top N] [--json]`: scores each source by a
  weighted composite of five participation rates across its active
  chunks: citation rate (0.3), edge rate (0.2), topic rate (0.2),
  cluster rate (0.15), tag rate (0.15).  Sorted by impact score
  descending.
- `detail --source SOURCE_ID [--db PATH] [--json]`: per-chunk
  breakdown for one source showing citation count, edge count, topic
  assignment, cluster assignment, and top tags for each chunk.
- `deadweight [--db PATH] [--json]`: lists sources whose chunks have
  zero analytical footprint (no citations, no edges, no topics, no
  clusters, no tags), sorted by word count descending to highlight
  large but unengaged sources.
- `selftest`: exercises 14 checks.

### Design properties

- **Cross-table joins**: reads chunks, claim_edges, chunk_topics,
  chunk_clusters, and chunk_tags in a single analysis pass per source.
- **Superseded-chunk aware**: only chunks with `status != 'superseded'`
  participate.
- **Resolved-edge aware**: only unresolved claim_edges count.
- **Table-creation safe**: creates analytical tables with IF NOT EXISTS
  so the tool works even if upstream tools have not run yet.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_impact.py`: new tool
- `docs/specs/2026-08-31-corpus-source-impact.md`: this spec

## See also

- [corpus-xray](2026-08-31-corpus-xray.md): cross-table analysis by
  topic and cluster; this tool analyses by source.
- [corpus-lineage](2026-08-30-corpus-lineage.md): traces provenance
  chains from a single chunk or source; this tool scores all sources.

## Non-goals

- Automatic source retirement based on impact score.
- Per-chunk quality scores (use quality.py for that).
- Source-level cost or licensing analysis.
- Cross-corpus impact comparison.
