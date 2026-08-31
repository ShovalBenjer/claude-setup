# Corpus Tag Landscape

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_landscape.py

## Problem

The chunk_tags table stores auto-tagger results with confidence scores,
but no tool analysed tag distribution, per-source tag profiles, or how
tags correlate with claim edges.  The existing tag_cooccurrence tool
covers co-occurrence matrices and community detection; this tool
addresses the complementary questions of frequency, source coverage,
edge correlation, and score quality.

## Solution

A new tool `tools/corpus/tag_landscape.py` with four subcommands:

- `distribution [--db PATH] [--json]`: tag frequency distribution
  across the corpus.  Reports each tag's chunk count and average
  score, plus totals for assignments, unique tags, and tagged chunks.
  Ordered by frequency descending.
- `per-source [--db PATH] [--json]`: per-source tag profile showing
  which tags each source contributes.  Each source lists its tags
  with chunk counts and average scores.
- `edge-tags [--db PATH] [--json]`: tags that appear on chunks
  involved in claim edges, grouped by tag and edge type.  Reveals
  which tags are associated with supporting or contradicting claims.
- `score-bands [--db PATH] [--json]`: tag score distribution across
  four confidence bands (0-0.25, 0.25-0.5, 0.5-0.75, 0.75-1.0).
  Shows where tag confidence concentrates.
- `selftest`: exercises 14 checks covering distribution totals, tag
  ordering, average score, per-source profiles, source tag membership,
  edge-tag correlation, edge types, score band counts, JSON
  serialisation, empty corpus, and source-exclusive tags.

### Design properties

- **Score-aware frequency**: every tag report carries average scores,
  enabling confidence-weighted analysis.
- **Source-level tag profiles**: reveals which sources drive which
  tags, complementing tag_cooccurrence's chunk-level view.
- **Edge correlation**: connects tagging to the claim graph, showing
  which topics are most debated.
- **Score bands**: four-band histogram of tag confidence, surfacing
  the proportion of weak vs strong classifications.
- **Graceful degradation**: returns empty results when the
  chunk_tags table does not exist.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_landscape.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-landscape.md`: this spec

## See also

- [corpus-domain-analysis](2026-08-31-corpus-domain-analysis.md):
  analyses domain classifications; this tool analyses tag
  classifications with a different granularity.
- [corpus-tag-store](2026-08-30-corpus-tag-store.md): the tagging
  infrastructure this tool reads from.
- [corpus-audit](2026-08-31-corpus-audit.md): weak_tags detects
  low-confidence tags; this tool provides the full score distribution.

- [corpus-similarity-analysis](2026-08-31-corpus-similarity-analysis.md):
  analyses chunk similarity patterns; this tool analyses tag
  classification patterns.
- [corpus-tag-entropy](2026-08-31-corpus-tag-entropy.md):
  measures per-chunk information content of tag assignments;
  this tool analyses tag distribution and coverage.

## Non-goals

- Tag editing or score recalibration.
- Tag taxonomy or hierarchy construction.
- Cross-corpus tag comparison.
- Tag-aware search or retrieval.
