# Corpus Artifact Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_tag_profile.py

## Problem

artifact_domain_distribution.py maps artifacts to domains.
tag_citation_correlation.py correlates tags with citations.
No tool joins artifacts with chunk_tags to show which topic tags
co-occur with which artifact types, or which tags predict the
presence of actionable artifacts.

## Solution

A new tool `tools/corpus/artifact_tag_profile.py` with four
subcommands:

- `by-tag [--db PATH] [--json]`: artifact counts per tag with tagged
  chunk count, artifact count, implemented count, and
  artifacts-per-chunk rate.
- `by-type [--db PATH] [--json]`: tag distribution per artifact type
  with distinct tag count, artifact count, and tagged chunk count.
- `cross [--db PATH] [--json]`: full tag by artifact_type
  cross-tabulation with counts and implemented counts.
- `summary [--db PATH] [--json]`: aggregate statistics including
  tagged-with-artifacts count, artifact coverage rate, tagged artifact
  share, and richest tag.
- `selftest`: exercises 14 checks covering per-tag artifact counts,
  tag exclusion (no artifacts), per-type distribution,
  cross-tabulation, summary totals, artifact share, JSON serialisation,
  and empty corpus.

### Design properties

- **Tag-artifact join**: joins chunk_tags with artifacts on chunk_id,
  capturing artifacts whose parent chunk carries a given tag.
- **Implementation tracking**: counts both total artifacts and
  implemented artifacts per tag and per cross-tabulation cell.
- **Coverage metrics**: measures how much of the tagged corpus
  carries artifacts, and what share of all artifacts sit on tagged
  chunks.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-tag-profile.md`: this spec

## See also

- [corpus-artifact-domain-distribution](2026-08-31-corpus-artifact-domain-distribution.md):
  maps artifacts to domains; this tool maps artifacts to tags.
- [corpus-tag-citation-correlation](2026-08-31-corpus-tag-citation-correlation.md):
  correlates tags with citations; this tool correlates tags with
  artifacts.

## Non-goals

- Tag recommendation based on artifact patterns.
- Artifact quality scoring by tag coverage.
- Multi-tag co-occurrence artifact analysis.
- Tag hierarchy or taxonomy analysis.
