# Corpus Version Tag Stability

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_tag_stability.py

## Problem

version_citation_drift.py checks citations against chunk_versions.
tag_citation_yield.py correlates tags with citation counts.
No tool joins chunk_versions with chunk_tags to detect tags that may
be stale because their parent chunk's content was revised after the
tag was assigned, leaving potentially inaccurate topic labels
undetected.

## Solution

A new tool `tools/corpus/version_tag_stability.py` with four
subcommands:

- `unstable [--db PATH] [--json]`: tag assignments whose parent chunk
  has a chunk_version with snapshot_utc after the tag's tagged_utc,
  with revision count and latest revision timestamp.
- `by-tag [--db PATH] [--json]`: per tag value statistics with total
  assignments, unstable count, and instability rate.
- `by-depth [--db PATH] [--json]`: unstable tags bucketed by revision
  depth of the parent chunk since tagging.
- `summary [--db PATH] [--json]`: aggregate statistics including
  instability rate, distinct tags, tagged chunks, revised tagged
  chunks, and most unstable tag.
- `selftest`: exercises 14 checks covering unstable detection,
  stable exclusion (revision before tagging, no revision), per-tag
  breakdown, depth bucketing, summary totals, JSON serialisation,
  and empty corpus.

### Design properties

- **Temporal join**: joins chunk_versions on chunk_tags via chunk_id,
  comparing snapshot_utc against tagged_utc to identify
  post-tagging content changes.
- **Tag-level granularity**: tracks instability per tag assignment
  rather than per chunk, since a chunk with multiple tags may have
  some stable and some unstable assignments depending on tagging time.
- **Instability rate**: measures the fraction of tag assignments
  affected by subsequent content revisions, surfacing which tags
  are most likely to need re-evaluation.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_tag_stability.py`: new tool
- `docs/specs/2026-08-31-corpus-version-tag-stability.md`: this spec

## See also

- [corpus-version-citation-drift](2026-08-31-corpus-version-citation-drift.md):
  checks citations against chunk_versions; this tool checks tags
  against chunk_versions.
- [corpus-version-edge-impact](2026-08-31-corpus-version-edge-impact.md):
  checks claim_edges against chunk_versions; this tool checks tags
  against chunk_versions.

## Non-goals

- Automatic tag re-evaluation or reassignment.
- Tag content similarity comparison before and after revision.
- Tag score adjustment based on revision count.
- Cross-tag co-occurrence stability analysis.
