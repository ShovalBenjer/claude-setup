# Corpus Edge Confidence Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_confidence_profile.py

## Problem

edge_chain_analysis.py walks multi-hop paths and edge_bridge_analysis.py
identifies structural bridges, but neither profiles how the confidence
column in claim_edges distributes across edge types, sources, or
confidence bands. Understanding where the corpus has high-confidence vs
low-confidence argumentative connections is necessary for quality
assessment.

## Solution

A new tool `tools/corpus/edge_confidence_profile.py` with four
subcommands:

- `by-band [--db PATH] [--json]`: edge statistics per confidence band
  (low <0.25, medium 0.25-0.5, high 0.5-0.75, very-high 0.75+),
  showing edge count, type diversity, and min/max/avg confidence.
- `by-type [--db PATH] [--json]`: confidence distribution per edge
  type, showing edge count, confidence range, average, and number of
  bands spanned.
- `by-source [--db PATH] [--json]`: confidence distribution per source
  (via source_chunk join), showing edge count and confidence range per
  source.
- `summary [--db PATH] [--json]`: aggregate statistics including
  edges with confidence, coverage rate, min/max/avg/median confidence,
  and counts of low and high confidence edges.
- `selftest`: exercises 14 checks covering per-band edge counts,
  per-type confidence averages, per-source edge counts, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Confidence banding**: groups edges into four bands by confidence
  score, providing a coarse view of argumentative certainty across
  the corpus.
- **Per-type profiling**: reveals whether certain edge types (supports,
  contradicts, refines) tend toward higher or lower confidence.
- **Source attribution**: joins via source_chunk to attribute edge
  confidence to the originating source document.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/edge_confidence_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-confidence-profile.md`: this spec

## See also

- [corpus-edge-chain-analysis](2026-08-31-corpus-edge-chain-analysis.md):
  walks multi-hop paths; this tool profiles confidence distribution.
- [corpus-edge-bridge-analysis](2026-08-31-corpus-edge-bridge-analysis.md):
  identifies structural bridges; this tool profiles edge quality.

## Non-goals

- Confidence score recalibration or adjustment.
- Confidence-weighted path computation.
- Automatic low-confidence edge removal.
- Confidence prediction from edge metadata.
