#!/usr/bin/env bash
# Local quality gate. This repo has no remote, so this script is the CI-BIND equivalent:
# run it before every commit (wire it as a git pre-commit hook, see README). Zero-tolerance:
# ruff, mypy, and the full test suite must all pass.
set -euo pipefail
# Locate the repo root robustly, whether run directly or as a symlinked git pre-commit hook
# (where $0 is .git/hooks/pre-commit, so a $0-relative path would resolve into .git/).
cd "$(git rev-parse --show-toplevel)"
echo "[check] ruff"
uv run ruff check src tests
echo "[check] mypy"
uv run mypy
echo "[check] pytest"
uv run pytest -q
echo "[check] all green"
