# Corpus Citation Verification

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/citation_verification.py

## Problem

The citation analysis tool reports overall citation counts and the
citation age tool measures verification freshness, but neither
analysed the verification rate itself: what fraction of citations
have been verified, which sources have low verification coverage,
and whether certain citation tags are systematically unverified.
Answering these questions required manual aggregation of the
verified flag across the citations table.

## Solution

A new tool `tools/corpus/citation_verification.py` with four
subcommands:

- `rate [--db PATH] [--json]`: per-source verification rate showing
  verified count, unverified count, and rate (verified/total).
  Sorted by rate ascending to surface the least-verified sources
  first.
- `per-tag [--db PATH] [--json]`: verification rate grouped by
  citation tag.  Reveals whether certain tag types (e.g. "see"
  references) are systematically unverified compared to others
  (e.g. "ref" citations).  Sorted by rate ascending.
- `unverified [--db PATH] [--threshold F] [--json]`: sources whose
  verification rate is below the threshold (default 0.5).
- `summary [--db PATH] [--json]`: aggregate verification statistics
  including total citations, verified and unverified counts, overall
  rate, fully verified and zero-verified source counts, and unique
  tag count.
- `selftest`: exercises 14 checks covering source enumeration,
  verified counts, total counts, sort order, tag coverage, tag rate
  ordering, zero-verification tags, threshold filtering, threshold
  sensitivity, summary structure, overall rate, count balance, JSON
  serialisation, and empty corpus.

### Design properties

- **Per-tag breakdown**: different citation tags may have different
  verification expectations, and this tool surfaces that split.
- **Low-verification surfacing**: ascending sort and threshold
  filtering highlight the sources most in need of verification
  attention.
- **Accepted-only scope**: joins through accepted chunks, excluding
  quarantined or rejected content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/citation_verification.py`: new tool
- `docs/specs/2026-08-31-corpus-citation-verification.md`: this spec

## See also

- [corpus-citation-analysis](2026-08-31-corpus-citation-analysis.md):
  analyses citation patterns and counts; this tool analyses the
  verified/unverified split specifically.
- [corpus-citation-age](2026-08-31-corpus-citation-age.md):
  analyses verification freshness; this tool analyses verification
  coverage.
- [corpus-cross-ref-density](2026-08-31-corpus-cross-ref-density.md):
  analyses internal vs external citation direction; this tool
  analyses citation verification status.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus health metrics; verification rate is a
  complementary quality signal.
- [corpus-source-citation-net](2026-08-31-corpus-source-citation-net.md):
  analyses source-to-source citation links; this tool analyses
  per-source verification coverage.

## Non-goals

- Citation verification execution or link checking.
- Verification scheduling or prioritisation.
- Citation tag taxonomy or normalisation.
- Cross-corpus verification comparison.
