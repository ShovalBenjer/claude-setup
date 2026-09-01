# Corpus Verification Timeline

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/verification_timeline.py

## Problem

The citations.verified_utc column had no temporal distribution
analysis.  Existing tools (citation_age, citation_verification)
examine per-citation age and verification rates but never when
verification activity happens over time, how it correlates with
citation tag, or the lag between chunk ingestion and verification.

## Solution

A new tool `tools/corpus/verification_timeline.py` with four
subcommands:

- `timeline [--db PATH] [--json]`: distribution of citation
  verification times by month, with count and share per month.
- `by-tag [--db PATH] [--json]`: verification rates per citation
  tag (url, doi, etc.) with total citations, verified count,
  verification rate, and distinct months of activity per tag.
- `lag [--db PATH] [--json]`: lag between chunk ingestion and
  citation verification per tag, with mean, max, and min days.
- `summary [--db PATH] [--json]`: aggregate verification statistics
  including total and verified counts, verification rate, distinct
  months, verification range, and tags with verification activity.
- `selftest`: exercises 14 checks covering timeline entry count,
  monthly counts, share summation, by-tag entries, per-tag verified
  counts, none-tag handling, lag entries, lag values, summary totals,
  JSON serialisation, and empty corpus.

### Design properties

- **Monthly granularity**: verification times grouped by month
  reveal whether verification happens in bursts or at a steady pace.
- **Tag stratification**: per-tag breakdown reveals whether certain
  citation types (doi, url) get verified faster or more completely.
- **Ingestion-to-verification lag**: connects verified_utc to
  ingested_utc to measure verification turnaround time.
- **Null-safe**: citations with no tag are grouped under "(none)";
  unverified citations are counted in by-tag totals but excluded
  from timeline and lag calculations.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/verification_timeline.py`: new tool
- `docs/specs/2026-08-31-corpus-verification-timeline.md`: this spec

## See also

- [corpus-citation-age](2026-08-31-corpus-citation-age.md):
  analyses per-citation age from verified_utc; this tool adds the
  temporal distribution dimension.
- [corpus-citation-verification](2026-08-31-corpus-citation-verification.md):
  analyses verification rates and methods; this tool adds the
  temporal and lag dimensions.
- [corpus-temporal-distribution](2026-08-31-corpus-temporal-distribution.md):
  analyses ingestion, publication, and fetch timestamps; this tool
  analyses the citation verification timestamp.

## Non-goals

- Automatic verification scheduling or prioritisation.
- Verification quality assessment or false-positive analysis.
- Citation verification method comparison.
- Temporal trend forecasting for verification rates.
