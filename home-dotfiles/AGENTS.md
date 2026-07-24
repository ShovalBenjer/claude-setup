# Codex Global Instructions (Migrated from ~/.claude)

## Scope
These instructions apply at `/home/shovalbe` and subprojects unless a deeper `AGENTS.md` overrides them.

## Core Engineering Rules
- Use `bun`/`bunx` for JS/TS projects. Do not use `npm`, `npx`, `yarn`, or `pnpm` unless a project explicitly requires it.
- Use `uv` for Python projects. Do not use `pip` directly unless a project explicitly requires it.
- Enforce TDD: RED -> GREEN -> REFACTOR.
- No mocks for business logic, external services, DB, or filesystem. Prefer recorded fixtures and real components.
- Never claim completion without verification evidence (command + real output + pass/fail).
- Do not use emojis unless the user explicitly requests them.

## PRD Control Plane
- When a PRD, spec, contract, or task list exists for the requested surface, treat it as the source of truth.
- Before creating a new plan, reconcile against that PRD: done, partial, not started, contradicted, and cite the file.
- A new plan must be a PRD delta: list what it implements, amends, supersedes, and leaves incomplete.
- Do not ask for a green light to start a fresh slice while PRD acceptance items remain unaddressed, unless the user explicitly changes scope.
- For platform work, verify the workflow outcome, state transition, data contract, deploy/runtime behavior, observability, rollback, and tests. Local code tests alone are not completion.
- If an article, benchmark, or brainstorm changes the approach, first convert the insight into PRD acceptance criteria.

## Dynamic R3P Loop
- For substantive work, use Reground -> Requirements -> Reduce -> Produce -> Prove.
- Reground dynamically when branch/root/artifact/spec state is unclear. Use `lite` for targeted `rtk git`, `rtk rg`, and task-shaped `rtk proxy find/du` probes. Use `full` for platform, production, data, UI, deploy, cleanup, or cross-repo work.
- Full-depth reground must inspect git hygiene, top-level tree, docs/plans, recent generated outputs, and `.png/.xlsx/.csv/.parquet/.json` artifacts.
- Reduce with Ponytail before coding: delete or reuse before adding, avoid monofiles, duplicate builders, one-off abstractions, speculative scaffolds, and new dependencies unless clearly justified.
- Prove platform outcomes, not only patch correctness: workflow, state transition, data contract, runtime/deploy, observability/logs, rollback, tests, and changed-file review.

## Security and Safety Defaults
- Treat `.env`, credentials, tokens, keys, and secrets as sensitive.
- Avoid destructive operations without explicit user intent.
- Prefer minimal-diff, reversible changes.

## Migrated Rule Sources
- `~/.codex/rules/tdd-enforcement.md`
- `~/.codex/rules/no-mocks.md`
- `~/.codex/rules/task-verification.md`
- `~/.codex/rules/no-emojis.md`
- `~/.codex/rules/model-selection.md`

## Skills
A skill is a set of local instructions in a `SKILL.md` file.

### Available global skills
- `mcp-activation` — on-demand MCP activation per Codex session (`~/.codex/skills/mcp-activation/SKILL.md`)
- `apify-mcp` — Apify Actor MCP workflows (`~/.codex/skills/apify-mcp/SKILL.md`)

<!-- Removed 2026-05-03: SKILL.md missing for these. Restoring is tracked in master plan.
     - perplexity-mcp: only at ~/projects/figma-4-all/.codex/skills/perplexity-mcp/ (needs promote-to-global)
     - playwright-cli: visual QA should use normal Chrome/Playwright, not Obscura-only checks
     - playwright-mcp: default `playwright` is screenshot-capable Chrome via `~/.codex/bin/playwright-mcp-visual`; `playwright-obscura` is the explicit stealth fallback
     See ~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md Part 8 §15-18 -->

- `heygen-mcp` — HeyGen MCP workflows (`~/.codex/skills/heygen-mcp/SKILL.md`)
- `elevenlabs-mcp` — ElevenLabs MCP workflows (`~/.codex/skills/elevenlabs-mcp/SKILL.md`)
- `azure-keyvault-secrets` — Azure Key Vault secret sync for global + project runtime (`~/.codex/skills/azure-keyvault-secrets/SKILL.md`)
- `azure-devops` — Azure DevOps CLI workflow automation with approval gates (`~/.codex/skills/azure-devops/SKILL.md`)
- `cleanup-crew` — cleanup and bloat removal (`~/.codex/skills/cleanup-crew/SKILL.md`)
- `code-simplifier` — refactor-only simplification (`~/.codex/skills/code-simplifier/SKILL.md`)
- `commit-push-pr` — commit/push/PR workflow (`~/.codex/skills/commit-push-pr/SKILL.md`)
- `eval-runner` — evaluation/test orchestration (`~/.codex/skills/eval-runner/SKILL.md`)
- `kill-stale` — stale process cleanup (`~/.codex/skills/kill-stale/SKILL.md`)
- `mutation-runner` — mutation testing workflow (`~/.codex/skills/mutation-runner/SKILL.md`)
- `ops-status` — system status snapshot (`~/.codex/skills/ops-status/SKILL.md`)
- `property-test-gen` — property-based test generation (`~/.codex/skills/property-test-gen/SKILL.md`)
- `red-team` — TDD quality red-team (`~/.codex/skills/red-team/SKILL.md`)
- `red-team-review` — multi-persona review (`~/.codex/skills/red-team-review/SKILL.md`)
- `triage-tests` — test-failure triage (`~/.codex/skills/triage-tests/SKILL.md`)
- `watchdog` — guardrail checks (`~/.codex/skills/watchdog/SKILL.md`)
- `web-inspect` — headed web inspection (`~/.codex/skills/web-inspect/SKILL.md`)
- `workspace-brain` — cross-project memory/index (`~/.codex/skills/workspace-brain/SKILL.md`)

### Skill trigger policy
- If the user names a skill (e.g. `$skill-name` or plain mention), use it for that turn.
- If task intent clearly matches a skill, use it even without explicit naming.
- If multiple skills fit, use the minimal set and state order briefly.
- MCP servers are default-disabled in `~/.codex/config.toml`; activate only required servers per session using `~/.codex/bin/codex-with-mcp`.

## Hook Parity Note
Claude hooks were migrated to `~/.codex/hooks/*`, but Codex does not auto-run Claude hook events.
Use these scripts manually when needed for parity.

@RTK.md
