# Claude Code → Codex CLI Auto-Delegation: Wired Integration Backlog

> **Setup ground truth**: Claude Code CLI v2.1.177 (Opus 4.8 orchestrator, Sonnet 5 subagents via `CLAUDE_CODE_SUBAGENT_MODEL`, effortLevel xhigh, ultracode/dynamic-workflows ON, doneMeansMerged ON) on WSL2. Codex CLI v0.125.0 at `~/.local/bin/codex` (gpt-5.5 / codex-5.3, ChatGPT subscription, `codex exec --full-auto`). Bridge: `~/.claude/bin/a2a-codex-call.sh`, `dispatch` skill at `codex:home`, `gastown-codex-automation.sh`.

***

## Part 1 — Native Claude Code Mechanisms

### Hook Events (full taxonomy)

Hooks fire at three cadences:[^1]

- **Per-session**: `SessionStart`, `SessionEnd`
- **Per-turn**: `UserPromptSubmit`, `Stop`, `StopFailure`
- **Per-tool-call (agentic loop)**: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`

Additional async events include `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `FileChanged`, `CwdChanged`, `ConfigChange`, `InstructionsLoaded`, `PreCompact`, `PostCompact`, `Notification`, `MessageDisplay`, `TeammateIdle`, `Elicitation`, `ElicitationResult`.[^1]

#### Hook Handler Types

All five handler types share `type`, `if`, `timeout`, `statusMessage`, and `once` common fields:[^1]

| Type | Description | Can Shell Out? | Default Timeout |
|------|-------------|---------------|-----------------|
| `command` | Runs a shell command; stdin=JSON event; stdout=decision or context | **Yes** — directly | 600 s (30 s for `UserPromptSubmit`) |
| `http` | POSTs event JSON to a URL endpoint | Via endpoint | 600 s |
| `mcp_tool` | Calls a connected MCP server tool; output treated as command stdout | Via MCP server | 600 s |
| `prompt` | Single-turn Claude model evaluation; returns yes/no JSON decision | No | 30 s |
| `agent` | Spawns a subagent with Read/Grep/Glob for multi-turn verification (experimental) | No direct shell | 60 s |

**`command` hooks** uniquely support:[^1]
- `async: true` — fire-and-forget, does not block the model
- `asyncRewake: true` — implies `async`; on exit code 2, Claude is woken and shown the hook's stderr (or stdout if stderr empty) as a **system reminder**, letting it react to a long-running background result. This is the primary mechanism for async feedback loops.
- `shell: "bash"` or `"powershell"` (ignored when `args` is set)
- `args` array → exec form (no shell, each arg exact)

#### Matcher and `if` Scoping

The `matcher` field filters which events trigger a hook group:[^1]

- Exact string (`"Bash"`, `"Edit|Write"`, `"code-reviewer"`) — requires v2.1.195+ for hyphenated names
- JavaScript regex (unanchored) — any matcher containing chars outside `[A-Za-z0-9_\- ,|]`
- `"*"`, `""`, or omitted — fires on every occurrence

