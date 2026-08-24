---
name: project-state
description: "Durable project memory via status.json, handovers, and resume prompts"
---

# Project State

Use this skill when the user wants:
- durable session memory across Codex runs
- a project handover or resume prompt
- per-project state bootstrapped from current repo reality

## Files

Maintain these files inside each project:
- `.Codex/status.json` — current state, blockers, next steps, verification commands
- `.Codex/handover-YYYYMMDD-topic.md` — latest session handover
- `.Codex/NEXT_SESSION_PROMPT.md` — concise restart prompt

## Workflow

1. Read the project authority docs first.
2. Read `.Codex/status.json` if it exists.
3. Refresh branch, last commit, blockers, in-progress work, and next steps from the real repo.
4. Update verification commands to match the project stack.
5. Write a short handover with:
   - what changed
   - what is unverified
   - exact next command
6. Refresh `NEXT_SESSION_PROMPT.md` so the next session starts with the right files and commands.

## Rules

- `status.json` is operational memory, not source-of-truth architecture.
- Keep handovers short and dated. Prefer one fresh handover over many stale ones.
- Never mark `testsPass: true` unless you actually ran verification.
- For compacted repos, runtime state files may live in `.Codex` even if active policy lives in `.codex` or `AGENTS.md`.

## Templates

- `templates/status-template.json`
- `templates/handover-template.md`
