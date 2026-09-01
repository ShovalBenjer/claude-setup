# Corpus Gap Analysis

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/gaps.py

## Problem

No tool reported what the corpus is missing.  The existing tools measure
what is in the corpus (summarize, coverage, quality) but none compare
the corpus against a reference set of expected topics to identify blind
spots or underrepresented areas.

## Solution

A new tool `tools/corpus/gaps.py` with three subcommands:

- `topics [--db PATH] [--min-chunks N] [--json]`: checks corpus coverage
  across 55 reference domains (sqlite, embedding, testing, security,
  kubernetes, etc.) and classifies each as strong, adequate, thin, or
  missing based on accepted chunk count.
- `terms [--db PATH] [--terms TERM,...] [--json]`: searches for specific
  user-provided terms and reports chunk counts, accepted counts, source
  counts, and coverage level.
- `uncovered-dirs [--db PATH] [--json]`: finds directories under the
  source trees (work-docs, research-papers, docs/analysis) that contain
  markdown files not yet indexed in the corpus.
- `selftest`: exercises 16 checks covering all three subcommands, edge
  cases, and JSON serialization.

### Design properties

- **Reference-based coverage**: compares against a curated domain list
  rather than relying solely on what is already indexed.
- **Actionable output**: each domain is labelled strong/adequate/thin/missing,
  directly guiding where to focus ingestion effort.
- **Custom term search**: the terms subcommand accepts arbitrary terms
  for ad-hoc coverage checks beyond the reference set.
- **Directory awareness**: uncovered-dirs finds on-disk markdown not
  yet in the corpus, complementing coverage.py's file-level check.

## Results

- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/gaps.py`: new tool
- `docs/specs/2026-08-30-corpus-gaps.md`: this spec

## Non-goals

- Automated ingestion of uncovered content.
- Topic modelling or unsupervised domain discovery.
- Cross-corpus gap comparison.
