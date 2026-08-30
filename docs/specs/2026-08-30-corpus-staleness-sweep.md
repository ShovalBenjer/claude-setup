# Corpus Staleness Sweep

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/staleness.py

## Problem

The research corpus computed staleness per-query in `tools/corpus/retrieve.py`,
checking source age, fetch age, local file drift, and vector generation at
retrieval time. This had two limitations: (a) a drifted local file was never
corrected in the database, so every subsequent query re-detected the same drift
and returned stale hashes, and (b) there was no way to get a corpus-wide
freshness picture without querying every chunk.

## Solution

A new tool `tools/corpus/staleness.py` with two subcommands:

- `sweep [--db PATH] [--json]`: walks all sources, re-hashes local files,
  updates liveness and content_sha256 in the database, and produces a structured
  report with a freshness verdict.
- `selftest`: exercises 18 checks covering drift detection, dead file detection,
  revival, stale source detection, unverified fetch detection, and DB updates.

### Signals checked (per spec section 7.3)

1. **Local file drift**: re-hash the file on disk. A content_sha256 mismatch
   updates the hash, byte count, and upstream_mtime in the database. Unlike
   retrieve.py which only reports drift, this tool corrects it.
2. **Dead files**: a local_md source whose file no longer exists gets
   liveness set to `dead`. If the file reappears, liveness is restored to `live`.
3. **Source age**: sources with upstream_mtime exceeding 18 months (548 days)
   get liveness set to `stale`.
4. **Fetch age**: sources with fetched_utc exceeding 90 days are reported as
   `unverified` (informational; liveness is not changed since re-fetching is
   an operator action).
5. **Vector generation**: checks corpus-vec.json generation against corpus_meta.
   A mismatch is reported but not corrected (re-fitting is done by embed.py).

### Design properties

- **Idempotent**: re-running after a sweep with no file changes produces FRESH
  with zero updates.
- **Corrective**: unlike the read-only staleness check in retrieve.py, this tool
  writes updated hashes and liveness back to the database.
- **Structured output**: `--json` produces a machine-readable report with
  per-signal details and a verdict.

### Verdict logic

- `FRESH`: zero drifted files, zero dead files, zero newly stale sources,
  vectors current.
- `DRIFT: N drifted, M dead, ...`: any signal fires, with counts.

## Results

First run against the real corpus (366 sources):
- 0 drifted, 0 dead, 0 stale, 0 unverified
- Vectors: current (generation 2)
- Verdict: FRESH
- 0 updates applied

## Scope

- `tools/corpus/staleness.py`: new tool
- `docs/specs/2026-08-30-corpus-staleness-sweep.md`: this spec

## Non-goals

- Re-fetching external sources (operator decision).
- Re-fitting vectors (done by embed.py).
- Modifying chunk status based on source staleness (chunks inherit source
  freshness via retrieve.py at query time).
