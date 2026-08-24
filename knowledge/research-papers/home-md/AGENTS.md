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
     - playwright-cli: not yet written; will target Obscura (~/.local/bin/obscura)
     - playwright-mcp: not yet written; will split — Obscura on Linux + MS Edge CDP on Windows for domain apps
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
