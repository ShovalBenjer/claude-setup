# Corpus License Citation Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/license_citation_profile.py

## Problem

license_tag_profile.py profiles licenses by tag vocabulary.
license_domain_profile.py profiles licenses by semantic domain.
license_edge_analysis.py profiles licenses by claim edges.
No tool joins sources.license_spdx with citations to measure which
license types concentrate citations, how verification rates vary
across licenses, or how citation tag usage differs by license.

## Solution

A new tool `tools/corpus/license_citation_profile.py` with four
subcommands:

- `by-license [--db PATH] [--json]`: citation distribution per
  license type, showing total citations, citing chunk count,
  verified count, distinct target URIs, and verification rate.
- `by-tag [--db PATH] [--json]`: citation tag distribution per
  license type, showing how ref, note, and other tags distribute
  across licenses.
- `verification [--db PATH] [--json]`: per-license verification
  rate, filtered to licenses with at least two citations, ordered
  from highest to lowest verification rate.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total citations, verified count, overall verification rate,
  licenses with citations, total licenses, coverage ratio, average
  citations per license, and distinct citation tags.
- `selftest`: exercises 14 checks covering per-license citation
  counts, citation tag distribution, verification rates, threshold
  filtering, summary totals, JSON round-trip, and empty corpus.

### Design properties

- **License-based attribution**: citations are attributed to the
  license of the source that contains the citing chunk.
- **Tag distribution**: breaks down citation tags per license so
  differences in citation style between permissive and copyleft
  sources are visible.
- **Verification threshold**: only licenses with at least two
  citations appear in the verification view.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/license_citation_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-license-citation-profile.md`: this spec

## See also

- [corpus-license-domain-profile](2026-08-31-corpus-license-domain-profile.md):
  profiles licenses by semantic domain; this tool profiles licenses
  by citation patterns.
- [corpus-license-edge-analysis](2026-08-31-corpus-license-edge-analysis.md):
  profiles licenses by claim edges; this tool adds the citation
  dimension.

## Non-goals

- License normalisation or SPDX expression parsing.
- Citation recommendation based on license type.
- License quality scoring beyond verification rates.
- Cross-license citation deduplication or routing.
