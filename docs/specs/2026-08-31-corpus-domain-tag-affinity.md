# Corpus Domain-Tag Affinity

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/domain_tag_affinity.py

## Problem

The chunk_domains and chunk_tags tables classify chunks along two
independent axes, but no tool measured the relationship between them.
Knowing which tags characterise a domain, which tags span multiple
domains, and whether the tag vocabulary discriminates between domains
required manual cross-referencing across both tables.

## Solution

A new tool `tools/corpus/domain_tag_affinity.py` with three
subcommands:

- `affinity [--db PATH] [--json]`: per-domain tag affinity scores
  using pointwise mutual information.  For each (domain, tag) pair,
  computes observed co-occurrence vs expected co-occurrence under
  independence, reporting the log2 ratio.  Positive values indicate
  the tag is over-represented in the domain.  Sorted by affinity
  descending.
- `spanning [--db PATH] [--json]`: tags that appear across multiple
  domains, sorted by domain count descending.  These are
  cross-cutting tags that do not discriminate between domains.
  Each entry lists the domains the tag spans.
- `summary [--db PATH] [--json]`: aggregate affinity statistics
  including total domains, tags, pairs, spanning vs domain-specific
  tag counts, and affinity range.
- `selftest`: exercises 14 checks covering affinity computation,
  sort order, positive affinity for characteristic tags, co-count
  accuracy, spanning tag detection, domain listing, domain-specific
  exclusion, summary structure, tag coverage, affinity range,
  spanning sort order, JSON serialisation, and empty corpus.

### Affinity metric

The affinity score for a (domain, tag) pair is:

    affinity = log2(observed / expected)

where observed is the number of chunks carrying both the domain and
the tag, and expected = (domain_size * tag_size) / total_tagged_chunks
under the assumption of independence.  A positive affinity means the
tag appears more often in the domain than chance predicts; negative
means less often.

### Design properties

- **PMI-based scoring**: pointwise mutual information naturally
  identifies characteristic tags without requiring arbitrary
  thresholds.
- **Spanning vs specific**: separating cross-cutting tags from
  domain-specific ones reveals which tags carry discriminative
  information.
- **Two-table join**: requires both chunk_domains and chunk_tags;
  returns empty results when either is absent.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/domain_tag_affinity.py`: new tool
- `docs/specs/2026-08-31-corpus-domain-tag-affinity.md`: this spec

## See also

- [corpus-tag-cooccurrence](2026-08-30-corpus-tag-cooccurrence.md):
  analyses tag-tag relationships; this tool analyses tag-domain
  relationships.
- [corpus-domain-analysis](2026-08-30-corpus-domain-analysis.md):
  analyses domain distribution and inter-domain edges; this tool
  analyses how tag vocabularies distribute across domains.
- [corpus-source-provenance](2026-08-31-corpus-source-provenance.md):
  scores source-level quality; this tool scores the discriminative
  power of tags within domains.
- [corpus-tag-landscape](2026-08-30-corpus-tag-landscape.md):
  maps the overall tag space; this tool maps tag-domain affinity
  within that space.
- [corpus-readability](2026-08-31-corpus-readability.md):
  measures text complexity per chunk; this tool measures tag-domain
  vocabulary relationships.

## Non-goals

- Tag recommendation or suggestion for domains.
- Domain reclassification based on tag affinity.
- Tag pruning or vocabulary optimization.
- Statistical significance testing of affinity scores.
