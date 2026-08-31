# Corpus Kind Citation Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/kind_citation_profile.py

## Problem

chunk_kind_profile.py profiles kinds per source.
kind_tag_profile.py profiles kinds by tag vocabulary.
kind_domain_profile.py profiles kinds by semantic domain.
No tool joins chunks.kind with citations to measure which chunk kinds
concentrate citations, how verification rates vary across kinds, or
how citation tag usage differs between claim and code chunks.

## Solution

A new tool `tools/corpus/kind_citation_profile.py` with four
subcommands:

- `by-kind [--db PATH] [--json]`: citation distribution per chunk
  kind, showing total citations, citing chunk count, verified
  count, distinct target URIs, and verification rate.
- `by-tag [--db PATH] [--json]`: citation tag distribution per
  chunk kind, showing how ref, note, and other tags distribute
  across chunk kinds.
- `verification [--db PATH] [--json]`: per-kind verification
  rate, filtered to kinds with at least two citations, ordered
  from highest to lowest verification rate.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total citations, verified count, overall verification rate,
  kinds with citations, total kinds, coverage ratio, average
  citations per kind, and distinct citation tags.
- `selftest`: exercises 14 checks covering per-kind citation
  counts, citation tag distribution, verification rates, threshold
  filtering, summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Kind-based attribution**: citations are attributed to the kind
  of the chunk that contains the citation.
- **Tag distribution**: breaks down citation tags per kind so
  differences in citation style between claim and code chunks
  are visible.
- **Verification threshold**: only kinds with at least two
  citations appear in the verification view.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/kind_citation_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-kind-citation-profile.md`: this spec

## See also

- [corpus-kind-domain-profile](2026-08-31-corpus-kind-domain-profile.md):
  profiles kinds by semantic domain; this tool profiles kinds by
  citation patterns.
- [corpus-kind-tag-profile](2026-08-31-corpus-kind-tag-profile.md):
  profiles kinds by tag vocabulary; this tool adds the citation
  dimension.

## Non-goals

- Kind normalisation or canonicalisation.
- Citation recommendation based on chunk kind.
- Kind quality scoring beyond verification rates.
- Cross-kind citation deduplication or routing.
