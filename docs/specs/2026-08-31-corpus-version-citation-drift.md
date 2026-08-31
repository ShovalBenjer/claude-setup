# Corpus Version Citation Drift

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_citation_drift.py

## Problem

version_edge_impact.py checks claim_edges against chunk_versions.
edge_citation_quality.py checks citation quality on claim_edges.
No tool joins chunk_versions with citations to detect citations whose
parent chunk content was revised after the citation was last verified,
leaving potentially stale verification results undetected.

## Solution

A new tool `tools/corpus/version_citation_drift.py` with four
subcommands:

- `drifted [--db PATH] [--json]`: verified citations whose parent
  chunk has a chunk_version with snapshot_utc after the citation's
  verified_utc, with revision count and latest revision timestamp.
- `by-tag [--db PATH] [--json]`: per citation tag statistics with
  total verified, drifted count, and drift rate.
- `by-depth [--db PATH] [--json]`: drifted citations bucketed by
  revision depth of the parent chunk since verification.
- `summary [--db PATH] [--json]`: aggregate statistics including
  drift rate, most drifted tag, chunks with verified citations, and
  chunks revised after verification.
- `selftest`: exercises 14 checks covering drifted detection,
  non-drifted exclusion (revision before verification, unverified),
  revision count, per-tag breakdown, depth bucketing, summary totals,
  JSON serialisation, and empty corpus.

### Design properties

- **Temporal join**: joins chunk_versions on citations via chunk_id,
  comparing snapshot_utc against verified_utc to identify
  post-verification content changes.
- **Verification-aware**: only considers verified citations with a
  recorded verified_utc, ignoring unverified citations that have no
  temporal anchor.
- **Tag stratification**: breaks down drift by citation tag, surfacing
  which citation categories (url, doi, isbn) are most affected by
  content revisions.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_citation_drift.py`: new tool
- `docs/specs/2026-08-31-corpus-version-citation-drift.md`: this spec

## See also

- [corpus-version-edge-impact](2026-08-31-corpus-version-edge-impact.md):
  checks claim_edges against chunk_versions; this tool checks citations
  against chunk_versions.
- [corpus-evidence-chain-audit](2026-08-31-corpus-evidence-chain-audit.md):
  audits provenance chains; this tool audits temporal validity of
  citation verification relative to chunk revisions.

## Non-goals

- Automatic re-verification of drifted citations.
- Citation content comparison before and after revision.
- Drift severity scoring beyond revision count.
- Cross-citation dependency analysis.
