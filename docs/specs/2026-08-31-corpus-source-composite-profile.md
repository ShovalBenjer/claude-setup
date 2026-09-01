# Corpus Source Composite Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_composite_profile.py

## Problem

No tool joins sources with all six downstream metadata tables (chunks,
citations, claim_edges, artifacts, chunk_tags, chunk_domains) to build
a single per-source richness vector.  Understanding which sources are
metadata-rich vs metadata-sparse required manual multi-table joins
across every table in the schema.

## Solution

A new tool `tools/corpus/source_composite_profile.py` with four
subcommands:

- `profile [--db PATH] [--json]`: per-source richness vector showing
  counts from each of the six metadata tables and a
  dimensions_populated score (0 to 6).
- `sparse [--db PATH] [--json]`: sources with fewer than three
  populated dimensions, surfacing metadata-poor entries.
- `ranking [--db PATH] [--json]`: sources ranked by dimension count
  and total metadata volume, richest first.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total sources, fully populated count, sparse count, mean
  dimensions, and richest and sparsest source identification.
- `selftest`: exercises 14 checks covering profile entry count,
  per-source dimension counts, sparse detection, ranking order,
  summary totals, richest and sparsest identification, JSON
  serialisation, and empty corpus.

### Design properties

- **Six-dimension vector**: chunks, citations, edges, artifacts,
  tags, and domains are counted per source, giving a complete
  metadata fingerprint.
- **Distinct edge counting**: edges are counted as distinct edge_ids
  per source rather than per-chunk participations, avoiding inflation
  when a source has multiple chunks in the same edge.
- **Sparse detection**: the sparse subcommand flags sources below
  a three-dimension threshold, identifying ingestion or enrichment
  gaps.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_composite_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-source-composite-profile.md`: this
  spec

## See also

- [corpus-source-health](2026-08-31-corpus-source-health.md):
  analyses source liveness and kind distribution; this tool adds the
  six-table metadata richness dimension.
- [corpus-upstream-provenance](2026-08-31-corpus-upstream-provenance.md):
  analyses upstream revision and modification time; this tool crosses
  sources with all downstream metadata rather than upstream fields.

## Non-goals

- Automatic metadata enrichment based on sparse profiles.
- Source quality scoring beyond dimension counting.
- Metadata completeness prediction or trend analysis.
- Cross-source metadata deduplication.
