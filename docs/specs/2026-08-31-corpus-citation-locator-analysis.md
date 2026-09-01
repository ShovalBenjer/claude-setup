# Corpus Citation Locator Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/citation_locator_analysis.py

## Problem

The citations table stores a locator field indicating where within a
target resource a citation points (page number, section, URL fragment,
figure reference), but no tool analysed locator completeness or
format distribution.  Citations without locators cannot be precisely
verified, and understanding which citation tags systematically lack
locators required manual SQL against the citations table.

## Solution

A new tool `tools/corpus/citation_locator_analysis.py` with four
subcommands:

- `completeness [--db PATH] [--json]`: per-tag locator completeness
  rates.  Reports total citations, with-locator count, without-locator
  count, and completeness rate for each citation tag.  Sorted by total
  count descending.
- `formats [--db PATH] [--json]`: distribution of locator format
  types.  Classifies each non-empty locator into one of seven
  categories (page, section, line, url_fragment, figure, paragraph,
  other) using regex patterns.  Reports count and share per format.
- `verification [--db PATH] [--json]`: verification rates grouped by
  locator presence and format type.  Shows whether citations with
  specific locators verify at higher rates than those without.
- `summary [--db PATH] [--json]`: aggregate locator statistics
  including total citations, with/without locator counts, completeness
  rate, format count, tag count, and verified counts split by locator
  presence.
- `selftest`: exercises 14 checks covering tag enumeration,
  completeness counts, format detection (page, url_fragment), share
  summation, verification categories, no-locator bucket, summary
  totals, completeness rate, JSON serialisation, and empty corpus.

### Design properties

- **Format classification**: seven regex-based categories separate
  page references, section references, line numbers, URL fragments,
  figure/table references, paragraph markers, and everything else.
- **Verification correlation**: surfaces whether locator specificity
  correlates with verification success rates.
- **Per-tag breakdown**: different citation tags may have different
  locator conventions (DOIs tend toward page numbers, URLs toward
  fragments).
- **Accepted-only scope**: joins through accepted chunks so locator
  analysis reflects only current corpus content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/citation_locator_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-citation-locator-analysis.md`: this spec

## See also

- [corpus-citation-analysis](2026-08-30-corpus-citation-analysis.md):
  analyses citation targets and coverage; this tool analyses the
  locator specificity of those citations.
- [corpus-citation-verification](2026-08-30-corpus-citation-verification.md):
  tracks verification status; this tool analyses whether locator
  presence correlates with verification outcomes.
- [corpus-citation-age](2026-08-31-corpus-citation-age.md):
  analyses citation temporal patterns; locator quality is a
  complementary citation quality dimension.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus health metrics; locator completeness is a
  complementary citation quality signal.

## Non-goals

- Locator normalisation or canonicalisation.
- Automatic locator extraction from source text.
- Cross-citation locator deduplication.
- Locator-based content retrieval or navigation.
