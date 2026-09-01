# Corpus Diversity Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/diversity.py

## Problem

No single command answered "how evenly is the corpus spread across topics
and sources?"  Measuring concentration required ad-hoc SQL joining
chunk_topics, sources, and chunk_tags, and there was no standard way to
detect topics dominated by a single source or to find underpopulated
topic areas.

## Solution

A new tool `tools/corpus/diversity.py` with three subcommands:

- `summary [--db PATH] [--json]`: computes corpus-wide diversity metrics.
  Reports topic entropy (Shannon), evenness (normalised entropy), Gini
  coefficient of topic sizes, topic coverage ratio (topics with chunks
  vs total), kind-topic spread (mean topics per chunk kind), and tag
  entropy.
- `topic-sources [--db PATH] [--json]`: per-topic source diversity.
  Lists each topic with its source count and a dominated flag (true when
  more than 80 percent of the topic's chunks come from one source).
- `gaps [--db PATH] [--min-chunks N] [--json]`: topics below a chunk
  count threshold (default 3), highlighting underpopulated areas.
- `selftest`: exercises 14 checks covering all three subcommands,
  edge cases (empty corpus, single-topic), JSON serialisation, and
  metric bounds.

### Design properties

- **Information-theoretic metrics**: Shannon entropy and Gini coefficient
  give complementary views of concentration.
- **Dominated-topic detection**: flags topics where a single source
  contributes more than 80 percent of chunks.
- **Superseded-chunk aware**: only active chunks participate.
- **Graceful degradation**: an empty corpus or missing analytical tables
  returns zeroed metrics rather than failing.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/diversity.py`: new tool
- `docs/specs/2026-08-31-corpus-diversity.md`: this spec

## See also

- [corpus-recommend](2026-08-31-corpus-recommend.md): multi-signal chunk
  recommender; this tool measures the corpus-level distribution those
  signals draw from.
- [corpus-topic-model](2026-08-31-corpus-topic-model.md): produces the
  topic assignments this tool analyses for diversity.
- [corpus-source-impact](2026-08-31-corpus-source-impact.md): scores
  individual sources; this tool measures their collective spread.
- [corpus-tag-cooccurrence](2026-08-31-corpus-tag-cooccurrence.md):
  analyses tag-to-tag structure; this tool measures tag entropy.

## Non-goals

- Prescriptive rebalancing or ingestion suggestions.
- Cross-corpus diversity comparison.
- Temporal diversity trends.
