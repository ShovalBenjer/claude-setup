# Corpus Audit

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/corpus_audit.py

## Problem

Individual corpus tools report signals in isolation: the dashboard counts
orphans, the tag store shows scores, the claim network finds
contradictions.  No tool cross-referenced these signals to surface
actionable issues, such as contradictions between chunks that a
clustering algorithm placed in the same group, or sources where most
chunks have been superseded.

## Solution

A new tool `tools/corpus/corpus_audit.py` with six subcommands:

- `contradictions [--db PATH] [--json]`: finds unresolved contradictions
  where both chunks share a cluster label.  These are the highest
  priority disputes because the clustering algorithm judged the chunks
  topically related yet their claims conflict.
- `citations [--db PATH] [--json]`: finds unverified citations on
  accepted chunks.  These are claims the corpus treats as valid but
  whose evidence has not been checked.
- `weak-tags [--db PATH] [--threshold F] [--json]`: finds tags assigned
  with confidence below threshold (default 0.5).  Low-confidence tags
  may be noise from the auto-tagger.
- `orphans [--db PATH] [--json]`: finds accepted chunks with no edges,
  citations, tags, or topic assignment.  These chunks are invisible to
  every analytical tool.
- `stale-sources [--db PATH] [--threshold F] [--json]`: finds sources
  where more than threshold fraction of chunks are superseded (default
  0.5).  These sources may need re-ingestion or retirement.
- `full [--db PATH] [--json]`: runs all five checks and combines results
  into one report.
- `selftest`: exercises 14 checks covering intra-cluster contradiction
  detection, resolved-edge exclusion, cross-cluster exclusion, unverified
  citation filtering, weak-tag thresholding, orphan detection, stale
  source detection, full audit composition, JSON serialisation, and empty
  corpus handling.

### Design properties

- **Cross-signal**: each check combines data from at least two tables,
  surfacing issues no single-table query can find.
- **Resolution aware**: contradiction check excludes resolved edges.
- **Missing-table resilient**: each check returns empty when its tables
  have not been created yet.
- **Threshold tunable**: weak-tag and stale-source thresholds are CLI
  arguments with sensible defaults.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/corpus_audit.py`: new tool
- `docs/specs/2026-08-31-corpus-audit.md`: this spec

## See also

- [corpus-chunk-profile](2026-08-31-corpus-chunk-profile.md): drills
  into individual chunks; this tool identifies which chunks need
  attention.
- [corpus-dashboard](2026-08-31-corpus-dashboard.md): reports aggregate
  metrics including orphan counts; this tool identifies specific
  orphan chunks and cross-references additional signals.
- [corpus-claim-network](2026-08-31-corpus-claim-network.md): analyses
  contradiction clusters by network structure; this tool finds
  contradictions within topical clusters.
- [corpus-edge-resolution](2026-08-31-corpus-edge-resolution.md):
  analyses resolution patterns across all edge types; this tool
  identifies specific unresolved contradictions worth resolving.

## Non-goals

- Automated resolution or remediation of detected issues.
- Severity scoring or prioritisation beyond confidence ordering.
- Historical audit comparison or trend tracking.
- Cross-corpus audit.
