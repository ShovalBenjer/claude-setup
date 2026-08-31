# Corpus Upstream Provenance

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/upstream_provenance.py

## Problem

The sources table stores upstream_rev (a version or commit hash from the
original source) and upstream_mtime (the last modification time at the
upstream location).  No tool analysed these columns for completeness,
age distribution, or per-kind patterns.  The upstream_rev column was
never read analytically at all, and upstream_mtime was used only for
operational staleness checks, not for distribution analysis.  Finding
which source kinds track upstream versions, how old source material
is, or which sources lack provenance metadata required manual queries.

## Solution

A new tool `tools/corpus/upstream_provenance.py` with four subcommands:

- `completeness [--db PATH] [--json]`: upstream field completeness per
  source kind, showing how many sources have upstream_rev, upstream_mtime,
  both, or neither populated.
- `age-distribution [--db PATH] [--json]`: distribution of upstream
  modification ages in buckets (at most 7 days, 8 to 30 days, 31 to
  90 days, 91 to 180 days, 181 to 365 days, more than 365 days),
  showing which time ranges the corpus material falls into.
- `per-kind [--db PATH] [--json]`: upstream revision patterns per
  source kind including distinct revision count, populated count,
  and liveness breakdown.
- `summary [--db PATH] [--json]`: aggregate provenance statistics
  including total sources, revision and mtime population rates,
  distinct revisions, oldest and newest modification times, and
  liveness counts.
- `selftest`: exercises 14 checks covering completeness entries,
  per-kind field counts, missing field detection, age bucket
  distribution, share summation, recent and old bucket presence,
  per-kind revision counts, summary totals, distinct counts, JSON
  serialisation, and empty corpus.

### Design properties

- **Completeness tracking**: reveals which source kinds carry
  upstream version identifiers and which lack provenance metadata
  entirely, making data quality gaps visible.
- **Age bucketing**: fixed time buckets classify source material
  age, surfacing staleness patterns without requiring date
  arithmetic from the operator.
- **Liveness correlation**: per-kind breakdown includes liveness
  status counts, showing whether stale or archived sources
  correlate with specific source kinds.
- **All-source scope**: analyses all sources, not just those with
  accepted chunks, since provenance metadata applies at the source
  level.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/upstream_provenance.py`: new tool
- `docs/specs/2026-08-31-corpus-upstream-provenance.md`: this spec

## See also

- [corpus-source-provenance](2026-08-31-corpus-source-provenance.md):
  analyses source provenance chains and supersession; this tool
  analyses upstream version tracking metadata.
- [corpus-source-lifecycle](2026-08-31-corpus-source-lifecycle.md):
  analyses liveness transitions; this tool analyses the upstream
  timestamps that drive liveness decisions.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; upstream completeness is a
  complementary data quality signal.
- [corpus-publisher-license-distribution](2026-08-31-corpus-publisher-license-distribution.md):
  analyses publisher and license metadata; upstream provenance is
  an orthogonal source metadata dimension.

## Non-goals

- Automatic upstream revision fetching or update checking.
- Content diffing between upstream revisions.
- Upstream URL validation or link checking.
- Automated liveness reclassification.
