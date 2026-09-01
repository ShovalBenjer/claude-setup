# Corpus Edge Source Temporal Lag

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_source_temporal_lag.py

## Problem

edge_detection_timeline.py profiles edge detection timestamps alone.
temporal_distribution.py profiles source timestamps alone. No tool
joins source publication time with edge detection time to measure
how long after a source is published its chunks start participating
in claim edges, or whether edges on older sources resolve differently
than those on newer ones.

## Solution

A new tool `tools/corpus/edge_source_temporal_lag.py` with four
subcommands:

- `pub-to-edge [--db PATH] [--json]`: lag histogram from source
  publication to edge detection, bucketed into six bands (0-1d,
  1-7d, 7-30d, 30-90d, 90-365d, 365d+), showing edge count and
  lag range per band.
- `age-curve [--db PATH] [--json]`: per-source edge accumulation
  as a function of source age at detection time, showing edge count,
  age range, and span per source.
- `resolution-lag [--db PATH] [--json]`: time from edge detection
  to resolution grouped by source age band, revealing whether edges
  on older sources resolve faster or slower.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total edges with dates, sources with dates, median and average
  lag, and resolved edge count.
- `selftest`: exercises 14 checks covering lag band placement,
  age curve per source, resolution timing, summary totals, JSON
  round-trip, and empty corpus.

### Design properties

- **Publication-to-detection lag**: measures the temporal gap between
  when a source document was published and when argumentative edges
  referencing its chunks were detected.
- **Source age at detection**: groups edges by how old the source
  was when the edge was created, revealing whether newer sources
  attract edges faster.
- **Resolution velocity by age**: correlates source maturity with
  edge resolution speed, testing whether established sources see
  faster dispute resolution.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/edge_source_temporal_lag.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-source-temporal-lag.md`: this spec

## See also

- edge_detection_timeline.py: profiles edge timestamps alone; this
  tool joins them with source publication dates.
- temporal_distribution.py: profiles source timestamps alone; this
  tool correlates them with edge activity.
- edge_confidence_profile.py: profiles confidence distribution;
  temporal lag adds a time dimension to edge quality analysis.

## Non-goals

- Causal inference between publication age and edge quality.
- Time-series forecasting of edge creation rates.
- Source freshness scoring or staleness detection.
- Automatic edge aging or expiration policies.
