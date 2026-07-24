# Claude Model Selection

## Default (Opus 5 era — updated 2026-07-24, ADR-0015)

- **Lead default is `opus` (= Opus 5).** Opus 5 lands within 0.5% of Fable 5's peak at HALF the cost per task ($5/$25, same as Opus 4.8), and is the Claude Max default. For work that wants near-frontier quality, Opus 5 is the cost-effective way to get it — roughly double the runway of Fable. Set in `~/.claude/settings.json` as `"model": "opus"`.
- **Fable is now exceptional-only, not the hard-work default.** Reserve `fable` for the single genuinely hardest long-horizon thread where the last 0.5% changes the outcome AND budget allows. Defaulting hard work to Fable is what burned the token budget; Opus 5 is the replacement. (`best` alias = Fable where the org has it, else latest Opus.)
- **Workers stay cheap: `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5`.** Fan-out subagents must not inherit the Opus 5 lead — set this env var (now live) so a workflow spawning 5 agents costs Sonnet, not Opus. Haiku for inventory/scan workers.
- Keep adaptive thinking disabled (`CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`); choose effort explicitly. Persist `effortLevel: xhigh` + `ultracode: true` (Opus 5 supports low/medium/high/xhigh/max). `/effort ultracode` is the session-only orchestration mode; `effortLevel` cannot store the literal `ultracode`.
- `opus[1m]` selects the 1M-context Opus 5 variant. NOTE: `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` is currently set (deliberate cost control), so 1M is OFF and the `[1m]` suffix is moot until that env var is removed. Re-enable only when a task genuinely needs the large window and the per-turn cost is acceptable.
- Let workflow phases choose models dynamically: Sonnet 5 for default implementation and structured analysis, Opus 5 for the lead/orchestration/synthesis, Haiku for cheap scans, Fable only for the rare hardest thread.
- Mythos 5 sits above Fable (cybersecurity/exploit tiers, approved orgs only) — not a coding-work option here.
- Runtime agents from Foundry/OpenAI/HeyGen/ElevenLabs are not model choices for coding work. Use them only through Runtime Agents Division or Voice and Media Studio for runtime/eval/media tasks.
- Keep first-party Claude routing unless the user explicitly asks for Z.ai fallback.
- Spawned subagents default to `claude-sonnet-5`. Override deliberately: Haiku for inventory/summarization, Opus for high-risk review/synthesis, Fable only for one hard lead thread.
- Never fork or paste the full transcript into subagents. Give each worker a compact context pack: goal, files/commands allowed, evidence required, write scope, stop condition, and how results will be verified.

## Current Aliases (Claude Code built-in, verified vs model-config doc 2026-07-24)

- `opus` -> **Opus 5** (latest Opus): the lead/default. Near-Fable quality, half the cost.
- `opus[1m]` -> Opus 5 with 1M context (moot while `CLAUDE_CODE_DISABLE_1M_CONTEXT=1`).
- `fable` -> `claude-fable-5`: the rare hardest thread only (budget-gated; often exhausted).
- `best` -> Fable 5 where available, else latest Opus. `default` -> account/org recommended.
- `sonnet` -> `claude-sonnet-5`: daily coding, implementation, and the subagent default.
- `haiku` -> latest Haiku: fast/simple edits, summarization, cheap parallel scans.
- `opusplan` -> Opus during plan mode, Sonnet for execution (cost-aware plan/build split).
- Aliases auto-track the newest version of each family, so `opus` follows Opus forward.
- Legacy shell launchers in `~/.local/bin` (`fable`, `sonnet5`, `opus48`, `haiku45`) still
  pin their exact IDs; `opus48` = Opus 4.8 specifically, distinct from the `opus`=Opus 5 alias.

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
