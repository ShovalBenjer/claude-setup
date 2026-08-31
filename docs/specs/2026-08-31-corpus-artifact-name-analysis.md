# Corpus Artifact Name Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_name_analysis.py

## Problem

The artifacts.name column had zero GROUP BY queries anywhere in the
codebase.  artifact_graph.py uses name only for labeling graph edges
and artifact_adoption.py groups by artifact_type but never by name.
No tool revealed which named artifacts appear most frequently, which
span multiple sources, or how implementation rates vary by name.

## Solution

A new tool `tools/corpus/artifact_name_analysis.py` with four
subcommands:

- `frequency [--db PATH] [--json]`: artifact name frequency
  distribution, most common first, with count and share per
  name-type pair.
- `multi-source [--db PATH] [--json]`: artifacts that appear across
  multiple sources, sorted by source count descending, revealing
  which libraries, APIs, or patterns are referenced corpus-wide.
- `implementation [--db PATH] [--json]`: implementation rate per
  artifact name showing implemented count, total, and rate, sorted
  by total descending.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total artifacts, distinct names, distinct name-type pairs,
  multi-source name count, implementation count and rate, and top
  five names by frequency.
- `selftest`: exercises 14 checks covering frequency entries, React
  count, share summation, multi-source entries, multi-source React,
  single-source Flask exclusion, implementation entries, React
  implementation count, Observer zero rate, Flask full rate, summary
  totals, multi-source and impl counts, JSON serialisation, and
  empty corpus.

### Design properties

- **Name-type pairing**: frequency and implementation group by both
  name and artifact_type, distinguishing a library named X from an
  API named X.
- **Multi-source detection**: the multi-source subcommand joins
  through chunks to sources, identifying artifacts referenced across
  independent documents rather than repeated within one.
- **Implementation correlation**: per-name implementation rates
  reveal which named artifacts are adopted versus merely mentioned.
- **All-artifact scope**: analyses all artifacts regardless of chunk
  or source status.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_name_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-name-analysis.md`: this spec

## See also

- [corpus-artifact-adoption](2026-08-31-corpus-artifact-adoption.md):
  analyses artifact implementation status and type distribution;
  this tool adds the name dimension.
- [corpus-artifact-version-analysis](2026-08-31-corpus-artifact-version-analysis.md):
  analyses version and snippet metadata; this tool analyses name
  frequency and cross-source overlap.
- [corpus-artifact-graph](2026-08-31-corpus-artifact-graph.md):
  maps artifact relationships across chunks; this tool analyses
  per-name statistics.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; artifact name coverage is a
  complementary completeness signal.

## Non-goals

- Artifact name normalisation or deduplication.
- Name resolution against external package registries.
- Automatic artifact linking across name variants.
- Artifact dependency graph construction.
