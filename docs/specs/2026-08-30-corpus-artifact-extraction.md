# Corpus Artifact Extraction

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/artifacts.py

## Problem

The `artifacts` table in `state/corpus.db` existed with a schema for
six artifact types (library, api, oneliner, config, command, pattern)
but held zero rows. Step 8 of the research corpus spec called for
populating it from accepted chunks, with `implemented=1` and a real
`evidence_path` for artifacts found on disk, `implemented=0` otherwise.
Without this, the corpus knows what text says about tools but not which
tools actually exist in this repository.

## Solution

A new tool `tools/corpus/artifacts.py` with three subcommands:

- `extract [--db PATH] [--repo PATH]`: scans accepted chunks through
  five extraction patterns, deduplicates by name, checks each artifact
  against the repository tree, writes rows to the `artifacts` table.
- `report [--db PATH]`: displays artifacts grouped by type with
  implementation status and evidence paths.
- `selftest`: exercises 9 checks covering each extractor, stdlib/noise
  filtering, DB writes, implementation detection, and idempotency.

### Five extraction patterns

1. **pip install**: matches `pip install <name>` with optional version.
2. **npm install**: matches `npm install <name>` with optional version.
3. **Python import**: matches `from X import` and `import X`, filters
   stdlib modules (70+ entries) and noise words.
4. **File paths**: matches slash-separated paths ending in code/config
   extensions, classifies by surrounding context.
5. **Backtick names**: matches backtick-wrapped identifiers with length
   >= 3, classifies as library when context suggests dependency usage.

### Disk search

Artifacts with file-like names are searched on disk via `rglob`,
skipping `.venv`, `node_modules`, `.git`, `__pycache__`, and other
build/cache directories. Generic basenames (`__init__.py`, `index.js`)
are not glob-searched to avoid false matches.

## Results

First run against the real corpus (5936 chunks from 365 sources):
- 2372 candidate mentions extracted
- 1602 unique artifact names after deduplication
- 46 found implemented on disk with evidence paths
- 1556 referenced but not present in this repository

## Design decisions

- One artifact row per unique name (case-insensitive), keeping the
  version from whichever mention had one. Multiple references to the
  same library produce one row, not one per chunk.
- Artifact IDs are deterministic (sha256 of name+type), so re-runs
  are idempotent via `INSERT OR IGNORE`.
- The tool does not auto-execute artifacts or verify they run. That
  is the cache2action path (spec step 10), a separate feature with
  its own trust model.

## Scope

- `tools/corpus/artifacts.py`: new tool
- `docs/specs/2026-08-30-corpus-artifact-extraction.md`: this spec

## Non-goals

- Executing extracted artifacts (cache2action, spec step 10).
- Version pinning or dependency resolution.
- Integration with the quality gate.
