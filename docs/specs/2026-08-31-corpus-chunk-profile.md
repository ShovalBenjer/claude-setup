# Corpus Chunk Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/chunk_profile.py

## Problem

Getting a complete picture of a single chunk required running multiple
tools: lineage for provenance, recommend for analytical signals,
dashboard for aggregate context.  No single command assembled the full
dossier for one chunk, and comparing two chunks meant running each
tool twice and mentally collating the results.

## Solution

A new tool `tools/corpus/chunk_profile.py` with three subcommands:

- `show --chunk-id CID [--db PATH] [--json]`: assembles a complete
  profile for one chunk.  Combines chunk metadata (kind, status, word
  count, heading path), parent source info (title, publisher, liveness),
  claim edges (direction, type, confidence, resolution), tags (with
  scores), topic assignment, cluster membership, top-5 similar chunks,
  and citations.
- `compare --chunk-id CID1 --chunk-id CID2 [--db PATH] [--json]`:
  side-by-side comparison of two chunks.  Reports shared tags, whether
  they share a topic or cluster, any direct edge between them, and
  their similarity score if one exists.
- `batch [--db PATH] [--status STATUS] [--limit N] [--json]`: profiles
  for multiple chunks filtered by status.
- `selftest`: exercises 14 checks covering profile assembly, source
  inclusion, edge directions, tag presence, citation inclusion,
  missing analytical tables, nonexistent chunks, comparison shared
  tags, direct edges, batch mode, JSON serialisation, empty corpus,
  and inbound edge direction.

### Design properties

- **Single-command dossier**: answers "tell me everything about this
  chunk" without running five separate tools.
- **Missing-table resilient**: each analytical signal degrades to
  empty or null when its table has not been created yet.
- **Direction-aware edges**: reports whether each edge is inbound or
  outbound relative to the profiled chunk.
- **Comparison mode**: surfaces relationships between any two chunks
  without manual cross-referencing.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/chunk_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-chunk-profile.md`: this spec

## See also

- [corpus-dashboard](2026-08-31-corpus-dashboard.md): aggregates
  corpus-wide metrics; this tool drills into individual chunks.
- [corpus-claim-network](2026-08-31-corpus-claim-network.md): analyses
  edge network structure; this tool shows edges from one chunk's
  perspective.
- [corpus-timeline](2026-08-31-corpus-timeline.md): temporal analysis;
  this tool shows a chunk's ingestion timestamp and source publication
  date.
- [corpus-audit](2026-08-31-corpus-audit.md): cross-signal issue
  detection; identifies which chunks need attention.

## Non-goals

- Chunk content display (shows metadata, not raw or normalised text).
- Automated quality scoring or recommendation.
- Batch comparison of all chunk pairs.
- Cross-corpus chunk lookup.
