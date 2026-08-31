# Corpus Chunk Readability Scorer

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/readability.py

## Problem

The corpus quality tools measure structural, citation, and freshness
dimensions, but none measured text complexity.  Chunks with unusually
dense jargon, long words, or repetitive vocabulary affect how well
retrieved content serves downstream consumers.  Identifying these
required reading the chunks manually.

## Solution

A new tool `tools/corpus/readability.py` with three subcommands:

- `score [--db PATH] [--json]`: per-chunk readability metrics for
  accepted chunks.  Reports average word length, type-token ratio,
  long word ratio, and a composite complexity score on a 0-1 scale.
  Sorted by complexity descending.
- `complex [--db PATH] [--threshold F] [--json]`: chunks above the
  complexity threshold (default 0.5).  These represent dense or
  jargon-heavy content that may need simplification.
- `summary [--db PATH] [--json]`: aggregate readability statistics
  including mean and median complexity, per-kind breakdowns, and
  complex vs simple chunk counts.
- `selftest`: exercises 14 checks covering score computation, sort
  order, relative ordering of simple vs complex text, metric ranges,
  threshold filtering, summary structure, score bounds, kind
  breakdowns, positive means, JSON serialisation, and empty corpus.

### Readability metrics

Four signals contribute to the composite complexity score:

1. **Average word length** (weight 0.4): total characters divided by
   word count, normalised to 0-1 by dividing by 10.  Longer average
   words indicate more technical or specialised vocabulary.
2. **Type-token ratio** inverted (weight 0.3): unique words divided
   by total words, inverted so repetitive text scores higher.  Low
   vocabulary diversity signals formulaic or repetitive content.
3. **Long word ratio** (weight 0.3): fraction of words with eight or
   more characters.  High ratios indicate dense technical prose.

### Design properties

- **No external dependencies**: uses only whitespace tokenisation and
  character counting, avoiding NLTK or spaCy requirements.
- **Kind-stratified summary**: per-kind breakdowns reveal whether
  certain chunk types (code, config, prose) are systematically more
  or less complex.
- **Bounded scores**: all metrics and the composite score are
  bounded to the 0-1 range.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/readability.py`: new tool
- `docs/specs/2026-08-31-corpus-readability.md`: this spec

## See also

- [corpus-vocab-analysis](2026-08-30-corpus-vocab-analysis.md):
  analyses vocabulary distribution; this tool measures per-chunk
  text complexity from the same vocabulary signals.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; readability adds a text complexity
  dimension the scorecard does not cover.
- [corpus-domain-tag-affinity](2026-08-31-corpus-domain-tag-affinity.md):
  analyses tag-domain relationships; this tool analyses text-level
  properties of chunks within those domains.
- [corpus-query-coverage](2026-08-31-corpus-query-coverage.md):
  measures retrieval reachability; this tool measures content
  readability of what the retrieval layer surfaces.
- [corpus-edge-density](2026-08-31-corpus-edge-density.md):
  measures claim network interconnectedness; this tool measures
  text-level complexity of chunk content.

## Non-goals

- Sentence boundary detection or sentence-level metrics.
- Flesch-Kincaid or other formula-based readability scores.
- Automated simplification or rewriting.
- External NLP library dependencies.
