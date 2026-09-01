# Corpus Source Provenance Chain

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_chain.py

## Problem

The sources table records supersession relationships via the supersedes
column, but no tool traced these into chains.  Finding which source is
the latest version of an original, which sources sit at the head of a
chain, or whether any chain references a missing predecessor required
manual graph traversal.

## Solution

A new tool `tools/corpus/source_chain.py` with three subcommands:

- `chains [--db PATH] [--json]`: builds all supersession chains from
  head (latest) to tail (original).  Reports chain length, member
  source IDs, and chunk count per source in the chain.  Chains are
  sorted by length descending.
- `heads [--db PATH] [--json]`: identifies active chain heads (sources
  that supersede others but are not themselves superseded).  Reports
  title, kind, liveness, chunk count, and which source they supersede.
- `broken [--db PATH] [--json]`: detects broken chains where a source
  references a superseded source_id that does not exist in the sources
  table.  These indicate incomplete ingestion or data loss.
- `selftest`: exercises 14 checks covering chain detection, chain
  ordering, head and tail identification, chunk counts, independent
  source exclusion, active head enumeration, broken chain detection,
  valid chain exclusion from broken, JSON serialisation, empty corpus,
  no-supersession corpus, and length sorting.

### Design properties

- **Full chain traversal**: follows supersedes links through arbitrary
  chain lengths, with cycle detection.
- **Chunk-count annotated**: each chain member carries its chunk count,
  showing content distribution across versions.
- **Broken chain detection**: missing predecessors surface data
  integrity issues.
- **Graceful degradation**: returns empty results when no supersession
  relationships exist.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_chain.py`: new tool
- `docs/specs/2026-08-31-corpus-source-chain.md`: this spec

## See also

- [corpus-edge-resolution](2026-08-31-corpus-edge-resolution.md):
  analyses claim edge lifecycle; this tool analyses source lifecycle.
- [corpus-source-overlap](2026-08-31-corpus-source-overlap.md):
  measures content redundancy between sources; supersession chains
  explain why some sources overlap heavily.
- [corpus-dashboard](2026-08-31-corpus-dashboard.md): reports source
  totals and liveness; this tool traces version lineage.
- [corpus-citation-analysis](2026-08-31-corpus-citation-analysis.md):
  analyses citation patterns; this tool analyses source lineage.

## Non-goals

- Automated supersession of sources based on publication dates.
- Content diffing between chain versions.
- Cross-corpus chain comparison.
- Source merging or deduplication.
