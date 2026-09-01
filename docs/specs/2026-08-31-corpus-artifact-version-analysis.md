# Corpus Artifact Version Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_version_analysis.py

## Problem

The artifacts table stores version (a version string for each
technology artifact) and snippet (a code excerpt showing usage).
Neither column had any analytical queries: version was never grouped
by or classified, and snippet was never measured for coverage or
length.  Understanding which artifact types carry version information,
what version formats are used, and how complete the snippet column is
required manual queries.

## Solution

A new tool `tools/corpus/artifact_version_analysis.py` with four
subcommands:

- `version-distribution [--db PATH] [--json]`: distribution of
  version format types (semver, calver, major-only, other, unset)
  across all artifacts.
- `snippet-coverage [--db PATH] [--json]`: snippet coverage per
  artifact type, showing how many artifacts have a snippet, the
  coverage rate, and mean and max snippet lengths.
- `per-type [--db PATH] [--json]`: version patterns per artifact
  type including population rate, distinct version count, and
  format breakdown.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total artifacts, version and snippet population rates, distinct
  versions, distinct names, version format distribution, and
  artifact type count.
- `selftest`: exercises 14 checks covering version format detection,
  unset detection, share summation, snippet coverage counts,
  zero-coverage types, per-type version counts, unpopulated types,
  summary totals, population rates, JSON serialisation, and empty
  corpus.

### Design properties

- **Version format classification**: regex-based classification into
  semver (e.g. 1.24.3), calver (e.g. 2024.1), major-only (e.g. 2),
  other, and unset, revealing versioning conventions across the
  corpus.
- **Snippet length analysis**: mean and max snippet length per
  artifact type shows whether snippets are terse references or
  substantive code examples.
- **Type-level granularity**: per-type breakdowns reveal which
  artifact types (library, api, command, etc.) carry version
  information versus which are version-agnostic.
- **All-artifact scope**: analyses all artifacts regardless of
  chunk or source status.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_version_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-version-analysis.md`: this spec

## See also

- [corpus-artifact-adoption](2026-08-31-corpus-artifact-adoption.md):
  analyses artifact implementation status and type distribution;
  this tool analyses version and snippet dimensions.
- [corpus-artifact-graph](2026-08-31-corpus-artifact-graph.md):
  maps artifact relationships across chunks; this tool analyses
  per-artifact metadata completeness.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; artifact version and snippet
  completeness are complementary quality signals.

## Non-goals

- Version comparison or upgrade recommendation.
- Snippet quality assessment or syntax validation.
- Automatic version resolution from package registries.
- Snippet deduplication or normalisation.
