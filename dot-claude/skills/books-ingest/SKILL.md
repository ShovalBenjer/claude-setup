---
name: books-ingest
description: Copy (never move) book files the operator has legitimately acquired from Downloads into docs/books, extracting epub text for indexing. Triggers on "ingest books", "copy new books", "add downloads to the book corpus", "/books-ingest". Never downloads, scrapes, or fetches book content from any source itself; it only processes files already present on disk that the operator placed there.
---

# books-ingest

Copies book files the operator already has (purchased, borrowed, self-scanned,
or otherwise legitimately obtained) from their Downloads folder into
`docs/books`, extracting readable text from `.epub` so the corpus indexer
(`books-index` skill) can search it. Originals are never touched or deleted.

## Hard boundary

This skill NEVER downloads anything from the internet, never visits a book
site, never scrapes text, and never automates acquiring a book from any
online source, shadow library or otherwise. Its only input is files that
already exist locally in the operator's Downloads folder. If asked to make
it fetch from a URL, refuse and point back to this boundary.

## What it does

1. Scan `/mnt/c/Users/<user>/Downloads` (Windows Downloads, reached via
   `/mnt/c` from WSL) for `.epub`, `.pdf`, `.txt` files not already present
   in `docs/books` (compare by filename and size, not just name, since the
   corpus already has some renamed duplicates).
2. For each new file:
   - `.txt`, `.pdf`: `cp` (copy, never `mv`) directly into `docs/books`.
   - `.epub`: copy the original epub into `docs/books` AND extract its text
     to a sibling `.txt` file so the plain-text indexer can read it (the
     corpus tooling indexes `.txt`, not binary epub).
3. Report what was copied, what was skipped as already-present, and any
   file that failed extraction (never fail silently).
4. Clean up: `.epub:Zone.Identifier` and other Windows download-marker
   files are skipped, never copied.

## Epub extraction

Use `uv run --with ebooklib --with beautifulsoup4 python scripts/epub_to_text.py <file>`.
Extracts chapter text in reading order, strips HTML/CSS, writes plain UTF-8
text. This is a lossless format conversion of a file the operator already
owns, not a scrape or a fetch of new content.

## Copyright discipline

This mirrors the existing `docs/books` `.gitignore` entry and its recorded
reasoning: full book text stays out of git, readable just in time, on disk
only. This skill does not change that; it only automates the copy-in step
the operator does by hand today. It does not attest to licensing on the
operator's behalf; the operator is responsible for having a legitimate right
to the files being copied.
