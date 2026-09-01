# Corpus Text Normaliser

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/normalise.py

## Problem

Stage 0 of the ingestion pipeline requires text normalisation before
hashing, dedup, and indexing.  Raw corpus files contain NFC/NFD
inconsistencies, mojibake from cp1255 round-trips (6 known filenames
per section 2.1), Unicode dash variants that break string matching, and
trailing whitespace that inflates word counts.  Without normalisation,
byte-identical content can hash differently, and search misses
semantically identical text.

## Solution

A new tool `tools/corpus/normalise.py` implementing stage 0:

- `text --input TEXT`: normalise a single string (for scripting).
- `file --path FILE [--in-place]`: normalise a file, optionally
  writing back in place.
- `scan [--db PATH] [--json]`: finds corpus chunks whose `norm_text`
  would change under normalisation.  Reports chunk IDs and character
  count deltas.  Excludes superseded chunks.
- `apply [--db PATH] [--dry-run]`: applies normalisation to corpus
  chunks, updating `norm_text` and recomputing `norm_sha256`.
  Idempotent: re-running with already-normalised text produces no
  changes.
- `selftest`: exercises 18 checks covering NFC normalisation,
  mojibake repair, dash mapping, trailing whitespace stripping, mixed
  cases, scan/apply correctness, idempotency, and edge cases.

### Normalisation steps

Four operations, applied in order:

1. **NFC unicode**: `unicodedata.normalize("NFC", text)`.  Ensures
   composed forms so identical characters hash identically.
2. **Mojibake repair**: 12 known patterns covering UTF-8-as-latin1
   damage (accented vowels, curly quotes, en/em dashes) and the
   cp1255 GAMMA-aleph-pe sequence from the Mathematics and Statistics
   Frontier document.
3. **Dash variant mapping**: 8 Unicode dash variants (en dash, em dash,
   horizontal bar, figure dash, fullwidth hyphen-minus, etc.) mapped
   to ASCII hyphen-minus for consistent matching.
4. **Trailing whitespace**: `[ \t]+$` stripped per line.

### Design properties

- **In-process**: no shelling out per file, per section 2.1 lesson.
- **Idempotent**: normalising already-normalised text is a no-op.
- **Composable**: `normalise_text()` is a pure function importable by
  other corpus tools (pipeline.py, research.py).
- **Superseded excluded**: scan and apply skip superseded chunks.

## Results

- Selftest: 18 checks, all passing

## Scope

- `tools/corpus/normalise.py`: new tool
- `docs/specs/2026-08-30-corpus-normalise.md`: this spec

## Non-goals

- Full ICU transliteration or locale-aware normalisation.
- Filename normalisation (the 6 mojibake filenames are a separate
  disk-level decision per section 8).
- Language detection or script conversion.
