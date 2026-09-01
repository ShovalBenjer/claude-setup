# Corpus License Domain Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/license_domain_profile.py

## Problem

license_tag_profile.py profiles licenses by tag vocabulary.
license_edge_analysis.py profiles licenses by edge patterns.
No tool joins sources.license_spdx with chunk_domains to measure
which license categories concentrate which knowledge domains,
whether permissive licenses attract broader domain coverage, or
how domain scores vary by license.

## Solution

A new tool `tools/corpus/license_domain_profile.py` with four
subcommands:

- `by-license [--db PATH] [--json]`: domain distribution per
  license type, showing distinct domain count, total domain
  assignments, classified chunk count, and average domain score.
- `by-domain [--db PATH] [--json]`: license distribution per
  domain, showing how many license types each domain appears
  under and average scores, ordered by license breadth.
- `diversity [--db PATH] [--json]`: per-license domain diversity
  as the ratio of distinct domains to total assignments, filtered
  to licenses with at least two assignments, ordered from most
  concentrated to most diverse.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total licenses, licenses with classified chunks, coverage ratio,
  average domains per license, single-license domains, and the
  single-license domain rate.
- `selftest`: exercises 14 checks covering per-license domain
  counts, per-domain license counts, diversity ratios, threshold
  filtering, summary totals, and empty corpus.

### Design properties

- **SPDX as license key**: uses sources.license_spdx directly as
  the grouping key, preserving the standard identifier without
  normalisation or family grouping.
- **Single-license domain rate**: measures what fraction of domains
  appear exclusively under one license type, identifying
  license-specific versus broadly shared domain coverage.
- **Diversity threshold**: only licenses with at least two domain
  assignments appear in the diversity view, since a single
  assignment always produces a trivial ratio of one.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/license_domain_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-license-domain-profile.md`: this spec

## See also

- [corpus-license-tag-profile](2026-08-31-corpus-license-tag-profile.md):
  profiles licenses by tag vocabulary; this tool profiles licenses
  by semantic domain vocabulary.
- [corpus-publisher-domain-profile](2026-08-31-corpus-publisher-domain-profile.md):
  profiles publishers by domain; this tool stratifies domains
  by their originating license type.

## Non-goals

- License family grouping or SPDX expression parsing.
- Domain recommendation based on license type.
- License compliance scoring beyond domain diversity.
- Cross-source license domain migration tracking.
