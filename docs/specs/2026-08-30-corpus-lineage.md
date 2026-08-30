# Corpus Lineage

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/lineage.py

## Problem

Understanding how a chunk arrived in the corpus, what it connects to, and
whether anything depends on it required manual SQL across four tables
(citations, claim_edges, artifacts, sources).  No single command traced the
full provenance chain from a chunk back to its source and forward to its
downstream consumers.

## Solution

A new tool `tools/corpus/lineage.py` with three subcommands:

- `chunk [--db PATH] [--depth N] [--json] <chunk_id>`: traces a single
  chunk's provenance chain.  Shows the chunk itself, its parent source,
  outbound citations, inbound/outbound claim edges, extracted artifacts,
  and (recursively up to `--depth`) downstream chunks that cite it.
- `source [--db PATH] [--json] <source_id>`: traces a source's full
  footprint.  Shows source metadata, its chunk list with statuses, the
  supersession chain (what it supersedes and what supersedes it), and
  aggregate citation and edge counts per chunk.
- `orphans [--db PATH] [--json]`: finds provenance gaps.  Reports
  accepted claim chunks with zero outbound citations ("uncited claims")
  and chunks with no citations, edges, or artifacts in any direction
  ("isolated chunks").
- `selftest`: exercises 16 checks covering all three subcommands,
  recursive depth traversal, JSON serialization, and edge cases.

### Design properties

- **Single-command provenance**: the chunk subcommand answers "where did
  this come from and what depends on it" in one call.
- **Recursive traversal**: downstream citations are followed to the
  configured depth, revealing citation chains.
- **Structured output**: `--json` on every subcommand for machine
  consumption and downstream tooling.
- **Orphan detection**: complements validate.py's structural checks with
  semantic provenance gaps.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/lineage.py`: new tool
- `docs/specs/2026-08-30-corpus-lineage.md`: this spec

## Non-goals

- Visualization or graph rendering of lineage chains.
- Cross-corpus lineage (comparing two database files).
- Automated repair of orphaned chunks.
