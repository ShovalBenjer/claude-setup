# Corpus License Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/license_tag_profile.py

## Problem

license_gate.py enforces license compliance.
publisher_license_distribution.py profiles publishers by license.
No tool joins sources.license_spdx with chunk_tags to measure which
license categories concentrate which tags, whether open licenses
attract broader tag vocabularies, or how tag scores vary by license.

## Solution

A new tool `tools/corpus/license_tag_profile.py` with four
subcommands:

- `by-license [--db PATH] [--json]`: tag distribution per license
  type, showing distinct tag count, total tag assignments, tagged
  chunk count, and average tag score per license.
- `by-tag [--db PATH] [--json]`: license distribution per tag,
  showing how many license types each tag appears under and
  average scores, ordered by license breadth.
- `diversity [--db PATH] [--json]`: per-license tag diversity as
  the ratio of distinct tags to total assignments, filtered to
  licenses with at least two assignments, ordered from most
  concentrated to most diverse.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total licenses, licenses with tagged chunks, coverage ratio,
  average tags per license, single-license tags, and the
  single-license tag rate.
- `selftest`: exercises 14 checks covering per-license tag counts,
  per-tag license counts, diversity ratios, threshold filtering,
  summary totals, and empty corpus.

### Design properties

- **SPDX as license key**: uses sources.license_spdx directly as
  the grouping key, preserving the standard identifier without
  normalisation or family grouping.
- **Single-license tag rate**: measures what fraction of tags
  appear exclusively under one license type, identifying
  license-specific versus broadly shared vocabulary.
- **Diversity threshold**: only licenses with at least two tag
  assignments appear in the diversity view, since a single
  assignment always produces a trivial ratio of one.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/license_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-license-tag-profile.md`: this spec

## See also

- [corpus-publisher-license-distribution](2026-08-31-corpus-publisher-license-distribution.md):
  profiles publishers by license; this tool profiles licenses
  by tag vocabulary.
- [corpus-license-edge-analysis](2026-08-31-corpus-license-edge-analysis.md):
  measures edges by license; this tool measures tags by license.

## Non-goals

- License family grouping or SPDX expression parsing.
- Tag recommendation based on license type.
- License compliance scoring beyond tag coverage.
- Cross-source license tag migration tracking.
