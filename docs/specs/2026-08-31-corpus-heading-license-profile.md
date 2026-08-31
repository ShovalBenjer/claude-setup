# Corpus Heading License Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_license_profile.py

## Problem

heading_publisher_profile.py cross-tabulates headings with publishers.
heading_kind_profile.py cross-tabulates headings with source kind.
No tool cross-tabulates chunks.heading_path with sources.license_spdx to
measure whether certain document sections appear more under specific
licenses, or how section structure distributes across licensing terms.

## Solution

A new tool `tools/corpus/heading_license_profile.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: license distribution per heading
  path, showing distinct licenses, total chunks, and total words.
- `by-license [--db PATH] [--json]`: heading distribution per license
  type, showing distinct headings, total chunks, and total words
  per license.
- `concentration [--db PATH] [--json]`: per-heading license
  concentration, filtered to headings with at least two chunks,
  ordered by how many licenses each heading spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total headings, total chunks, total licenses, headings spanning
  multiple licenses, multi-license rate, and distinct heading-license
  pairs.
- `selftest`: exercises 14 checks covering per-heading license counts,
  per-license heading counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins chunks with sources on source_id to
  associate heading paths with license identifiers.
- **License coverage**: reveals which document sections draw content
  from multiple license types versus sections confined to one license.
- **Multi-license detection**: summary tracks headings that span
  more than one license, indicating sections with mixed licensing.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_license_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-license-profile.md`: this spec

## See also

- [corpus-heading-publisher-profile](2026-08-31-corpus-heading-publisher-profile.md):
  profiles headings by publisher; this tool profiles headings by
  license type.
- [corpus-license-status-profile](2026-08-31-corpus-license-status-profile.md):
  profiles licenses by status; this tool adds the heading dimension
  to license.

## Non-goals

- License recommendation from heading patterns.
- Automatic heading licensing based on content.
- License prediction from heading path.
- Heading-driven license transitions.
