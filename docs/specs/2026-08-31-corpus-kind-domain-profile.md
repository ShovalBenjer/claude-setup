# Corpus Kind Domain Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/kind_domain_profile.py

## Problem

chunk_kind_profile.py profiles kinds per source and has a per-domain
breakdown view. kind_tag_profile.py profiles kinds by tag vocabulary.
No tool joins chunks.kind with chunk_domains to measure which chunk
kinds concentrate which domains, whether claims attract different
domains than code or prose chunks, or how domain diversity varies
by kind.

## Solution

A new tool `tools/corpus/kind_domain_profile.py` with four
subcommands:

- `by-kind [--db PATH] [--json]`: domain distribution per chunk
  kind, showing distinct domain count, total domain assignments,
  classified chunk count, and average domain score.
- `by-domain [--db PATH] [--json]`: kind distribution per domain,
  showing how many chunk kinds each domain appears under and
  average scores, ordered by kind breadth.
- `diversity [--db PATH] [--json]`: per-kind domain diversity as
  the ratio of distinct domains to total assignments, filtered to
  kinds with at least two assignments, ordered from most
  concentrated to most diverse.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total kinds, kinds with classified chunks, coverage ratio,
  average domains per kind, single-kind domains, and the
  single-kind domain rate.
- `selftest`: exercises 14 checks covering per-kind domain counts,
  per-domain kind counts, diversity ratios, threshold filtering,
  summary totals, and empty corpus.

### Design properties

- **Kind as grouping key**: uses chunks.kind directly, preserving
  the schema's CHECK constraint vocabulary (claim, code, prose,
  etc.) without normalisation.
- **Single-kind domain rate**: measures what fraction of domains
  appear exclusively under one chunk kind, identifying
  kind-specific versus broadly shared domain coverage.
- **Diversity threshold**: only kinds with at least two domain
  assignments appear in the diversity view, since a single
  assignment always produces a trivial ratio of one.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/kind_domain_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-kind-domain-profile.md`: this spec

## See also

- [corpus-kind-tag-profile](2026-08-31-corpus-kind-tag-profile.md):
  profiles kinds by tag vocabulary; this tool profiles kinds by
  semantic domain vocabulary.
- [corpus-license-domain-profile](2026-08-31-corpus-license-domain-profile.md):
  profiles licenses by domain; this tool stratifies domains by
  their originating chunk kind.

## Non-goals

- Kind normalisation or custom kind vocabularies.
- Domain recommendation based on chunk kind.
- Kind quality scoring beyond domain diversity.
- Cross-kind domain migration tracking.
