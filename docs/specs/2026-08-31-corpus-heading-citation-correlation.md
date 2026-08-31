# Corpus Heading Citation Correlation

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_citation_correlation.py

## Problem

heading_tag_correlation.py measures heading paths against chunk tags.
heading_edge_correlation.py measures heading paths against claim edges.
No tool measures which heading paths concentrate citations, whether
deeper headings produce more or fewer citations, or how verification
rates vary across heading structures.

## Solution

A new tool `tools/corpus/heading_citation_correlation.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: citation distribution per
  heading path, showing total citations, citing chunk count,
  verified count, distinct target URIs, and verification rate.
- `by-depth [--db PATH] [--json]`: citation statistics grouped by
  heading depth (separator count plus one), showing how citation
  density and verification rates vary with structural depth.
- `verification [--db PATH] [--json]`: per-heading verification
  rate, filtered to headings with at least two citations, ordered
  from highest to lowest verification rate.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total citations, verified count, overall verification rate,
  headings with citations, total headings, coverage ratio, max
  cited depth, and average citations per heading.
- `selftest`: exercises 14 checks covering per-heading citation
  counts, per-depth citation counts, verification rates, threshold
  filtering, summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Heading-based citation attribution**: citations are attributed
  to the heading of the chunk that contains the citation.
- **Depth computation**: counts separator characters plus one,
  matching the heading_tag_correlation convention.
- **Verification threshold**: only headings with at least two
  citations appear in the verification view.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_citation_correlation.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-citation-correlation.md`: this spec

## See also

- [corpus-heading-tag-correlation](2026-08-31-corpus-heading-tag-correlation.md):
  measures heading paths against tags; this tool measures heading
  paths against citations.
- [corpus-heading-edge-correlation](2026-08-31-corpus-heading-edge-correlation.md):
  measures heading paths against claim edges; this tool adds the
  citation dimension.

## Non-goals

- Heading path normalisation or canonicalisation.
- Citation recommendation based on heading structure.
- Heading quality scoring beyond verification rates.
- Cross-heading citation routing or deduplication.
