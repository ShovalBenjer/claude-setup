# Corpus Summarize

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/summarize.py

## Problem

Understanding the research corpus required multiple SQL queries or running
several tools to get a picture of its state. No single command showed chunk
distribution, citation density, contradiction status, artifact adoption
rates, and freshness together.

## Solution

A new tool `tools/corpus/summarize.py` with three subcommands:

- `report [--db PATH] [--json]`: full statistical profile covering totals,
  chunk distribution by kind and status, word count statistics, citation
  density and verification rate, open contradictions, artifact adoption
  rate, and source breakdowns by kind and liveness.
- `top-sources [--db PATH] [--n N] [--json]`: ranks sources by chunk
  count and total words, showing which documents contribute most to the
  corpus.
- `freshness [--db PATH] [--json]`: freshness profile showing liveness
  distribution, superseded chunk rate, and listing stale/archived/dead
  sources.
- `selftest`: exercises 16 checks covering all three subcommands, result
  shapes, edge cases, and JSON serialization.

### Design properties

- **Single-command dashboard**: the report subcommand is the one place to
  see the entire corpus state.
- **Structured output**: `--json` on every subcommand for machine
  consumption and downstream tooling.
- **Computed metrics**: citation density, artifact adoption rate, and
  superseded rate are calculated, not raw counts.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/summarize.py`: new tool
- `docs/specs/2026-08-30-corpus-summarize.md`: this spec

## Non-goals

- Trend analysis over time (use diff.py for temporal changes).
- Visualization or chart generation.
- Comparison between corpus snapshots.
