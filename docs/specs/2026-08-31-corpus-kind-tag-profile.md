# Corpus Kind Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/kind_tag_profile.py

## Problem

chunk_kind_profile.py profiles chunk kinds per source and per domain.
tag_landscape.py profiles tags corpus-wide.
No tool joins chunks.kind with chunk_tags to measure which chunk
kinds concentrate which tags, whether claims attract different tags
than code or prose chunks, or how tag diversity varies by kind.

## Solution

A new tool `tools/corpus/kind_tag_profile.py` with four subcommands:

- `by-kind [--db PATH] [--json]`: tag distribution per chunk kind,
  showing distinct tag count, total tag assignments, tagged chunk
  count, and average tag score per kind.
- `by-tag [--db PATH] [--json]`: kind distribution per tag, showing
  how many chunk kinds each tag appears in and average scores,
  ordered by kind breadth.
- `diversity [--db PATH] [--json]`: per-kind tag diversity as the
  ratio of distinct tags to total assignments, filtered to kinds
  with at least two assignments, ordered from most concentrated
  to most diverse.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total kinds, kinds with tagged chunks, coverage ratio, average
  tags per kind, single-kind tags, and the single-kind tag rate.
- `selftest`: exercises 14 checks covering per-kind tag counts,
  per-tag kind counts, diversity ratios, threshold filtering,
  summary totals, JSON serialisation, and empty corpus.

### Design properties

- **Kind as content type signal**: chunk kind reflects the
  structural role of content (claim, code, prose, table), and
  correlating it with tags reveals whether topical tagging
  concentrates on particular content types.
- **Single-kind tag rate**: measures what fraction of tags appear
  exclusively in one chunk kind, identifying kind-specific versus
  cross-cutting vocabulary.
- **Diversity threshold**: only kinds with at least two tag
  assignments appear in the diversity view, since a single
  assignment always produces a trivial ratio of one.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/kind_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-kind-tag-profile.md`: this spec

## See also

- [corpus-chunk-kind-profile](2026-08-31-corpus-chunk-kind-profile.md):
  profiles kinds per source and domain; this tool profiles kinds
  by tag vocabulary.
- [corpus-tag-landscape](2026-08-31-corpus-tag-landscape.md):
  profiles tags corpus-wide; this tool stratifies tags by their
  originating chunk kind.

## Non-goals

- Tag recommendation based on chunk kind.
- Kind reclassification based on tag patterns.
- Cross-source kind tag comparison.
- Tag score normalisation by kind.
