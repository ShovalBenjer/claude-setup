---
name: codex-call
description: Bridge Codex → Codex CLI for review, eval, automation, and any work where gpt-5.5 with explicit reasoning effort fits better than Codex. Use for /review on a PR or branch, batch test generation, codex automation prompts, second opinions from a different model family, or when Codex is the orchestrator and Codex should be the executor. Triggers on "/review", "ask codex", "have codex do it", "codex review", "/codex".
model: sonnet
allowed-tools: ["Bash(/home/shovalbe/.local/bin/codex *)", "Bash($HOME/.codex/automations/run-codex-automation.sh *)"]
---

# codex-call — Codex orchestrator, Codex executor

## Why this skill exists

Codex Opus is the orchestrator. Codex (gpt-5.5) is the executor. Don't collapse the two. When the task is "do this concrete thing" (review a PR, generate boilerplate tests, run an automation prompt, get a second opinion from a different model family), shell out to Codex instead of doing it inline.

The two models complement, not replace, each other. Use both.

## Invocation patterns

### Pattern A — code review on a PR or branch

```bash
codex review --base origin/master HEAD              # current branch vs master
codex review <PR_NUMBER>                            # GitHub PR (needs gh)
codex review --files "src/handler.py,src/router.py" # specific files
```

`codex review` is a built-in non-interactive subcommand. Output is structured review markdown. Pipe through `tee` if you want a saved artifact:

```bash
codex review --base origin/master HEAD | tee /tmp/codex-review-$(date -u +%Y%m%dT%H%M%SZ).md
```

### Pattern B — one-shot exec with explicit model + effort

```bash
codex exec --full-auto \
  -m gpt-5.5 \
  -c reasoning_effort=high \
  -C "$PWD" \
  --output-last-message /tmp/codex-out.md \
  - <<< "Generate property-based tests for src/validators.py covering OWASP input cases. No mocks."
```

Effort levels: `low` (cheap, 1-shot answers), `medium` (default, routine), `high` (deep reasoning, reviews and refactors), `xhigh` (maximum, architecture decisions only — slow + expensive).

### Pattern C — run a Codex automation prompt

```bash
~/.codex/automations/run-codex-automation.sh a09-forge-loop-compliance-score
```

The runner handles locking, logging, and `codex exec --full-auto` invocation. Effort defaults to `medium` per `~/.codex/config.toml`. To override per run, prefix with `CODEX_REASONING_EFFORT=high` (the runner reads this env via the codex config override pattern).

### Pattern D — fork an existing Codex session for a tangent

```bash
codex fork --last       # branch off the most recent codex session
codex resume --last     # continue the most recent
```

## When to use Codex vs Codex vs subagent

| Task type | Use |
|---|---|
| Orchestration, planning, multi-file design | Codex Opus (this session) |
| Concrete review of a single PR/branch | `codex review` |
| Boilerplate test gen, single-file refactor | `codex exec` with effort=medium |
| Architecture review, multi-domain critique | Codex Opus + `codex review` (both, compare) |
| Cheap parallel exploration | Codex subagents at `model: haiku` |
| Scheduled night automations | Codex via `run-codex-automation.sh` (cron-driven) |
| Multi-model debate / second opinion | Codex (one perspective) + Codex (another) — compare outputs |

## Effort × cost guidance

`gpt-5.5 high` is roughly 4-6× the latency of `gpt-5.5 medium` and proportional cost. Use `high` only when:
- The task is a code review or architectural decision
- The output is a one-time artifact (not iterated)
- You'd otherwise have to re-run with `low`/`medium` and waste tokens

For day-to-day execution prefer `medium`. For exploration prefer `low` or Codex Haiku.

## Output handling

Codex writes the final assistant message to `--output-last-message <path>` (used by the automation runner). For interactive `codex exec` use `tee` to capture. For `codex review`, output is stdout.

## Safety

- Codex `--full-auto` permits file writes and shell execution within the working tree. Never run with `--full-auto` against `$HOME` directly without a worktree boundary.
- The user's `~/.codex/config.toml` already trusts `/home/shovalbe`, `/home/shovalbe/projects/*`, etc. — Codex will not prompt for trust.
- Codex respects the deny-list patterns in `~/.codex/config.toml` `[shell_environment_policy]`.
- Per project memory: destructive operations still need explicit per-action OK from the user, even when delegating to Codex.

## Anti-patterns

- Don't shell out to `codex exec` for tasks Codex can do trivially in 1-2 turns (asks → ask, simple file reads → use Read tool).
- Don't use `codex` as a fallback when Codex is rate-limited — pick the right tool for the task, not as a substitute.
- Don't pipe codex output back into Codex verbatim — it's another model's voice; quote selectively or extract the structured parts.
