# Corpus Edge Detection Timeline

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_detection_timeline.py

## Problem

The claim_edges.detected_utc column had zero analytical queries
anywhere in the codebase.  All references were INSERT values in
ingestion and test code.  No tool examined when edges were
discovered, whether detection activity varies by edge type, or how
long edges take to resolve after detection.

## Solution

A new tool `tools/corpus/edge_detection_timeline.py` with four
subcommands:

- `timeline [--db PATH] [--json]`: distribution of edge detection
  times by month, showing count and share per month.
- `by-type [--db PATH] [--json]`: detection timeline broken down by
  edge type (supports, contradicts, supersedes, duplicates,
  refines), showing total edges and distinct months per type.
- `resolution-lag [--db PATH] [--json]`: lag between detection and
  resolution for resolved edges, with mean, max, and min days per
  edge type.
- `summary [--db PATH] [--json]`: aggregate detection statistics
  including total edges, distinct types, detection range, distinct
  months, resolved count and rate, and mean confidence.
- `selftest`: exercises 14 checks covering timeline entries,
  distinct months, share summation, monthly counts, by-type entries,
  supports count and months, contradicts count, resolution lag
  entries, resolved count, minimum lag, summary totals, resolved
  rate, JSON serialisation, and empty corpus.

### Design properties

- **Monthly granularity**: detection times are grouped by month,
  revealing whether edge discovery happens in bursts or at a steady
  pace.
- **Type-stratified view**: per-type timelines reveal whether
  certain edge types (contradicts, supports) cluster in particular
  periods.
- **Resolution lag**: connecting detected_utc to resolved_utc
  measures how quickly detected relationships are confirmed or
  rejected.
- **All-edge scope**: analyses all edges regardless of resolution
  status, since unresolved edges are the work backlog.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/edge_detection_timeline.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-detection-timeline.md`: this spec

## See also

- [corpus-claim-edge-analysis](2026-08-31-corpus-claim-edge-analysis.md):
  analyses edge type distribution and confidence; this tool adds
  the temporal dimension to edge analysis.
- [corpus-temporal-distribution](2026-08-31-corpus-temporal-distribution.md):
  analyses ingestion, publication, and fetch timestamps; this tool
  analyses the claim_edges detection timestamp.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; edge detection velocity is a
  complementary coverage signal.

## Non-goals

- Automatic edge detection scheduling or prioritisation.
- Detection quality assessment or false-positive analysis.
- Edge detection algorithm comparison.
- Temporal trend forecasting for edge discovery rates.
