# Corpus Citation Graph

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/citation_graph.py

## Problem

The `claim_edges` table records pairwise relationships between chunks
(supports, contradicts, supersedes, duplicates, refines), but there was
no tool to analyze the citation network as a whole.  Questions like
"which chunk is most cited?", "which chunks cite the most others?", and
"which claim chunks have no connections at all?" required manual SQL
queries against the edge table.

## Solution

A new tool `tools/corpus/citation_graph.py` that computes graph metrics
over the `claim_edges` table.

### Tool commands

- `authority [--db PATH] [--top N] [--json]`: ranks chunks by citation
  authority (in-degree weighted by edge confidence).  Chunks that many
  others point to with high confidence rank highest.
- `hubs [--db PATH] [--top N] [--json]`: ranks chunks by hub score
  (out-degree weighted by confidence).  Chunks that cite many others
  with high confidence rank highest.
- `isolated [--db PATH] [--json]`: finds active claim chunks with no
  incoming or outgoing edges at all, sorted by word count descending.
  Only claim-kind chunks are reported since prose and code chunks are
  not expected to participate in the citation graph.
- `stats [--db PATH] [--json]`: summary including total active edges,
  connected vs. isolated chunk counts, edge type breakdown, average
  confidence, and max in/out degree.
- `selftest`: exercises 14 checks.

### Design properties

- **Resolved-edge aware**: edges with a non-null `resolution` are
  excluded from all computations (they represent adjudicated false
  positives or resolved contradictions).
- **Superseded-chunk aware**: only chunks with `status != 'superseded'`
  participate in the graph.
- **Confidence-weighted**: authority and hub scores weight each edge by
  its detection confidence rather than treating all edges equally.
- **Per-edge-type breakdown**: both chunk-level results and global stats
  report the mix of edge types (supports, contradicts, refines, etc.).

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/citation_graph.py`: new tool
- `docs/specs/2026-08-31-corpus-citation-graph.md`: this spec

## See also

- [corpus-contradiction-detection](2026-08-30-corpus-contradiction-detection.md):
  the contradiction detector that populates `claim_edges`.
- [corpus-lineage](2026-08-30-corpus-lineage.md): provenance chain
  tracing (lineage tracks source-to-chunk, this tool tracks
  chunk-to-chunk citations).

## Non-goals

- PageRank or HITS iterative convergence (confidence-weighted degree
  is sufficient for the corpus size).
- Graph visualization or rendering.
- Modifying edge resolution based on graph structure.
- Cross-corpus citation analysis.
