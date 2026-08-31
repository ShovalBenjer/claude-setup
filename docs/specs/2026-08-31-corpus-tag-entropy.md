# Corpus Tag Entropy

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_entropy.py

## Problem

The tag landscape and tag cooccurrence tools analyse tag distribution
and pairwise relationships, but neither measured how surprising or
predictable a chunk's tag assignments are relative to the corpus.
A chunk tagged with common tags is predictable; one tagged with rare
tags carries more information and may represent niche content or
miscategorisation.  Quantifying this required manually computing
information content from tag probabilities.

## Solution

A new tool `tools/corpus/tag_entropy.py` with three subcommands:

- `scores [--db PATH] [--json]`: per-chunk tag entropy as
  information content in bits.  For each chunk, sums the
  self-information (-log2 p) of each assigned tag where p is the
  corpus-wide probability of that tag.  Reports both total and
  average information bits.  Sorted by average info descending to
  surface the most surprising tag assignments first.
- `outliers [--db PATH] [--threshold F] [--json]`: chunks whose
  average tag information exceeds the threshold (default 3.0 bits).
  These have unusually rare tag combinations.
- `summary [--db PATH] [--json]`: aggregate tag entropy statistics
  including mean, median, min, max average information, high and
  low entropy chunk counts, and mean tags per chunk.
- `selftest`: exercises 14 checks covering score enumeration,
  descending sort, rare vs common tag ordering, tag count accuracy,
  positive information, outlier filtering, threshold sensitivity,
  summary structure, positive mean, ordering invariants, tags per
  chunk, JSON serialisation, and empty corpus.

### Information content model

Each tag's self-information is -log2(p) where p is the fraction of
accepted tagged chunks carrying that tag.  A tag appearing on every
chunk has p=1 and zero bits; a tag on one chunk out of a thousand
carries about 10 bits.  Per-chunk entropy is the average
self-information across its tags, making chunks with rare tag
combinations score higher regardless of tag count.

### Design properties

- **Corpus-relative**: entropy depends on the current tag
  distribution, so the same tags may score differently as the
  corpus grows.
- **Average normalisation**: dividing by tag count prevents chunks
  with many tags from dominating purely by volume.
- **Accepted-only scope**: joins through accepted chunks, excluding
  quarantined or rejected content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_entropy.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-entropy.md`: this spec

## See also

- [corpus-tag-landscape](2026-08-31-corpus-tag-landscape.md):
  analyses tag distribution and coverage; this tool measures
  per-chunk information content of those tag assignments.
- [corpus-tag-cooccurrence](2026-08-30-corpus-tag-cooccurrence.md):
  analyses pairwise tag relationships; this tool measures
  per-chunk tag surprise.
- [corpus-domain-tag-affinity](2026-08-31-corpus-domain-tag-affinity.md):
  analyses domain-tag PMI relationships; this tool analyses
  tag information content per chunk.
- [corpus-domain-balance](2026-08-31-corpus-domain-balance.md):
  measures domain distribution evenness; this tool measures
  tag assignment predictability.
- [corpus-readability](2026-08-31-corpus-readability.md):
  measures text complexity; this tool measures tag complexity.

## Non-goals

- Tag recommendation or suggestion.
- Entropy-weighted search ranking.
- Temporal entropy tracking.
- Cross-entropy between tag sets of different chunks.
