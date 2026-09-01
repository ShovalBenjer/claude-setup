# Corpus Cross-Kind Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/cross_kind_analysis.py

## Problem

Three cross-table relationships had no analytical coverage:

1. No tool crossed chunk kind (claim, code, table, config, link,
   prose) against source kind (paper, repo, local_md, hf_dataset,
   derived).  chunk_kind_profile analyses per individual source and
   per domain but never per source kind.
2. No tool crossed artifact type (library, api, command, config,
   pattern, oneliner) against source kind.  artifact_adoption groups
   by artifact_type alone.
3. No tool measured citation density per source kind.
   citation_analysis groups by target URI or individual source but
   never by the source kind dimension.

Understanding whether paper sources produce different chunk type
mixes than repo sources, or whether certain source kinds carry more
citations, required manual multi-table joins.

## Solution

A new tool `tools/corpus/cross_kind_analysis.py` with four
subcommands:

- `chunk-kind [--db PATH] [--json]`: chunk kind distribution per
  source kind with dominant chunk kind and full breakdown.
- `artifact-type [--db PATH] [--json]`: artifact type distribution
  per source kind with dominant artifact type and full breakdown.
- `citation-density [--db PATH] [--json]`: citation density per
  source kind with total citations, mean citations, and cited rate.
- `summary [--db PATH] [--json]`: aggregate cross-kind statistics
  including source kind count, chunk kind dominance map, artifact
  type dominance map, and citation metrics per source kind.
- `selftest`: exercises 14 checks covering chunk-kind entry count,
  paper/repo/local_md dominant kinds, artifact-type entries,
  paper API dominance, repo library dominance, citation density
  entries, citation ordering, cited rate comparison, summary source
  kind count, dominance maps, JSON serialisation, and empty corpus.

### Design properties

- **Three gaps in one tool**: combines chunk kind, artifact type,
  and citation density cross-tabulations against source kind into
  a single coherent tool.
- **Dominance detection**: each cross-tab identifies the dominant
  category per source kind, enabling quick structural comparisons.
- **Accepted-only scope for chunks**: chunk and citation analyses
  filter to accepted chunks; artifact analysis covers all artifacts.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/cross_kind_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-cross-kind-analysis.md`: this spec

## See also

- [corpus-chunk-kind-profile](2026-08-31-corpus-chunk-kind-profile.md):
  analyses chunk kind per source and per domain; this tool adds the
  source kind dimension.
- [corpus-artifact-adoption](2026-08-31-corpus-artifact-adoption.md):
  analyses artifact type distribution; this tool crosses artifact
  type against source kind.
- [corpus-citation-analysis](2026-08-31-corpus-citation-analysis.md):
  analyses citation targets and verification; this tool adds
  citation density per source kind.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; cross-kind patterns are
  complementary structural signals.

## Non-goals

- Automatic source kind reclassification.
- Chunk kind prediction from source kind.
- Citation normalisation across source kinds.
- Source kind recommendation or balancing.
