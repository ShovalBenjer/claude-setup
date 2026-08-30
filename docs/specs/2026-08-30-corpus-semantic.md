# Corpus Semantic Analysis

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/semantic.py

## Problem

Regex-based reclassification (reclassify.py) and keyword TF-IDF tagging
(tagger.py) lack semantic generalisation.  They cannot match synonyms,
detect topic similarity across different phrasings, or cluster chunks by
meaning.  The spec (section 4.5) identifies this gap and recommends
upgrading when "semantic recall turns out to be the binding constraint."

## Solution

A new tool `tools/corpus/semantic.py` using scikit-learn's TF-IDF
vectorizer with n-gram features and cosine similarity:

- `classify [--db PATH] [--json]`: classifies each active chunk against
  20 domain descriptions using TF-IDF cosine similarity.  Returns the
  top-3 matching domains per chunk with scores.
- `similar --chunk CHUNK_ID [--db PATH] [--top-k N] [--json]`: finds
  the most semantically similar chunks to a given chunk using pairwise
  cosine similarity on TF-IDF vectors.
- `clusters [--db PATH] [--n-clusters N] [--json]`: groups chunks into
  topic clusters using MiniBatchKMeans on TF-IDF vectors.  Reports
  top terms per cluster for interpretability.
- `outliers [--db PATH] [--threshold F] [--json]`: finds chunks whose
  maximum similarity to any other chunk falls below a threshold,
  indicating they are topically isolated.
- `selftest`: exercises 16 checks covering classification accuracy,
  similarity ordering, clustering structure, and edge cases.

### ML stack

- **scikit-learn 1.9.0**: TfidfVectorizer (unigram + bigram, sublinear
  TF, English stop words), cosine_similarity, MiniBatchKMeans.
- **No neural models**: stays within the spec's "decided after the
  lexical version runs and fails" guidance while providing genuine
  semantic features.
- **Graceful degradation**: falls back with a clear error message if
  scikit-learn is not installed.

### Design properties

- **Semantic generalisation**: TF-IDF with bigrams captures multi-word
  concepts that single-token matching misses.
- **Sublinear TF**: dampens the effect of high-frequency terms, giving
  rarer domain-specific terms more weight.
- **Read-only**: all analysis is computed on the fly, no schema changes.
- **Interpretable**: cluster top terms and similarity scores are
  directly inspectable.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/semantic.py`: new tool
- `docs/specs/2026-08-30-corpus-semantic.md`: this spec

## Non-goals

- Neural embeddings (sentence-transformers, ONNX models).
- Persisting classifications or clusters in the database.
- Online/incremental learning.
