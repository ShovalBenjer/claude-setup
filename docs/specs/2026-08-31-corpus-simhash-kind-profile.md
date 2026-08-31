# Corpus Simhash Kind Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_kind_profile.py

## Problem

simhash_edge_profile.py profiles simhash groups by claim edges.
simhash_status_profile.py profiles simhash groups by chunk status.
No tool cross-tabulates chunks.simhash with sources.kind to measure
whether near-duplicate clusters appear more in certain source formats,
or how content similarity distributes across source kinds.

## Solution

A new tool `tools/corpus/simhash_kind_profile.py` with four
subcommands:

- `by-simhash [--db PATH] [--json]`: kind distribution per simhash
  collision group (groups with 2+ chunks), showing distinct kinds,
  total chunks, and total words.
- `by-kind [--db PATH] [--json]`: simhash distribution per source
  kind, showing distinct simhash values, total chunks, and total
  words per kind.
- `concentration [--db PATH] [--json]`: per-group kind diversity
  with kind ratio, filtered to collision groups (2+ chunks),
  ordered by kind diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total simhashes, collision groups, cross-kind groups, cross-kind
  rate, and distinct simhash-kind pairs.
- `selftest`: exercises 14 checks covering per-group kind counts,
  per-kind simhash counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins chunks with sources on source_id to
  associate simhash collision groups with source format types.
- **Cross-format duplication**: reveals whether near-duplicate content
  appears across multiple source formats, indicating content reuse
  across different ingestion paths.
- **Cross-kind detection**: summary tracks collision groups spanning
  more than one source kind.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_kind_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-kind-profile.md`: this spec

## See also

- [corpus-simhash-status-profile](2026-08-31-corpus-simhash-status-profile.md):
  profiles simhash groups by chunk status; this tool profiles simhash
  groups by source kind.
- [corpus-simhash-edge-profile](2026-08-31-corpus-simhash-edge-profile.md):
  profiles simhash groups by claim edges; this tool adds the kind
  dimension to simhash.

## Non-goals

- Automatic deduplication across source kinds.
- Kind prediction from simhash similarity.
- Simhash threshold tuning from kind patterns.
- Cross-format content merging.
