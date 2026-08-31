# Corpus Edge Text Correlation

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_text_correlation.py

## Problem

word_count_distribution.py profiles chunk sizes in isolation.
edge_confidence_profile.py profiles confidence across edge types.
No tool correlates chunk text properties with claim edge patterns,
measuring whether longer or shorter chunks attract more edges,
higher confidence, or different edge types, and whether chunk kind
influences argumentative connectivity.

## Solution

A new tool `tools/corpus/edge_text_correlation.py` with four
subcommands:

- `by-wordcount [--db PATH] [--json]`: edge statistics bucketed
  by source-chunk word count band (0-25, 26-50, 51-100, 101-250,
  251-500, 501+), showing edge count, type breakdown, and
  confidence range per band.
- `by-kind [--db PATH] [--json]`: edge statistics per source-chunk
  kind, showing edge count, type breakdown, average confidence,
  and dominant edge type.
- `density [--db PATH] [--json]`: edge density (edges per chunk)
  bucketed by word count band, revealing which chunk sizes are
  most argumentatively active.
- `summary [--db PATH] [--json]`: aggregate statistics including
  highest/lowest density bands, highest confidence band, and
  overall edge density.
- `selftest`: exercises 14 checks covering per-band edge counts,
  confidence averages, per-kind counts, dominant types, density
  computation, summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Word count banding**: groups source chunks into six size bands
  to reveal how chunk length correlates with edge participation.
- **Edge density metric**: edges per chunk per band provides a
  normalized measure independent of band population size.
- **Kind-level profiling**: different chunk kinds may attract
  different edge types, and this tool surfaces those patterns.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/edge_text_correlation.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-text-correlation.md`: this spec

## See also

- word_count_distribution.py: profiles chunk sizes in isolation;
  this tool correlates sizes with edge patterns.
- edge_confidence_profile.py: profiles confidence by type; this
  tool profiles confidence by chunk text properties.
- source_edge_stance.py: profiles edge types per source; this tool
  profiles edge types per chunk property.

## Non-goals

- Readability score computation from raw text.
- Causal inference between chunk length and edge creation.
- Automatic chunk resizing for edge optimization.
- Natural language complexity metrics beyond word count.
