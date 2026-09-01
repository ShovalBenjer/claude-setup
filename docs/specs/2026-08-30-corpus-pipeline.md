# Corpus Ingestion Pipeline

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/pipeline.py

## Problem

The research corpus had individual tools for each ingestion stage (stages
0-4 in research.py, stage 5 in contradict.py, stage 6 in artifacts.py,
step 5 in embed.py, health check in health.py), but no single command
that ran the full pipeline end-to-end. An operator wanting to bring the
corpus up to date had to know the correct stage order and run each tool
separately.

## Solution

A new tool `tools/corpus/pipeline.py` with two subcommands:

- `run [--db PATH] [--skip-embed] [--json]`: runs the full pipeline in
  the correct order and produces a structured report with per-stage
  timing, results, and a final health verdict.
- `selftest`: exercises 10 checks covering stage sequencing, idempotent
  re-runs, and report shape.

### Pipeline stages

1. **Ingest** (stages 0-4): normalize, chunk, dedup, citation gate via
   `research.py ingest`. Skips unchanged sources.
2. **Contradiction detection** (stage 5): numeric, negation, and
   recommendation detectors via `contradict.py detect`.
3. **Artifact extraction** (stage 6): library, command, and pattern
   extraction with disk evidence via `artifacts.py extract`.
4. **Embedding fit** (step 5): hashed char-ngram TF-IDF + PCA via
   `embed.py fit`. Skippable with `--skip-embed`.
5. **Health check**: aggregated defect queries and tool signals via
   `health.py check`.

### Design properties

- **Idempotent**: each stage skips work already done. Re-running the
  pipeline on an up-to-date corpus takes seconds.
- **Graceful degradation**: if numpy is not installed, the embedding
  stage reports the error and the pipeline continues.
- **Structured output**: `--json` produces a machine-readable report
  with per-stage timing, results, errors, and the health verdict.

## Results

First run against the real corpus (366 sources, 5937 chunks):
- Ingest: no-op (0.04s, already ingested)
- Contradiction detection: 11 recommendation conflicts, 0 new edges (47s)
- Artifact extraction: 1602 artifacts, 46 implemented (0.14s)
- Embedding fit: 1362 chunks, 256 components (3.3s)
- Health: DEFECTS (11 unresolved contradictions)
- Total: 50.6s

## Scope

- `tools/corpus/pipeline.py`: new tool
- `docs/specs/2026-08-30-corpus-pipeline.md`: this spec

## Non-goals

- Replacing individual stage tools (each remains independently usable).
- External source fetching (the pipeline operates on local files only).
- Auto-resolution of contradictions.
