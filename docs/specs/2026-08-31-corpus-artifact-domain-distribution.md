# Corpus Artifact Domain Distribution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_domain_distribution.py

## Problem

artifact_citation_provenance.py checks citation backing on artifacts.
evidence_chain_audit.py audits the full provenance chain through
artifacts. No tool joins artifacts with chunk_domains to show which
knowledge domains contain which artifact types, or which domains
are richest in actionable artifacts versus which have no artifacts
at all.

## Solution

A new tool `tools/corpus/artifact_domain_distribution.py` with four
subcommands:

- `by-domain [--db PATH] [--json]`: per domain artifact counts with
  chunk count, implemented count, and average domain score.
- `by-type [--db PATH] [--json]`: per artifact type statistics with
  domain count, artifact count, and implemented count.
- `cross [--db PATH] [--json]`: full domain by artifact_type
  cross-tabulation with counts and implemented counts.
- `summary [--db PATH] [--json]`: aggregate statistics including
  classified/unclassified artifact counts, classification rate,
  domains with artifacts, and richest/sparsest domains.
- `selftest`: exercises 14 checks covering per-domain counts,
  implemented filtering, per-type domain span, cross-tabulation,
  unclassified artifact detection, summary totals, JSON
  serialisation, and empty corpus.

### Design properties

- **Artifact-domain join**: joins artifacts with chunk_domains via
  chunk_id, mapping each artifact to its parent chunk's domain
  classifications.
- **Classification gap detection**: identifies artifacts on chunks
  that have no domain classification, surfacing unclassified content
  that may need domain assignment.
- **Cross-tabulation**: provides a full domain by artifact_type matrix,
  enabling analysis of which domains contain which types of actionable
  content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_domain_distribution.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-domain-distribution.md`: this spec

## See also

- [corpus-evidence-chain-audit](2026-08-31-corpus-evidence-chain-audit.md):
  audits provenance chains through artifacts; this tool maps artifacts
  to their domain classification.
- [corpus-classification-timeline](2026-08-31-corpus-classification-timeline.md):
  analyses chunk_domains temporal distribution; this tool analyses
  artifact content within those domains.

## Non-goals

- Artifact quality scoring by domain.
- Domain-based artifact recommendation.
- Artifact deduplication across domains.
- Domain hierarchy or taxonomy analysis.
