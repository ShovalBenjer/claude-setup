# Corpus Evidence Coverage

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/evidence_coverage.py

## Problem

The artifacts.evidence_path column had zero analytical queries
anywhere in the codebase.  Every reference was an INSERT column in
test fixtures or ingestion code.  No tool examined what fraction of
artifacts carry evidence paths, what file patterns those paths
follow, or how evidence coverage correlates with implementation
status.

## Solution

A new tool `tools/corpus/evidence_coverage.py` with four
subcommands:

- `coverage [--db PATH] [--json]`: evidence_path coverage per
  artifact type, showing total artifacts, count with evidence, and
  coverage rate.  Sorted by total descending.
- `by-type [--db PATH] [--json]`: evidence presence cross-tabulated
  by artifact type and implementation status, revealing whether
  implemented artifacts are more likely to carry evidence paths.
- `patterns [--db PATH] [--json]`: distribution of evidence_path
  file patterns (source-code, documentation, config, script,
  directory, bare-name, unset), classified by file extension.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total artifacts, coverage rate, implemented-with-evidence count,
  implemented-without-evidence count, unimplemented-with-evidence
  count, types with zero coverage, distinct paths, and pattern
  breakdown.
- `selftest`: exercises 14 checks covering coverage entries,
  library and API evidence counts, by-type entries, implemented
  library evidence, pattern entries, unset count, source-code
  pattern count, share summation, documentation pattern,
  summary totals, implementation-evidence cross counts, JSON
  serialisation, and empty corpus.

### Design properties

- **Extension-based classification**: evidence paths are classified
  by file extension into meaningful categories (source-code,
  documentation, config, script) rather than raw extension counts.
- **Implementation correlation**: the by-type subcommand reveals
  whether artifacts that claim implementation also carry evidence,
  surfacing potential data quality gaps.
- **Zero-coverage detection**: summary reports which artifact types
  have no evidence paths at all, identifying systematic gaps.
- **All-artifact scope**: analyses all artifacts regardless of chunk
  or source status.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/evidence_coverage.py`: new tool
- `docs/specs/2026-08-31-corpus-evidence-coverage.md`: this spec

## See also

- [corpus-artifact-adoption](2026-08-31-corpus-artifact-adoption.md):
  analyses artifact implementation status and type distribution;
  this tool adds the evidence_path dimension.
- [corpus-artifact-name-analysis](2026-08-31-corpus-artifact-name-analysis.md):
  analyses name frequency and multi-source overlap; this tool
  analyses evidence completeness.
- [corpus-artifact-version-analysis](2026-08-31-corpus-artifact-version-analysis.md):
  analyses version and snippet metadata; this tool analyses
  evidence_path metadata.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; evidence coverage is a
  complementary completeness signal.

## Non-goals

- Evidence path validation or file existence checking.
- Automatic evidence path population or inference.
- Evidence quality assessment or content analysis.
- Evidence path deduplication or normalisation.
