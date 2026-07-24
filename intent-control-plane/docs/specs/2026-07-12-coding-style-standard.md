---
prd: intent-control-plane
ticket: none (internal platform brain)
status: active
---

# Coding style standard

The house style for this package, and the rubric the craft-critic and human review score against.
Governs the auto-go burn-down. Companion to the audit fix backlog
(`docs/analysis/2026-07-12-implementation-audit.md`) and the effort/craft research
(`~/docs/coding-effort-craft-completion-2026-07.md`).

## The three rules

1. **Docstrings mandatory and load-bearing.** Every module, class, public function, and helper
   carries a docstring. The module docstring states: purpose, the files it connects to, and the
   PRD/feature item it serves. A function docstring states what it returns and the non-obvious why
   (invariants, fail-closed behavior, cost/latency contract), not a restatement of the signature.
2. **Minimal LOC, compact, idiomatic.** One clear way. Comprehensions/generators over accumulator
   loops. No scaffolds (a public symbol with zero live callers is deleted or wired). No speculative
   abstraction. Reuse before add.
3. **Comments: near-zero.** Names + docstrings carry meaning; a comment that restates code is
   deleted, and a comment explaining a block means the block should be an extracted, named,
   docstring'd function. The only inline comments that survive: (a) a `# noqa: RULE - reason`
   directive ruff itself needs, and (b) an external citation grounding a constant or design choice
   (an arXiv id, a rule-file link). Nothing else.

## Mechanical enforcement (what the gate blocks)

| Rule | Enforced by | State |
|---|---|---|
| Idiomatic, no accumulator loops | ruff `PERF401`, `C4`, `SIM`, `PIE` | on |
| No dead / commented-out code | ruff `ERA` | on (2026-07-12) |
| No unwired public scaffold | `done_gate.unwired_public_symbols` + vulture | on |
| Typed DTOs, no `dict[str, Any]` at seams | mypy `--strict` (+ TypedDict migration) | in progress |
| Docstring on every module/class/public def | ruff `D100`,`D101`,`D102`,`D103`,`D107` | pending: flip on after the 76-docstring batch |
| Comment near-zero (prose comments) | craft-critic + human review | judge, not lint |

## Measured gap at adoption (2026-07-12)

- 76 undocumented public defs (67 functions, 5 methods, 3 inits, 1 module) -> the docstring batch.
- 51 non-directive inline comments in `src` -> the comment sweep (keep only noqa-reasons + citations).
- `ERA`: 0 (no commented-out code already; the gate locks that).

## Sequence

1. Enable `ERA` now (0 violations, locks the state). Done.
2. Burn-down batch 1: add the 76 docstrings + sweep the 51 comments to the rule-3 survivors.
3. Flip the `D100-D107` subset on (with `pydocstyle` convention set to avoid D203/D213 conflict);
   the gate now blocks any undocumented public def.
4. The craft-critic scores comment-density and docstring-substance (not just presence) as part of
   the >= B craft gate.
