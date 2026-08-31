# Corpus Source Enrichment Completeness

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_enrichment_completeness.py

## Problem

version_source_profile.py measures revision activity per source.
artifact_domain_distribution.py maps artifacts to domains.
No tool measures how completely each source has been enriched across
all six enrichment tables (chunk_tags, chunk_domains, chunk_versions,
artifacts, citations, claim_edges), or which sources have enrichment
gaps that need filling.

## Solution

A new tool `tools/corpus/source_enrichment_completeness.py` with
four subcommands:

- `by-source [--db PATH] [--json]`: enrichment completeness per
  source with counts of tagged, classified, versioned, artifact,
  cited, and edged chunks, plus a dimensions-hit count and a
  completeness score (0 to 1).
- `by-kind [--db PATH] [--json]`: enrichment counts aggregated by
  source kind.
- `gaps [--db PATH] [--json]`: sources missing one or more enrichment
  dimensions, listing which dimensions are absent.
- `summary [--db PATH] [--json]`: aggregate statistics including
  per-dimension chunk counts, fully enriched source count, and
  average completeness score.
- `selftest`: exercises 14 checks covering per-source dimension
  counts, completeness scoring, source exclusion, per-kind
  aggregation, gap detection, summary totals, JSON serialisation,
  and empty corpus.

### Design properties

- **Six-dimension model**: measures enrichment across tags, domains,
  versions, artifacts, citations, and edges, treating each as an
  independent dimension.
- **Source-level aggregation**: rolls up chunk-level enrichment to the
  source level, counting how many chunks in each source have been
  touched by each enrichment table.
- **Gap detection**: the gaps subcommand filters to sources below full
  enrichment, listing exactly which dimensions are missing.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_enrichment_completeness.py`: new tool
- `docs/specs/2026-08-31-corpus-source-enrichment-completeness.md`:
  this spec

## See also

- [corpus-version-source-profile](2026-08-31-corpus-version-source-profile.md):
  measures revision activity per source; this tool measures all six
  enrichment dimensions.
- [corpus-artifact-domain-distribution](2026-08-31-corpus-artifact-domain-distribution.md):
  maps artifacts to domains; this tool measures completeness across
  all enrichment types.

## Non-goals

- Enrichment quality scoring beyond presence/absence.
- Enrichment scheduling or prioritisation.
- Cross-source enrichment correlation.
- Temporal enrichment trend analysis.
