# Contributing to claude-setup

Thank you for your interest in contributing. This document describes how to work with this repository effectively. For the overarching philosophy, governance model, and AI-assisted development guidance, see [CLAUDE-OS.md](CLAUDE-OS.md).

## Development setup

### Prerequisites

- Python >= 3.11
- `uv` (for intent-control-plane subproject)
- `git` with GPG signing enabled
- `gh` CLI authenticated with `repo` scope
- Node.js and bun (for dashboard development)

### Initial clone

```bash
git clone https://github.com/ShovalBenjer/claude-setup.git
cd claude-setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

### Verify the harness

```bash
python tools/gate/gate.py run --project . -v   # Full 12-domain contract
python -m pytest tests/ -q                     # Root test suite
```

If either command fails, the repository is not in a contributing state.

## Branch naming

Branches follow the pattern:

```
<lane>/<short-description>-<ticket-id>
```

Examples:
- `a/fix-gate-selftest-042`
- `b/update-docmap-generation`
- `convoy/claude-setup-reorganization-cleanup/0de18e7b/head`

Lane prefixes are defined in `docs/charters.md`. For ad-hoc work, use the `misc/` prefix.

## Commit conventions

Commits follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

Rules:
- Keep commits small and focused: one logical change per commit.
- The body should explain why, not what. The diff shows what.
- Reference ticket IDs in the body when applicable.
- Do not mix refactoring with behavior changes in one commit.

Example:
```
docs: regenerate DOCMAP.md after adding specs/archive

The archive directory was missing from the generated inventory.
Regenerating aligns the living document with actual state.

Refs: #122
```

## Code style

- Python target: `>=3.11`.
- Line length: 100 characters.
- Lint and format with `ruff`. Run `ruff check .` and `ruff format .` before pushing.
- Type check with `mypy --strict` on `tools/` and `tests/`.
- The `intent-control-plane` subproject has its own `pyproject.toml`. Run `cd intent-control-plane && uv run ruff check . && uv run mypy` when touching that package.
- Follow existing patterns in the file you are editing. Do not introduce new frameworks or libraries without discussion.

## Testing requirements

- Root tests live in `tests/`.
- Run `python -m pytest tests/ -q` before pushing.
- Add a test for every bug fix and every new feature.
- Mutation testing: `python tools/audit/mutate.py --spec <tool-name>` must catch all applicable mutations for any oracle you touch.
- The intent-control-plane subproject has its own tests under `intent-control-plane/tests/`.
- Dashboard tests: `cd dashboard && npm test` (when applicable).

### Test tiers

1. **Unit** - `tests/` plus per-tool selftests. Fast, deterministic, run on every commit.
2. **Contract** - `tools/gate/gate.py run`. The 12-domain gate. Run before pushing.
3. **Mutation** - `tools/audit/mutate.py --spec all`. Proves selftests can go red. Slow but required for oracles.
4. **E2E** - `tools/e2e/`. Live browser and integration tests. Run in CI only.

## Pre-commit hooks

Install the pre-commit hooks after cloning:

```bash
pip install pre-commit
pre-commit install
```

This runs ruff (lint + format), mypy, trailing-whitespace, end-of-file-fixer, check-yaml, and check-json before every commit.

## Pull request process

1. **Claim before starting.** Append a claim row to `state/claims.jsonl` with your name, lane, and intent before beginning work.
2. **Small PRs.** A PR should do one thing. If you find yourself writing "and also" in the description, split it.
3. **Self-review first.** Run `python tools/gate/gate.py run --project . -v` and ensure all configured domains pass. Do not submit a PR with a failing gate.
4. **Description.** The PR body must state: what changed, why, acceptance evidence (commands + output), and intent coverage (covered / uncovered + why).
5. **No draft merges.** A PR with WIP commits must not be merged. Squash or rebase to a clean history before merge.
6. **Autonomy ships only via PR gate** (ADR-0012). Do not push directly to `main`.

## Code review expectations

- Reviews are adversarial by design. Expect pushback on untested claims, stub functions, and always-pass checks.
- Every claim needs evidence. "I tested it" is not evidence; command + output is.
- Aspect-split verification: parallel single-aspect verifiers (correctness, security, contract, simplicity, slop) with binary verdict + evidence each.
- A reviewer who rubber-stamps a PR is failing their role. The gate exists to disagree.
- Resolve threads fully. Do not leave open comments with "will fix in next PR."

## Secrets and PII

- Never commit secrets, API keys, tokens, or credentials.
- Use `.env` locally; it is gitignored. Copy `.env.example` to `.env` and fill in only what you need.
- PII must never enter embedding indexes or commit history.
- `tools/gate/gate.py` includes a secret-scan domain. Make sure your change passes it.

## Release process

This repository does not ship releases in the conventional sense. Changes propagate through:

1. **PR gate** - All changes must pass `gate.py run` and review.
2. **Deploy step** - The operator deploys `dot-*` payload to live runtime via `skills_sync.py deploy --apply`.
3. **Documentation** - Regenerate `docs/DOCMAP.md` and `docs/CODEBASE-MAP.md` when directory structure changes.

## Questions

- Process and conventions: [CLAUDE-OS.md](CLAUDE-OS.md).
- Session boot and lane assignment: [docs/SESSION-BOOT.md](docs/SESSION-BOOT.md).
- Harness behavior: [AGENTS.md](AGENTS.md).
- Tool internals: read the docstring at the top of the relevant `tools/*/*.py` file. Every major tool has one.
