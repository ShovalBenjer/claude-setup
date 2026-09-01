# Stack-lint oracle

Status: active
Filed: 2026-08-30
Source: TODO.md (filed 2026-07-29), code-quality-rethink spec action 2

## Problem

Nothing enforces the coding-style standard on `tools/`. The intent-control-plane
subproject adopted ruff (PERF/C4/SIM/PIE + E/F/I/UP/B) in its pyproject.toml, but
the root repo never adopted that config, so `tools/` has no mechanical lint check
and style violations accumulate silently.

## Solution

1. Create `ruff.toml` at repo root with the core ruleset (C4, PERF, PIE, I) scoped
   to `tools/`.
2. Fix all existing violations for those rules.
3. Wire a `lint` gate domain that runs `ruff check` and fails the gate on violations.
4. Future PRs expand the ruleset (SIM, B, ERA, UP, full E/F) after batch-fixing
   violations for each rule group.

## Scope

Phase 1 (this change): C4, PERF, PIE, I rules. ~63 violations fixed (28 auto-fix
import sorting, 35 manual performance/style fixes).

Phase 2 (later): SIM subset (excluding SIM115/SIM105), B, ERA. ~50 violations.

Phase 3 (later): UP, full E/F, D-rules after docstring backfill.

## Non-goals

- Changing intent-control-plane's existing ruff config (stays in its pyproject.toml).
- Enforcing D-rules (docstrings) until a backfill batch closes the 76-function gap.
