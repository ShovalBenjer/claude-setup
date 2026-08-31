# Corpus Citation Verification Age

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/citation_age.py

## Problem

The corpus tracks when citations were last verified, but no tool
measured the staleness of those verification checks.  Citations
verified months ago may now point to moved or retracted targets,
and citations that were never verified represent unchecked claims.
Identifying overdue citations required manually querying the
database and computing date differences.

## Solution

A new tool `tools/corpus/citation_age.py` with three subcommands:

- `age [--db PATH] [--json]`: per-citation verification age in days
  for accepted chunks.  Joins citations with chunks to report
  source context and heading.  Sorted by age descending, with
  never-verified citations last.
- `overdue [--db PATH] [--days N] [--json]`: citations verified
  more than N days ago (default 90) or never verified.  These
  represent stale or unchecked claims that need re-verification.
- `summary [--db PATH] [--json]`: aggregate verification age
  statistics including total and verified counts, verification
  rate, mean and median age, maximum age, overdue count, and
  never-verified count.
- `selftest`: exercises 14 checks covering age computation, recent
  and old citation ages, unverified handling, verified flag
  accuracy, overdue filtering, threshold sensitivity, summary
  structure, verification rate, never-verified count, positive
  mean age, JSON serialisation, and empty corpus.

### Design properties

- **Verification-aware**: distinguishes between verified-but-stale
  and never-verified citations, surfacing both as overdue.
- **UTC normalisation**: handles ISO timestamps with Z suffix,
  timezone offsets, and naive datetimes by normalising to UTC.
- **Accepted-only scope**: joins citations through accepted chunks,
  excluding quarantined or rejected content from age analysis.
- **Configurable threshold**: the overdue subcommand accepts a
  custom day threshold for different freshness requirements.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/citation_age.py`: new tool
- `docs/specs/2026-08-31-corpus-citation-age.md`: this spec

## See also

- [corpus-freshness-scorer](2026-08-30-corpus-freshness-scorer.md):
  measures source-level staleness; this tool measures citation-level
  verification staleness.
- [corpus-citation-analysis](2026-08-30-corpus-citation-analysis.md):
  analyses citation density and patterns; this tool analyses
  verification timeliness.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; citation age adds a verification
  freshness dimension.
- [corpus-source-provenance](2026-08-31-corpus-source-provenance.md):
  computes composite source quality; this tool measures how
  recently citations within those sources were checked.
- [corpus-edge-density](2026-08-31-corpus-edge-density.md):
  measures claim network density; this tool measures citation
  verification currency.
- [corpus-citation-verification](2026-08-31-corpus-citation-verification.md):
  analyses verification coverage per source and tag; this tool
  analyses verification freshness.

## Non-goals

- Automated re-verification or link checking.
- Citation validity or correctness assessment.
- Per-source aggregation of citation ages.
- Notification or alerting on overdue citations.
