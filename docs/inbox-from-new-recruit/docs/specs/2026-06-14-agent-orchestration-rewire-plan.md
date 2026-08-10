# Agent Orchestration Rewire Plan

Date: 2026-06-14
Owner: Shoval
Role of this document: external-helper diagnosis and target-state spec for Claude, Codex, Hive, MCP startup, workflows, effort modes, skills, personas, testing pyramids, and agentic evals.

## Bottom Line

The current direction is right: Codex is the source-of-truth runtime, Claude is the interactive compatibility worker, and Hive is the shared task bus. The wiring is not yet at the standard implied by the plans.

The biggest problem is not "which model" or "more MCPs." It is that the control loops are incomplete:

- MCPs are not consistently lazy-loaded across Claude and Codex.
- Claude health still has a bypass path that hits the bubblewrap/env-scrub failure.
- Hive has a real bead bus, but the claim-close-reaper loop is broken: current bead count is `open=86`, `closed=2`, `killed=1`.
- Claude hooks claim voice/visual/workflow automation exists, but `UserPromptSubmit` and `PostToolUse` are empty in `~/.claude/settings.json`.
- `/workflows` exists in Claude session artifacts, but it is not yet a first-class routing plane tied to Hive beads, budgets, evidence, and eval gates.
- `/effort ultracode` exists as a user intention and backup-era setting, but the live runtime default is still medium-reasoning Codex automations plus Claude `effortLevel=high`.

The target state should be a small orchestration control plane, not a pile of always-on tools.

## Immediate Answers

### Why are MCPs starting?

Because Claude and Codex are configured differently.

Codex has explicit lazy-disable entries for several MCP servers:

- `playwright`: `enabled = false`
- `realize-mcp`: `enabled = false`
- `brand24`: `enabled = false`
- `atlassian`: present in `~/.codex/config.toml`, but missing an explicit `enabled = false`

Claude is stricter in `settings.local.json` about project MCP startup:

- `enableAllProjectMcpServers: false`
- `enabledMcpjsonServers: []`

But Claude still has plugin and MCP permission surfaces for Atlassian, Playwright, and HeyGen. A live launcher-based check on 2026-06-14 returned:

```text
plugin:heygen:heygen ... Failed to connect
atlassian ... Failed to connect
playwright ... Pending approval
```

So the current answer is:

- Codex mostly uses lazy loading.
- Claude is not cleanly lazy-loaded because plugin MCPs and global MCP registrations still get health-checked or exposed.
- Atlassian should be explicitly disabled in Codex unless the session asks for Jira/Azure DevOps/Atlassian work.
- HeyGen should not be part of the default Claude MCP surface unless the task is video/avatar generation.

### Do we use lazy loading?

Partially.

The intended policy in `mcp-activation` is correct: keep managed MCP servers disabled in config, activate narrowly with `codex-with-mcp`, and hydrate secrets only when required. Codex aligns with that policy for Playwright, Brand24, and Realize. Claude does not fully align yet because plugin MCP surfaces remain visible and a direct `claude mcp list` path still fails unless launched through the scrub-disabling launcher.

### What is `4%` in the prompt?

That is context-window usage, not battery. Your Claude statusline reads `.context_window.used_percentage`, floors it, and prints it next to the context bar. In the prompt fragment:

```text
4% > codexv .
```

`4%` means the session context is only about 4 percent used. The `~` is your home directory. The branch/status text after it is git state.

## Verified Current State

### Claude

Active files checked:

- `~/.claude/settings.json`
- `~/.claude/settings.local.json`
- `~/.claude/bin/claude-launcher.sh`
- `~/.claude/bin/statusline.sh`
- `~/.claude/plugins/installed_plugins.json`

Current Claude facts:

