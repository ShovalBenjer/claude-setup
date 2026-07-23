# ADR-0001 — claude-setup is the canonical OS repo

Status: Accepted (2026-07-23)

## Context
The personal Claude harness lived scattered across `~/.claude`, repo roots, and an
undeclared nested git repo (`claude-setup-repo`) inside new-recruit/archive — a
repo-in-repo defect per repo-topology. The May-2026 work master plan's core
unfinished phase was "one canonical dotfiles repo."

## Decision
`github.com/ShovalBenjer/claude-setup`, cloned to `C:\Users\shova\claude-setup`, is
the single canonical home of the Claude OS. `dot-claude/` `dot-codex/` `dot-agents/`
are the deployable payload; `CLAUDE-OS.md` is the spine; the May work export remains
as commit 910dec2 for provenance. Everything the OS owns (rules, hooks, skills, bin,
docs, tools) lives here and deploys to `~/.claude` via a sync script.

## Consequences
+ One findable source; inheritance from the work setup is literal git history.
+ The PR-review fabric can dogfood on this repo's own PRs.
- A sync step now mediates repo → `~/.claude`; drift between them is a new failure
  mode to guard (a health check compares them).
- Machine-portability requires the sync script to be Windows-first (WSL paths purged).
