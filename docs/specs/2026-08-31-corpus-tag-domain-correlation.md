# Corpus Tag Domain Correlation

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_domain_correlation.py

## Problem

tag_citation_yield.py measures tags against citations.
tag_edge_correlation.py measures tags against claim edges.
No tool joins chunk_tags with chunk_domains to measure which tags
co-occur with which domains, whether tag diversity correlates with
domain diversity, or how domain scores vary across tag vocabularies.

## Solution

A new tool `tools/corpus/tag_domain_correlation.py` with four
subcommands:

- `by-tag [--db PATH] [--json]`: domain distribution per tag,
  showing distinct domains, domain assignments, tagged chunk count,
  and average domain score for chunks that carry each tag.
- `by-domain [--db PATH] [--json]`: tag distribution per domain,
  showing distinct tags, tag assignments, classified chunk count,
  and average tag score for chunks in each domain.
- `co-occurrence [--db PATH] [--json]`: tag-domain pair counts,
  showing shared chunk count and average scores for each observed
  tag-domain combination.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total tags, total domains, tags with domains, domains with tags,
  distinct pairs, pair density, and average domains per tag.
- `selftest`: exercises 14 checks covering per-tag domain counts,
  per-domain tag counts, co-occurrence pairs, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level co-occurrence**: a tag and domain co-occur when
  the same chunk carries both, joining through chunk_id.
- **Bidirectional view**: by-tag shows which domains each tag
  attracts; by-domain shows which tags each domain attracts.
- **Pair density**: summary measures how many of the possible
  tag-domain pairs actually appear, indicating vocabulary overlap.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_domain_correlation.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-domain-correlation.md`: this spec

## See also

- [corpus-tag-citation-yield](2026-08-31-corpus-tag-citation-yield.md):
  correlates tags with citations; this tool correlates tags with
  domains.
- [corpus-tag-edge-correlation](2026-08-31-corpus-tag-edge-correlation.md):
  correlates tags with claim edges; this tool adds the domain
  dimension.

## Non-goals

- Domain prediction from tag assignments.
- Automatic tag suggestion based on domain classification.
- Tag-domain co-occurrence clustering or embedding.
- Domain-driven tag pruning or enrichment.
