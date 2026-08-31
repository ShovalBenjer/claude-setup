# Corpus Source Provenance Scorer

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_provenance.py

## Problem

The sources table carries metadata about license standing, liveness,
publication date, and publisher, but no tool combined these signals
into a composite quality score.  Identifying low-quality sources
required manually cross-referencing license verdicts, liveness states,
and chunk acceptance rates across multiple tables.

## Solution

A new tool `tools/corpus/source_provenance.py` with three subcommands:

- `score [--db PATH] [--json]`: per-source provenance scores on a 0-1
  composite scale derived from five weighted signals.  Sorted by
  provenance score descending.
- `weak [--db PATH] [--threshold F] [--json]`: sources below the
  provenance threshold (default 0.4).  These represent low-trust
  sources whose content may need additional verification.  Sorted
  by score ascending to surface the weakest sources first.
- `summary [--db PATH] [--json]`: aggregate provenance statistics
  including mean, median, min, max scores, weak and strong source
  counts, and per-kind breakdowns.
- `selftest`: exercises 14 checks covering score computation, sort
  order, license mapping, liveness mapping, acceptance rates,
  weak source detection, exclusion of strong sources, summary
  structure, score bounds, weak/strong counts, JSON serialisation,
  and empty corpus.

### Scoring signals

Five signals contribute to the composite provenance score:

1. **License standing** (weight 0.25): maps license_verdict to a
   trust score.  vendor=1.0, index_only=0.6, link_only=0.3,
   blocked=0.0.
2. **Liveness** (weight 0.20): maps source liveness to a currency
   score.  live=1.0, stale=0.5, archived=0.3, dead=0.0.
3. **Chunk acceptance rate** (weight 0.25): ratio of accepted chunks
   to total chunks from the source.  Sources whose content passes
   quality gates score higher.
4. **Citation density** (weight 0.15): citations per chunk, capped
   at 5.0 and normalised to 0-1.  Well-cited sources carry more
   verifiable claims.
5. **Temporal freshness** (weight 0.15): exponential decay from the
   most recent of fetched_utc and published_utc, with a 365-day
   half-life.  Recently fetched or published sources score higher.

### Design properties

- **Multi-signal composite**: no single bad signal dominates the
  score; a blocked license still contributes from other signals.
- **Source-level granularity**: scores individual sources rather
  than chunks, complementing chunk-level quality tools.
- **Kind-stratified summary**: per-kind breakdowns reveal whether
  certain source types systematically score lower.
- **Graceful degradation**: missing timestamps default to a neutral
  freshness score of 0.5.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_provenance.py`: new tool
- `docs/specs/2026-08-31-corpus-source-provenance.md`: this spec

## See also

- [corpus-freshness-scorer](2026-08-31-corpus-freshness-scorer.md):
  per-chunk temporal freshness; this tool scores source-level
  provenance across multiple quality dimensions.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; source provenance reveals a
  trust dimension the scorecard does not cover.
- [corpus-citation-analysis](2026-08-30-corpus-citation-analysis.md):
  analyses citation patterns; this tool uses citation density as
  one signal in a composite source quality score.
- [corpus-query-coverage](2026-08-31-corpus-query-coverage.md):
  measures retrieval reachability; this tool measures source-level
  trustworthiness.
- [corpus-domain-tag-affinity](2026-08-31-corpus-domain-tag-affinity.md):
  analyses tag-domain relationships; this tool analyses source-level
  quality signals.

## Non-goals

- Automatic source removal or quarantine.
- External registry lookups for license verification.
- Publisher reputation databases.
- Source ranking for retrieval prioritisation.
