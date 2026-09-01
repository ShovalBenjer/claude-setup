# Corpus Topic Coherence

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/topic_coherence.py

## Problem

The NMF topic model (`tools/corpus/topic_model.py`) discovers latent
topics but provides no measure of topic quality.  Without a coherence
metric, there is no objective way to tell whether a topic's top terms
form a semantically meaningful cluster or are an artifact of the matrix
decomposition.  Choosing the right number of topics requires trial and
error with no quantitative signal.

## Solution

A new tool `tools/corpus/topic_coherence.py` that computes Normalized
Pointwise Mutual Information (NPMI) for each topic's top terms,
evaluated against their co-occurrence in the actual corpus.

### Tool commands

- `score [--db PATH] [--json]`: computes NPMI coherence for every
  fitted topic.  Returns topic label, NPMI score, size, and top terms.
  NPMI ranges from -1 (terms never co-occur) to +1 (terms always
  co-occur).
- `rank [--db PATH] [--json]`: ranks topics by coherence, best first,
  with sequential rank numbers.
- `suggest [--db PATH] [--json]`: heuristic recommendation on whether
  to increase, decrease, or keep the current n_topics.  Based on the
  proportion of topics with negative vs. strongly positive NPMI.
- `selftest`: exercises 14 checks.

### NPMI computation

For each pair of top terms (t_i, t_j) in a topic:

1. Count document frequency of each term and their co-occurrence
   within a sliding window of 10 words.
2. Compute PMI = log(P(t_i, t_j) / (P(t_i) * P(t_j))).
3. Normalize: NPMI = PMI / (-log(P(t_i, t_j))).
4. Average across all term pairs in the topic.

NPMI is preferred over raw PMI because it is bounded [-1, 1] and
comparable across topics with different term frequencies.

### n_topics suggestion heuristic

- **decrease**: if more than half the topics have negative NPMI, the
  model is over-specified (too many topics splitting coherent groups).
- **increase**: if all topics have NPMI above 0.1, the model may be
  under-specified (too few topics merging distinct areas).
- **keep**: otherwise, the current topic count is adequate.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/topic_coherence.py`: new tool
- `docs/specs/2026-08-31-corpus-topic-coherence.md`: this spec

## See also

- [corpus-topic-model](2026-08-31-corpus-topic-model.md): the NMF
  topic model whose quality this tool measures.

## Non-goals

- Automatic n_topics optimization (the tool suggests, the operator
  decides).
- Alternative coherence metrics (C_V, UMass) beyond NPMI.
- Per-chunk coherence contribution scoring.
