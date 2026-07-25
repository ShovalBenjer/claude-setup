---
name: agent-team
description: Agent team coordination protocol — spawn rules, worktree isolation, handoff protocol, quality checkpoints. Use when spawning multiple agents for parallel work.
---

# /agent-team

Structured agent coordination with quality gates at every handoff.
See archived full protocol: `~/.Codex/rules/.archive-agent-team-protocol.md`

## Spawn Template

Always include in agent prompts: NO mocks, NO files >500 LOC, NO functions >50 LOC, NO new deps without documenting why, test everything, paste output. Use `isolation: "worktree"` for agents that write code.

## Task Size: <200 LOC per task. Split if larger.

## Handoff: Agent A completes → lead verifies → Agent B reads A's files before starting.

## Red Flags: Agent says "done" without test output, modified files outside scope, added undocumented deps, two agents modified same file.
