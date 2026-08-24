# Harness Maturity Plan (PRD delta) - 2026-07-09

Delta to `repo-enterprise-maturity-todo-2026-07-09.md` and
`repo-maintenance-file-plan-2026-07-09.md`. Those two rank 7 product repos and scope the
local agent harness (`.claude/`, `.codex/`) out, as clutter to gitignore. This plan adds
the missing surface: the harness that enforces maturity on every repo was itself the least
mature, unmeasured code.

## Question answered

"Is `.py` the mature way to build the harness?" Language: yes (Python is the prescribed
glue/automation choice; bash is not a candidate). Form as found: no, it was bash hooks with
embedded python heredocs and untested standalone scripts. The mature form is a tested
Python package with thin bash adapters. See ADR
`~/projects/intent-control-plane/docs/adr/0001-harness-is-a-python-package-with-thin-bash-adapters.md`.

## Packages (executed 2026-07-09)

### B - hygiene, dedup, split (done)

- B1: deleted 14 dead-stub hooks (`exit 0` placeholders), verified unreferenced by
  `settings.json` or any hook. Live hooks intact.
- B2: reconciled duplicate hooks to single-source. `prompt-router.sh` and
  `session-recall.sh` were already `.codex`-symlink-to-`.claude`; `visual-explainer-trigger.sh`
  and `voice-explainer-trigger.sh` were genuine two-file dups, now symlinked. Zero drift.
- B3: split `cli.py` 1736 to 1453 lines into `schema.py` (DDL, connect, init) and
  `mappers.py` (row mappers) via an AST migration. Tests green throughout.
- B4: added `README.md` and `[tool.ruff]` / `[tool.mypy]` / `[tool.pytest.ini_options]` and
  a dev dependency group. ruff clean, mypy clean.

### A - the maturity core: tested logic + thin shims (done)

- A1: extracted `intent_control_plane.harness.self_improve` (reachability, reflect-prompt)
  and `intent_control_plane.harness.router` (routes, personas, confidence check, corpus
  I/O split out). Pure decision logic separated from I/O.
- A2: unit + golden tests. Router output verified byte-identical to the old embedded hook
  across 5 cases (low-confidence, deploy, trivial, review, hebrew) before the swap.
- A3: `prompt-router.sh` is now a 13-line shim; `self-improve.py` imports the tested
  functions.
- A4: full gate green: `uv run pytest` 24 passed, ruff clean, mypy clean (7 files).

### C - record + close the blind spot (this file + ADR + control-plane entry)

- C1: ADR 0001 written.
- C2: harness maturity entry added to `repo-enterprise-maturity-todo-2026-07-09.md`.
- C3: this plan.

## Verification

```
uv run pytest -q          # 24 passed
uv run --group dev ruff check src   # All checks passed
uv run --group dev mypy             # Success: no issues in 7 source files
SELF_IMPROVE_NO_CODEX=1 python3 ~/.claude/bin/self-improve.py   # unreachable skills 0
```

## Not done / follow-ups

- The other heredoc hooks (9 of the remaining live hooks) are not migrated to the shim
  shape. Opportunistic, per ADR 0001.
- The promptfoo push-gate nano judge (JSON-parse variance on the injection row, tests a
  stale `seekapa-system-prompt.md`) is a separate cleanup: point at the deployed prompt and
  a sturdier grader (a Foundry judge such as `grok-4-1-fast`).