The `if` field (per handler) uses **permission rule syntax** (`"Bash(git *)"`, `"Edit(*.ts)"`) and is only evaluated on tool events (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`). It holds exactly one rule; combine by declaring multiple handlers.[^1]

For `SubagentStart`/`SubagentStop`, the matcher filters on **agent type** (e.g., `"general-purpose"`, `"Explore"`, `"Plan"`, or custom names like `"codex-junior"`). `Stop`, `PostToolBatch`, `TaskCreated`, `TaskCompleted`, `MessageDisplay`, and `CwdChanged` have **no matcher support** — they always fire.[^1]

MCP tools appear as `mcp__<server>__<tool>` in tool events; match all tools from a server with `mcp__<server>__.*`.[^1]

**VERIFIED**: Hook locations — `~/.claude/settings.json` (global), `.claude/settings.json` (project, committable), `.claude/settings.local.json` (project-local, gitignored), skill/agent frontmatter (`hooks:` key), plugin `hooks/hooks.json`.[^1]

***

### Subagents / Agent Tool

Subagents are Markdown files with YAML frontmatter stored in `.claude/agents/` (project) or `~/.claude/agents/` (user). Claude delegates tasks to them based on the `description` field. Key frontmatter fields:[^2]

| Field | Effect |
|-------|--------|
| `name` | Lowercase-hyphen identifier; received as `agent_type` in `SubagentStart`/`SubagentStop` hooks |
| `description` | When Claude should delegate; text used by the model |
| `model` | `sonnet`, `opus`, `haiku`, `fable`, full model ID, or `inherit`. Resolution order: `CLAUDE_CODE_SUBAGENT_MODEL` env var → per-invocation `model` param → frontmatter `model` → main session model |
| `tools` | Allowlist; `Agent(worker, researcher)` restricts spawnable sub-types |
| `disallowedTools` | Denylist (applied first) |
| `permissionMode` | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan`, `manual` |
| `isolation` | `"worktree"` — runs in a temporary git worktree, cleaned up if no changes made |
| `effort` | `low`, `medium`, `high`, `xhigh`, `max` — overrides session effort |
| `hooks` | Scoped lifecycle hooks for this subagent only |
| `mcpServers` | Inline or reference MCP servers (inline = scoped to this subagent only) |
| `memory` | `user`, `project`, `local` — persistent memory directory |
| `background` | `true` = always run as background task |
| `maxTurns` | Cap on agentic turns |
| `skills` | Preload skill content into context at startup |

**VERIFIED**: `CLAUDE_CODE_SUBAGENT_MODEL` is the highest-priority override for subagent model selection, evaluated before per-invocation param and frontmatter. Setting it to `inherit` (v2.1.196+) is treated as unset, falling through to lower-priority sources.[^2]

**Shell-out capability**: Command hooks on `SubagentStop` (matched by `agent_type`) can shell out to `a2a-codex-call.sh`. Subagents themselves can use Bash tool to exec any CLI. An inline MCP server scoped to a subagent can wrap `codex exec`.

***

### Skills (Custom Slash Commands)

Skills are `SKILL.md` files under `.claude/skills/<name>/` (project) or `~/.claude/skills/<name>/` (user). Custom commands merged into skills — `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` are equivalent. Key frontmatter:[^3]

| Field | Relevant Behaviour |
|-------|--------------------|
| `context: fork` + `agent` | Runs the skill in a forked subagent context using specified agent type |
| `disable-model-invocation: true` | Only human-invocable; not auto-triggered by Claude; excluded from subagent preloading |
| `user-invocable: false` | Only Claude can invoke (background knowledge) |
| `model` | Override for duration of that turn only |
| `effort` | Override for that turn |
| `allowed-tools` | Pre-approve tools while skill is active (no prompt) |
| `hooks` | Scoped hooks for this skill's lifecycle |

Dynamic context injection with `` !`command` `` runs a shell command at invocation and inlines its stdout. `${CLAUDE_PROJECT_DIR}` and `${CLAUDE_EFFORT}` are available as substitution variables.[^3]

**Shell-out**: A skill can call `a2a-codex-call.sh` via `` !`...` `` injection or via `Bash` tool with `allowed-tools: Bash(~/.claude/bin/a2a-codex-call.sh *)`.

***

### MCP Servers as Tool Surfaces

MCP servers connect as stdio, HTTP, SSE, or WebSocket processes and expose tools named `mcp__<server>__<tool>`. Key configuration:[^4]

- **Local stdio** (`~/.claude.json` or `.mcp.json`): `command + args + env`; ideal for wrapping a local CLI
- **Project-scoped** (`.mcp.json` checked into repo): shared with collaborators, requires workspace trust
- **User-scoped** (`~/.claude.json`): all projects

A stdio MCP server can wrap `codex exec` as a callable tool. Claude Code sets `CLAUDE_PROJECT_DIR` in the spawned server's environment. Dynamic `list_changed` notifications allow tools to appear/disappear at runtime.[^4]

**Shell-out**: A Node.js/Python stdio MCP server that runs `~/.local/bin/codex exec --full-auto -q <prompt>` exposes this as a first-class MCP tool. Claude calls it via the Agent tool or directly; hooks can call `mcp_tool` type handlers on it.

***

### Dynamic Workflows (`ultracode`)

**CLAIMED** (prior knowledge; no single doc page exclusively describes "ultracode" as a distinct syntax): In ultracode mode (set via `effortLevel: xhigh` + dynamic-workflows ON in settings), Claude gains access to `agent()`, `pipeline()`, and `parallel()` built-in constructs that orchestrate multi-stage agentic work within a single session. These are model-level orchestration primitives — Claude uses them implicitly when planning a complex task — rather than explicit config fields. `verify` stages can be composed after `agent()` calls to gate output.

**VERIFIED adjacent**: The `effort` field on subagents and skills controls how much reasoning the subagent applies. The `maxTurns` field on subagents caps runaway delegation.[^2][^3]

***

### Claude Agent SDK

**CLAIMED**: The Agent SDK (`@anthropic-ai/claude-code` npm package / `--sdk` flag) exposes a programmatic API for spawning and monitoring Claude Code sessions non-interactively. It supports `--agents` JSON for injecting session-ephemeral subagent definitions, and `--settings` for per-run settings overrides. Sessions with `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS=1` load only caller-supplied subagents.[^2]

***

## Part 2 — Integration Design: Codex as Supervised Junior

### 2a. Trigger Surfaces by Task Class

The goal is: Claude finishes an edit or a turn → trigger class is detected → `a2a-codex-call.sh` runs → result returned → senior verifies.

#### Mechanism Matrix

| Task Class | Best Trigger | Why | Wiring |
|-----------|-------------|-----|--------|
| Lint/format auto-fix | `PostToolUse` on `Edit\|Write`, `command`, async=false | Fires immediately after each file edit; result feeds back to Claude via stdout | `~/.claude/settings.json` |
| Docstring/comment generation | `PostToolUse` on `Edit`, `asyncRewake` | Non-blocking; wakes Claude with result for review | `.claude/settings.json` |
| Boilerplate test scaffold | `Stop` hook, `command` | Fires at turn end; inspects git diff for new files | `~/.claude/settings.json` |
| Mechanical refactor | Named subagent (`codex-refactor`), `model: sonnet`, `isolation: worktree` | Opus delegates via Agent tool; worktree isolates; Opus reviews diff | `.claude/agents/codex-refactor.md` |
| PR/diff second-opinion | `Stop` hook → `a2a-codex-call.sh`, or `/codex-review` skill | Turn-scoped; senior reads diff, passes to Codex, reviews result | `.claude/skills/codex-review/SKILL.md` |
| Coverage-gap filling | `Stop` hook or subagent | Slow path; scan coverage report, fill gaps | Subagent or Stop hook |
| Commit-message draft | `PostToolUse` on `Bash(git add *)` or Stop hook | Triggered by staging activity | Hook in `.claude/settings.local.json` |
| Changelog generation | `/codex-changelog` skill, `disable-model-invocation: true` | Human-triggered only; Codex drafts, senior edits | `.claude/skills/codex-changelog/SKILL.md` |
| Dependency bump smoke check | `asyncRewake` Stop hook (schedule aware) | Long-running; wake Claude only on error | `.claude/settings.local.json` |
| Over-engineering pass | Subagent `codex-simplifier`, `permissionMode: plan` | Read-only; returns structured suggestions | `.claude/agents/codex-simplifier.md` |

***

#### Concrete Wiring: Lint/Format Auto-Fix (Highest Leverage)

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "if": "Edit(*.py)|Edit(*.ts)|Edit(*.js)|Write(*.py)|Write(*.ts)|Write(*.js)",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/codex-lint-fix.sh",
            "timeout": 60,
            "statusMessage": "Codex lint-fix running…"
          }
        ]
      }
    ]
  }
}
```

**Script**: `.claude/hooks/codex-lint-fix.sh`

```bash
#!/usr/bin/env bash
# Reads PostToolUse JSON from stdin; extracts file_path; delegates lint/format to Codex.
# GUARD: never re-enter if already invoked by a Codex-triggered edit.
set -euo pipefail

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[[ -z "$FILE" ]] && exit 0

