# ADR-0015 — Opus 5 is the lead default; Fable is exceptional-only

Date: 2026-07-24. Status: accepted. Supersedes the Opus-4.8/Fable routing in ADR-0006-era model-selection.

## Context

The session ran out of Fable 5 credits mid-workflow (3 of 4 mapping agents died
"out of usage credits, resets Jul 26"). The prior routing defaulted hard/long-horizon
work to Fable, which is the most expensive tier — so the operator kept hitting the
ceiling exactly on the work that mattered most. Same day, Anthropic released **Claude
Opus 5** (VERIFIED from anthropic.com/news/claude-opus-5 + code.claude.com/docs/en/model-config):
model id `claude-opus-5`, alias `opus` now resolves to it; $5/$25 per Mtok (same as
Opus 4.8); "within 0.5% of Fable 5's peak score, but at half the cost per task"; the
new default on Claude Max; supports effort levels low/medium/high/xhigh/max; `opus[1m]`
gives the 1M variant. Fable 5 and Mythos 5 remain higher tiers (Mythos: cybersecurity/
exploit, approved orgs only).

## Decision

1. **Lead default = `opus` (Opus 5)**, set in `~/.claude/settings.json` (`"model": "opus"`).
   Near-Fable quality at half the per-task cost is the cost-effective way to get the
   frontier-adjacent output the operator actually wants; it roughly doubles the runway.
2. **Fable becomes exceptional-only** — reserved for the single hardest long-horizon
   thread where the last 0.5% changes the outcome and budget allows. It is no longer the
   default target for "hard work."
3. **Workers stay on Sonnet 5** via `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5` (now
   live). A fan-out of N agents must cost Sonnet, not Opus — the dead mapping workflow
   would have been far cheaper this way.
4. **Effort**: keep `effortLevel: xhigh` + `ultracode: true` (both valid on Opus 5).
5. **1M context stays off** (`CLAUDE_CODE_DISABLE_1M_CONTEXT=1`) as deliberate cost
   control; re-enable per-task with `opus[1m]` only when the window is genuinely needed.

## Consequences

- Directly fixes the recurring token-exhaustion pain: the expensive tier is no longer
  the default, and workers are decoupled from the lead cost.
- Live sessions (3 open) do not switch retroactively — each needs `/model opus` or a
  restart; only new sessions inherit the settings default. (STAGED until the operator
  restarts; cannot be verified from this session.)
- Aliases auto-track forward, so `opus` follows future Opus releases without a config
  edit; `opus48` still pins Opus 4.8 for A/B needs.
- Revisit if Opus 5's quality proves insufficient for a specific class of work — then
  that class (not the default) escalates to Fable.
