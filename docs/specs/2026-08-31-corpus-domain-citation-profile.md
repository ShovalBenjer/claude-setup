# Corpus Domain Citation Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/domain_citation_profile.py

## Problem

tag_citation_correlation.py correlates tags with citations.
artifact_domain_distribution.py maps artifacts to domains. No tool
joins chunk_domains with citations to measure how well each knowledge
domain is externally referenced, or which domains carry the highest
and lowest citation verification rates.

## Solution

A new tool `tools/corpus/domain_citation_profile.py` with four
subcommands:

- `by-domain [--db PATH] [--json]`: citation density per domain with
  classified chunk count, total/verified/unverified citation counts,
  and citations-per-chunk rate.
- `by-verified [--db PATH] [--json]`: verification rate per domain
  among chunks that have at least one citation.
- `top-uris [--db PATH] [--json]`: domain-target_uri pairs with
  highest citation counts, showing which domains reference which
  external sources most often.
- `summary [--db PATH] [--json]`: aggregate statistics including
  classified-with-citations count, citation coverage rate, classified
  citation share, and densest/sparsest domains.
- `selftest`: exercises 14 checks covering per-domain density,
  verified/unverified breakdown, verification rate, domain exclusion
  (no citations), top URIs, summary totals, citation share, JSON
  serialisation, and empty corpus.

### Design properties

- **Domain-citation join**: joins chunk_domains with citations via
  chunk_id, mapping each domain to its citation density and quality.
- **Verification stratification**: separates verified and unverified
  citations per domain, showing which knowledge areas have the
  strongest external backing.
- **Coverage measurement**: computes what fraction of classified chunks
  carry any citation and what share of all citations land on classified
  chunks, quantifying domain-level provenance coverage.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/domain_citation_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-domain-citation-profile.md`: this spec

## See also

- [corpus-tag-citation-correlation](2026-08-31-corpus-tag-citation-correlation.md):
  correlates tags with citations; this tool correlates domains with
  citations.
- [corpus-artifact-domain-distribution](2026-08-31-corpus-artifact-domain-distribution.md):
  maps artifacts to domains; this tool maps citations to domains.

## Non-goals

- Domain-level citation recommendation.
- Cross-domain citation flow analysis.
- Citation quality scoring beyond verified/unverified.
- Domain hierarchy or taxonomy analysis.