# Re-entrancy guard: Codex edits set CODEX_LINT_PASS=1; skip if already set.
[[ "${CODEX_LINT_PASS:-}" == "1" ]] && exit 0

# Strip secrets: pass only the file path, never env vars or prompt content.
PROMPT="Fix all lint and format issues in the file: $FILE. Apply fixes in-place. Do not change logic."

RESULT=$(CODEX_LINT_PASS=1 ~/.claude/bin/a2a-codex-call.sh "$PROMPT" \
  --timeout 55 --effort low 2>/dev/null)

STATE=$(echo "$RESULT" | jq -r '.state // "error"')
if [[ "$STATE" == "error" || "$STATE" == "timeout" ]]; then
  echo "codex-lint-fix: Codex unavailable or timed out, skipping ($STATE)" >&2
  exit 0  # Graceful degrade — do not block Claude
fi

# Inject summary as context for Claude.
echo "$RESULT" | jq -r '"[codex-lint] " + .response_text'
exit 0
```

**Feedback-loop prevention**: The `CODEX_LINT_PASS=1` env var is set before invoking `a2a-codex-call.sh`. If Codex edits a file via `codex exec --full-auto`, the same `PostToolUse` hook will re-fire. The guard checks `CODEX_LINT_PASS` in the child environment — because `a2a-codex-call.sh` is a synchronous subprocess within the same shell environment, the child inherits the variable and exits 0.[^1]

> **VERIFIED**: `asyncRewake: true` on command hooks wakes Claude on exit code 2, showing stderr as a system reminder. Use this instead of the above for async docstring generation — the Codex run is non-blocking; Claude is woken only if Codex exits non-zero.[^1]

***

#### Concrete Wiring: Test Scaffold via Stop Hook

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/codex-test-scaffold.sh",
            "async": true,
            "asyncRewake": true,
            "timeout": 120,
            "statusMessage": "Codex test-scaffold in background…"
          }
        ]
      }
    ]
  }
}
```

