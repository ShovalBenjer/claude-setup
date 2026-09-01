# Corpus Publisher License Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_license_profile.py

## Problem

heading_publisher_profile.py profiles headings by publisher.
license_kind_profile.py profiles licenses by source kind.
No tool cross-tabulates sources.publisher with sources.license_spdx to
measure which publishers use which licenses, or how license choices
distribute across publishers.

## Solution

A new tool `tools/corpus/publisher_license_profile.py` with four
subcommands:

- `by-publisher [--db PATH] [--json]`: license distribution per publisher,
  showing distinct licenses, total sources, and total chunks.
- `by-license [--db PATH] [--json]`: publisher distribution per license,
  showing distinct publishers, total sources, and total chunks.
- `concentration [--db PATH] [--json]`: per-publisher license diversity
  with license ratio, ordered by distinct licenses descending.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  publishers, licenses, sources, multi-license publishers, multi-license
  rate, and distinct publisher-license pairs.
- `selftest`: exercises 14 checks covering per-publisher license counts,
  per-license publisher counts, concentration ratios, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Source-level join**: joins sources with chunks to count chunk volume
  per publisher-license pair, since both publisher and license_spdx are
  source-level attributes.
- **License diversity**: reveals which publishers use multiple licenses,
  useful for understanding licensing strategy across the corpus.
- **Multi-license detection**: summary tracks publishers with more than
  one license, indicating heterogeneous licensing practices.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_license_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-license-profile.md`: this spec

## See also

- [corpus-heading-publisher-profile](2026-08-31-corpus-heading-publisher-profile.md):
  profiles headings by publisher; this tool profiles publishers by license.
- [corpus-license-kind-profile](2026-08-31-corpus-license-kind-profile.md):
  profiles licenses by source kind; this tool adds the publisher
  dimension to license.

## Non-goals

- Automatic license assignment from publisher identity.
- License prediction from publisher patterns.
- Publisher reorganization from license distribution.
- Cross-publisher license merging.
