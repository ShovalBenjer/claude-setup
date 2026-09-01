# Corpus Evidence Chain Audit

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/evidence_chain_audit.py

## Problem

edge_citation_quality.py checks citation quality on claim_edges.
artifact_citation_provenance.py checks citation backing on artifacts.
Neither audits the full chain from source through chunk to both
citations and artifacts in a single pass.  Understanding which chunks
lack any external evidence (no citations AND no artifact evidence_path)
required separate queries against each table.

## Solution

A new tool `tools/corpus/evidence_chain_audit.py` with four
subcommands:

- `unattested [--db PATH] [--json]`: chunks with zero citations AND
  zero artifact evidence_paths, joined to source metadata.
- `by-source [--db PATH] [--json]`: per-source statistics with total
  chunks, total citations, evidenced artifact count, and citations per
  chunk rate.
- `by-kind [--db PATH] [--json]`: per chunk kind statistics with
  citation count, verified citation count, evidenced artifact count,
  and citation rate.
- `summary [--db PATH] [--json]`: aggregate statistics including
  unattested chunk count and rate, verification rate, evidence rate,
  and weakest/strongest chunk kind by citation rate.
- `selftest`: exercises 14 checks covering unattested detection,
  citation exclusion, evidenced artifact exclusion, per-source counts,
  per-kind counts, summary totals, rates, JSON serialisation, and
  empty corpus.

### Design properties

- **Four-way join**: joins sources, chunks, citations, and artifacts
  in a single pass to identify provenance gaps.
- **Evidence threshold**: a chunk is "attested" if it has at least one
  citation OR at least one artifact with a non-null evidence_path,
  reflecting two independent forms of external backing.
- **Kind stratification**: breaks down evidence coverage by chunk kind,
  surfacing which content types (claim, code, table, config, link,
  prose) have the weakest provenance chains.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/evidence_chain_audit.py`: new tool
- `docs/specs/2026-08-31-corpus-evidence-chain-audit.md`: this spec

## See also

- [corpus-edge-citation-quality](2026-08-31-corpus-edge-citation-quality.md):
  checks citation quality on claim_edges; this tool checks citation and
  artifact evidence on chunks directly.
- [corpus-artifact-citation-provenance](2026-08-31-corpus-artifact-citation-provenance.md):
  checks citation backing on artifacts; this tool audits the full chain
  from source through chunk to both citations and artifacts.

## Non-goals

- Automatic evidence remediation or citation insertion.
- Evidence quality scoring beyond verified/unverified.
- Cross-source evidence chain comparison.
- Evidence freshness or staleness detection.
