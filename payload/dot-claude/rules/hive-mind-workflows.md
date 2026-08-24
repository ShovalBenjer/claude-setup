# Hive Mind Workflow Rules

## Operating Mode

- For substantive work, use `/effort ultracode` so Claude creates dynamic workflows with explicit phases, agents, model choices, and verification.
- Keep Sonnet 5 as the normal lead and spawned-agent default. Escalate the lead to Opus only when decomposition, worker selection, conflict resolution, or final synthesis is too broad or risky for Sonnet.
- Route through `~/.claude/rules/gastown-company-registry.md`. The registry is the source of truth for persona ownership and skill routing.
- For high-fanout or repeated handoff workflows, also load `~/.claude/rules/latent-vector-workflows.md` and use a dual human/machine state channel.
- Treat projects as client accounts. Do not create one-off project personas when a generalized company role can take a project context pack.
- Foundry/OpenAI/HeyGen/ElevenLabs agents are runtime, eval, media, or deployed project-model surfaces only. They are never coding subagents.
- If the lead needs the whole working set in memory, switch it to `/model claude-opus-4-8[1m]`. Use this for broad repo audits, long research sessions, multi-agent synthesis, large PR reviews, migrations, or anything that would otherwise compact away decisions.
- Auto-compaction stays enabled. The lead must compact into a durable handoff: goal, current phase, active skills, agent roster, key decisions, evidence, changed files, blockers, next action.
- Use parallelism only when work has independent branches. Prefer one lead plus 3-5 focused workers; scale beyond that only for broad research or large audits.
- Workers must have named roles, owned paths or questions, expected output shape, and a stop condition.
- Do not let the lead keep implementing while workers are still investigating unless the work is intentionally independent.
- When fanout exceeds 3 workers, require a shared state artifact: JSONL, SQLite, DuckDB, vector index, or notebook. Long prose handoffs are a defect in that mode.
- Use embeddings and retrieval for routing and recall, never as proof. Evidence still requires path, URL, command, artifact, or eval output.

## Dynamic Model Routing

- Fable: only for hardest long-horizon work, ambiguous architecture, or broad autonomous investigations where cost and fallback risk are justified.
- Opus 4.8: escalated lead orchestration, decomposition, architecture, risk arbitration, review synthesis, and final decision-making when the scope justifies it.
- Opus 4.8 1M: same lead role when the hive needs a large shared context window.
- Sonnet 5: default session model, default spawned-agent model, implementation, focused analysis, test repair, structured extraction, and most teammate work.
- Haiku: cheap scans, inventory, summarization, routing prechecks, and low-risk mechanical tasks.
- Keep `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5` so spawned agents do not accidentally inherit expensive Opus/Fable lead sessions. Override per-agent only when the task explicitly needs Haiku, Opus, or Fable.

## Skill Coverage

- Before a workflow runs, the lead must select the relevant skills from the installed skill set and name why each selected skill is active.
- If no skill applies, state `skills: none` with the reason. Do not silently skip skill routing.
- If an installed skill has no clear trigger, route, or use case, mark it as `unwired skill` and propose one of: add trigger text, add frontmatter, merge into another skill, or remove it.
- Skills are routed by use case, not by name nostalgia. A stale or duplicate skill is a defect.
- Full skill ownership lives in `gastown-company-registry.md`. The short routes below are only the fast mental model.

## Default Skill Routes

- Decision and stakeholder quality: `LTMD`, `decision-grade`, `requirement-anchor`, `premortem`.
- Azure and cloud operations: `azure-runtime`, `azure-audit`, `azure-activity-watch`, `azure-cert-coach`, `agent-builder`.
- Implementation quality: `review`, `coverage-enforcer`, `testing-pyramid`, `refactor-pre-push`.
- Cross-agent execution: `codex-call`, `dispatch`, `openai-agents`.
- Writing and communication: `blog`, `meeting-notes`, `jira-task-draft`, `pii-scrubber`.
- Product and interface work: `ui-ux-pro-max`, `blonde-designer`.
- Persona or conversation mode: `persona`.
- Context-bounded analysis: `context-bounded-analyst`.

## Workflow Pattern

1. Classify the task: research, build, debug, review, deploy, write, cloud ops, product/design, or stakeholder decision.
2. Select company personas, skills, and models explicitly from `gastown-company-registry.md`.
3. Choose relay mode: prose-only for small work, dual-channel latent/vector state for high-fanout or recursive work.
4. Spawn independent workers only where parallelism reduces risk or time.
5. Require structured worker returns: claim, evidence, changed files or checked sources, confidence, open risks, and state-record id when using the latent/vector relay.
6. Run an adversarial review pass for risky work.
7. Have Sonnet synthesize normal work; escalate to Opus for high-risk or cross-system synthesis. Final output must separate verified facts, synthesis, and remaining risk.
