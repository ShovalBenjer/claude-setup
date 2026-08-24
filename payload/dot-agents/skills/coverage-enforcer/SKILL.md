---
name: coverage-enforcer
description: Block /commit-push-pr from pushing if the staged diff has source changes (.py/.ts/.js) without matching test changes. Closes the COVERAGE axis of Shoval's forge loop. Triggers on /commit-push-pr or "ready to push". Companion hook is at ~/.codex/hooks/coverage-enforcer.sh — wired as PreToolUse on git push.
model: sonnet
---

# Coverage Enforcer — COVERAGE axis gate

## When to invoke

- Just before `/commit-push-pr` runs the push step
- The PreToolUse hook on `Bash(git push*)` will also fire `~/.codex/hooks/coverage-enforcer.sh` automatically
- User said "/coverage" or "did I add tests?"

## Why this exists

The forge loop's COVERAGE axis (acceptance criteria explicitly mapped to tests) is the most-missed axis in the 4-week rolling average (current 2.06/8). When source code changes ship without test changes, COVERAGE = 0 for that session.

This skill + hook closes the loop: a push that touches source code MUST include either (a) a test change, (b) an explicit `[skip-coverage: <reason>]` line in the commit message, or (c) a `--no-verify` flag (which is itself audited).

## What counts as "source changes"

```
*.py *.ts *.tsx *.js *.jsx *.go *.rs *.java *.kt *.swift *.rb *.php
```

Excluded (don't trigger the gate):
- `*.md *.txt *.json *.yaml *.yml *.toml *.lock *.cfg *.ini`
- `**/migrations/*` (Alembic / Django migrations are auto-generated)
- `**/__pycache__/**`, `**/node_modules/**`, `**/.venv/**`, `**/dist/**`, `**/build/**`
- `tests/test_data/**` (test fixtures don't need their own tests)

## What counts as a "test change"

Diff includes any of:
- A file path matching `**/test_*.py`, `**/*_test.py`, `**/*.test.ts`, `**/*.spec.ts`, `**/*_test.go`, `**/*Test.java`
- A path matching `tests/**`, `test/**`
- A new function name starting with `test_` in a file already in the test path

## Behavior

The companion hook runs deterministically (no LLM call) before the push:

1. Compute staged diff: `git diff --cached --name-only`
2. Classify each path: source / test / neutral
3. Build sets: `S` = source files changed, `T` = test files changed
4. Decision:
   - `|S| > 0` and `|T| == 0` → **block with exit 2**, show:
     ```
     COVERAGE GATE: source changes without test changes.
       Source changed: <list>
       Tests changed: (none)

     To proceed, either:
       a) Add a test that exercises the change
       b) Append `[skip-coverage: <reason>]` to the commit message
       c) Re-run with --no-verify (this gets logged for the forge audit)
     ```
   - `|S| > 0` and `|T| > 0` → pass silently
   - `|S| == 0` → pass silently (doc-only or refactor-of-tests pushes are fine)
   - Commit message contains `[skip-coverage: ...]` → log skip reason, pass

## Anti-patterns

- **Don't fail on whitespace-only changes.** `git diff --cached --check` first; if no actual content change, exempt.
- **Don't require test count to *increase*.** A bug-fix commit may modify an existing test (e.g. tighten an assertion) — that's a valid test change.
- **Don't block hotfix push.** If the commit message starts with `hotfix:` or `revert:`, log the skip but don't block.

## How to bypass legitimately

The `[skip-coverage: <reason>]` token in the commit message is the official escape hatch. Examples that pass:

```
fix(crm): retry transient mysql disconnect [skip-coverage: existing integration test covers this path]
chore(deps): bump azure-functions to 1.18.0 [skip-coverage: dep bump only]
docs(wiki): update v109 deploy notes [skip-coverage: docs only]
```

The `a12-skill-usage-telemetry` automation will track skip-reasons over time. If a single reason category dominates (e.g. >50% of skips are "dep bump only"), that's signal we need a more specific exemption rule.

## Companion hook

`~/.codex/hooks/coverage-enforcer.sh` does the actual deterministic gate. The skill exists to give Codex context when discussing coverage with the user — the hook is the enforcement layer.