- Adaptive thinking is disabled: `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`.
- Nonessential traffic is disabled.
- `defaultMode` is `bypassPermissions`, with broad local permissions in settings.local.
- Bash `PreToolUse` uses `~/.codex/hooks/coverage-enforcer.sh`, not a direct RTK rewrite wrapper.
- `UserPromptSubmit` is empty.
- `PostToolUse` is empty.
- `SessionStart`, `PreToolUse`, `PreCompact`, and `Stop` hooks exist.
- `enabledPlugins` includes `understand-anything`.
- Installed plugin registry still lists `ralph-loop`, `understand-anything`, and `telegram`.
- The live launcher path sets `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=0`.
- Direct `claude mcp list` failed with the bubblewrap/env-scrub error; launcher-based invocation worked but reported failed/pending MCPs.

Diagnosis: Claude is usable, but the runtime has two competing entrypoint realities. Interactive launcher invocations are patched. Direct binary/non-interactive invocations can still fail. This is exactly the kind of split that makes multi-session operation unreliable.

### Codex

Active files checked:

- `~/.codex/config.toml`
- `~/.codex/RTK.md`
- `~/.codex/skills/mcp-activation/SKILL.md`
- `~/.codex/automations/run-codex-automation.sh`
- `~/.codex/automations/env/*.env`

Current Codex facts:

- Default model: `gpt-5.5`.
- Default reasoning effort: `medium`.
- RTK is the command boundary.
- MCP lazy-loading policy exists and is mostly reflected in config.
- Understand Anything plugin is enabled.
- User systemd timers are the scheduler of record.
- Current active timers: 9 Codex automation timers, with `c02-engineering-review-sweep` next at 2026-06-15 09:30 IDT.

Diagnosis: Codex is the cleaner base. Keep it as the source-of-truth runtime. Do not move orchestration authority back into Claude.

### Hive

Active files checked:

- `~/.hive/bin/hive.py`
- `~/.hive/rigs.yaml`
- `~/.hive/rigs.draft.yaml`
- `docs/specs/2026-05-13-hive-adoption-plan.md`
- `docs/specs/2026-05-17-systemd-hive-automation-map.md`
- `docs/audits/2026-06-09-stack-modernization-and-hive-upgrade.md`

Current Hive facts:

- Hive DB exists at `~/.hive/beads.db`.
- CLI supports create, claim, close/list semantics through SQLite.
- Active rigs are `cs-agent`, `qc-telephony-api`, `video-understanding`, and `campaign-analysis`.
- Current bead status count:
  - `open`: 86
  - `closed`: 2
  - `killed`: 1
- By role:
  - `polecat open`: 40
  - `dogs open`: 19
  - `deacon open`: 14
  - `witness open`: 13

Diagnosis: Hive is real as storage, but not real as an execution loop. It is currently closer to a backlog log than a living multi-agent work bus.

## Target Architecture

### Control Plane

Use these authority boundaries:

- Codex: scheduler, source-of-truth config, automation runner, quality gate executor.
- Claude: interactive operator shell, fast task shaping, compatibility worker, subagent UX when the user is actively steering.
- Hive: shared work bus, claim/close ledger, evidence ledger, role routing.
- MCP: on-demand tool adapters only.
- Skills: local procedure library, selected by intent and constrained by task scope.
- Personas: reviewer/judge lenses, not uncontrolled always-on voices.
- Evals: release and loop gates, not after-the-fact reports.

### Workflow Model

Every meaningful workflow should be represented as:

```text
intent -> scope -> bead/workflow id -> role -> context pack -> agents -> evidence -> eval/deacon gate -> close
```

The system should avoid free-floating agents. Every spawned agent needs:

- a bead id or workflow id
- a role
- a fresh context pack
- a token/effort budget
- an allowed tool/MCP set
- a required evidence output
- a close gate

### `/workflows`

`/workflows` should become the operator-facing view of active orchestration:

- list active workflows and beads
- show owner role, status, last evidence, and budget
- spawn role-specific subagents only from a workflow/bead
- resume or close workflows
- show blocked workflows separately from running workflows
- show cost/context burn

It should not just be transcript artifacts under `~/.claude/projects/.../workflows`.

### `/effort ultracode`

`ultracode` should not mean "turn every task to max effort." It should be a budget profile:

