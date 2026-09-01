# Corpus Contradiction Detection

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/contradict.py

## Problem

The research corpus (`state/corpus.db`) held 5936 chunks from 365 sources
with 3581 citations and zero contradiction edges. Step 7 of the research
corpus spec (2026-07-31) called for mechanical contradiction detection
across accepted chunks. Without it, two chunks asserting conflicting
values for the same metric, or recommending opposite actions for the same
tool, sit side by side in search results with no signal that they
disagree.

## Solution

A new tool `tools/corpus/contradict.py` with three subcommands:

- `detect [--db PATH]`: scans accepted chunks through three detectors,
  writes `claim_edges` rows with `edge_type='contradicts'`, returns
  counts per detector and new edges written.
- `report [--db PATH]`: queries and displays open contradictions ordered
  by confidence.
- `selftest`: exercises 8 checks covering each detector's true and false
  positive paths plus the persistence and idempotency invariants.

### Three detectors, cheapest first

1. **Numeric**: extracts metric patterns (`N units`, `label: N`) from
   chunk text, groups by unit/label, and flags pairs from different
   sources where the values differ by more than 50% and more than 1,
   with a context overlap (Jaccard similarity of words around the metric)
   of at least 0.25. This context requirement prevents matching "26 rows"
   in a backlog document against "0 rows" in a security audit.

2. **Negation**: pairs chunks by word overlap (Jaccard of non-negation
   words >= 0.5) or simhash Hamming distance (<= threshold), then checks
   whether the negation word density differs by at least 2 words. This
   catches "the results are reliable" vs "the results are not reliable
   and never consistent" when the surrounding text overlaps.

3. **Recommendation**: extracts tool names (file-extension-qualified
   capitalized words like `Gate.py`, or backtick-wrapped lowercase names
   like `` `pytest` ``), filters through a stopword list, scores
   positive vs negative verb proximity within a 60-char window around
   each mention, and flags pairs where the same tool appears with
   opposing sentiment across different chunks.

### Noise control

First run against the real corpus (5936 chunks) before tightening
produced 4194 contradictions. After adding:
- context overlap requirement for numeric (0.25 threshold)
- same-source exclusion for numeric
- file-extension requirement for capitalized tool names
- tool stopwords list filtering common English words
- lowercase-only backtick names (3-39 chars)

Re-run produced 11 contradictions (all recommendation type), which is a
reasonable signal-to-noise ratio for manual review.

## Design decisions

- Nothing is auto-resolved. An open contradiction downgrades both sides
  in ranking queries and surfaces in the defects query, per the spec.
- Edge IDs are deterministic (sha256 of source+target+type), so re-runs
  are idempotent via `INSERT OR IGNORE`.
- The tool reuses the `claim_edges` table already in the corpus schema
  rather than adding a new table.
- This is not a gate domain. The corpus DB is a generated artifact that
  depends on indexed content, and is not always present on CI runners.

## Scope

- `tools/corpus/contradict.py`: new tool (532 lines)
- `docs/specs/2026-08-30-corpus-contradiction-detection.md`: this spec

## See also

- [corpus-citation-graph](2026-08-31-corpus-citation-graph.md): graph
  analysis over the `claim_edges` table populated by this tool.

## Non-goals

- Auto-resolution or adjudication of contradictions.
- Integration with the quality gate (the corpus is not always available).
- Cross-corpus contradiction detection (only within `state/corpus.db`).
