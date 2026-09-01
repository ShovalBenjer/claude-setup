# Corpus Tag Citation Correlation

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_citation_correlation.py

## Problem

tag_citation_yield.py correlates tags with raw citation count.
artifact_domain_distribution.py maps artifacts to domains. No tool
breaks down the citation density per tag into verified versus
unverified, measures which tags predict high verification rates,
or identifies the most cited tag-URI pairs in the corpus.

## Solution

A new tool `tools/corpus/tag_citation_correlation.py` with four
subcommands:

- `by-tag [--db PATH] [--json]`: citation density per tag with
  tagged chunk count, total/verified/unverified citation counts,
  and citations-per-chunk rate.
- `by-verified [--db PATH] [--json]`: verification rate per tag
  among chunks that have at least one citation.
- `top-pairs [--db PATH] [--json]`: tag-target_uri pairs with
  highest citation counts, showing which tags co-occur most often
  with which external references.
- `summary [--db PATH] [--json]`: aggregate statistics including
  tagged-with-citations count, citation coverage rate, tagged
  citation share, and highest/lowest density tags.
- `selftest`: exercises 14 checks covering per-tag density,
  verified/unverified breakdown, verification rate, tag exclusion
  (no citations), top pairs, summary totals, citation share, JSON
  serialisation, and empty corpus.

### Design properties

- **Tag-citation join**: joins chunk_tags with citations via chunk_id,
  correlating topic labels with external reference density and quality.
- **Verification stratification**: separates verified and unverified
  citations per tag, showing which topic areas have the strongest
  external backing.
- **Coverage measurement**: computes what fraction of tagged chunks
  carry any citation and what share of all citations land on tagged
  chunks, quantifying the overlap between tagging and citing activity.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_citation_correlation.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-citation-correlation.md`: this spec

## See also

- [corpus-tag-citation-yield](2026-08-31-corpus-tag-citation-yield.md):
  correlates tags with raw citation count; this tool adds verified vs
  unverified breakdown and verification rate per tag.
- [corpus-artifact-domain-distribution](2026-08-31-corpus-artifact-domain-distribution.md):
  maps artifacts to domains; this tool maps tags to citations.

## Non-goals

- Causal inference between tagging and citation likelihood.
- Tag recommendation based on citation patterns.
- Citation quality scoring beyond verified/unverified.
- Multi-tag co-occurrence analysis.
