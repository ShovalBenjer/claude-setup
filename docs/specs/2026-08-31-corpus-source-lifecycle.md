# Corpus Source Lifecycle

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_lifecycle.py

## Problem

The staleness and freshness scorer tools measure how old a source's
fetch is relative to now, but neither measured the ingestion lag
(time between publication and first fetch) or the distribution of
sources across liveness states and kind values.  A source published
six months before ingestion reveals a discovery bottleneck; a corpus
dominated by one kind or liveness state reveals collection bias.
Answering these questions required manual timestamp arithmetic.

## Solution

A new tool `tools/corpus/source_lifecycle.py` with four subcommands:

- `lag [--db PATH] [--json]`: per-source ingestion lag in days
  between published_utc and fetched_utc.  Sorted by lag descending
  to surface the slowest discoveries first.  Sources with
  unparseable timestamps report null lag.
- `liveness [--db PATH] [--json]`: distribution of sources across
  liveness states (live, stale, archived, dead).  Reports count and
  share per state.
- `kinds [--db PATH] [--json]`: distribution of sources across kind
  values (paper, local_md, repo, hf_dataset, derived).  Reports
  source count, share, average byte size, and accepted chunk count
  per kind.
- `summary [--db PATH] [--json]`: aggregate lifecycle statistics
  including total sources, mean/median/max ingestion lag, liveness
  state count, source kind count, live count, and stale-or-dead
  count.
- `selftest`: exercises 14 checks covering lag enumeration, specific
  lag values, sort order, liveness state coverage, share summation,
  state counts, kind coverage, kind source counts, chunk positivity,
  summary structure, lag ordering, JSON serialisation, and empty
  corpus.

### Design properties

- **Publication-to-fetch lag**: measures discovery speed, not fetch
  age, complementing staleness which measures fetch age from now.
- **Multi-format timestamp parsing**: handles ISO-8601 with and
  without trailing Z and date-only formats.
- **Kind-level chunk counts**: joins through accepted chunks to show
  which source kinds contribute most content.
- **Graceful null handling**: sources with unparseable timestamps
  get null lag rather than erroring.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_lifecycle.py`: new tool
- `docs/specs/2026-08-31-corpus-source-lifecycle.md`: this spec

## See also

- [corpus-source-provenance](2026-08-31-corpus-source-provenance.md):
  analyses source metadata completeness; this tool analyses source
  temporal lifecycle and collection profiles.
- [corpus-freshness-scorer](2026-08-31-corpus-freshness-scorer.md):
  scores source freshness from fetch age; this tool measures
  publication-to-fetch ingestion lag.
- [corpus-staleness](2026-08-30-corpus-staleness.md):
  detects stale sources by fetch age; this tool analyses liveness
  state distribution and ingestion timing.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus health metrics; lifecycle statistics are a
  complementary collection quality signal.
- [corpus-citation-age](2026-08-31-corpus-citation-age.md):
  analyses citation verification age; this tool analyses source
  ingestion age.

## Non-goals

- Source liveness state transitions or history tracking.
- Automatic re-fetch scheduling or staleness remediation.
- Source discovery recommendation.
- Cross-corpus lifecycle comparison.
