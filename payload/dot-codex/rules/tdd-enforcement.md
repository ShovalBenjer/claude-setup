# TDD Enforcement (Global)

**Reference:** `~/.codex/rules/no-mocks.md`

## Workflow

RED: Write failing test first → GREEN: Minimal implementation → REFACTOR: Format + lint

## CI Gate Tiers

**Tier 1 — Every Commit (<5s):**
- Linter: 0 errors
- Formatter: 0 violations
- Type check: 0 errors
- Unit tests: all pass
- Property tests: all invariants pass

**Tier 2 — Every PR (<2m):**
- All Tier 1 gates +
- Integration tests
- Regression suite
- Coverage >= project threshold
- Frontend projects: Playwright CLI (functional) + Playwright Visual (screenshot analysis on UI-touching PRs)

**Tier 3 — Nightly:**
- Fuzz tests (external input parsers)
- Mutation tests (target >80% score)
- Performance baselines
- Concurrency + chaos tests

**Tier 4 — Pre-Release:**
- Full regression suite
- Load tests
- Security scan

## Test Types Required

Unit | Property (invariants) | Integration | Regression | Performance baseline
Frontend: Playwright CLI (functional) + Playwright Visual (screenshot analysis)
Nightly: Fuzz | Mutation | Chaos

## Test Reporting (Non-Binary)

```
CRITICAL [95%] test_name — category — root cause — impact
HIGH     [80%] test_name — category — root cause — impact
LOW      [60%] test_name — performance — CI flakiness — likely transient
```

## Rules

- NEVER assume code works — verify tests pass
- NEVER skip RED step
- Every PR includes tests for changed behavior
- Every production bug gets a permanent regression test
- No mock violations (see no-mocks.md)
- No emojis in test names, output, or reports (see no-emojis.md)

## Project-Specific Overrides

Each project `.codex/rules/tdd-enforcement.md` defines the exact commands for each tier.
Do NOT run tools from other stacks (e.g. ruff/mypy in a JS-only project).
Reference: project `docs/TESTING-PROTOCOL.md` for full detail.
