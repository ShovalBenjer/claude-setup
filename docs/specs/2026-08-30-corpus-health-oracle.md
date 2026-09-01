# Corpus Health Oracle

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/health.py

## Problem

The research corpus had individual tools for defect queries (uncited claims,
unresolved contradictions), embedding status, staleness distribution, and
artifact coverage, but no single command that aggregated them into a health
verdict. The section 4.4 defect queries existed in `research.py defects`
but produced no pass/fail exit code and did not integrate with embedding
freshness, staleness, or artifact signals. A caller wanting to know whether
the corpus was healthy had to run multiple tools and interpret each result
independently.

## Solution

A new tool `tools/corpus/health.py` with two subcommands:

- `check [--db PATH] [--json]`: runs the full health check and exits 0
  (HEALTHY) or 1 (DEFECTS). Produces a structured report covering all
  corpus health dimensions.
- `selftest`: exercises 18 checks covering uncited claims, unresolved
  contradictions, embedding status, staleness distribution, artifact
  coverage, chunk summary, and the pass/fail verdict logic.

### Health dimensions checked

1. **Uncited accepted claims** (section 4.4 query 1): accepted chunks
   with `kind='claim'` and no verified citation.
2. **Unresolved contradictions** (section 4.4 query 2): accepted chunks
   on a `contradicts` edge with no resolution.
3. **Embedding freshness**: generation counter match between corpus_meta
   and corpus-vec.json. Stale vectors are a defect.
4. **Staleness distribution**: sources grouped by liveness, with a count
   of sources whose upstream_mtime exceeds 18 months.
5. **Artifact implementation coverage**: total, implemented, and
   unimplemented artifact counts with implementation rate.
6. **Chunk status summary**: total chunks broken down by status
   (accepted/quarantined/superseded) and by kind.

### Verdict logic

The verdict is HEALTHY when all three defect conditions are clear:
- Zero uncited accepted claims
- Zero unresolved contradictions
- Embedding vectors current (or not_fitted, which is not a defect)

Any defect produces DEFECTS with exit code 1 and a list naming each
problem.

## Results

First run against the real corpus (366 sources, 5937 chunks):
- 0 uncited accepted claims
- 11 unresolved contradictions (genuine open edges)
- Embedding: current (1362 chunks, 256 components, generation 1)
- Sources: 366 total, all live
- Artifacts: 1602 total, 46 implemented (2.9%)
- Verdict: DEFECTS (11 unresolved contradictions)

The 11 contradictions are correct: they were detected by
`tools/corpus/contradict.py` and are awaiting operator resolution.

## Design decisions

- Not a gate domain: the corpus health check reports defects but is not
  wired into quality-contract.json as a blocking domain. The corpus has
  known unresolved contradictions that are operator decisions, not CI
  failures. Wiring it as a gate would require a baseline or waiver.
- Embedding not_fitted is not a defect: a corpus without vectors still
  works via FTS5-only retrieval. Only a stale generation mismatch (where
  vectors exist but are outdated) is flagged.
- JSON output for machine consumption: `--json` produces a structured
  report suitable for dashboards or downstream tools.

## Scope

- `tools/corpus/health.py`: new tool
- `docs/specs/2026-08-30-corpus-health-oracle.md`: this spec

## Non-goals

- Auto-resolving contradictions (detection is mechanical, adjudication
  is judgement).
- Blocking the gate on corpus health (operator decision).
- Replacing `research.py defects` (that remains for quick interactive
  use without the full aggregation).
