---
paths:
  - "**/*.py"
  - "**/*.ipynb"
---

# Numerical and tabular stack

Polars for tabular work, Numba for hot numerical loops, NumPy for linear algebra.
The choice is per layer, not per project, and each layer has a different default.

## Tabular: Polars, never pandas

Loading, filtering, joining, grouping, and aggregating rows is Polars. Use
`LazyFrame` above ~100k rows and let the query planner push predicates down.
DuckDB for anything that wants SQL or spans files larger than memory.

**This includes statistics over a column.** Pulling rows into Python lists and
calling `statistics.median` is the same anti-pattern as `pandas.apply`: it is a
per-row interpreter loop where a vectorised expression exists.

## Hot numerical loops: Numba

A Python loop that runs per element over a large collection gets `@njit`, or is
rewritten as an array expression. Character n-gram counting, per-row distance
work, and simulation inner loops are the usual candidates.

Do not reach for it first. Vectorise, measure, and only then compile: an
`@njit` that is not the bottleneck is compile latency and a debugging tax for
nothing.

## Linear algebra: NumPy

Dense matrix products, decompositions (`eigh`, `svd`, `qr`), and BLAS-backed
reductions stay in NumPy. Polars is a DataFrame library and does not replace
this, and "use Polars" is the wrong instruction for an eigendecomposition.

Correct division of labour, all three in one pipeline:

- read and aggregate the corpus with Polars
- compile the per-token counting loop with Numba
- take the covariance and its eigenvectors with NumPy

## Why this rule exists here and not only in a skill

The preference was already written down in `dot-agents/skills/notebook`,
`dot-agents/skills/review`, and the `data-bureau` / `evidence-clerk` /
`latent-systems-lab` agent definitions. All of those load only when that skill
or agent is invoked, so a general session building numerical code never saw it
and defaulted to NumPy plus `statistics` for everything. A standing preference
has to live in a standing rule.
