# Corpus Query Coverage

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/query_coverage.py

## Problem

The FTS5 index enables keyword retrieval, but no tool measured which
chunks are actually reachable by plausible queries.  Knowledge that
exists in the corpus but uses terminology that no query would match
is effectively invisible to the retrieval layer.  Identifying these
dead zones required manually testing queries and comparing results
against the full chunk inventory.

## Solution

A new tool `tools/corpus/query_coverage.py` with three subcommands:

- `probe [--db PATH] [--json]`: runs auto-generated probe queries
  derived from corpus metadata (tags, domains, artifact names, heading
  keywords) against the FTS5 index.  Reports each probe's match count
  and the chunk IDs it surfaces, sorted by match count descending.
- `uncovered [--db PATH] [--json]`: chunks that no probe query
  matches.  These represent dead knowledge unreachable by the
  retrieval layer.  Sorted by word count descending to surface the
  largest unreachable chunks first.
- `summary [--db PATH] [--json]`: coverage statistics including total
  accepted chunks, probe count, covered and uncovered counts,
  coverage rate, and average matches per probe.
- `selftest`: exercises 14 checks covering probe extraction, tag
  inclusion, FTS matching, coverage results, sort order, uncovered
  detection, covered exclusion, uncovered ordering, summary
  structure, coverage rate bounds, covered plus uncovered totals,
  average matches, JSON serialisation, and empty corpus.

### Probe generation

Probe terms are extracted from four corpus metadata sources:

1. **Tags**: the 20 most frequent tags from chunk_tags.
2. **Domains**: up to 20 distinct domains from chunk_domains.
3. **Artifacts**: up to 20 distinct artifact names.
4. **Headings**: words of four or more characters from accepted
   chunk heading paths, up to 50 unique terms.

The combined set is capped at 50 probes and run against the FTS5
index.  Any chunk matched by at least one probe is counted as
covered.

### Design properties

- **Self-derived probes**: queries come from the corpus's own
  metadata, testing whether the FTS5 index can reach content
  described by the corpus's own vocabulary.
- **Dead knowledge detection**: chunks unreachable by any probe
  represent gaps in the retrieval layer's effective vocabulary.
- **Size-weighted uncovered list**: sorting uncovered chunks by
  word count surfaces the largest invisible knowledge first.
- **Graceful degradation**: works without chunk_tags, chunk_domains,
  or artifacts tables by deriving probes from headings alone.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/query_coverage.py`: new tool
- `docs/specs/2026-08-31-corpus-query-coverage.md`: this spec

## See also

- [corpus-artifact-graph](2026-08-31-corpus-artifact-graph.md):
  maps inter-artifact relationships; this tool measures retrieval
  reachability of the corpus content.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; query coverage reveals a retrieval
  dimension the scorecard does not cover.
- [corpus-similarity-analysis](2026-08-31-corpus-similarity-analysis.md):
  analyses chunk relatedness; this tool analyses chunk retrievability.

## Non-goals

- Custom query sets or user-defined probes.
- Query expansion or synonym matching.
- Retrieval ranking or relevance scoring.
- FTS5 index repair or vocabulary augmentation.
