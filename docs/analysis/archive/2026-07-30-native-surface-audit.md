# Claude Code native surface: what we wire, what we leave on the floor

Date: 2026-07-30. Lane B. Measured from live `~/.claude/settings.json` and the live
`~/.claude` tree, not from documentation.

The question that produced this: are we using the native capabilities of the harness we
are building on, and is `ultracode` one of them. The short answer to the second is yes,
it is native and enabled, and nothing in this repository consumes it.

## In use

| Surface | State |
| --- | --- |
| Hook events | 7 of 9 wired: SessionStart 2, PreToolUse 2, PostToolUse 1, PreCompact 1, Stop 3, Notification 1, UserPromptSubmit 2 |
| Subagents | 23 definitions live, 23 in repo |
| Skills | 36 live against 179 in repo. `skills_sync.py check` reports DRIFT, 52 items need a decision |
| Slash commands | 5 live, 7 in repo |
| Statusline | custom, `python ~/.claude/statusline.py` |
| Model and context | `opus[1m]`, `API_TIMEOUT_MS 600000` |
| Permissions | 20 allow rules, 53 deny rules, `skipDangerousModePermissionPrompt: true` |
| Remote control | `remoteControlAtStartup: true` |
| Memory | in use, project memory directory with an index |
| Background tasks | in use |
| Plugin marketplace | `claude-plugins-official` registered 2026-07-30T12:43. **Zero plugins installed** |

## Never used

Ordered by leverage, which is not the same as by effort.

1. **`SubagentStop`.** The only native point at which a subagent's output can be gated
   BEFORE it returns to the parent. That is exactly where the agreement gate in
   `docs/specs/2026-07-23-persona-review-economy.md` belongs, and there is no other
   native place to put it. It appears nowhere in this repository except three 2026-05
   master-plan documents and their duplicate copies under `research-papers/home-md/`.
2. **Output styles.** `~/.claude/output-styles` is absent and no output-style file exists
   anywhere in the repo. The operator's own position, stated 2026-07-30, is that output
   styles are the lever that works where `CLAUDE.md` does not. Meanwhile
   `completion_gate.py` polices the response channel with regexes after generation, which
   is the same job attempted one layer too late.
3. **`CLAUDE.md` `@import`.** Never used. `nexu-io/open-design` ships an eleven-byte
   `CLAUDE.md` containing `@AGENTS.md`, so one canonical agent contract serves every
   vendor filename. This repo hand-maintains five overlapping files: `CLAUDE-OS.md`, a
   root `CLAUDE.md` that is **still untracked**, `dot-claude/CLAUDE.md`,
   `dot-codex/AGENTS.md`, `home-dotfiles/AGENTS.md`.
4. **Plugins.** A marketplace is registered and nothing is installed from it.
5. **Project-scoped `.mcp.json`.** Absent. MCP configuration is user-global and not
   versioned with the repository, so a fresh clone inherits none of it.
6. **`SessionEnd`.** Durable handoff writing currently depends on `PreCompact` firing,
   which is why the compaction-churn investigation mattered. `SessionEnd` is the
   deterministic place for it.
7. **Workflow scripts** under `.claude/workflows/`, and **Artifacts**. Neither has ever
   been created.

## ultracode: native, enabled, unconsumed

`workflowKeywordTriggerEnabled: true` is set in live settings, and Workflow is a
first-party tool. It routes through the same agent registry the Agent tool uses, so the
23 agent definitions here are eligible as `agentType`, and it accepts per-call `model`
and `effort` overrides. Its subagents reach session MCP tools through tool search.

Three things are true at once and the third is the finding:

- It is opt-in per session.
- It is wired to our agent layer for free, with no adapter.
- **Nothing here consumes it.** No scripts in `.claude/workflows/`, no ledger of workflow
  runs, and the twelve-domain gate has no concept of one. A grep for `ultracode` returns
  only prose: `CLAUDE-OS.md`, ADR-0015, three dated analyses, `model-selection.md`, and
  `dot-claude/settings.json`. Never code.

`model-selection.md` already prescribes the routing pattern, measurement and mechanical
stages on sonnet or haiku at low effort and adversarial verify or judge stages on opus or
fable at xhigh. No workflow has ever run under it, so that row is a hypothesis rather
than a measurement.

## Correction owed to `dot-claude/rules/model-selection.md`

That rule states the live `effortLevel` has been `xhigh` since before the fable
experiment, and frames the difference from its own prescribed default as a deliberate
unmeasured contradiction. **Live `effortLevel` is now `low`**, set by the operator at the
start of the 2026-07-30 session as a trial with the stated condition that it becomes the
new default if the session's output satisfies him. Per that file's own convention the fix
is a correcting row, not a rewrite of the losing side.

## What to wire first, and why in this order

`SubagentStop` first, because it closes the largest hole in a spec that is already
written and it has no substitute. An output style second, because it is close to free and
it moves an existing enforcement from after generation to before it. `@import` third,
because it collapses five hand-maintained files into one and would get the root
`CLAUDE.md` tracked as a side effect. Then one real workflow run under the routing that
`model-selection.md` prescribes, so the rule stops being untested.
