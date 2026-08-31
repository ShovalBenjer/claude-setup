# Corpus Artifact Version Conflicts

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_version_conflicts.py

## Problem

No tool detects when a claim_edge links two chunks that reference the
same artifact name with different versions.  artifact_graph.py finds
co-occurrence relationships between artifacts but never inspects
whether linked artifacts share a name with differing versions.
artifact_edge_profile.py cross-tabulates artifact_type against
edge_type but never checks name/version matches.  A contradicts edge
between chunks referencing torch 1.0 and torch 2.0 is a version
conflict signal that no existing tool surfaces.

## Solution

A new tool `tools/corpus/artifact_version_conflicts.py` with four
subcommands:

- `conflicts [--db PATH] [--json]`: edges where both endpoints
  reference the same artifact name with different non-null versions,
  with a flag indicating contradiction edges.
- `by-artifact [--db PATH] [--json]`: conflict counts per artifact
  name with contradiction count, distinct version count, and version
  list.
- `all-version-edges [--db PATH] [--json]`: all edges between chunks
  sharing an artifact name regardless of version match, with a
  same_version flag for comparison.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total same-name edges, conflict count and rate, contradiction
  conflicts, artifacts with conflicts, and the artifact with the
  most versions.
- `selftest`: exercises 14 checks covering conflict detection,
  contradiction flagging, same-version exclusion, different-name
  exclusion, null-version exclusion, per-artifact aggregation,
  version set correctness, same-version edge inclusion, summary
  totals, conflict rate, JSON serialisation, and empty corpus.

### Design properties

- **Four-way join**: joins claim_edges to artifacts twice (once per
  endpoint) via chunk_id, then filters on matching names with
  differing versions.
- **Null-version safety**: excludes artifacts without versions from
  conflict detection, since a null version cannot be meaningfully
  compared.
- **Contradiction highlighting**: specifically flags contradicts
  edges among version conflicts, since those represent the strongest
  version disagreement signal.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_version_conflicts.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-version-conflicts.md`:
  this spec

## See also

- [corpus-artifact-edge-profile](2026-08-31-corpus-artifact-edge-profile.md):
  cross-tabulates artifact_type against edge_type; this tool matches
  artifact names across edge endpoints for version conflicts.
- [corpus-artifact-name-analysis](2026-08-31-corpus-artifact-name-analysis.md):
  analyses artifact name frequency and multi-source overlap; this
  tool focuses on version disagreements between edge-linked chunks.

## Non-goals

- Automatic version conflict resolution or upgrade recommendation.
- Semantic version comparison or compatibility analysis.
- Version deprecation detection or lifecycle tracking.
- Artifact dependency graph construction.
