# Corpus Artifact Adoption

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_adoption.py

## Problem

The artifacts table records technology references (libraries, APIs,
commands, patterns, configs) extracted from chunks, with an
`implemented` flag indicating whether the reference includes working
evidence.  No tool analysed these artifacts at scale: finding which
technologies are referenced but unimplemented, which sources carry the
most artifact density, or which artifacts sit on quarantined or
rejected chunks required manual queries.

## Solution

A new tool `tools/corpus/artifact_adoption.py` with four subcommands:

- `summary [--db PATH] [--json]`: corpus-wide artifact adoption
  statistics.  Reports total, implemented, unimplemented counts,
  overall adoption rate, and per-type breakdown (library, api,
  command, pattern, config, oneliner).
- `unimplemented [--db PATH] [--limit N] [--json]`: artifacts marked
  as not implemented, with their parent chunk context (source, heading,
  kind).  Ordered by type then name for review grouping.
- `by-source [--db PATH] [--json]`: artifact counts per source,
  showing technology density, implementation count, type variety, and
  per-source adoption rate.  Ordered by artifact count descending.
- `orphans [--db PATH] [--json]`: artifacts whose parent chunk has
  been quarantined or rejected.  These are technology references that
  may need re-evaluation or removal.
- `selftest`: exercises 14 checks covering summary totals, adoption
  rate, per-type breakdown, unimplemented listing, implemented
  exclusion, chunk context, limit parameter, by-source counts, source
  ordering, type variety, orphan detection, accepted exclusion from
  orphans, JSON serialisation, and empty corpus.

### Design properties

- **Per-type granularity**: adoption rates per artifact type reveal
  which categories (libraries vs commands vs patterns) have the
  weakest implementation evidence.
- **Source-level density**: ranks sources by how many technology
  references they contribute, showing which papers or documents are
  most technology-rich.
- **Orphan detection**: artifacts on quarantined or rejected chunks
  surface technology references that may be unreliable.
- **Graceful degradation**: returns empty results when the artifacts
  table does not exist or is empty.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_adoption.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-adoption.md`: this spec

## See also

- [corpus-chunk-evolution](2026-08-31-corpus-chunk-evolution.md):
  analyses content change patterns; this tool analyses technology
  reference patterns.
- [corpus-chunk-profile](2026-08-31-corpus-chunk-profile.md):
  includes artifact data in chunk dossiers; this tool aggregates
  adoption across the corpus.
- [corpus-audit](2026-08-31-corpus-audit.md): detects cross-signal
  issues; orphan artifacts are a related integrity concern.

## Non-goals

- Automated artifact extraction from chunk text.
- Version comparison or upgrade recommendation.
- Cross-corpus artifact matching.
- Artifact dependency graph construction.
