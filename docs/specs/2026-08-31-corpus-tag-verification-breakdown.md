# Corpus Tag-Verification Breakdown

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_verification_breakdown.py

## Problem

No tool joins chunk_tags with individual citation rows from the
citations table.  tag_citation_yield correlates chunk_tags.tag with
chunks.citation_count (the aggregate count column on the chunks
table itself); verification_timeline analyses citations.verified_utc
but not against topical tags.  Understanding which topical tags have
the highest per-citation verification rates required a manual
multi-table join.

## Solution

A new tool `tools/corpus/tag_verification_breakdown.py` with four
subcommands:

- `by-tag [--db PATH] [--json]`: citation verification rates per
  topical tag with total, verified, unverified counts and rate.
- `unverified [--db PATH] [--json]`: tags where no citation on any
  tagged chunk has been verified.
- `lag [--db PATH] [--json]`: mean ingestion-to-verification lag per
  topical tag in days with min and max.
- `summary [--db PATH] [--json]`: aggregate statistics including
  tags with citations, overall verification rate, fully verified
  and unverified tag counts, highest and lowest rate tags.
- `selftest`: exercises 14 checks covering per-tag verification
  counts, rates, unverified detection, lag calculation, summary
  totals, highest and lowest rate identification, JSON
  serialisation, and empty corpus.

### Design properties

- **Per-citation granularity**: joins chunk_tags to individual
  citation rows rather than the aggregate citation_count column,
  giving precise verification rates per tag.
- **Distinct counting**: uses DISTINCT citation_id to avoid
  inflating counts when a chunk has multiple tags.
- **Verification lag dimension**: measures the time from chunk
  ingestion to citation verification per tag, connecting topical
  classification to verification throughput.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_verification_breakdown.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-verification-breakdown.md`: this
  spec

## See also

- [corpus-tag-citation-yield](2026-08-31-corpus-tag-citation-yield.md):
  correlates chunk_tags.tag with the aggregate citation_count column;
  this tool joins tags with individual citation rows for verification
  analysis.
- [corpus-verification-timeline](2026-08-31-corpus-verification-timeline.md):
  analyses verification timing by citation.tag (the citation type);
  this tool crosses verification with chunk_tags.tag (the topical
  tag).

## Non-goals

- Automatic verification prioritisation based on tag.
- Causal analysis of why certain tags have higher verification rates.
- Tag-based verification scheduling or queue management.
- Verification quality scoring beyond rate measurement.
