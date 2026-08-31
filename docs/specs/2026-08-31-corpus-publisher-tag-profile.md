# Corpus Publisher Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_tag_profile.py

## Problem

publisher_license_distribution.py profiles publishers by license.
tag_landscape.py profiles tags corpus-wide.
No tool joins sources.publisher with chunk_tags to measure which
publishers concentrate which tags, whether publisher diversity
correlates with tag diversity, or how tag scores vary by publisher.

## Solution

A new tool `tools/corpus/publisher_tag_profile.py` with four
subcommands:

- `by-publisher [--db PATH] [--json]`: tag distribution per
  publisher, showing distinct tag count, total tag assignments,
  tagged chunk count, and average tag score.
- `by-tag [--db PATH] [--json]`: publisher distribution per tag,
  showing how many named publishers contribute each tag and
  average scores, ordered by publisher breadth.
- `concentration [--db PATH] [--json]`: per-publisher tag
  concentration as the ratio of distinct tags to total
  assignments, filtered to publishers with at least two
  assignments, ordered from most concentrated to most diverse.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total publishers, publishers with tagged chunks, coverage ratio,
  average tags per publisher, single-publisher tags, and the
  single-publisher tag rate.
- `selftest`: exercises 14 checks covering per-publisher tag
  counts, per-tag publisher counts, concentration ratios, null
  publisher handling, summary totals, and empty corpus.

### Design properties

- **Named publisher counting**: COUNT(DISTINCT publisher) excludes
  NULL publishers from aggregate counts, matching the sources
  table convention where publisher is optional. NULL-publisher
  chunks still appear in per-publisher groupings but do not
  inflate publisher-count metrics.
- **Single-publisher tag rate**: measures what fraction of the tag
  vocabulary is exclusive to one named publisher, identifying
  editorial specialisation versus shared vocabulary.
- **Concentration threshold**: only publishers with at least two
  tag assignments appear in the concentration view, since a single
  assignment always produces a trivial ratio of one.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-tag-profile.md`: this spec

## See also

- [corpus-publisher-license-distribution](2026-08-31-corpus-publisher-license-distribution.md):
  profiles publishers by license; this tool profiles publishers
  by tag vocabulary.
- [corpus-tag-landscape](2026-08-31-corpus-tag-landscape.md):
  profiles tags corpus-wide; this tool stratifies tags by their
  originating publisher.

## Non-goals

- Publisher normalisation or deduplication.
- Tag recommendation based on publisher patterns.
- Publisher quality scoring beyond tag diversity.
- Cross-publisher tag migration tracking.