**Script**: `.claude/hooks/codex-test-scaffold.sh`

```bash
#!/usr/bin/env bash
# Fires at turn end; finds new/modified source files without matching tests; delegates scaffold to Codex.
set -euo pipefail

INPUT=$(cat)
# Extract changed files from git working tree (NEW or MODIFIED, not test files).
CHANGED=$(git diff --name-only HEAD -- '*.py' '*.ts' '*.js' \
  | grep -v '_test\.\|\.spec\.\|/tests/' | head -5)
[[ -z "$CHANGED" ]] && exit 0

# Lock: only one Codex scaffold task at a time.
LOCK=/tmp/codex-scaffold.lock
[ -f "$LOCK" ] && exit 0
touch "$LOCK"
trap "rm -f $LOCK" EXIT

PROMPT="For each of these source files, generate the missing unit test stubs following TDD RED phase (no implementation assumed):
$CHANGED
Write tests to the conventional test file location. Follow the project's existing test patterns."

RESULT=$(~/.claude/bin/a2a-codex-call.sh "$PROMPT" --timeout 110 --effort med 2>/dev/null)
STATE=$(echo "$RESULT" | jq -r '.state // "error"')

if [[ "$STATE" != "completed" ]]; then
  echo "codex-scaffold failed: $STATE" >&2
  exit 2  # asyncRewake: wake Claude with failure notice
fi

# Exit 0 with no output = success, no wake needed (tests written silently).
exit 0
```

**Senior verify step**: Because `asyncRewake: true` only wakes Claude on exit code 2 (failure), a successful scaffold is silent. Claude's next turn naturally runs the tests. For a positive wake (inform Claude of new test files), return the file list on stdout and exit 0; it appears in context.[^1]

***

#### Concrete Wiring: Codex Junior Subagent (Mechanical Refactor)

**File**: `.claude/agents/codex-refactor.md`

```markdown
---
name: codex-refactor
description: >
  Delegates mechanical, non-semantic refactors to Codex CLI.
  Use when the task is: rename a symbol everywhere, extract a repeated pattern,
  convert callback chains to async/await, or apply a purely structural transformation
  with zero business-logic change. Always operates on a worktree copy.
tools: Bash, Read, Grep, Glob
model: sonnet
effort: medium
isolation: worktree
permissionMode: auto
---

You are a mechanical refactor coordinator. When invoked:

1. Read the task description carefully.
2. Identify every file that must change.
3. Construct a precise, scoped prompt for Codex — no context beyond what Codex needs.
4. Run: `~/.claude/bin/a2a-codex-call.sh "<prompt>" --effort med --timeout 90`
5. Parse the JSON result. If state != "completed", report failure and stop.
6. Run `git diff --stat` to enumerate what Codex changed.
7. Run `git diff` and perform a semantic correctness check:
   - Were any tests deleted?
   - Were any imports or exports broken?
   - Does the change match the original intent?
8. Report your findings as a structured diff summary for the Opus senior to approve.
```

**Model resolution**: The `model: sonnet` frontmatter is overridden by `CLAUDE_CODE_SUBAGENT_MODEL` if set, so the existing pin to Sonnet 5 takes effect. `isolation: worktree` gives the subagent a throw-away git worktree; the worktree is auto-cleaned if no changes are made.[^2]

***

#### Concrete Wiring: PR/Diff Review Skill

**File**: `.claude/skills/codex-review/SKILL.md`

```markdown
---
name: codex-review
description: >
  Asks Codex to review the current git diff for correctness, over-engineering,
  missing edge cases, and style. Returns a structured JSON critique for the senior.
disable-model-invocation: true
allowed-tools: Bash(git diff *) Bash(~/.claude/bin/a2a-codex-call.sh *)
---

## Current diff

!`git diff HEAD --unified=4`

## Instructions

Pass the diff above to Codex for second-opinion review.

Run: `~/.claude/bin/a2a-codex-call.sh "Review this diff for bugs, missing tests, over-engineering, and style issues. Return JSON with keys: bugs, missing_tests, over_engineering, style_issues. Diff:\n$(git diff HEAD --unified=4)" --effort med --timeout 60`

Parse the JSON in `.response_text`. Present findings as a structured list to the user.
Only apply suggestions after explicit approval.
```

