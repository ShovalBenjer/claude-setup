# Corpus Heading Tag Correlation

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_tag_correlation.py

## Problem

tag_landscape.py profiles tags corpus-wide.
heading_depth_analysis.py profiles heading path depths.
No tool measures which heading paths concentrate which tags,
whether deeper headings attract different tag vocabularies, or
how tag diversity varies across heading structures.

## Solution

A new tool `tools/corpus/heading_tag_correlation.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: tag distribution per heading
  path, showing distinct tag count, total tag assignments, chunk
  count at each heading, and average tag score.
- `by-depth [--db PATH] [--json]`: tag statistics grouped by
  heading depth (separator count plus one), with distinct tags,
  assignment counts, tagged chunk counts, and average scores per
  depth level.
- `diversity [--db PATH] [--json]`: per-heading tag diversity as
  the ratio of distinct tags to total assignments, filtered to
  headings with at least two tag assignments, ordered from lowest
  to highest diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total tagged chunks, total distinct tags, headings with tags,
  total headings, heading tag coverage ratio, maximum tagged
  depth, and average tags per heading.
- `selftest`: exercises 14 checks covering per-heading tag counts,
  per-depth assignments, diversity ratios, threshold filtering,
  summary totals, JSON serialisation, and empty corpus.

### Design properties

- **Depth from separators**: heading depth is computed as the
  number of forward-slash separators plus one, matching the
  heading_depth_analysis convention without requiring a separate
  depth column.
- **Diversity threshold**: only headings with at least two tag
  assignments appear in the diversity view, since a single
  assignment always produces a trivial ratio of one.
- **Coverage ratio**: heading tag coverage is the fraction of
  distinct heading paths that have at least one tagged chunk,
  measuring how broadly tagging has reached across the heading
  structure.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_tag_correlation.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-tag-correlation.md`: this spec

## See also

- [corpus-tag-landscape](2026-08-31-corpus-tag-landscape.md):
  profiles tags corpus-wide; this tool profiles tags per heading
  path and depth.
- [corpus-heading-depth-analysis](2026-08-31-corpus-heading-depth-analysis.md):
  profiles heading path depths; this tool adds tag vocabulary
  analysis at each depth level.

## Non-goals

- Automatic tag suggestion based on heading context.
- Heading path normalisation or merging.
- Tag co-occurrence analysis within headings.
- Cross-source heading tag comparison.
