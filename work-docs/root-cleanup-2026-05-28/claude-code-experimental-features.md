# Claude Code Power-User Feature Punch List

Researched 2026-04-30 by claude-code-guide subagent. Curated for your existing setup (voice/visual explainer hooks, ElevenLabs + gpt-image, 25 codex skills, auto mode).

> ⚠️ I have NOT verified each item with a live test. Treat this as a starting menu — confirm each feature exists in your installed Claude Code version (`v2.1.123`) before wiring. Some items below are flagged "experimental" and may behave differently than documented.

---

## 1. Hook event types beyond `UserPromptSubmit`

You only use `UserPromptSubmit` today. These others are documented:

### `SubagentStart` / `SubagentStop`
Fires when subagents spawn or finish. Matcher supports agent type names.
- **Fit for you**: chain voice/visual narration when `code-reviewer` or `feature-investor` finishes. "Subagent done — here's the 60-word summary."
- **Wire**:
  ```json
  "hooks": {
    "SubagentStop": [{
      "matcher": "code-reviewer",
      "hooks": [{"type": "command", "command": "$HOME/.claude/hooks/completion-voiceover.sh"}]
    }]
  }
  ```

### `PreToolUse` / `PostToolUse` / `PostToolBatch`
Fires before/after tool execution. `PreToolUse` exit code 2 blocks the call.
- **Fit for you**: credit guard for ElevenLabs (count chars before TTS, block if budget exceeded). Block destructive `Bash(rm -rf*)` even if Claude tries it.
- **Wire**:
  ```json
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "$HOME/.claude/hooks/credit-guard.sh"}]
    }]
  }
  ```

### `PreCompact` / `PostCompact`
Fires before/after context compaction. Matcher: `manual` vs `auto`.
- **Fit for you**: snapshot eval baselines / current state before Claude compacts and forgets. Auto-update memory on compact.
- **Wire**:
  ```json
  "hooks": {
    "PreCompact": [{
      "hooks": [{"type": "command", "command": "$HOME/.claude/hooks/snapshot-state.sh"}]
    }]
  }
  ```

### `SessionStart` / `SessionEnd`
Lifecycle hooks. `SessionStart` context: `source` (startup/resume/clear/compact), `model`.
- **Fit for you**: load project-specific narration prompts on resume; persist eval results on end.
- **Wire**:
  ```json
  "hooks": {
    "SessionStart": [{
      "hooks": [{"type": "command", "command": "$HOME/.claude/hooks/load-context.sh"}]
    }]
  }
  ```

### `Notification`
Fires when Claude sends system notifications (permission prompts, idle prompts).
- **Fit for you**: trigger desktop notify/sound when auto-mode blocks something or when Claude is idle waiting for input.

### `PermissionDenied` / `StopFailure` (auto-mode era)
Fires when auto-mode classifier blocks a tool call or when Stop hook errors.
- **Fit for you**: voice alert "auto mode just blocked X" so you don't miss it overnight.

> ⚠️ **`FileChanged`, `CwdChanged`, `InstructionsLoaded`** — research agent listed these but I'm less confident they exist as named events in v2.1.123. Verify in `code.claude.com/docs/en/hooks.md` before wiring.

---

## 2. Experimental / recently-launched features

### Forked subagents (`CLAUDE_CODE_FORK_SUBAGENT=1`) — experimental
Subagents inherit full conversation history instead of starting fresh. Shares prompt cache with parent.
- **Fit for you**: spawn voice + visual explainer in parallel without re-explaining context.
- **Wire**: `export CLAUDE_CODE_FORK_SUBAGENT=1` then use `/fork <task>`.

### Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) — experimental
Multiple agents coordinate across sessions via `SendMessage`. Each gets own context.
- **Fit for you**: parallel evals across many cases; coordinate cleanup-crew + red-team + mutation-runner without single-context bottleneck.

### Worktree Isolation (GA)
Each subagent gets own git worktree under `.claude/worktrees/<name>/`. Auto-cleanup if no changes.
- **Fit for you**: run cleanup-crew, mutation-runner, red-team in parallel without branch conflicts.
- **Wire**: subagent frontmatter: `isolation: worktree`.

### Skills with frontmatter (`disable-model-invocation`, `paths`, `allowed-tools`, `effort`, `model`)
Skills auto-invoke based on description matching + path glob. Per-skill model + effort overrides.
- **Fit for you**: convert your codex skills into Claude skills with proper auto-invocation. Run `eval-runner` at `effort: max` and `model: opus`; route exploratory `web-inspect` to `model: haiku`.
- **Wire**: `~/.claude/skills/<name>/SKILL.md` with frontmatter:
  ```yaml
  ---
  name: voice-explainer
  description: When user signals out-of-focus or asks for narration
  paths: "**/*"
  model: sonnet
  effort: low
  allowed-tools: ["Bash($HOME/.claude/bin/generate-voice.py *)"]
  ---
  ```

### Subagent Persistent Memory (`memory: user|project|local`)
Subagents maintain MEMORY.md across sessions, read first 200 lines on startup.
- **Fit for you**: code-reviewer learns project patterns over time; eval-runner accumulates benchmark baselines.

