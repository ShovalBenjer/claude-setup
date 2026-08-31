# Corpus Artifact Dependency Graph

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_graph.py

## Problem

The artifacts table records technology references found in chunks, but
no tool mapped relationships between the artifacts themselves.
Discovering which libraries co-occur in the same chunk, which artifacts
share a source document, or which artifacts are semantically linked
through claim edges required manual cross-referencing across three
tables.

## Solution

A new tool `tools/corpus/artifact_graph.py` with three subcommands:

- `edges [--db PATH] [--json]`: artifact relationship edges.
  Each edge connects two artifacts and carries one or more relation
  types: co_mention (same chunk), co_source (same source document),
  claim_linked (chunks connected by a claim_edge).  Sorted by
  relation count descending.
- `clusters [--db PATH] [--json]`: connected components via
  union-find.  Groups artifacts that share any relationship into
  clusters, with isolated artifacts as singleton clusters.  Sorted
  by cluster size descending.
- `summary [--db PATH] [--json]`: graph statistics including total
  artifacts, edge count, connected vs isolated artifact counts,
  cluster count, and per-relation-type totals.
- `selftest`: exercises 14 checks covering co-mention detection,
  co-source detection, claim-linked detection, sort order, edge
  names, cluster grouping, cluster completeness, cluster ordering,
  summary structure, connected vs isolated counts, relation types,
  cluster count, JSON serialisation, and empty corpus.

### Relation types

1. **co_mention**: two artifacts referenced in the same chunk,
   indicating direct textual co-occurrence.
2. **co_source**: two artifacts in chunks from the same source
   document, indicating document-level co-presence.
3. **claim_linked**: the chunks carrying the two artifacts are
   connected by a claim_edge, indicating a semantic relationship
   between the claims mentioning each artifact.

### Design properties

- **Multi-relation edges**: a single edge can carry multiple relation
  types, revealing the strength of the connection.
- **Union-find clustering**: efficient connected-component detection
  groups artifacts into dependency clusters.
- **Graceful degradation**: returns empty results when the artifacts
  table does not exist.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_graph.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-graph.md`: this spec

## See also

- [corpus-ingestion-regression](2026-08-31-corpus-ingestion-regression.md):
  detects version-level quality drops; this tool maps structural
  relationships between artifacts.
- [corpus-artifact-adoption](2026-08-31-corpus-artifact-adoption.md):
  analyses artifact implementation rates; this tool analyses
  inter-artifact relationships.
- [corpus-claim-consensus](2026-08-31-corpus-claim-consensus.md):
  analyses claim agreement; this tool uses claim edges to discover
  artifact-level semantic links.

## Non-goals

- Artifact version dependency resolution (npm/pip style).
- Transitive dependency chains beyond direct edges.
- Artifact removal or deduplication.
- External package registry lookups.
