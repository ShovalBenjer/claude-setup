# Corpus Domain Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/domain_analysis.py

## Problem

The chunk_domains table stores ML-based semantic domain classifications
for chunks, but no tool analysed these classifications at scale.
Finding which domains dominate the corpus, which sources are topically
focused vs broad, which chunks bridge multiple domains, or how claim
edges flow between domains required manual queries.

## Solution

A new tool `tools/corpus/domain_analysis.py` with four subcommands:

- `distribution [--db PATH] [--json]`: domain distribution across the
  corpus.  Reports chunk count per domain, score statistics (avg, min,
  max), total assignments, unique domain count, and classified chunk
  count.  Ordered by chunk count descending.
- `per-source [--db PATH] [--json]`: per-source domain breakdown
  showing the topical focus of each source.  Each source entry lists
  its domains with chunk counts and average scores.
- `multi-domain [--db PATH] [--top N] [--json]`: chunks classified
  into more than one domain, ranked by domain count.  Reports the
  domain list, chunk kind, and heading path.  These chunks sit at
  disciplinary boundaries.
- `edge-flow [--db PATH] [--json]`: claim edges that cross domain
  boundaries, grouped by source domain, target domain, and edge type.
  Shows where claims in one field support or contradict claims in
  another.
- `selftest`: exercises 14 checks covering distribution totals,
  domain ordering, score statistics, per-source breakdown, source
  domain membership, multi-domain detection, single-domain exclusion,
  domain count and list, top-N limiting, edge flow presence,
  cross-domain edge capture, JSON serialisation, and empty corpus.

### Design properties

- **Score-aware**: reports classification confidence statistics per
  domain, enabling quality-filtered views.
- **Source-level granularity**: reveals whether sources are topically
  narrow (one domain) or broad (spanning several).
- **Boundary detection**: multi-domain chunks identify content at
  disciplinary intersections.
- **Edge flow**: inter-domain claim edges reveal how different fields
  relate through supporting or contradicting evidence.
- **Graceful degradation**: returns empty results when the
  chunk_domains table does not exist.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/domain_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-domain-analysis.md`: this spec

## See also

- [corpus-artifact-adoption](2026-08-31-corpus-artifact-adoption.md):
  analyses technology references; this tool analyses semantic domain
  classifications.
- [corpus-domain-store](2026-08-30-corpus-domain-store.md): the
  domain classification infrastructure this tool reads from.
- [corpus-edge-resolution](2026-08-31-corpus-edge-resolution.md):
  analyses edge lifecycle; this tool analyses edges across domain
  boundaries.

- [corpus-tag-landscape](2026-08-31-corpus-tag-landscape.md):
  analyses tag classifications; this tool analyses domain
  classifications.

## Non-goals

- Domain reclassification or score recalibration.
- Domain hierarchy or taxonomy construction.
- Cross-corpus domain comparison.
- Domain-aware search or retrieval.
