# Corpus Edge Basis Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_basis_analysis.py

## Problem

The claim_edges table stores a basis field describing why each edge
was created, but no tool analysed the distribution and quality of
these justification texts.  Missing or sparse basis text weakens
the evidentiary value of the claim graph, since edges without
explanations cannot be audited or contested.  Identifying coverage
gaps and patterns in basis quality required manual queries.

## Solution

A new tool `tools/corpus/edge_basis_analysis.py` with four
subcommands:

- `frequency [--db PATH] [--json]`: word-count distribution of
  basis text across five bins (empty, 1-5w, 6-15w, 16-50w, >50w)
  with counts and share percentages.
- `per-type [--db PATH] [--json]`: basis statistics per edge type
  (count, non-empty count, coverage rate, mean/max words, stddev),
  sorted by coverage ascending to surface the least-documented
  edge types first.
- `quality [--db PATH] [--json]`: edges with missing (0 words)
  or sparse (1-5 words) basis text, sorted by word count then
  edge id.
- `summary [--db PATH] [--json]`: aggregate basis statistics
  including total edges, with/without basis counts, coverage
  rate, mean/median/max words, sparse count, and edge type count.
- `selftest`: exercises 14 checks covering bin count, share sum,
  total count, empty-bin membership, type enumeration, coverage
  ordering, type count, quality detection, missing identification,
  sparse identification, summary totals, coverage rate, JSON
  serialisation, and empty corpus.

### Design properties

- **Coverage-first reporting**: surfaces which edge types lack
  justification text, enabling targeted documentation effort.
- **Word-count bins**: five practical bands distinguish missing,
  token, short, medium, and detailed justifications.
- **Quality detection**: flags both missing and sparse basis text
  as actionable items for claim graph improvement.
- **Graceful degradation**: returns empty results when the
  claim_edges table has no rows.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/edge_basis_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-basis-analysis.md`: this spec

## See also

- [corpus-edge-confidence](2026-08-31-corpus-edge-confidence.md):
  analyses confidence score calibration; this tool analyses the
  textual justification that accompanies confidence scores.
- [corpus-edge-density](2026-08-31-corpus-edge-density.md):
  measures how interconnected the claim network is; this tool
  measures how well-documented those connections are.
- [corpus-edge-resolution](2026-08-31-corpus-edge-resolution.md):
  tracks resolution patterns; basis text quality may correlate
  with resolution velocity.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; basis coverage is a
  complementary claim graph quality signal.

## Non-goals

- Basis text generation or auto-completion.
- Semantic analysis of basis content.
- Cross-edge basis deduplication.
- Basis text editing or correction.
