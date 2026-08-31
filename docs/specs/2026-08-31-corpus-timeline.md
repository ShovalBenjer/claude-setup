# Corpus Timeline Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/timeline.py

## Problem

No tool answered "when did the corpus grow and how has its topical
composition shifted over time?"  Ingestion velocity, publication age
distribution, and topic trends across time all required ad-hoc SQL
joining chunks, sources, and chunk_topics.

## Solution

A new tool `tools/corpus/timeline.py` with three subcommands:

- `velocity [--db PATH] [--bucket month|week|day] [--json]`: counts
  chunks ingested per time bucket.  Uses ingested_utc (present on
  every chunk) for a complete temporal signal regardless of whether
  published_utc is populated.
- `age [--db PATH] [--json]`: publication age distribution of sources.
  Reports total sources, dated vs undated count, by-year breakdown,
  and oldest/newest publication dates.
- `topic-trend [--db PATH] [--top N] [--json]`: tracks how the top N
  topics evolved over ingestion time.  For each topic, shows a monthly
  timeline of chunk counts.
- `selftest`: exercises 14 checks covering all three subcommands,
  bucket modes (month, week), age distribution correctness, topic
  trend timelines, superseded-chunk exclusion, empty corpus, and JSON
  serialisation.

### Design properties

- **Dual timestamps**: velocity uses ingested_utc (always present);
  age uses published_utc (sparse but meaningful).
- **Configurable buckets**: month, week, or day granularity for
  velocity tracking.
- **Missing-table resilient**: the topic-trend subcommand returns
  empty results if chunk_topics has not been fitted yet.
- **Superseded-chunk aware**: only active chunks participate.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/timeline.py`: new tool
- `docs/specs/2026-08-31-corpus-timeline.md`: this spec

## See also

- [corpus-topic-model](2026-08-31-corpus-topic-model.md): fits the
  topic assignments this tool tracks over time.
- [corpus-quality-trend](2026-08-30-corpus-quality-trend.md): tracks
  quality metrics over time; this tool tracks content volume and
  topic composition.
- [corpus-source-overlap](2026-08-31-corpus-source-overlap.md):
  measures source redundancy; this tool measures source age spread.
- [corpus-claim-network](2026-08-31-corpus-claim-network.md): analyses
  claim relationship structure; this tool analyses temporal structure.

## Non-goals

- Forecasting or trend extrapolation.
- Per-chunk timestamp correction or normalisation.
- Cross-corpus temporal comparison.
- Visualization or chart rendering.
