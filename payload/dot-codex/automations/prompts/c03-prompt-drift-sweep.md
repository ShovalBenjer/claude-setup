# C3. Active Prompt Drift Sweep

Schedule: Thursdays 7:30-8:00 PM Asia/Jerusalem
Mode: read + propose + local Hive beads; no prompt deployment in v1

Run one prompt-source drift pass across the active rigs that rely on live prompts:

- `cs-agent` -> `/home/shovalbe/projects/cs-agent`
- `campaign-analysis` -> `/home/shovalbe/projects/campaign-analysis`
- shared prompt library -> `/home/shovalbe/agent-prompts`
- general prompt scratch/reference -> `/home/shovalbe/Prompts`

Use `gpt-5.5` with medium reasoning. Treat `~/.codex` as the source of truth, `~/.claude` as a compatibility layer, and `~/.hive` as the local work bus.

## Scope

Read:

- `/home/shovalbe/agent-prompts/README.md`
- `/home/shovalbe/agent-prompts/*.md`
- `/home/shovalbe/agent-prompts/drafts/*.md`
- project prompt files under `cs-agent` and `campaign-analysis`
- Foundry deployment metadata only when local SDK/auth is already available

Do not:

- print secrets or full customer transcripts
- deploy prompts
- edit prompt files
- create Azure DevOps work items
- comment on PRs
- run long evals unless a project has a documented fast prompt smoke

## Checks

- Identify the likely canonical prompt per product/agent.
- Identify newer drafts that are not referenced by project runtime docs.
- Identify project prompt files that diverge from `/home/shovalbe/agent-prompts`.
- For Foundry-backed agents, compare git/library prompt version claims with live deployment metadata when available.
- Flag prompt versions that lack eval evidence, security review, or rollback notes.
- Check for security-risk language: tool overreach, identity leakage, investment advice beyond scope, weak escalation rules, missing language-specific guardrails.

## Hive Routing

Create at most 3 beads total:

- `P1`: live Foundry/runtime prompt appears newer than git/library with no evidence.
- `P1`: prompt has clear regulated-finance or PII/security regression risk.
- `P2`: canonical prompt unclear or missing eval/rollback evidence.
- `P3`: archive/reference cleanup.

Use `bead-create` only. Do not close or claim beads.

## Output

Write one report:

`~/.claude/docs/PROMPT_DRIFT_<DATE>.md`

Sections:

- `EXECUTIVE_SUMMARY`
- `PROMPT_SOURCE_MAP`
- `CS_AGENT_DRIFT`
- `CAMPAIGN_ANALYSIS_DRIFT`
- `FOUNDRY_METADATA`
- `SECURITY_AND_COMPLIANCE_FLAGS`
- `HIVE_BEADS_CREATED`
- `ACTIONABLE_NEXT_STEPS`

