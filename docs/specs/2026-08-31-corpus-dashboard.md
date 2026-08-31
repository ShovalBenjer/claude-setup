# Corpus Dashboard

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/dashboard.py

## Problem

Getting a corpus overview required running many individual tools:
chunk counts from validate, edge stats from contradict, tag coverage
from tag_store, topic coverage from topic_model, and so on.  No single
command aggregated key metrics into one report.

## Solution

A new tool `tools/corpus/dashboard.py` with three subcommands:

- `overview [--db PATH] [--json]`: chunk counts by status (active,
  superseded, accepted, quarantined) and kind, plus source totals and
  liveness counts.
- `health [--db PATH] [--json]`: edge statistics (total, unresolved,
  open contradictions, by type), citation and artifact counts, and
  orphan claim chunk detection (accepted claims with no citations or
  edges).
- `signals [--db PATH] [--json]`: analytical signal coverage across
  topics, clusters, tags, similarities, and domains.  For each signal
  reports chunks covered, distinct label count, and coverage ratio.
- `selftest`: exercises 14 checks covering all three subcommands,
  kind breakdowns, edge type breakdowns, orphan detection, signal
  coverage, superseded-chunk exclusion, missing analytical tables, and
  JSON serialisation.

### Design properties

- **Single-command overview**: answers "what does the corpus look like?"
  without running five separate tools.
- **Missing-table resilient**: each signal degrades to zero coverage
  when its analytical table has not been created yet.
- **Orphan detection**: finds accepted claim chunks with no citations
  or edges in any direction.
- **Superseded-chunk aware**: overview and signal coverage count only
  active chunks.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/dashboard.py`: new tool
- `docs/specs/2026-08-31-corpus-dashboard.md`: this spec

## See also

- [corpus-quality-trend](2026-08-30-corpus-quality-trend.md): tracks
  quality metrics over time; this tool provides a point-in-time
  overview.
- [corpus-diversity](2026-08-31-corpus-diversity.md): measures topic
  distribution; this tool measures signal coverage breadth.
- [corpus-claim-network](2026-08-31-corpus-claim-network.md): analyses
  edge network structure; this tool reports edge aggregate statistics.

## Non-goals

- Historical dashboard snapshots or diffing.
- Visualization or chart rendering.
- Automated remediation recommendations.
- Cross-corpus dashboard comparison.