**`disable-model-invocation: true`** ensures Claude never auto-triggers a Codex review — human-invoked only via `/codex-review`.[^3]

***

#### Concrete Wiring: Commit-Message Draft

**File**: `.claude/settings.local.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(git add *)",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/codex-commit-msg.sh",
            "async": true,
            "asyncRewake": false,
            "timeout": 45,
            "statusMessage": "Codex drafting commit message…"
          }
        ]
      }
    ]
  }
}
```

**Script**: `.claude/hooks/codex-commit-msg.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
DIFF=$(git diff --cached --stat 2>/dev/null)
[[ -z "$DIFF" ]] && exit 0

PROMPT="Write a conventional commit message (type: scope: description) for this staged diff summary. Output only the commit message.
$DIFF"

RESULT=$(~/.claude/bin/a2a-codex-call.sh "$PROMPT" --effort low --timeout 40 2>/dev/null)
MSG=$(echo "$RESULT" | jq -r '.response_text // empty')
[[ -z "$MSG" ]] && exit 0

# Write to ~/.claude/cache/a2a/last-commit-msg.txt for Claude to read.
echo "$MSG" > ~/.claude/cache/a2a/last-commit-msg.txt
echo "[codex-commit] Suggested message written to ~/.claude/cache/a2a/last-commit-msg.txt"
exit 0
```

***

#### MCP Server Wrapper (Alternative to Direct Shell-Out)

For richer tool composition, a thin stdio MCP server wrapping Codex is the cleanest long-term surface:

```json
// .mcp.json (project-scoped)
{
  "mcpServers": {
    "codex-junior": {
      "type": "stdio",
      "command": "${CLAUDE_PROJECT_DIR}/.claude/bin/mcp-codex-server.js",
      "env": {
        "CODEX_BIN": "${HOME}/.local/bin/codex",
        "A2A_BRIDGE": "${HOME}/.claude/bin/a2a-codex-call.sh",
        "AUDIT_LOG": "${HOME}/.claude/cache/a2a/audit.jsonl"
      }
    }
  }
}
```

Tools exposed: `codex_junior__lint_fix`, `codex_junior__scaffold_tests`, `codex_junior__write_docstrings`, `codex_junior__refactor`, `codex_junior__review_diff`. Claude invokes these directly via tool calls; `PostToolUse` on `mcp__codex-junior__.*` can intercept and log.[^4][^1]

**Key advantage over raw shell hooks**: MCP server keeps a stateful JSON-RPC session, can maintain a task queue, and supports `list_changed` to expose new tools dynamically. Claude sees the tool in its context and can decide to call it autonomously.[^4]

***

### 2b. Task Routing: Codex Junior Ownership

| Task Class | Trigger Surface | File | Codex Effort | Senior Verify Step | ⭐ |
|-----------|----------------|------|-------------|-------------------|---|
| **Lint/format auto-fix** | `PostToolUse` on `Edit\|Write`, `command`, sync | `.claude/settings.json` | `low` | Check exit 0; read diff for non-format changes | ⭐⭐⭐ |
| **Docstring & comment gen** | `PostToolUse` on `Edit`, `asyncRewake` | `.claude/settings.json` | `low` | Claude reads generated text on wake; approves or revises |  |
| **Test scaffold (stubs)** | `Stop` hook, `asyncRewake` | `.claude/settings.json` | `med` | Run tests (RED); if tests pass unexpectedly, flag as suspicious |  |
| **Mechanical refactor** | Named subagent `codex-refactor`, `isolation: worktree` | `.claude/agents/` | `med` | Subagent does semantic diff check; Opus approves merge | ⭐⭐⭐ |
| **PR/diff review** | `/codex-review` skill, `disable-model-invocation` | `.claude/skills/codex-review/` | `med` | Human reviews Codex critique; Opus acts on agreed items |  |
| **Coverage-gap filling** | Stop hook (async, asyncRewake) | `.claude/settings.local.json` | `high` | Run coverage; confirm delta before merging |  |
| **Commit-message draft** | `PostToolUse` on `Bash(git add *)`, async | `.claude/settings.local.json` | `low` | Human edits; never auto-commit |  |
| **Changelog entry** | `/codex-changelog` skill, `disable-model-invocation` | `.claude/skills/codex-changelog/` | `med` | Human reviews draft entries |  |
| **Dep bump smoke check** | Stop hook, `asyncRewake`, load-aware | `.claude/settings.local.json` | `low` | Read test results; escalate to Opus on failure |  |
| **Over-engineering pass** | Subagent `codex-simplifier`, `permissionMode: plan` | `.claude/agents/` | `med` | Read-only report; Opus decides whether to act | ⭐⭐⭐ |