```yaml
effort_profiles:
  quick:
    model: default
    reasoning: low
    subagents: 0
    max_context_pack: small
  standard:
    model: gpt-5.5
    reasoning: medium
    subagents: 0-1
    max_context_pack: focused
  ultracode:
    model: gpt-5.5
    reasoning: high
    subagents: 2-4 only when blast radius or uncertainty justifies it
    context_pack: fresh, role-specific, no transcript dumping
    required_gates: tests, diff review, evidence, deacon check
```

Use `ultracode` only for:

- production fixes
- multi-repo coordination
- security/eval failures
- broad refactors
- ambiguous architecture problems
- tasks with high rollback cost

Do not use it for quick file edits, one-off questions, simple docs, or status checks.

## Dynamic Agent Spawning Rules

### Spawn only from a decision

Spawn an agent only when one of these is true:

- the work can be parallelized across independent files/modules
- a second judge/reviewer materially reduces risk
- a specialist skill is needed
- a fresh context pack avoids main-thread context bloat
- the task has high blast radius

### Every subagent gets fresh context

Fresh context means:

- objective
- relevant files only
- constraints
- current known facts
- exact output contract
- time/effort budget
- no raw session dump

This matches the practical reason for subagents: isolate context and reduce main-thread drift.

### Hard caps

Default caps:

- 0 subagents for quick tasks
- 1 subagent for focused implementation review
- 2 subagents for multi-surface diagnosis
- 4 subagents for `ultracode`, unless explicitly approved

Run more only when the work divides cleanly and the output can be merged deterministically.

## Skills, Rules, Flows, Pyramids

### Do we use the skills?

Yes, but unevenly.

Codex has a large skill inventory and explicit trigger policy. Claude has symlinked legacy skills plus plugin skills. The problem is not lack of skills. The problem is missing runtime mediation:

- skills are selected by the main agent
- skills are not always written into Hive evidence
- skill use does not always create/close beads
- some Claude hooks that should trigger skills are empty

Target rule: every workflow records which skills were used and why.

### Do we use the rules?

Mostly, but there are gaps:

- TDD, no-mocks, verification, no-emojis, `bun`/`uv`, and RTK rules exist globally.
- Codex obeys RTK by contract.
- Claude has a coverage-enforcer Bash hook, but not a guaranteed RTK wrapper.
- The old plan said Claude-side RTK rewrite was TODO; that is still not fully resolved.

Target rule: all shell surfaces either call RTK directly or are explicitly exempted.

### Do we use the pyramids?

Partially.

The testing/eval pyramid exists in docs and automations:

- static checks
- unit tests
- property tests
- contract tests
- integration tests
- eval gates
- red-team/adversarial checks
- production replay
- deacon/meta-eval close gate

The missing part is enforcement. The pyramid should be part of bead closure, not only an audit report.

### Do we use the personas?

Partially.

Persona skills and persona panel methods exist, and prior workflows used persona subagents. They are not yet first-class in Hive routing.

Target rule:

- personas are lenses for review, eval, and UX/stakeholder simulation
- personas should not be always-on
- each persona invocation must have an output rubric
- persona outputs must be checked by a deacon/judge gate before becoming truth

## SOTA Agentic Eval Pyramid

Use a layered gate for every serious agent workflow:

1. Static and config gate
   - lint, type checks, secret scan, tool allowlist, MCP allowlist

2. Deterministic unit/property gate
   - pure logic, parsers, chunkers, validators, scoring helpers

3. Contract gate
   - API schemas, tool schemas, MCP tool definitions, auth requirements

4. Integration/replay gate
   - recorded real traces, no fake business mocks

5. Agent trajectory gate
   - tool choice, tool input accuracy, tool output use, navigation efficiency

6. Outcome gate
   - did the task actually complete with a usable deliverable

7. Red-team gate
   - prompt injection, data exfiltration, policy bypass, adversarial user behavior

8. Production replay gate
   - convert real failures into replay rows and beads

9. Deacon/meta-eval gate
   - judge the evidence, not the agent's self-report

