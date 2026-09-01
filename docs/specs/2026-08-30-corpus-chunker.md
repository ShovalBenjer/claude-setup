# Corpus Document Chunker

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/chunker.py

## Problem

Stage 2 of the ingestion pipeline requires splitting markdown documents
into indexable chunks.  Raw files range from single paragraphs to
10,000-word documents.  Without a chunker, downstream stages (dedup,
citation gate, embedding) operate on entire files, producing chunks too
large for retrieval and too coarse for kind classification.

The parent spec (section 4.1a) establishes the strategy: section-based
splitting on h2/h3 headings, with long sections subdivided at paragraph
boundaries, targeting ~350 words per chunk with a 30-word floor for
fragment filtering.

## Solution

A new tool `tools/corpus/chunker.py` implementing stage 2:

- `chunk --text TEXT [--source-id SID] [--json]`: chunk a text string,
  showing chunk IDs, kinds, word counts, and heading paths.
- `ingest --path FILE --source-id SID [--db PATH] [--dry-run]`: chunk
  a file and insert rows into the chunks table.
- `scan --dir DIR [--db PATH] [--json]`: scan a directory for markdown
  files, reporting chunk counts per file.
- `stats [--db PATH] [--json]`: chunk statistics from the database.
- `selftest`: exercises 17 checks.

### Chunking steps

Three operations, applied in order:

1. **Normalise**: applies `normalise_text()` from stage 0 (NFC, mojibake
   repair, dash mapping, trailing whitespace) before any splitting.
2. **Heading split**: regex `^(#{2,3})\s+(.+)$` splits on h2/h3
   boundaries.  Preamble before the first heading becomes its own
   section.  Heading paths are captured: bare title for h2, `h3:title`
   for h3.
3. **Subdivide**: sections exceeding 350 words are split on paragraph
   boundaries (`\n\s*\n`).  Fragments under 30 words in multi-part
   sections are dropped.

### Chunk properties

Each chunk carries:

- `chunk_id`: deterministic, `"c" + sha256(norm_text)[:16]`
- `source_id`: propagated from caller
- `ordinal`: sequential within the document
- `heading_path`: section heading for retrieval context
- `kind`: detected by `reclassify._detect_kind()` (claim, code, table,
  config, link, prose)
- `norm_text` / `raw_text`: normalised text (both set to the same
  normalised value since normalisation precedes chunking)
- `word_count`, `norm_sha256`, `simhash`, `citation_count`, `status`

### Design properties

- **In-process**: uses `normalise_text()` and `_detect_kind()` as
  library imports, no shelling out.
- **Deterministic**: same input always produces the same chunk IDs.
- **Idempotent**: duplicate inserts are silently skipped (try/except
  on INSERT).
- **Composable**: `chunk_text()` returns a list of dicts usable by
  `pipeline.py` without database access.

## Results

- Selftest: 17 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/chunker.py`: new tool
- `docs/specs/2026-08-30-corpus-chunker.md`: this spec

## Non-goals

- Per-cluster chunking strategies (section 4.1a proposes semantic and
  hierarchical strategies for specific atlas clusters; this tool
  implements the section-based baseline).
- Embedding window validation (no embedding model selected yet).
- Incremental re-chunking (full re-chunk is acceptable at current
  corpus scale).