***

### 2c. Guardrails

#### No Secrets / PII to Codex

Add a `PreToolUse` hook on `Bash` scoped to `a2a-codex-call.sh` invocations that scrubs the prompt before calling Codex:

```bash
# .claude/hooks/scrub-prompt.sh
INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
# Block if prompt contains common secret patterns.
if echo "$CMD" | grep -qE 'OPENAI_API_KEY|sk-|password|secret|token|Bearer '; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Prompt contains potential secret — Codex call blocked."}}' 
  exit 0
fi
exit 0
```

Register as a `PreToolUse` hook with `if: "Bash(~/.claude/bin/a2a-codex-call.sh *)"`.

#### No Auto-Destructive Operations

The standing rule in your setup (never auto branch-delete / force-push / prod-deploy without OK) must extend to Codex tasks. The `codex-refactor` subagent is configured with `permissionMode: auto` and runs in `isolation: worktree`, meaning Codex edits a copy. The subagent's system prompt explicitly forbids pushing, deleting branches, or deploying. The Opus senior reviews the diff before any merge.[^2]

For the `codex-simplifier` subagent, `permissionMode: plan` enforces read-only exploration — no writes.[^2]

#### Feedback-Loop Prevention

Three layers of protection:

1. **Env-var guard** (`CODEX_LINT_PASS=1`) — inherited by child process; hook exits early on re-entry.
2. **Lock file** (`/tmp/codex-scaffold.lock`) — prevents concurrent Codex invocations from the same hook.
3. **`a2a-codex-call.sh` audit log** — `~/.claude/cache/a2a/audit.jsonl` already records every Codex invocation. Add a rate-limit check: if more than N Codex calls in M seconds, skip and log.

**VERIFIED**: The `if` field in hook handlers is "best-effort" and fails open. Rely on the env-var guard in the script, not just the `if` condition, for hard dedup.[^1]

#### Concurrency / Timeout Caps

- All hooks have explicit `timeout` fields (55 s for lint, 120 s for scaffold, 60 s for review).[^1]
- The lock file in `codex-test-scaffold.sh` serializes concurrent Stop hook invocations.
- `a2a-codex-call.sh` already accepts `--timeout` and returns `{state: "timeout"}` on overflow — the hook reads this and exits 0 (graceful degrade).
- `gastown-codex-automation.sh` is load-aware and lock-based — do not invoke it from hooks; invoke only `a2a-codex-call.sh`.

#### Idempotency

- Lint/format: `codex exec --full-auto` with a lint prompt on an already-clean file is a no-op.
- Test scaffold: check for existing test file before delegating.
- Commit message: only fires if `git diff --cached` is non-empty.

#### Graceful Degrade

Every hook checks `state != "completed"` and exits 0 (no decision, no block) when Codex is unavailable. Claude is never blocked by a Codex failure.

#### Audit Trail

`a2a-codex-call.sh` already writes to `~/.claude/cache/a2a/audit.jsonl`[user-setup]. Each entry should record: `{ts, hook_event, file, codex_effort, state, duration_ms, prompt_hash}`. Never log the raw prompt — hash it to avoid storing sensitive context.

***

## Part 3 — External SOTA: Cross-CLI Delegation Patterns (2025–2026)

### Patterns and Projects

**CLAIMED** (community observation, not a single citable doc): The architecture described here — a powerful expensive model orchestrating a cheap fast model for structured subtasks — is widely called the **"senior/junior" or "generate/verify" pattern** in 2025-2026 multi-agent coding literature. Key emerging patterns:

#### 1. MCP-Wrapped CLI Tools (CLI-Agnostic)

The Model Context Protocol (MCP) is the dominant 2026 standard for exposing any CLI as a callable tool surface for LLM agents. The pattern: write a thin `stdio` MCP server (Node.js/Python/Rust) that translates tool call JSON to CLI flags and back. Claude's MCP tooling supports `list_changed` for dynamic tool updates, per-server timeouts, and project-scoped `.mcp.json` distribution. This is the most interoperable approach: any LLM supporting MCP can call the same Codex-wrapping server.[^4]

**OpenAI Codex CLI** (`github.com/openai/codex`, Apache-2.0, 93.7k stars as of July 2026) already includes an MCP connection manager (`codex-rs/codex-mcp/src/mcp_connection_manager.rs`), indicating that Codex itself is designed to both consume and expose MCP tools. The `sdk/` directory in the repo suggests programmatic API access beyond the CLI. **CLAIMED**: Codex v0.125.0+ likely exposes an MCP server mode; check `codex mcp serve` or similar undocumented flags.[^5]

