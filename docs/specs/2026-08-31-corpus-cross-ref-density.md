# Corpus Cross-Reference Density

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/cross_ref_density.py

## Problem

The citation analysis and source citation net tools measure citation
counts and source-to-source links, but neither distinguished internal
citations (within the same source) from external ones (across sources).
A document that only cites itself is self-contained but insular; one
that cites many external sources is outward-linking but potentially
less cohesive.  Quantifying this split required manually filtering
citation targets against source URIs.

## Solution

A new tool `tools/corpus/cross_ref_density.py` with three subcommands:

- `density [--db PATH] [--json]`: per-source internal vs external
  citation counts.  For each source, counts citations whose target
  matches the source's own source_id or canonical_uri (internal) versus
  all others (external).  Reports internal and external rates per chunk,
  plus an insularity score (internal/total).  Sorted by total citations
  descending.
- `insular [--db PATH] [--threshold F] [--json]`: sources whose
  insularity exceeds the threshold (default 0.7).  These are highly
  self-referencing documents.  Sorted by insularity descending.
- `summary [--db PATH] [--json]`: aggregate cross-reference statistics
  including total internal and external citations, overall insularity,
  mean internal and external rates, and counts of highly insular
  (insularity > 0.7) and highly outward (insularity < 0.3) sources.
- `selftest`: exercises 14 checks covering density enumeration,
  internal/external split accuracy, total citation counts, insularity
  computation, zero-insularity sources, sort order, threshold
  filtering, threshold sensitivity, summary structure, citation
  totals, insularity bounds, rate positivity, JSON serialisation,
  and empty corpus.

### Design properties

- **URI-aware matching**: internal citations are detected by both
  target_source_id and canonical_uri match, handling citations that
  reference the source by URI rather than ID.
- **Per-chunk normalisation**: internal and external rates are
  normalised by chunk count, enabling comparison across sources of
  different sizes.
- **Insularity metric**: a single 0-to-1 score summarising how
  self-contained a source's citations are.
- **Accepted-only scope**: joins through accepted chunks, excluding
  quarantined or rejected content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/cross_ref_density.py`: new tool
- `docs/specs/2026-08-31-corpus-cross-ref-density.md`: this spec

## See also

- [corpus-citation-analysis](2026-08-31-corpus-citation-analysis.md):
  analyses citation patterns at the chunk level; this tool measures
  the internal/external split at the source level.
- [corpus-source-citation-net](2026-08-31-corpus-source-citation-net.md):
  analyses source-to-source citation links; this tool analyses the
  direction of those links relative to the citing source.
- [corpus-citation-age](2026-08-31-corpus-citation-age.md):
  analyses citation verification freshness; this tool analyses
  citation target distribution.
- [corpus-source-provenance](2026-08-31-corpus-source-provenance.md):
  analyses source metadata completeness; this tool analyses source
  citation self-referencing patterns.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus health metrics; insularity is a complementary
  quality signal.

## Non-goals

- Citation target resolution or link checking.
- Cross-corpus citation comparison.
- Citation weighting by confidence or recency.
- Automatic insularity remediation or recommendation.
