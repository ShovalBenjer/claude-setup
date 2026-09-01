# Corpus License Kind Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/license_kind_profile.py

## Problem

license_liveness_profile.py profiles licenses by source liveness.
license_status_profile.py profiles licenses by chunk status.
No tool cross-tabulates sources.license_spdx with sources.kind to
measure which licenses appear in which source formats, or how content
volume distributes across license-kind combinations.

## Solution

A new tool `tools/corpus/license_kind_profile.py` with four
subcommands:

- `by-license [--db PATH] [--json]`: kind distribution per license,
  showing distinct kinds, total sources, and total bytes.
- `by-kind [--db PATH] [--json]`: license distribution per source
  kind, showing distinct licenses, total sources, and total bytes
  per kind.
- `concentration [--db PATH] [--json]`: per-license kind
  concentration, filtered to licenses with at least two sources,
  ordered by how many kinds each license spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total licenses, total kinds, total sources, licenses spanning
  multiple kinds, multi-kind rate, and distinct license-kind pairs.
- `selftest`: exercises 14 checks covering per-license kind counts,
  per-kind license counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Source-level cross-tabulation**: operates on sources table
  only, joining license_spdx with kind without descending to
  chunks.
- **License format coverage**: reveals which licenses appear across
  multiple source formats and which are confined to one format.
- **Multi-kind detection**: summary tracks licenses that span
  more than one source kind, indicating broader licensing patterns.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/license_kind_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-license-kind-profile.md`: this spec

## See also

- [corpus-license-liveness-profile](2026-08-31-corpus-license-liveness-profile.md):
  profiles licenses by liveness state; this tool profiles
  licenses by source kind.
- [corpus-publisher-kind-profile](2026-08-31-corpus-publisher-kind-profile.md):
  profiles publishers by source kind; this tool adds the license
  dimension.

## Non-goals

- License recommendation from source kind patterns.
- Automatic license assignment based on source format.
- License-driven kind transitions.
- Kind prediction from license metadata.
