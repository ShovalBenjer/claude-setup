# Corpus Health Scorecard

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/health_scorecard.py

## Problem

Each corpus signal table (chunks, citations, claim_edges, chunk_tags,
chunk_versions, chunk_domains, artifacts) has its own analysis tool, but
no tool combined these signals into a single quality summary.  Answering
"how healthy is the corpus?" required running multiple tools and mentally
aggregating their outputs.

## Solution

A new tool `tools/corpus/health_scorecard.py` with two subcommands:

- `report [--db PATH] [--json]`: unified health report with an overall
  score, source and chunk totals, and a per-dimension breakdown.  The
  text output includes an ASCII bar chart for each dimension.  The
  overall score is the arithmetic mean of all dimension scores.
- `dimensions [--db PATH] [--json]`: individual dimension scores with
  detail strings, without the overall summary.
- `selftest`: exercises 14 checks covering report structure, acceptance
  rate, citation verification rate, edge resolution rate, tag
  confidence, artifact adoption rate, domain coverage, version tracking
  coverage, overall score computation, dimension count, required keys,
  detail strings, JSON serialisation, and empty corpus.

Seven dimensions are scored:

1. **acceptance**: fraction of chunks with status "accepted".
2. **citation_verification**: fraction of citations marked verified.
3. **edge_resolution**: fraction of claim edges with a non-null
   resolution.
4. **tag_confidence**: average score across all chunk_tags entries.
5. **artifact_adoption**: fraction of artifacts marked implemented.
6. **domain_coverage**: fraction of chunks with at least one
   chunk_domains entry.
7. **version_tracking**: fraction of chunks with at least one
   chunk_versions entry.

### Design properties

- **Single number**: the overall score gives one metric for corpus
  quality at a glance.
- **Dimensional breakdown**: each dimension is independently scored,
  enabling targeted improvement.
- **Graceful degradation**: dimensions that depend on optional tables
  (chunk_tags, chunk_domains, chunk_versions) return 0 when the table
  is absent rather than failing.
- **ASCII visualisation**: the text report renders a 20-character bar
  per dimension, readable in any terminal.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/health_scorecard.py`: new tool
- `docs/specs/2026-08-31-corpus-health-scorecard.md`: this spec

## See also

- [corpus-similarity-analysis](2026-08-31-corpus-similarity-analysis.md):
  analyses chunk relatedness patterns; this tool aggregates all signal
  tables into a quality summary.
- [corpus-audit](2026-08-31-corpus-audit.md): the audit tool checks
  for specific quality problems; this tool provides quantitative
  dimension scores.

## Non-goals

- Threshold-based alerting or pass/fail verdicts.
- Dimension weighting or configurable scoring.
- Historical score tracking or trend analysis.
- Automated remediation of low-scoring dimensions.
