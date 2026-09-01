# Corpus Heading Domain Correlation

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_domain_correlation.py

## Problem

heading_tag_correlation.py measures heading paths against chunk tags.
heading_depth_analysis.py profiles heading path depths.
No tool measures which heading paths concentrate which semantic
domains, whether deeper headings attract different domain profiles,
or how domain diversity varies across heading structures.

## Solution

A new tool `tools/corpus/heading_domain_correlation.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: domain distribution per heading
  path, showing distinct domain count, total domain assignments,
  classified chunk count, and average domain score.
- `by-depth [--db PATH] [--json]`: domain statistics grouped by
  heading depth (separator count plus one), showing how domain
  breadth and scores vary with structural depth.
- `diversity [--db PATH] [--json]`: per-heading domain diversity as
  the ratio of distinct domains to total assignments, filtered to
  headings with at least two assignments, ordered from most
  concentrated to most diverse.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total classified chunks, total distinct domains, headings with
  domains, heading count, coverage ratio, max classified depth,
  and average domains per heading.
- `selftest`: exercises 14 checks covering per-heading domain
  counts, per-depth domain counts, diversity ratios, threshold
  filtering, summary totals, and empty corpus.

### Design properties

- **Heading path as grouping key**: uses chunks.heading_path
  directly, preserving the full path hierarchy.
- **Depth computation**: counts separator characters plus one,
  matching the heading_tag_correlation convention.
- **Diversity threshold**: only headings with at least two domain
  assignments appear in the diversity view.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_domain_correlation.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-domain-correlation.md`: this spec

## See also

- [corpus-heading-tag-correlation](2026-08-31-corpus-heading-tag-correlation.md):
  measures heading paths against tags; this tool measures heading
  paths against semantic domains.
- [corpus-kind-domain-profile](2026-08-31-corpus-kind-domain-profile.md):
  profiles domains by chunk kind; this tool stratifies domains
  by heading structure.

## Non-goals

- Heading path normalisation or canonicalisation.
- Domain recommendation based on heading structure.
- Heading quality scoring beyond domain diversity.
- Cross-source heading domain migration tracking.
