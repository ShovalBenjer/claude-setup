# Corpus Simhash Domain Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_domain_profile.py

## Problem

simhash_tag_profile.py profiles simhash groups by chunk tags.
simhash_license_profile.py profiles simhash groups by source license.
No tool cross-tabulates chunks.simhash with chunk_domains.domain to measure
whether near-duplicate clusters share the same semantic domains, or how
domain classifications distribute across simhash collision groups.

## Solution

A new tool `tools/corpus/simhash_domain_profile.py` with four
subcommands:

- `by-simhash [--db PATH] [--json]`: domain distribution per simhash
  collision group (groups with 2+ classified chunks), showing distinct
  domains, classified chunks, domain assignments, and average score.
- `by-domain [--db PATH] [--json]`: simhash distribution per semantic
  domain, showing distinct simhash values, classified chunks, and
  average score per domain.
- `concentration [--db PATH] [--json]`: per-group domain diversity with
  domain ratio, filtered to collision groups (2+ classified chunks),
  ordered by domain diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total simhashes, collision groups, cross-domain groups, cross-domain
  rate, and distinct simhash-domain pairs.
- `selftest`: exercises 14 checks covering per-group domain counts,
  per-domain simhash counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level join**: joins chunks with chunk_domains on chunk_id to
  associate simhash collision groups with semantic classifications.
- **Domain divergence detection**: reveals whether near-duplicate content
  carries different domain classifications, indicating inconsistent
  semantic labeling across similar content.
- **Cross-domain detection**: summary tracks collision groups spanning
  more than one semantic domain.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_domain_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-domain-profile.md`: this spec

## See also

- [corpus-simhash-tag-profile](2026-08-31-corpus-simhash-tag-profile.md):
  profiles simhash groups by chunk tags; this tool profiles simhash
  groups by semantic domains.
- [corpus-simhash-license-profile](2026-08-31-corpus-simhash-license-profile.md):
  profiles simhash groups by source license; this tool adds the domain
  dimension to simhash.

## Non-goals

- Automatic domain reconciliation across near-duplicates.
- Domain prediction from simhash similarity.
- Simhash threshold tuning from domain patterns.
- Cross-domain content merging.
