# Corpus Publisher Kind Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_kind_profile.py

## Problem

publisher_liveness_profile.py profiles publishers by source liveness.
publisher_status_profile.py profiles publishers by chunk status.
No tool cross-tabulates sources.publisher with sources.kind to measure
which publishers contribute which source formats, or how content volume
distributes across publisher-kind combinations.

## Solution

A new tool `tools/corpus/publisher_kind_profile.py` with four
subcommands:

- `by-publisher [--db PATH] [--json]`: kind distribution per
  publisher, showing distinct kinds, total sources, and total bytes.
- `by-kind [--db PATH] [--json]`: publisher distribution per source
  kind, showing distinct publishers, total sources, and total bytes
  per kind.
- `concentration [--db PATH] [--json]`: per-publisher kind
  concentration, filtered to named publishers with at least two
  sources, ordered by how many kinds each publisher spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total publishers, total kinds, total sources, publishers spanning
  multiple kinds, multi-kind rate, and distinct publisher-kind pairs.
- `selftest`: exercises 14 checks covering per-publisher kind
  counts, per-kind publisher counts, concentration filtering,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Source-level cross-tabulation**: operates on sources table
  only, joining publisher with kind without descending to chunks.
- **Format diversity**: reveals which publishers contribute across
  multiple source formats versus specializing in one.
- **Multi-kind detection**: summary tracks publishers that span
  more than one source kind, indicating format diversity in their
  contributions.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_kind_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-kind-profile.md`: this spec

## See also

- [corpus-publisher-liveness-profile](2026-08-31-corpus-publisher-liveness-profile.md):
  profiles publishers by liveness state; this tool profiles
  publishers by source kind.
- [corpus-kind-liveness-profile](2026-08-31-corpus-kind-liveness-profile.md):
  profiles source kinds by liveness; this tool adds the publisher
  dimension to kind.

## Non-goals

- Publisher format recommendation from kind patterns.
- Automatic format migration per publisher.
- Publisher-driven kind transitions.
- Kind prediction from publisher metadata.
