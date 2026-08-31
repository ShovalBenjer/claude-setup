# Corpus Source Citation Network

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_citation_net.py

## Problem

The citation graph tool analyses claim edges at the chunk level, but
no tool aggregated citations up to source-to-source relationships.
Knowing which sources cite which other sources reveals the
intellectual dependency structure of the corpus: which sources are
authorities, which are hubs, and which pairs mutually cite each
other.  Building this view required manually joining citations
through chunks to their source assignments.

## Solution

A new tool `tools/corpus/source_citation_net.py` with three
subcommands:

- `links [--db PATH] [--json]`: source-to-source citation links
  with citation counts.  A link from source A to source B means
  accepted chunks in A contain citations whose target_uri matches
  B's canonical_uri or whose target_source_id points to B.
  Self-citations are excluded.  Sorted by citation count descending.
- `ranks [--db PATH] [--json]`: per-source network metrics
  including in-degree, out-degree, weighted in/out citation counts,
  net citations, and mutual citation flag.  Sorted by in-citations
  descending to surface the most-cited sources first.
- `summary [--db PATH] [--json]`: aggregate network statistics
  including total links, total cross-source citations, citing and
  cited source counts, mutual pair count, isolated source count,
  most cited and most citing sources, and mean degree.
- `selftest`: exercises 14 checks covering link enumeration, count
  accuracy, mutual citation detection, self-citation exclusion,
  sort order, rank participation, in-citation ranking, mutual flag,
  rank ordering, summary structure, mutual pairs, most-cited
  identification, JSON serialisation, and empty corpus.

### Design properties

- **Source-level aggregation**: lifts chunk-level citations to
  source pairs, providing a higher-level dependency view.
- **Dual resolution**: uses both target_source_id (explicit) and
  target_uri matching against canonical_uri (implicit) to find
  source-to-source links.
- **Mutual detection**: flags sources that both cite and are cited
  by other sources, revealing bidirectional intellectual exchange.
- **Self-citation exclusion**: filters out citations within the
  same source to focus on cross-source relationships.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_citation_net.py`: new tool
- `docs/specs/2026-08-31-corpus-source-citation-net.md`: this spec

## See also

- [corpus-citation-graph](2026-08-30-corpus-citation-graph.md):
  analyses claim edges at chunk level; this tool aggregates
  citations up to source-to-source relationships.
- [corpus-citation-analysis](2026-08-30-corpus-citation-analysis.md):
  analyses citation density and patterns; this tool analyses
  cross-source citation topology.
- [corpus-citation-age](2026-08-31-corpus-citation-age.md):
  measures verification staleness; this tool measures citation
  network structure between sources.
- [corpus-source-provenance](2026-08-31-corpus-source-provenance.md):
  computes composite source quality; this tool maps citation
  dependencies between those sources.
- [corpus-source-overlap](2026-08-31-corpus-source-overlap.md):
  measures content similarity between sources; this tool measures
  citation relationships between them.

## Non-goals

- PageRank or betweenness centrality computation.
- Citation recommendation or suggestion.
- Temporal citation network evolution.
- Citation graph visualisation.
