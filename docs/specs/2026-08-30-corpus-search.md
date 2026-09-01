# Corpus Search

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/search.py

## Problem

The research corpus had per-database query paths: `retrieve.py` searched
`state/corpus.db` via FTS5 and returned section 7.2 records, and the books
index at `~/.claude/corpus/books.sqlite3` had its own FTS5 table but no
CLI tool for querying it.  An operator wanting to find content across both
databases had to run two separate commands with different schemas and merge
the results manually.

## Solution

A new tool `tools/corpus/search.py` with two subcommands:

- `query TEXT [--k N] [--json] [--corpus-only | --books-only] [--snippet N] [--kind KIND] [--db PATH] [--books-db PATH]`:
  searches accepted chunks in the research corpus and content in the books
  index, merging results with provenance tags.
- `selftest`: exercises 18 checks covering both databases, graceful
  degradation, filters, output shape, and edge cases.

### Unified result shape

Each result carries a `source_db` tag ("corpus" or "books") so the caller
knows its provenance:

```json
{
  "source_db": "corpus",
  "id": "c9f2...",
  "snippet": "...",
  "kind": "prose",
  "source_id": "s1",
  "word_count": 42,
  "uri": "/path/to/source.md",
  "title": "Source Title"
}
```

Books results derive their title from the filename and have `source_id` and
`word_count` set to null.

### Design properties

- **Graceful degradation**: either database may be absent.  The tool queries
  whichever databases exist and reports which were available in the
  `databases` field.
- **Provenance-tagged**: every result carries `source_db` so downstream
  consumers can distinguish corpus chunks from book excerpts.
- **Filterable**: `--corpus-only` and `--books-only` restrict the search
  scope; `--kind` filters corpus chunks by kind (prose, code, etc.).
- **Configurable**: `--snippet N` controls snippet length, `--k N` limits
  total results, `--json` produces structured output.

## Results

First run against the real corpus (366 sources, 5937 chunks):
- Corpus database: available (state/corpus.db)
- Books database: not available on cloud machine (local-only)
- Selftest: 18 checks, all passing

## Scope

- `tools/corpus/search.py`: new tool
- `docs/specs/2026-08-30-corpus-search.md`: this spec

## Non-goals

- Reranking across databases (corpus results use FTS5 rank; cross-DB
  relevance ranking would require a shared embedding space).
- Full section 7.2 record shape for search results (use `retrieve.py` for
  that; this tool trades depth for breadth).
- Books ingestion (done by `dot-claude/skills/books-index/scripts/build_index.py`).
