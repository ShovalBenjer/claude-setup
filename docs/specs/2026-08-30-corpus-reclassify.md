# Corpus Chunk Reclassification

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/reclassify.py

## Problem

Chunks ingested by the pipeline inherit a kind label from the ingestion
step, but that label is sometimes wrong.  A code snippet labelled as prose,
a table labelled as code, or a link list labelled as config all degrade
downstream retrieval and quality scoring.  No tool existed to detect or
fix these mismatches at scale.

## Solution

A new tool `tools/corpus/reclassify.py` with three subcommands:

- `scan [--db PATH] [--status STATUS] [--source SOURCE_ID] [--json]`:
  scans chunks for kind mismatches using content heuristics and reports
  each mismatch with current and detected kinds.
- `apply [--db PATH] [--dry-run]`: applies reclassifications to the
  database, with a dry-run mode for previewing changes.
- `stats [--db PATH] [--json]`: reports current vs detected kind
  distributions, total mismatch count, mismatch rate, and a
  current-to-detected mismatch matrix.
- `selftest`: exercises 16 checks covering detection, scanning,
  application, stats, filtering, and edge cases.

### Detection heuristics

Content is classified into six kinds using regex patterns:

- **code**: import/def/class statements, control flow, brace-heavy lines
- **table**: pipe-delimited rows with separator lines
- **link**: lines dominated by URLs (>50% of non-empty lines)
- **config**: INI sections, key=value pairs, Kubernetes manifests
- **claim**: assertion words (must, should, always, never, etc.)
- **prose**: default when no other pattern dominates

Detection order matters: code is checked first (highest signal), then
table, link, config, claim, with prose as the fallback.  Link is checked
before config because URLs match the config key:value pattern.

### Design properties

- **Non-destructive by default**: scan and stats are read-only; apply
  defaults to dry-run mode.
- **Filterable**: scan accepts status and source_id filters for targeted
  reclassification.
- **Heuristic transparency**: the detection logic uses simple, auditable
  regex patterns rather than opaque models.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/reclassify.py`: new tool
- `docs/specs/2026-08-30-corpus-reclassify.md`: this spec

## Non-goals

- ML-based or embedding-based classification (future work).
- Automatic reclassification on ingestion.
- Cross-chunk context for kind detection.
