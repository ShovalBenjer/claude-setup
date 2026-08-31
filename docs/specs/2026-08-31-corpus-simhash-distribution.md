# Corpus Simhash Distribution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_distribution.py

## Problem

The corpus uses simhash for near-duplicate detection, but no tool
analysed the quality of the hash distribution itself.  A biased
hash function or skewed inputs can cause clustering in hash space,
creating blind spots where distinct chunks share hashes while
genuinely similar chunks land far apart.  Detecting these patterns
required manual bit-level analysis of the simhash column.

## Solution

A new tool `tools/corpus/simhash_distribution.py` with four
subcommands:

- `entropy [--db PATH] [--json]`: per-bit set-rate across all
  accepted simhashes, measuring how close each bit is to the
  ideal 50% rate.  Sorted by deviation descending to surface
  the most biased bits first.
- `collisions [--db PATH] [--json]`: groups of chunks sharing
  exact simhash values.  Expected for near-duplicates but a high
  collision rate on distinct content signals hash weakness.
- `bit-balance [--db PATH] [--json]`: distribution of popcount
  (number of set bits) across simhashes.  For a well-distributed
  64-bit hash, popcount should cluster around 32.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total and unique hash counts, collision groups and rate, mean
  and median popcount, and maximum bit deviation.
- `selftest`: exercises 14 checks covering bit count, rate bounds,
  deviation ordering, collision detection, collision group accuracy,
  collision count, balance entries, share summation, zero-popcount
  representation, summary structure, uniqueness accounting, JSON
  serialisation, and empty corpus.

### Design properties

- **Bit-level analysis**: examines individual bit positions rather
  than treating hashes as opaque values, revealing systematic bias
  in the hash function or input distribution.
- **Collision-aware**: groups exact collisions to distinguish
  expected near-duplicate matches from hash-space saturation.
- **Popcount distribution**: the set-bit count is a proxy for
  hash-space coverage, and its distribution reveals whether
  hashes cluster in a narrow band or spread evenly.
- **Accepted-only scope**: analyses only accepted chunks, matching
  the dedup system's working set.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_distribution.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-distribution.md`: this spec

## See also

- [corpus-dedup](2026-08-30-corpus-dedup.md): uses simhash for
  near-duplicate detection; this tool analyses the hash quality
  underlying that detection.
- [corpus-similarity-analysis](2026-08-30-corpus-similarity-analysis.md):
  measures pairwise similarity; this tool measures hash-space
  distribution.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; hash distribution quality is a
  complementary dedup reliability signal.
- [corpus-word-count-distribution](2026-08-31-corpus-word-count-distribution.md):
  analyses word count distribution; this tool analyses hash value
  distribution.

## Non-goals

- Modifying the simhash algorithm or parameters.
- Hamming distance analysis between non-colliding hashes.
- Simhash computation or recomputation.
- Comparison with alternative hash functions.
