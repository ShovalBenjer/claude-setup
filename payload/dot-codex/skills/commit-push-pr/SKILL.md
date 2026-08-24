---
name: commit-push-pr
description: Run pre-commit quality gates (ruff/mypy/tests for Python, knip/eslint for JS), commit with Conventional format, push, open PR, sweep merged branches. Auto-detects bun/uv stack and Azure DevOps vs GitHub remote. Triggers on "/commit-push-pr", "commit and push", "open a PR", "ship it".
model: sonnet
allowed-tools: ["Bash", "Read", "Grep", "Glob"]
---

# /commit-push-pr

Auto-detect stack (bun/uv), run pre-commit quality gates, commit with Conventional format, push, and create PR.

## When to Use

- Changes are ready to ship and pass all tests
- Need to create a PR for code review
- Want automated Conventional Commits + PR body generation

## When NOT to Use

- Pre-commit checks are failing (fix locally first)
- Working on main branch directly (workflow forces branch creation)
- Unsure if changes are ready (commit manually with git instead)

## Usage

```
/commit-push-pr [optional commit message]
```

## Instructions

1. **Detect stack:** Check for `package.json` (bun) or `pyproject.toml` (uv) in CWD.

2. **Pre-commit checks** (run in parallel where possible):
   - **JS/TS:** `bun run test:p0 || bun test`, `bunx eslint --fix`, `bunx knip`
   - **Python:** `uv run pytest tests/unit/`, `uv run ruff check --fix .`, `uv run mypy .`
   - If any check fails, stop and report. Do NOT proceed.

3. **Stage changes:**
   - `git add` only relevant files (no `.env`, credentials, large binaries)
   - Review staged diff before committing

4. **Commit:**
   - Use Conventional Commits format: `type(scope): description`
   - If no message arg provided, generate from staged diff
   - Include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

5. **Push:**
   - Create branch if on main: `git checkout -b feat/description`
   - `git push -u origin HEAD`

6. **Create PR:**
   - `gh pr create --title "..." --body "..."`
   - Body format: `## Summary` (bullets) + `## Test plan` (checklist)
   - Return the PR URL

## Notes

- Never force push
- Never push directly to main/master
- If pre-commit checks fail, fix issues first and re-run
