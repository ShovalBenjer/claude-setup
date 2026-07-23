# Claude Model Selection

## Default

- Use `claude-sonnet-5` as the global Claude Code default. This avoids the stale TUI picker label and keeps normal sessions off expensive Opus/Fable unless the task needs them.
- Keep adaptive thinking globally disabled with `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`. Use explicit effort/model choices per task instead of global adaptive behavior.
- Use `/effort ultracode` for substantive work so Claude writes dynamic workflows instead of only chatting through a plan.
- Treat Sonnet 5 as the everyday execution model for coding, analysis, and most agent work.
- Treat Opus as the orchestrator when the task is broad enough to justify it: decomposition, parallel fanout, subagent assignment, review, synthesis, and escalation decisions.
- Escalate the lead to `/model claude-opus-4-8[1m]` only when the work needs a large shared context window.
- Let workflow phases choose models dynamically: Sonnet 5 for default implementation and structured analysis, Opus for orchestration and synthesis, Haiku for cheap scans and summarization, Fable only for unusually hard long-horizon work.
- Runtime agents from Foundry/OpenAI/HeyGen/ElevenLabs are not model choices for coding work. Use them only through Runtime Agents Division or Voice and Media Studio for runtime/eval/media tasks.
- Keep first-party Claude routing unless the user explicitly asks for Z.ai fallback.
- Spawned subagents default to `claude-sonnet-5`. Override deliberately: Haiku for inventory/summarization, Opus for high-risk review/synthesis, Fable only for one hard lead thread.
- Never fork or paste the full transcript into subagents. Give each worker a compact context pack: goal, files/commands allowed, evidence required, write scope, stop condition, and how results will be verified.

## Current Aliases

- `fable` -> `claude-fable-5`: hardest, longest-running, ambiguous investigations.
- `opus` -> `claude-opus-4-8`: orchestration, architecture, subagent fanout, review, synthesis, high-autonomy coding.
- `sonnet` -> `claude-sonnet-5`: daily coding and implementation.
- `haiku` -> `claude-haiku-4-5`: fast/simple edits, summarization, cheap parallel work.
- Shell launchers in `~/.local/bin`: `fable`, `sonnet5`, `opus48`, `haiku45`.
- Persistent default switches: `claude-provider fable`, `claude-provider sonnet5`, `claude-provider opus48`, `claude-provider haiku45`, `claude-provider claude`.

## Usage

- Start normal sessions with the global default `claude-sonnet-5`, or run `sonnet5` explicitly.
- Use `fable`, `opus48`, or `haiku45` for one-shot sessions on those models without touching the persistent default.
- Use `claude-provider sonnet5|fable|opus48|haiku45` to change the persistent default.
- Immediately switch serious sessions to `/effort ultracode`; it is session-only and cannot be persisted in settings.
- Use `/model claude-opus-4-8[1m]` for hive lead sessions when scope spans many files, multiple repos, long transcripts, large specs, big generated artifacts, or repeated compaction would hide decisions from the orchestrator.
- Keep auto-compaction enabled. Before compaction, preserve task state, active worker findings, decisions, open risks, verification evidence, and next action.
- On multi-file, ambiguous, risky, or cross-system work, escalate the lead to Opus and spawn parallel subagents early for discovery, implementation options, risk review, and verification.
- Keep Opus in the lead loop only after that escalation; otherwise Sonnet 5 coordinates normal work.
- Do not reduce Opus to a single upfront plan when the task benefits from parallel investigation or independent critique.
- In each workflow, route by phase:
  - Discover: Haiku or Sonnet workers in parallel, depending on risk.
  - Decide: Sonnet for normal decisions; Opus lead compares findings and chooses the path when risk or breadth warrants it.
  - Build: Sonnet workers own scoped files or components.
  - Review: separate Sonnet or Opus reviewers for tests, security, architecture, and regressions.
  - Synthesize: Sonnet 5 merges normal findings; Opus lead merges high-risk or cross-system findings, resolves contradictions, and states verification.
- Use `/model claude-fable-5` or `claude-provider fable` only for work that justifies higher cost and possible safety fallback.
- Use `/model claude-opus-4-8[1m]` for long-context Opus orchestration and `/model sonnet[1m]` for long-context worker execution.
- Keep fallback chain cheap by default: `haiku` behind the Sonnet 5 default, or `sonnet`, then `haiku` behind Opus/Fable defaults.
