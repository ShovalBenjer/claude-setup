# Corpus Simhash License Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_license_profile.py

## Problem

simhash_publisher_profile.py profiles simhash groups by source publisher.
simhash_kind_profile.py profiles simhash groups by source kind.
No tool cross-tabulates chunks.simhash with sources.license_spdx to measure
whether near-duplicate clusters span multiple license types, or how content
similarity distributes across licensing terms.

## Solution

A new tool `tools/corpus/simhash_license_profile.py` with four
subcommands:

- `by-simhash [--db PATH] [--json]`: license distribution per simhash
  collision group (groups with 2+ chunks), showing distinct licenses,
  total chunks, and total words.
- `by-license [--db PATH] [--json]`: simhash distribution per license
  type, showing distinct simhash values, total chunks, and total words
  per license.
- `concentration [--db PATH] [--json]`: per-group license diversity
  with license ratio, filtered to collision groups (2+ chunks),
  ordered by license diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total simhashes, collision groups, cross-license groups,
  cross-license rate, and distinct simhash-license pairs.
- `selftest`: exercises 14 checks covering per-group license counts,
  per-license simhash counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins chunks with sources on source_id to
  associate simhash collision groups with license types.
- **License conflict detection**: reveals whether near-duplicate content
  appears under different licenses, indicating potential licensing
  conflicts in syndicated or copied content.
- **Cross-license detection**: summary tracks collision groups
  spanning more than one license type.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_license_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-license-profile.md`: this spec

## See also

- [corpus-simhash-publisher-profile](2026-08-31-corpus-simhash-publisher-profile.md):
  profiles simhash groups by source publisher; this tool profiles simhash
  groups by source license.
- [corpus-simhash-kind-profile](2026-08-31-corpus-simhash-kind-profile.md):
  profiles simhash groups by source kind; this tool adds the license
  dimension to simhash.

## Non-goals

- Automatic license conflict resolution.
- License prediction from simhash similarity.
- Simhash threshold tuning from license patterns.
- Cross-license content relicensing.
