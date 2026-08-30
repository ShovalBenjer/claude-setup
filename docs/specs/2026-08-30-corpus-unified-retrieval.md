# Corpus Unified Retrieval

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/retrieve.py

## Problem

The research corpus had individual tools for FTS5 search, vector
reranking, contradiction detection, artifact extraction, and trust
classification, but no unified query path that combined them into
the section 7.2 record shape. Callers had to assemble results from
multiple tools and compute staleness themselves, which no caller
would actually do.

## Solution

A new tool `tools/corpus/retrieve.py` with two subcommands:

- `query TEXT [--kind KIND] [--implemented] [--max-age DAYS] [--k N]
  [--db PATH] [--json]`: executes a corpus query returning the full
  section 7.2 record shape. FTS5 first, vector rerank second, then
  staleness, trust, citations, contradictions, and artifacts attached
  per result.
- `selftest`: exercises 9 checks covering query, record shape,
  citations, contradictions, artifacts, trust, staleness, and empty
  query handling.

### Record shape

Each result is a record, not a paragraph:

```json
{
  "chunk_id": "c9f2...",
  "text": "...",
  "kind": "pattern",
  "source": {
    "uri": "...",
    "license_verdict": "vendor",
    "liveness": "live",
    "fetched_utc": "...",
    "upstream_mtime": "..."
  },
  "citations": [{"target_uri": "...", "verified": true}],
  "contradicted_by": [],
  "artifacts": [{"name": "...", "implemented": true, ...}],
  "staleness": {"verdict": "fresh", "age_days": 4, "reasons": []},
  "trust": "trusted",
  "reranked": true
}
```

### Staleness computation (spec section 7.3)

Four signals, verdict is the worst:

1. Source age: `upstream_mtime` older than 18 months gives `stale`;
   archived upstream gives `archived`.
2. Fetch age: `fetched_utc` older than 90 days gives `unverified`.
3. Local file drift: re-hash the file, `content_sha256` mismatch
   gives `drifted`.
4. Vector generation mismatch: `rerank_unavailable` when generation
   counters diverge.

### Facets

- `--kind`: filter by chunk kind (prose, code, table, config, etc.)
- `--implemented`: show only chunks with implemented artifacts
- `--max-age`: exclude results older than N days
- `--k`: top-K results (default 10)
- `--json`: machine-readable output

## Results

First run against the real corpus:
- Query "deploy script service": 5 results, all reranked, all trusted,
  all fresh. Top result is the Azure DevOps dormancy audit with 2
  citations and 2 artifacts.
- JSON output includes full record shape with all fields populated.

## Design decisions

- FTS5 first, vectors second: the lexical embedder has limited
  semantic generalization (noted in spec section 4.5), so FTS5
  provides the candidate set and vectors reorder it.
- Staleness computed per result: the caller never has to infer
  freshness. A result that cannot prove its freshness says so in the
  payload.
- Trust derived from license_verdict: vendor sources are trusted,
  index_only sources are untrusted, matching the section 7.2 spec.
- Graceful degradation: if embed.py or license_gate.py cannot be
  imported, retrieval still works without reranking or license
  checking.

## Scope

- `tools/corpus/retrieve.py`: new tool
- `docs/specs/2026-08-30-corpus-unified-retrieval.md`: this spec

## Non-goals

- Replacing the existing `research.py query` command (that remains
  for simple FTS5-only queries).
- Caching query results (row-reuse handles write-back separately).
- Auto-resolution of contradictions shown in results.
