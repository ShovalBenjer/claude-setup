# Corpus Temporal Distribution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/temporal_distribution.py

## Problem

The timestamp columns ingested_utc (chunks), published_utc (sources),
and fetched_utc (sources) had zero GROUP BY queries anywhere in the
codebase.  Understanding when content was created, when it was
fetched, and when it was ingested required manual single-row
inspection.  No tool revealed ingestion cadence, publication era
distribution, or the lag between publication and fetch.

## Solution

A new tool `tools/corpus/temporal_distribution.py` with four
subcommands:

- `ingestion [--db PATH] [--json]`: distribution of chunk ingestion
  times by month, showing count and share per month.
- `publication [--db PATH] [--json]`: distribution of source
  publication dates by month with count and share.
- `fetch-lag [--db PATH] [--json]`: distribution of lag between
  publication and fetch times in buckets (same-day, 1-7d, 8-30d,
  31-90d, >90d, negative).
- `summary [--db PATH] [--json]`: aggregate temporal statistics
  including ingested range with distinct months, publication range
  with population count, fetch range, and fetch lag mean/max/min.
- `selftest`: exercises 14 checks covering ingestion entries,
  distinct months, share summation, publication entries, publication
  month count, fetch-lag entries, bucket presence, lag share
  summation, summary chunk/source counts, ingestion range,
  publication range, fetch lag stats, JSON serialisation, and
  empty corpus.

### Design properties

- **Monthly granularity**: both ingestion and publication use
  year-month keys, balancing resolution against readability.
- **Lag bucketing**: fetch lag is classified into operationally
  meaningful buckets rather than raw day counts, revealing whether
  content is fetched promptly or with significant delay.
- **Negative lag detection**: the negative bucket catches sources
  where fetched_utc precedes published_utc, flagging possible
  metadata errors.
- **All-accepted scope**: ingestion distribution considers only
  accepted chunks, matching the corpus that downstream consumers
  actually use.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/temporal_distribution.py`: new tool
- `docs/specs/2026-08-31-corpus-temporal-distribution.md`: this spec

## See also

- [corpus-upstream-provenance](2026-08-31-corpus-upstream-provenance.md):
  analyses upstream_rev and upstream_mtime for provenance tracking;
  this tool analyses the three user-facing timestamp columns.
- [corpus-source-lifecycle](2026-08-31-corpus-source-lifecycle.md):
  analyses liveness transitions over time; this tool analyses the
  raw temporal distribution of ingestion and publication.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; temporal coverage gaps are a
  complementary freshness signal.

## Non-goals

- Automated staleness detection or expiry scheduling.
- Time-series trend analysis or forecasting.
- Timezone conversion or local-time display.
- Ingestion rate alerting or throughput monitoring.