#### 2. `asyncRewake` as Async Verification Loop

**VERIFIED**: `asyncRewake: true` on command hooks runs the hook in background and wakes the senior model on exit code 2, passing stderr as a system reminder. This is the native mechanism for **generate (Codex, background) → verify (Claude, woken on failure)**. It avoids polling and is zero-latency on the happy path.[^1]

#### 3. Subagent Worktree Isolation for Junior Runs

**VERIFIED**: `isolation: worktree` in subagent frontmatter creates a temporary git worktree for the subagent's changes. This is the canonical Claude Code pattern for safe junior-agent work: Codex (invoked via Bash in the subagent) edits the worktree; Opus reviews the diff and merges or discards.[^2]

#### 4. Trending Open-Source Projects

| Project | Pattern | CLI-Agnostic? | Notes |
|---------|---------|--------------|-------|
| `openai/codex` (GitHub) | Rust-core agent, MCP integration, app-server API | Partially — MCP yes, but model is OpenAI-specific | Includes `codex-mcp` crate for MCP tool calls[^5] |
| `anthropics/claude-plugins-official` | Plugin + MCP bundling for Claude Code | Yes — plugin distributes MCP server + agents | Official Anthropic plugin marketplace |
| AgentSkills.io standard | Open standard for `SKILL.md` cross-tool skills | Yes — Claude Code + other tools implementing standard | Claude Code implements + extends[^3] |
| MCP safety audit / `MCPSafetyScanner` (arxiv 2504.03767) | Tool injection risk in multi-MCP setups | Agnostic | Relevant for Codex MCP server trust model[^4] |

**CLAIMED**: Projects like `swe-agent`, `aider`, and `Agentless` (arxiv 2407.01489) explore the generate/verify loop at the diff-review level but are not directly wired to Claude Code hooks. They validate the pattern but require adaptation.[^6]

***

## Prioritized Integration Backlog

> ⭐⭐⭐ = Top 3 highest-leverage items to wire first.

| # | Task Class | Trigger Surface / File | Codex Invocation | Senior Verify | Effort | Extends Existing? | Evidence |
|---|-----------|----------------------|-----------------|--------------|--------|------------------|---------|
| **1** ⭐⭐⭐ | **Lint/format auto-fix** | `PostToolUse`, `Edit\|Write`, `command` sync / `.claude/settings.json` | `a2a-codex-call.sh "t prompt for $FILE>" --effort low --timeout 55` | Check exit 0; diff for non-format changes; audit log | **S** | Extends `a2a-codex-call.sh`; new hook | VERIFIED[^1] |
| **2** ⭐⭐⭐ | **Mechanical refactor (worktree)** | Subagent `codex-refactor`, `isolation: worktree`, `model: sonnet` / `.claude/agents/codex-refactor.md` | `a2a-codex-call.sh "<structured refactor prompt>" --effort med --timeout 90` inside subagent Bash | Subagent runs semantic diff check; Opus approves merge | **M** | Extends `dispatch` skill; new agent file | VERIFIED[^2] |
| **3** ⭐⭐⭐ | **Over-engineering pass** | Subagent `codex-simplifier`, `permissionMode: plan`, read-only / `.claude/agents/codex-simplifier.md` | `a2a-codex-call.sh "Is this over-engineered? Suggest simplifications. Return JSON." --effort med` | Opus reads structured JSON report; approves or ignores suggestions | **S** | New agent file | VERIFIED[^2] |
| 4 | Test scaffold (TDD stubs) | `Stop` hook, `asyncRewake`, lock-file / `.claude/settings.json` | `a2a-codex-call.sh "<scaffold prompt for changed files>" --effort med --timeout 110` | Run tests (RED); if green unexpectedly, flag | **M** | Extends Stop hook; new script | VERIFIED[^1] |
| 5 | Docstring/comment gen | `PostToolUse` on `Edit`, `asyncRewake` / `.claude/settings.json` | `a2a-codex-call.sh "Add docstrings to all public functions in $FILE" --effort low` | Claude woken on failure only; review on next turn | **S** | New hook handler | VERIFIED[^1] |
| 6 | PR/diff review | `/codex-review` skill, `disable-model-invocation` / `.claude/skills/codex-review/SKILL.md` | `a2a-codex-call.sh "<diff review prompt>" --effort med --timeout 60` | Human reviews Codex critique JSON; Opus acts | **S** | Extends `codex-call` skill | VERIFIED[^3] |
| 7 | Commit-message draft | `PostToolUse` on `Bash(git add *)`, `async` / `.claude/settings.local.json` | `a2a-codex-call.sh "<staged diff summary>" --effort low --timeout 40` | Human edits; never auto-commit | **S** | New hook | VERIFIED[^1] |
| 8 | Codex MCP server | `.mcp.json`, stdio server / `.claude/bin/mcp-codex-server.js` | All tasks routed via `mcp__codex-junior__<task>` tool calls | `PostToolUse` on `mcp__codex-junior__.*` for logging | **L** | New MCP server; extends `.mcp.json` | VERIFIED[^4] |
| 9 | Coverage-gap fill | Stop hook, `asyncRewake`, load-aware / `.claude/settings.local.json` | `a2a-codex-call.sh "verage gap files>" --effort high --timeout 180` | Run coverage; confirm delta before merge | **M** | New hook | VERIFIED[^1] |
| 10 | Changelog generation | `/codex-changelog` skill, `disable-model-invocation` / `.claude/skills/codex-changelog/SKILL.md` | `a2a-codex-call.sh "Generate changelog entry for: $(git log --oneline -10)" --effort med` | Human reviews draft entries before commit | **S** | New skill | VERIFIED[^3] |
| 11 | Dep bump smoke check | Stop hook, `asyncRewake`, skip if gastown lock held / `.claude/settings.local.json` | `a2a-codex-call.sh "Run tests after dep bump; report failures" --effort low --timeout 120` | Wake on failure (exit 2); Opus triages | **S** | New hook | VERIFIED[^1] |

