# Corpus Language Distribution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/language_distribution.py

## Problem

The chunks table stores a lang column for every chunk, encoding the
programming or natural language of each piece of content.  No tool
analysed the language distribution, per-source language diversity, or
language-kind correlations.  Identifying multilingual sources,
finding chunks with missing language tags, or understanding which
kinds of content carry which languages required manual queries.

## Solution

A new tool `tools/corpus/language_distribution.py` with four
subcommands:

- `distribution [--db PATH] [--json]`: language distribution across
  accepted chunks, showing count, share, and total word count per
  language.
- `per-source [--db PATH] [--json]`: language diversity per source
  including chunk count, distinct languages, dominant language and
  its share.  Sorted by distinct language count descending to surface
  the most linguistically diverse sources first.
- `per-kind [--db PATH] [--json]`: language distribution per chunk
  kind, showing which languages appear in each content type.
- `summary [--db PATH] [--json]`: aggregate language statistics
  including total chunks, distinct languages, unset count and rate,
  dominant language, source count, and multilingual source count.
- `selftest`: exercises 14 checks covering distribution entries,
  dominant language, share summation, unset presence, per-source
  counts, distinct language counts, sort order, per-kind entries,
  code kind languages, summary totals, unset and multilingual
  counts, JSON serialisation, and empty corpus.

### Design properties

- **Unset tracking**: chunks with NULL lang are reported as
  "(unset)", making missing-tag prevalence visible.
- **Per-source diversity**: distinct language count and dominant
  share reveal whether sources are monolingual or mixed.
- **Kind correlation**: per-kind breakdown shows which content
  types carry which languages (e.g. code chunks with python/sql).
- **Accepted-only scope**: analyses only accepted chunks.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/language_distribution.py`: new tool
- `docs/specs/2026-08-31-corpus-language-distribution.md`: this spec

## See also

- [corpus-chunk-profile](2026-08-30-corpus-chunk-profile.md):
  analyses chunk structure; language is a complementary content
  dimension.
- [corpus-heading-depth-analysis](2026-08-31-corpus-heading-depth-analysis.md):
  analyses structural depth; language diversity is an orthogonal
  content property.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; language tag completeness is
  a complementary quality signal.
- [corpus-domain-analysis](2026-08-31-corpus-domain-analysis.md):
  analyses chunk domain classification; language and domain are
  independent content dimensions.

## Non-goals

- Language detection or automatic tagging.
- Language quality or fluency assessment.
- Translation or multilingual alignment.
- Language-based chunk filtering or splitting.
