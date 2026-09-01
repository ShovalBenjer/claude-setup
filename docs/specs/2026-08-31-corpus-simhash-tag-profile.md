# Corpus Simhash Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_tag_profile.py

## Problem

simhash_license_profile.py profiles simhash groups by source license.
simhash_publisher_profile.py profiles simhash groups by source publisher.
No tool cross-tabulates chunks.simhash with chunk_tags.tag to measure
whether near-duplicate clusters share the same topic tags, or how tag
vocabulary distributes across simhash collision groups.

## Solution

A new tool `tools/corpus/simhash_tag_profile.py` with four
subcommands:

- `by-simhash [--db PATH] [--json]`: tag distribution per simhash
  collision group (groups with 2+ tagged chunks), showing distinct tags,
  tagged chunks, tag assignments, and average score.
- `by-tag [--db PATH] [--json]`: simhash distribution per tag, showing
  distinct simhash values, tagged chunks, and average score per tag.
- `concentration [--db PATH] [--json]`: per-group tag diversity with
  tag ratio, filtered to collision groups (2+ tagged chunks), ordered
  by tag diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total simhashes, collision groups, cross-tag groups, cross-tag rate,
  and distinct simhash-tag pairs.
- `selftest`: exercises 14 checks covering per-group tag counts,
  per-tag simhash counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level join**: joins chunks with chunk_tags on chunk_id to
  associate simhash collision groups with topic annotations.
- **Tag divergence detection**: reveals whether near-duplicate content
  carries different topic tags, indicating inconsistent annotation
  across similar content.
- **Cross-tag detection**: summary tracks collision groups spanning
  more than one tag.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-tag-profile.md`: this spec

## See also

- [corpus-simhash-license-profile](2026-08-31-corpus-simhash-license-profile.md):
  profiles simhash groups by source license; this tool profiles simhash
  groups by chunk tags.
- [corpus-simhash-publisher-profile](2026-08-31-corpus-simhash-publisher-profile.md):
  profiles simhash groups by source publisher; this tool adds the tag
  dimension to simhash.

## Non-goals

- Automatic tag reconciliation across near-duplicates.
- Tag prediction from simhash similarity.
- Simhash threshold tuning from tag patterns.
- Cross-tag content merging.
