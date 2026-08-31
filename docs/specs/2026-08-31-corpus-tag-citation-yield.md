# Corpus Tag-Citation Yield

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_citation_yield.py

## Problem

No tool correlated chunk_tags.tag with chunks.citation_count.
citation_tag_profile analyses the citations.tag column (a different
field on a different table); tag_landscape covers tag-edge
correlation but not citations.  Understanding which topical tags
produce the most-cited chunks required a manual multi-table join.

## Solution

A new tool `tools/corpus/tag_citation_yield.py` with four
subcommands:

- `yield [--db PATH] [--json]`: mean citation count per tag with
  chunk count, total citations, mean citations, and cited rate.
- `top-tags [--db PATH] [--json] [--limit N]`: tags ranked by
  mean citation count, highest first.
- `uncited [--db PATH] [--json]`: tags where no tagged chunk has
  any citations at all.
- `summary [--db PATH] [--json]`: aggregate yield statistics
  including total tags, tags with and without citations, highest
  yield tag, and overall mean citations.
- `selftest`: exercises 14 checks covering yield entry count,
  per-tag totals and means, uncited tag detection, cited rates,
  top-tags ranking, summary totals, highest yield identification,
  JSON serialisation, and empty corpus.

### Design properties

- **Accepted-only scope**: only accepted chunks contribute to yield
  calculations, matching how downstream tools consume the corpus.
- **Two citation metrics**: mean citations measures average yield
  while cited rate measures breadth of citation coverage per tag.
- **Uncited detection**: tags with zero citations across all chunks
  are surfaced as potential coverage gaps or low-value categories.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_citation_yield.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-citation-yield.md`: this spec

## See also

- [corpus-citation-tag-profile](2026-08-31-corpus-citation-tag-profile.md):
  analyses citations.tag (the citation type field); this tool
  correlates chunk_tags.tag (the topical tag) with citation count.
- [corpus-tag-landscape](2026-08-31-corpus-tag-landscape.md):
  analyses tag-edge correlation; this tool adds the tag-citation
  correlation dimension.

## Non-goals

- Tag recommendation based on citation yield.
- Causal analysis of why certain tags correlate with citations.
- Tag quality scoring or tag pruning suggestions.
- Citation prediction from tag assignments.
