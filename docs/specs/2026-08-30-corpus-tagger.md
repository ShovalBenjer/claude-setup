# Corpus Auto-Tagger

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/tagger.py

## Problem

Chunks have a kind (prose, code, table, etc.) but no topic labels.
Without topic tags, finding all chunks about a domain (e.g. "security"
or "embedding") requires full-text search, which misses synonyms and
overmatches on incidental mentions.  The gaps tool checks coverage
against reference domains but does not tag individual chunks.

## Solution

A new tool `tools/corpus/tagger.py` with four subcommands:

- `tag [--db PATH] [--top-k N] [--min-score F] [--json]`: scores every
  active chunk against a 20-domain vocabulary using TF-IDF and assigns
  the top-k tags above the minimum score threshold.
- `vocab [--json]`: displays the domain vocabulary (20 domains, 200
  terms total) used for scoring.
- `chunks --tag TAG [--db PATH] [--json]`: finds all chunks matching a
  specific tag, sorted by relevance score.
- `stats [--db PATH] [--json]`: reports tag coverage, distribution
  across domains, and vocabulary size.
- `selftest`: exercises 16 checks covering tagging accuracy, filtering,
  sorting, edge cases, and empty corpus handling.

### TF-IDF scoring

Each domain has a curated term list (e.g. database: sqlite, sql, query,
schema, etc.).  For each chunk, term frequency is computed from tokenised
text, and inverse document frequency is computed across the corpus.  The
product gives a relevance score per domain, and the top-k scoring
domains become the chunk's tags.

### Domain vocabulary (20 domains)

database, search, embedding, dedup, citation, testing, security, ml,
python, typescript, rust, devops, api, prompt, agent, observability,
data, git, cloud, quality.

### Design properties

- **Numpy-only**: no sklearn, scipy, or neural model dependencies.
- **Transparent scoring**: TF-IDF is interpretable and auditable.
- **Read-only**: tagging is computed on the fly, not persisted, so it
  never conflicts with the schema or other tools.
- **Extensible vocabulary**: adding a domain is one dict entry.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/tagger.py`: new tool
- `docs/specs/2026-08-30-corpus-tagger.md`: this spec

## Non-goals

- Persisting tags in the database (future work).
- Neural or embedding-based classification (future work, per spec
  section 4.5 guidance on small ONNX embedder).
- Hierarchical or multi-label taxonomy.
