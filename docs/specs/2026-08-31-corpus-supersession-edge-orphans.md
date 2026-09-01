# Corpus Supersession Edge Orphans

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/supersession_edge_orphans.py

## Problem

No tool identifies claim_edges pointing to or from chunks whose source
has been superseded.  supersession_analysis.py analyses the
sources.supersedes column (chain depths, rates by kind) but never
joins with claim_edges.  source_chain.py walks supersession chains but
never checks downstream edge impact.  Edges referencing chunks from
superseded sources may need re-evaluation or resolution, and finding
them required a manual three-way join across sources, chunks, and
claim_edges.

## Solution

A new tool `tools/corpus/supersession_edge_orphans.py` with four
subcommands:

- `orphans [--db PATH] [--json]`: edges where at least one endpoint
  chunk belongs to a superseded source, with flags for which endpoint
  is superseded and whether a resolution exists.
- `by-type [--db PATH] [--json]`: orphaned edge counts per edge_type
  with resolved and unresolved breakdowns.
- `resolvable [--db PATH] [--json]`: orphaned edges with no resolution
  yet, surfacing the backlog that needs attention.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total edges, orphaned count and rate, resolved and unresolved
  counts, and breakdown by supersession side (both, source-only,
  target-only).
- `selftest`: exercises 14 checks covering orphan detection,
  per-endpoint supersession flags, both-superseded detection,
  resolved orphan handling, non-orphan exclusion, per-type counts,
  resolvable filtering, summary totals, orphan rate, side breakdown,
  JSON serialisation, and empty corpus.

### Design properties

- **Three-way consistency check**: joins sources (via supersedes),
  chunks (via source_id), and claim_edges (via source_chunk and
  target_chunk) to find edges stranded by supersession.
- **Resolution awareness**: distinguishes resolved from unresolved
  orphans, since a resolved edge referencing a superseded source may
  be intentional.
- **Side classification**: reports whether the source endpoint, target
  endpoint, or both belong to superseded sources, enabling different
  remediation strategies.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/supersession_edge_orphans.py`: new tool
- `docs/specs/2026-08-31-corpus-supersession-edge-orphans.md`: this
  spec

## See also

- [corpus-supersession-analysis](2026-08-31-corpus-supersession-analysis.md):
  analyses sources.supersedes population and chain depth; this tool
  checks downstream edge impact of supersession.
- [corpus-edge-citation-quality](2026-08-31-corpus-edge-citation-quality.md):
  measures citation backing at edge endpoints; this tool measures
  supersession staleness at edge endpoints.

## Non-goals

- Automatic edge resolution based on supersession status.
- Supersession chain traversal to find replacement edges.
- Edge migration from superseded to superseding source chunks.
- Quality scoring of orphaned edges beyond resolution status.
