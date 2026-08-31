# Corpus Simhash Publisher Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_publisher_profile.py

## Problem

simhash_liveness_profile.py profiles simhash groups by source liveness.
simhash_kind_profile.py profiles simhash groups by source kind.
No tool cross-tabulates chunks.simhash with sources.publisher to measure
whether near-duplicate clusters span multiple publishers, or how content
similarity distributes across content sources.

## Solution

A new tool `tools/corpus/simhash_publisher_profile.py` with four
subcommands:

- `by-simhash [--db PATH] [--json]`: publisher distribution per simhash
  collision group (groups with 2+ chunks), showing distinct publishers,
  total chunks, and total words.
- `by-publisher [--db PATH] [--json]`: simhash distribution per
  publisher, showing distinct simhash values, total chunks, and total
  words per publisher.
- `concentration [--db PATH] [--json]`: per-group publisher diversity
  with publisher ratio, filtered to collision groups (2+ chunks),
  ordered by publisher diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total simhashes, collision groups, cross-publisher groups,
  cross-publisher rate, and distinct simhash-publisher pairs.
- `selftest`: exercises 14 checks covering per-group publisher counts,
  per-publisher simhash counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins chunks with sources on source_id to
  associate simhash collision groups with content publishers.
- **Cross-publisher duplication**: reveals whether near-duplicate content
  appears across multiple publishers, indicating syndicated or copied
  content from different sources.
- **Cross-publisher detection**: summary tracks collision groups
  spanning more than one publisher.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_publisher_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-publisher-profile.md`: this spec

## See also

- [corpus-simhash-liveness-profile](2026-08-31-corpus-simhash-liveness-profile.md):
  profiles simhash groups by source liveness; this tool profiles simhash
  groups by source publisher.
- [corpus-simhash-kind-profile](2026-08-31-corpus-simhash-kind-profile.md):
  profiles simhash groups by source kind; this tool adds the publisher
  dimension to simhash.

## Non-goals

- Automatic deduplication across publishers.
- Publisher prediction from simhash similarity.
- Simhash threshold tuning from publisher patterns.
- Cross-publisher content merging.
