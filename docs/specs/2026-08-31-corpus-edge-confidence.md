# Corpus Edge Confidence

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_confidence.py

## Problem

The edge density and claim network tools measure edge counts and
topology, but neither analysed the confidence scores attached to
claim edges.  A corpus where most edges cluster at 1.0 or 0.0 may
indicate miscalibrated detection rather than genuinely certain
relationships.  Understanding confidence distribution per edge type
and flagging extreme values required manual SQL against the
claim_edges table.

## Solution

A new tool `tools/corpus/edge_confidence.py` with four subcommands:

- `distribution [--db PATH] [--json]`: confidence histogram across
  all claim edges in five buckets (0.0-0.2, 0.2-0.4, 0.4-0.6,
  0.6-0.8, 0.8-1.0).  Reports count and share per bucket.
- `extremes [--db PATH] [--threshold F] [--json]`: edges whose
  confidence is below the threshold (default 0.05) or above
  (1 - threshold).  Labels each as "low" or "high" extreme.
  Sorted by confidence ascending.
- `per-type [--db PATH] [--json]`: confidence statistics per edge
  type (supports, contradicts, supersedes, duplicates, refines).
  Reports count, mean, median, min, max, and standard deviation.
  Sorted by count descending.
- `summary [--db PATH] [--json]`: aggregate confidence statistics
  including total edges, mean, median, standard deviation, resolved
  and unresolved counts, edge type count, and high/low confidence
  counts.
- `selftest`: exercises 14 checks covering histogram bucket count,
  share summation, total count, high bucket membership, extreme
  filtering, extreme labelling, sort order, type enumeration, type
  count accuracy, mean-min-max invariant, summary structure,
  resolved count balance, JSON serialisation, and empty corpus.

### Design properties

- **Five-bucket histogram**: even-width buckets reveal clustering
  patterns that a single mean would obscure.
- **Extreme detection**: configurable threshold surfaces potentially
  miscalibrated edges at both ends.
- **Per-type breakdown**: different edge types may have legitimately
  different confidence profiles (duplicates near 1.0, contradictions
  more spread).
- **Accepted-only scope**: joins through accepted chunks on both
  sides of each edge.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/edge_confidence.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-confidence.md`: this spec

## See also

- [corpus-edge-density](2026-08-31-corpus-edge-density.md):
  measures edge count and density ratios; this tool analyses the
  confidence values on those edges.
- [corpus-claim-network](2026-08-31-corpus-claim-network.md):
  analyses claim graph topology; this tool analyses edge confidence
  calibration.
- [corpus-claim-consensus](2026-08-31-corpus-claim-consensus.md):
  measures agreement patterns across claims; this tool measures
  confidence quality of the edges encoding those patterns.
- [corpus-cross-ref-density](2026-08-31-corpus-cross-ref-density.md):
  analyses citation direction; this tool analyses claim edge
  confidence.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus health metrics; edge confidence calibration
  is a complementary quality signal.
- [corpus-edge-basis-analysis](2026-08-31-corpus-edge-basis-analysis.md):
  analyses basis text quality; this tool analyses the confidence
  scores that accompany basis justifications.

## Non-goals

- Confidence recalibration or score adjustment.
- Edge creation or deletion.
- Confidence-weighted graph analysis.
- Temporal confidence drift tracking.
