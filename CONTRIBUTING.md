# Contributing to claude-setup

**CLAUDE-OS.md is the single source of truth for conventions, governance, and process.**
Read it before making changes. This file covers the PR process, code style, and testing only.

## PR process

- Work on the feature branch assigned by the convoy rig.
- Keep commits small and focused: one logical change per commit.
- Commit messages follow the imperative mood: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
- The body should explain why, not what. The diff shows what.
- The repository is gated. `python tools/gate/gate.py run --project . -v` is the full 12-domain contract.
- Do not bypass the gate. If a domain is genuinely not applicable, add a waiver with a reason and expiry date.
- Review fabric (`tools/review/panel.py`) writes artifacts under `state/reviews/`. These are generated and not committed.

## Code style

- Python target: `>=3.11`.
- Line length: 100 characters.
- Lint and format with `ruff`. Run `ruff check .` and `ruff format .` before pushing.
- Type check with `mypy --strict` on `tools/` and `tests/`.
- Follow existing patterns in the file you are editing. Do not introduce new frameworks or libraries without discussion.
- Install the pre-commit hooks after cloning:

```bash
pip install pre-commit
pre-commit install
```

This runs ruff (lint + format), mypy, trailing-whitespace, end-of-file-fixer, check-yaml, and check-json before every commit.

## Testing

- Root tests live in `tests/`.
- Run `python -m pytest tests/ -q` before pushing.
- The intent-control-plane subproject has its own tests under `intent-control-plane/tests/`. Run `cd intent-control-plane && uv run pytest -q` when touching that package.
