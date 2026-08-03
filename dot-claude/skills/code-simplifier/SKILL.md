---
name: code-simplifier
description: "/code-simplifier"
disable-model-invocation: true
---

# /code-simplifier

Refactor-only simplification: reduce complexity, improve readability, apply idiomatic patterns. No behavior changes.

## When to Use

- Code is working but overly complex or verbose
- Want to apply language idioms or design patterns
- Need linting cleanup + test verification after refactor

## When NOT to Use

- Tests are failing (fix logic first)
- Unsure if changes would break behavior (use code-reviewer instead)
- Need to add features or fix bugs (implement separately)

## Usage

```
/code-simplifier [path]          # Simplify specific file/directory
/code-simplifier                 # Simplify recently changed files (git diff)
```

## Instructions

1. **Identify targets:**
   - If path arg: use that file/directory
   - If no arg: `git diff --name-only HEAD~1` for recently changed files
   - Filter to source files only (`.ts`, `.tsx`, `.js`, `.jsx`, `.py`)

2. **Analyze each file for:**
   - Unnecessary complexity (nested conditionals, long functions)
   - Non-idiomatic patterns (could use built-in methods, destructuring, etc.)
   - Dead code paths, unused variables
   - Overly verbose constructs that have simpler equivalents
   - Duplicated logic that could be extracted

3. **Apply simplifications:**
   - Flatten nested conditionals (early returns)
   - Replace verbose loops with map/filter/reduce where clearer
   - Extract repeated patterns into well-named helpers
   - Use language idioms (Python: comprehensions, walrus; JS: optional chaining, nullish coalescing)
   - Remove dead code

4. **Post-simplification checks:**
   - **JS/TS:** `bunx eslint --fix`, then `bun test` or `bun run test:p0`
   - **Python:** `uv run ruff format .`, `uv run ruff check --fix .`, then `uv run pytest`
   - All tests must still pass. If any fail, revert that change.

5. **Report:** Summary of changes made and complexity reduction.

## Rules

- NO behavior changes — refactor only
- NO new dependencies
- If unsure whether a change preserves behavior, skip it
- Prefer readability over cleverness