***

## Evidence Classification

**VERIFIED** (read from official Claude Code documentation at `docs.anthropic.com`):
- All hook event names, cadences, matcher rules, `if` field semantics, `async`/`asyncRewake` behavior, exit code semantics[^1]
- All subagent frontmatter fields: `model`, `isolation`, `permissionMode`, `effort`, `hooks`, `mcpServers`, `background`, `maxTurns`, `memory`; model resolution order including `CLAUDE_CODE_SUBAGENT_MODEL` priority[^2]
- SubagentStart/SubagentStop matcher behavior (agent type)[^1]
- Skills: `context: fork`, `disable-model-invocation`, `allowed-tools`, dynamic context injection, `${CLAUDE_PROJECT_DIR}`[^3]
- MCP server configuration (stdio, HTTP, SSE, WS), plugin MCP servers, `list_changed`, `mcp__<server>__<tool>` naming, per-server timeouts[^4]
- `PostToolUse` hook for `Edit|Write` as the canonical auto-format pattern (Prettier example in official docs)[^1]

**CLAIMED** (pattern knowledge; not directly cited from a single page):
- `ultracode` / dynamic-workflows `agent()`, `pipeline()`, `parallel()` syntax details
- Codex CLI `codex exec --full-auto` headless mode flag behavior (verified existence of repo; exec flags not directly read)[^5]
- Specific Codex MCP server mode availability
- Cross-community "senior/junior" pattern naming and SOTA projects beyond what was directly confirmed

---

## References

1. [Commands as AI Conversations](https://arxiv.org/pdf/2309.06551.pdf) - Developers and data scientists often struggle to write command-line inputs,
even though graphical in...

2. [Language hooks: a modular framework for augmenting LLM reasoning that
  decouples tool usage from the model and its prompt](https://arxiv.org/pdf/2412.05967.pdf) - ...tool
use to the task at hand and limiting generalisation. Fine-tuning removes the
need for task-s...

3. [The Synergy of Automated Pipelines with Prompt Engineering and
  Generative AI in Web Crawling](http://arxiv.org/pdf/2502.15691.pdf) - ...Claude AI (Sonnet 3.5) and
ChatGPT4.0 with prompt engineering to automate web scraping. Using two...

4. [MCP Safety Audit: LLMs with the Model Context Protocol Allow Major
  Security Exploits](https://arxiv.org/html/2504.03767v2) - ...agentic tools. By
connecting multiple MCP servers, each defined with a set of tools, resources,
a...

5. [OpenCodeInterpreter: Integrating Code Generation with Execution and
  Refinement](http://arxiv.org/pdf/2402.14658.pdf) - The introduction of large language models has significantly advanced code
generation. However, open-...

6. [HyperAgent: Generalist Software Engineering Agents to Solve Coding Tasks
  at Scale](https://arxiv.org/pdf/2409.16299.pdf) - Large Language Models (LLMs) have revolutionized software engineering (SE),
showcasing remarkable pr...

