# Corpus Vocabulary Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/vocab_analysis.py

## Problem

The auto-tagger scores chunks against a fixed 20-domain vocabulary, but
there was no tool to discover what the corpus actually talks about, which
terms are most distinctive per chunk kind, or how much of each domain
vocabulary the corpus covers.  Those questions required ad-hoc SQL or
manual inspection.

## Solution

A new tool `tools/corpus/vocab_analysis.py` with three subcommands:

- `profile [--db PATH] [--top N] [--json]`: corpus-wide term frequency
  profile reporting total chunks, total words, vocabulary size, average
  words per chunk, kind distribution, and the N most frequent terms with
  their document frequency and document fraction.
- `distinctive [--db PATH] [--top N] [--json]`: discovers the most
  distinctive terms per chunk kind using sklearn TF-IDF.  Merges all
  texts of each kind into a single pseudo-document, fits a
  TfidfVectorizer (max_features=3000, unigrams and bigrams, English stop
  words, sublinear TF), and ranks terms by their TF-IDF weight within
  each kind.
- `coverage [--db PATH] [--json]`: measures corpus vocabulary overlap
  against the tagger's 20-domain `DOMAIN_VOCAB` dictionary.  Reports
  per-domain match count, coverage percentage, and the first 10 missing
  terms, plus an overall coverage percentage across all domains.
- `selftest`: exercises 14 checks.

### Design properties

- **Complements the tagger**: the tagger scores individual chunks; this
  tool profiles the corpus vocabulary as a whole, surfaces what
  distinguishes kinds from each other, and measures how much of the
  reference vocabulary is represented.
- **Superseded-chunk aware**: only chunks with `status != 'superseded'`
  participate.
- **sklearn-optional by subcommand**: `profile` and `coverage` use only
  standard library; `distinctive` requires sklearn for TF-IDF.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/vocab_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-vocab-analysis.md`: this spec

## See also

- [corpus-tagger](2026-08-30-corpus-tagger.md): the auto-tagger whose
  `DOMAIN_VOCAB` the coverage subcommand measures against.
- [corpus-topic-model](2026-08-31-corpus-topic-model.md): NMF topic
  discovery (unsupervised); this tool's `distinctive` subcommand uses
  supervised TF-IDF per known chunk kind.

## Non-goals

- Modifying or extending the domain vocabulary.
- Embedding-based vocabulary profiling.
- Cross-corpus vocabulary comparison.