This aligns with current Foundry agent evaluators, which distinguish system evaluation from process evaluation and include tool call, tool input, tool output, task adherence, and task navigation efficiency checks. It also aligns with trace-first agent practice: workflows need traces of generations, tool calls, handoffs, guardrails, and custom events.

## Rewire Backlog

### P0 - Make startup predictable

1. Fix direct Claude invocation path
   - Ensure every `claude` entrypoint, including non-interactive `claude mcp list`, sets `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=0` or has bubblewrap configured.
   - Verification: both `claude mcp list` and `~/.claude/bin/claude-launcher.sh mcp list` behave the same.

2. Make MCP lazy-loading explicit everywhere
   - Add explicit `enabled = false` for Codex `atlassian`.
   - Remove or disable stale Claude plugin MCP surfaces unless needed.
   - Keep HeyGen/Playwright/Atlassian off by default.
   - Verification: clean session starts with no failed MCP health checks for unused services.

3. Remove stale Telegram plugin registry/state
   - `installed_plugins.json` still lists Telegram even after earlier cleanup intent.
   - Verification: plugin list and process/listener check show no Telegram plugin.

### P1 - Make Hive a real work loop

1. Add `bead-reaper`
   - unclaim stale beads
   - mark dead duplicates
   - surface aged P0/P1 beads

2. Add `bead-pick`
   - Codex claims by role and rig
   - runs scoped automation
   - writes evidence
   - closes only after gate pass

3. Wire close gates
   - closed bead requires evidence URL/path
   - deacon role verifies evidence
   - meta-eval score required for high-risk work

4. Publish `/workflows`
   - show workflows, beads, agents, budget, evidence, and status
   - support resume/close/reaper commands

### P2 - Make dynamic spawning efficient

1. Add context-pack generator
   - input: bead/workflow id
   - output: role-specific markdown payload
   - includes only relevant files and facts

2. Add spawn policy
   - role
   - budget
   - allowed MCPs
   - allowed skills
   - output contract

3. Add merge policy
   - subagent output is advisory until main agent or deacon validates it

### P3 - Wire the pyramids into CI and Hive

1. Per rig, encode required gates in `~/.hive/rigs.yaml`.
2. For eval-capable repos, run trace/trajectory evals as release gates.
3. Add production failure to replay-row conversion.
4. Add weekly scorecard: open beads, closed beads, stale beads, failed eval rows, context/cost burn, RTK savings.

## Acceptance Criteria

This rewire is done only when:

- A new Claude session starts without unused MCP failures.
- Direct and launcher Claude invocations agree.
- Codex MCP config has no default-on remote/tool server except intentionally approved ones.
- Hive open beads decrease because agents claim and close work, not because humans manually prune the DB.
- `/workflows` shows live bead/workflow state and evidence.
- `/effort ultracode` changes budgets and gates, not just vibes.
- Every spawned agent has a fresh context pack and output contract.
- Persona outputs are traceable and judged.
- Agentic eval gates include process and outcome checks.
- The statusline context percentage is understood as context usage and warns before quality degradation.

## Sources Checked

Local:

- `~/.codex/RTK.md`
- `~/.codex/skills/mcp-activation/SKILL.md`
- `~/.codex/config.toml`
- `~/.claude/settings.json`
- `~/.claude/settings.local.json`
- `~/.claude/bin/claude-launcher.sh`
- `~/.claude/bin/statusline.sh`
- `~/.hive/bin/hive.py`
- `~/.hive/rigs.yaml`
- `docs/specs/2026-05-13-hive-adoption-plan.md`
- `docs/specs/2026-05-17-systemd-hive-automation-map.md`
- `docs/audits/2026-06-09-stack-modernization-and-hive-upgrade.md`

External:

- Model Context Protocol architecture: https://modelcontextprotocol.io/docs/learn/architecture
- Microsoft Foundry agent evaluators: https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/agent-evaluators
- OpenAI evals guide: https://developers.openai.com/api/docs/guides/evals
- OpenAI Agents SDK tracing: https://openai.github.io/openai-agents-python/tracing/
