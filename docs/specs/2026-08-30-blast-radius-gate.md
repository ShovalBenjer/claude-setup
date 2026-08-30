# Blast-Radius Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** blast_radius

## Problem

When a PR changes a Python file, reviewers have no automatic signal about how
many other modules are transitively affected. A change to a widely-imported
utility has a much larger blast radius than a change to a leaf script, and the
review fabric should know the difference.

## Solution

A new gate domain `blast_radius` builds the intra-repo Python import graph
using `tools/graph/blast_radius.py` (AST-based, no external deps) and reports,
for every changed `.py` file, how many modules import it transitively. The
domain is informational: it always passes, but flags files whose blast radius
is three or more importers so downstream review tooling can widen the reviewer
set.

The import graph resolves both dotted-path imports (`from tools.lib.tracing
import ...`) and bare-name imports produced by `sys.path.insert` patterns
(`import tracing`), using a basename lookup with same-directory preference for
disambiguation.

## Schema

```json
{
  "blast_radius": {
    "required": true,
    "builtin": "blast_radius",
    "_note": "Computes the transitive Python import blast radius of changed files."
  }
}
```

The builtin accepts an optional `base` key in the spec to override the
comparison branch (defaults to the repo's default remote branch).

## Scope

- `tools/graph/blast_radius.py`: graph builder with `build()`, `reverse_deps()`,
  `selftest()`, and CLI
- `tools/gate/gate.py`: `blast_radius` builtin function, registered in `BUILTINS`
- `quality-contract.json`: `blast_radius` domain entry

## Non-goals

- Blocking on wide blast radius (the domain is informational, always PASS)
- Cross-language import graphs (Python only)
- Resolving dynamic imports or `importlib` usage
