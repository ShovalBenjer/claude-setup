# Corpus Chunk Kind Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/chunk_kind_profile.py

## Problem

The research module reports a bare chunks_by_kind count in its
status output, but no tool analysed kind proportions per source or
per domain, detected kind-skewed sources (all prose, no claims), or
measured average word counts by kind.  Understanding content
composition required manual SQL grouping across the chunks,
sources, and chunk_domains tables.

## Solution

A new tool `tools/corpus/chunk_kind_profile.py` with four
subcommands:

- `distribution [--db PATH] [--json]`: corpus-wide chunk kind
  distribution.  Reports count, share, and average word count per
  kind (claim, code, table, config, link, prose).  Sorted by count
  descending.
- `per-source [--db PATH] [--json]`: per-source kind breakdown
  showing which kinds each source contributes, the dominant kind
  and its share.  Sorted by dominant share descending to surface
  kind-skewed sources first.
- `per-domain [--db PATH] [--json]`: per-domain kind breakdown
  (requires chunk_domains table) showing kind composition within
  each domain classification.  Sorted by total chunks descending.
- `summary [--db PATH] [--json]`: aggregate kind profile statistics
  including total accepted chunks, unique kinds, dominant kind and
  share, single-kind vs multi-kind source counts, and mean kinds
  per source.
- `selftest`: exercises 14 checks covering kind enumeration, share
  summation, dominant kind identification, average word count,
  per-source counts, kind count accuracy, single-kind detection,
  per-domain enumeration, domain kind membership, domain sort
  order, summary structure, source balance, JSON serialisation,
  and empty corpus.

### Design properties

- **Word-count-aware**: each kind carries average word count,
  revealing whether claims are short assertions while prose sections
  are longer expositions.
- **Dominant-kind detection**: per-source dominant share highlights
  sources that contribute only one kind, suggesting either
  specialised content or incomplete extraction.
- **Domain-kind correlation**: connecting chunk_domains to chunk
  kinds reveals whether certain domains are predominantly claims
  versus code or prose.
- **Accepted-only scope**: counts only accepted chunks, consistent
  with all other corpus analysis tools.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/chunk_kind_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-chunk-kind-profile.md`: this spec

## See also

- [corpus-domain-analysis](2026-08-31-corpus-domain-analysis.md):
  analyses domain classifications; this tool analyses chunk kind
  classifications with a structural rather than topical lens.
- [corpus-chunk-profile](2026-08-31-corpus-chunk-profile.md):
  analyses chunk-level metadata like word counts and simhash;
  this tool analyses the kind dimension specifically.
- [corpus-readability](2026-08-31-corpus-readability.md):
  measures text complexity per chunk; this tool measures structural
  content type composition.
- [corpus-source-lifecycle](2026-08-31-corpus-source-lifecycle.md):
  analyses source-level temporal and liveness profiles; this tool
  analyses source-level content composition.
- [corpus-domain-balance](2026-08-31-corpus-domain-balance.md):
  measures domain distribution evenness; this tool measures kind
  distribution within domains.

## Non-goals

- Chunk kind reclassification or correction.
- Kind-weighted search or retrieval.
- Kind prediction or inference.
- Temporal kind distribution tracking.
