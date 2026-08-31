# Corpus Supersession Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/supersession_analysis.py

## Problem

The sources.supersedes column had only chain-walking queries
(source_chain.py) but no statistical distribution analysis.  No tool
examined supersession population rates, chain depth distributions, or
how supersession varies by source kind.

## Solution

A new tool `tools/corpus/supersession_analysis.py` with four
subcommands:

- `rates [--db PATH] [--json]`: supersession population rates with
  total sources, sources with supersedes set, supersession rate,
  count of superseded sources, and head sources (not superseded by
  anything).
- `chains [--db PATH] [--json]`: distribution of supersession chain
  depths, counting how many chains reach each depth level.
- `by-kind [--db PATH] [--json]`: supersession rates per source kind
  with total sources, sources with supersedes, and supersession rate
  per kind.
- `summary [--db PATH] [--json]`: aggregate supersession statistics
  including population rates, max chain depth, total chains, and
  kinds with supersession.
- `selftest`: exercises 14 checks covering rate totals, supersession
  rate calculation, superseded source count, head source count, chain
  distribution entries, depth 2 and depth 3 chains, by-kind entries,
  paper/repo/local_md supersession counts, summary aggregates, JSON
  serialisation, and empty corpus.

### Design properties

- **Head detection**: identifies sources that are not superseded by
  any other source, revealing the current frontier of each chain.
- **Chain depth measurement**: walks supersession chains with a
  depth limit of 100 to prevent infinite loops from cycles.
- **Kind stratification**: reveals whether certain source kinds
  (paper, repo) have higher supersession rates than others.
- **Cycle safety**: the depth limit prevents runaway chain walking
  if the data contains unexpected cycles.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/supersession_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-supersession-analysis.md`: this spec

## See also

- [corpus-source-chain](../prior-art/source_chain.json):
  chain-walking queries that traverse supersession links; this tool
  adds the statistical distribution analysis.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; supersession rates are a
  complementary data lineage signal.

## Non-goals

- Automatic supersession chain repair or cycle detection.
- Source version recommendation or upgrade suggestions.
- Supersession prediction or forecasting.
- Chain visualisation or graph rendering.
