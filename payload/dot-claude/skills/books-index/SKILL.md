---
name: books-index
description: Build and query a full-text search index over every file in docs/books, not just a curated subset. Triggers on "index the books", "rebuild book corpus", "search my books for X", "/books-index". Local-only SQLite FTS5 index, no network access, operates purely on files already on disk.
---

# books-index

A general-purpose local search index over the entire `docs/books` directory,
superseding the earlier hand-curated `~/.claude/corpus` build (which only
covered ~67 of 284+ files, picked by a one-off agent pass). This one walks
the whole directory automatically and re-indexes incrementally, so a file
added by `books-ingest` (or dropped in by hand) is searchable without anyone
maintaining a source list.

## Hard boundary

Local-only. No network calls, no fetching, no scraping. Reads files already
present in `docs/books` and writes only to `~/.claude/corpus/books.sqlite3`.

## Storage

SQLite + FTS5 (stdlib `sqlite3`, no new dependency), one row per ~800-word
chunk, columns: `path`, `chunk_index`, `content`, `mtime`, `size`. A
`files` table tracks `path -> (mtime, size)` so re-running only re-chunks
files that changed since the last index, not the whole corpus.

## Usage

- `uv run python scripts/build_index.py`: incremental build/update. Safe to
  run repeatedly (e.g. after `books-ingest`); only touches changed files.
  Since 2026-08-23 it first writes `<name>.pdf.txt` beside every PDF that has
  none (pypdf, lazily imported; without it the PDFs are counted and reported,
  never skipped silently). Measured that day: 300 of 335 files were indexed and
  every gap was a PDF, mobi, or djvu.
- `python tools/corpus/books_check.py` (in claude-setup): the coverage oracle.
  Exit 1 on a txt the index does not know, a txt that changed since indexing, or
  a pdf/epub with no extracted text. mobi, djvu, and partial downloads are
  reported, not failed; they need calibre or djvulibre, which this machine lacks.
- `uv run python scripts/build_index.py --full`: force full rebuild.
- `uv run python scripts/query.py "search terms"`: FTS5 query, returns
  path, chunk index, and a snippet per hit, ranked by relevance.

## Copyright discipline

The index stores full chunk text in `~/.claude/corpus/books.sqlite3`,
outside the git tree, same as the source files it indexes. Query results
return short snippets for locating material, not whole-chapter dumps;
whoever reads results is bound by the same never-redistribute rule as the
source corpus.
