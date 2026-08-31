# Corpus Heading Domain Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_domain_profile.py

## Problem

heading_tag_profile.py profiles headings by chunk tags.
heading_license_profile.py profiles headings by source license.
No tool cross-tabulates chunks.heading_path with chunk_domains.domain to
measure which semantic domains appear under which document sections, or how
domain classifications distribute across heading paths.

## Solution

A new tool `tools/corpus/heading_domain_profile.py` with four subcommands:

- `by-heading [--db PATH] [--json]`: domain distribution per heading
  path, showing distinct domains, classified chunks, domain assignments,
  and average score.
- `by-domain [--db PATH] [--json]`: heading distribution per semantic
  domain, showing distinct headings, classified chunks, and average
  score per domain.
- `concentration [--db PATH] [--json]`: per-heading domain diversity
  with domain ratio, ordered by domain diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  headings, classified chunks, domains, multi-domain headings,
  multi-domain rate, and distinct heading-domain pairs.
- `selftest`: exercises 14 checks covering per-heading domain counts,
  per-domain heading counts, concentration ratios, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level join**: joins chunks with chunk_domains on chunk_id to
  associate heading paths with semantic classifications.
- **Section domain mapping**: reveals which document sections carry
  which semantic domains, useful for understanding content organization
  at the domain level.
- **Multi-domain detection**: summary tracks headings spanning more
  than one domain, indicating topically diverse sections.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_domain_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-domain-profile.md`: this spec

## See also

- [corpus-heading-tag-profile](2026-08-31-corpus-heading-tag-profile.md):
  profiles headings by chunk tags; this tool profiles headings by
  semantic domains.
- [corpus-heading-license-profile](2026-08-31-corpus-heading-license-profile.md):
  profiles headings by source license; this tool adds the domain
  dimension to heading.

## Non-goals

- Automatic domain assignment from heading structure.
- Domain prediction from heading path patterns.
- Heading reorganization from domain distribution.
- Cross-heading domain merging.