### `/schedule` Routines (GA, ~15 runs/24h cap)
Cron-like scheduled tasks with `/schedule check deploy status every 10m`.
- **Fit for you**: nightly eval pass; hourly Seekapa OTP-auth compliance check.

### `/batch` Parallel Worktree Agents (GA)
Decompose task into 5–30 units; spawn isolated subagents in worktrees; each opens a PR.
- **Fit for you**: parallelize property-test-gen across `src/` modules in one shot.

### `/loop` Self-Pacing (GA)
Run prompt repeatedly; omit interval for self-paced loops.
- **Fit for you**: autonomous overnight cleanup loops (with voice-narrated status updates).

### Status Line (`/statusline`) — GA
Terminal indicator showing model, mode, effort, context %.
- **Fit for you**: at-a-glance verification that auto-mode is on and you're using opus + correct effort.

---

## 3. Settings.json features that aren't widely known

### Permissions allow/deny lists (GA)
```json
"permissions": {
  "allow": ["Bash(npm test)", "Bash(git status)", "Read(src/**)"],
  "deny": ["Bash(rm -rf *)", "Bash(curl *)", "Bash(git push --force*)"],
  "defaultMode": "auto"
}
```
**Fit**: lock down credit-burning curls, block dangerous git ops site-wide.

### Per-skill / per-subagent model + effort override
Frontmatter: `model: haiku|sonnet|opus|inherit`, `effort: low|medium|high|xhigh|max`.

### `allowed-tools` whitelist in skills
Pre-approve tools without per-use permission dialog. Wildcard supported.

### MCP Server Scoping
Define MCP servers globally, per-subagent, or inline. Telegram/Figma/Gmail can be scoped to specific agents instead of always-on.

### Output styles (`outputStyle`)
`compact|verbose|minimal`. Useful: `minimal` makes voice-narration cleaner (less code-block noise).

### Env injection (`env: {}`)
Already standard; pass KeyVault secrets, debug flags, model overrides into all subprocesses.

### Hooks scoped to skills (skill-frontmatter `hooks:`)
Skill-scoped hooks fire only while skill is active. E.g. PostToolUse Edit-lint inside a code-gen skill.

---

## 4. CLI / interactive shortcuts

| Shortcut | What | Fit for you |
|----------|------|-------------|
| `!cmd` | Inline bash | Quick `!git status` mid-conversation |
| `#key` | Memory shortcut | `#voice-prefs` injects memory entry inline |
| `@path` | File mention with autocomplete | `@src/handler.py` |
| `@agent-name` | Force specific subagent | `@code-reviewer` instead of routing |
| `/loop` | Self-paced loop | Overnight automation |
| `/context` | Visualize context usage | Spot bloat from skills/memory |
| `/diff` | Per-turn git-like diffs | Audit AI changes turn-by-turn |
| `ESC` | Cancel current response | Stop runaway evals |
| `ESC ESC` | Revert last turn | Roll back bad code-gen |

---

## 5. Env vars worth knowing

| Variable | Purpose |
|----------|---------|
| `CLAUDE_CODE_FORK_SUBAGENT=1` | Forked subagents (experimental) |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | Agent teams (experimental) |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50` | Trigger compaction earlier |
| `CLAUDE_CODE_SUBAGENT_MODEL=haiku` | Cheap exploratory subagents |
| `BASH_MAX_TIMEOUT_MS=600000` | 10-min bash timeout |
| `CLAUDE_CODE_SIMPLE=1` | Minimal system prompt (test TTS readability) |

---

## My recommendation: pick 5 to actually wire this week

If I had to pick a tight first wave from this list, given your setup:

1. **`SubagentStop` hook → voice narration** — when feature-investor / red-team / mutation-runner finishes, get a 60-word ElevenLabs recap. Closes a feedback loop you don't have today.
2. **`PreToolUse` hook → ElevenLabs credit guard** — count chars before TTS API call, block if monthly budget exceeded. You already mentioned credit caution.
3. **`PreCompact` hook → snapshot to memory** — before Claude forgets, dump current eval baselines / TODO / open threads to `~/.claude/projects/<proj>/memory/`. Preserves overnight-run state.
4. **Convert codex skills to Claude skills with frontmatter** — start with voice-explainer + visual-explainer + cleanup-crew. Add `paths:` + `model:` + `effort:` to each. Auto-invocation will fire correctly without your existing UserPromptSubmit regex layer.
5. **`/statusline` config** — show `model | effort | mode | context%` so auto-mode is verifiable at a glance and you spot context bloat early.

Worth deferring:
- Agent teams / forked subagents — experimental, behavior may change.
- `/batch` 30-agent parallelization — high blast radius if misconfigured.
- Persistent subagent memory — wait until your `MEMORY.md` proven first.

---

## Sources cited by research agent

- code.claude.com/docs/en/hooks.md
- code.claude.com/docs/en/sub-agents.md
- code.claude.com/docs/en/skills.md
- code.claude.com/docs/en/settings.md
- code.claude.com/docs/en/commands.md
- code.claude.com/docs/en/env-vars.md
- mindstudio.ai blog post on Q1 2026 updates
- builder.io blog post on March 2026 changes

Verify each before wiring — agent did not run code or call APIs to confirm behavior.
