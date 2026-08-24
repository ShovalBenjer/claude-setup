# Systemd Hive Automation Map

Date: 2026-05-17
Status: implemented v1

## Authority

`~/.codex` is the runtime source of truth.

`~/.claude` is the interactive Claude agent compatibility layer.

`~/.hive` is the shared task bus:

- `~/.hive/rigs.yaml`
- `~/.hive/beads.db`
- `~/.hive/bin/bead-create`
- `~/.hive/bin/bead-list`
- `~/.hive/bin/bead-claim`
- `~/.hive/bin/bead-close`

## Active Rigs

- `cs-agent`
- `qc-telephony-api`
- `video-understanding`
- `campaign-analysis`

Each rig should have:

- `AGENTS.md`
- `.codex/hive.yaml`
- `.claude/hive.yaml` when `.claude/` exists

## Scheduler

Systemd user timers are canonical for Codex Hive automations.

The service template is:

- `~/.config/systemd/user/codex-automation@.service`

The runner is:

- `~/.codex/automations/run-codex-automation.sh`

The service loads per-job env files from:

- `~/.codex/automations/env/%i.env`

Default model:

- `gpt-5.5`

Default scheduled reasoning:

- `medium`, unless an env file sets `CODEX_REASONING_EFFORT=high`

## Active Timers

| Timer | Purpose | Schedule |
|---|---|---|
| `codex-automation-c01-platform-hygiene-sweep.timer` | Platform hygiene and Hive parity | Sunday 09:30, Asia/Jerusalem |
| `codex-automation-c02-engineering-review-sweep.timer` | Active project engineering review | Monday-Friday 09:30 and 16:30, Asia/Jerusalem |
| `codex-automation-c03-prompt-drift-sweep.timer` | Prompt source and Foundry drift | Sunday 16:30, Asia/Jerusalem |
| `codex-automation-c04-security-testing-pyramid-sweep.timer` | Security and testing pyramid coverage | Sunday 16:30, Asia/Jerusalem |
| `codex-automation-a01-memory-curator-sweep.timer` | Memory curator | Sunday 09:30, Asia/Jerusalem |
| `codex-automation-a05-pst-email-action-mining.timer` | PST/email action mining | Sunday 09:30, Asia/Jerusalem |
| `codex-automation-a08-claudemd-drift-per-project.timer` | CLAUDE.md drift | Sunday 09:30, Asia/Jerusalem |
| `codex-automation-d05-hot-zone-indicator.timer` | Hot-zone churn versus tests | Sunday 16:30, Asia/Jerusalem |
| `codex-automation-a09-forge-loop-compliance-score.timer` | Forge-loop compliance score | Sunday 16:30, Asia/Jerusalem |

## Cron

Legacy crontab still contains old Codex automation lines. They should remain disabled or be removed after backup because systemd now owns the schedule.

If cron is active later, old Codex cron lines could duplicate systemd runs. The safe cleanup is:

1. Back up current crontab.
2. Comment only lines invoking `~/.codex/automations/run-codex-automation.sh`.
3. Leave health reminders and unrelated cron entries untouched.

## Skills and Rule Surfaces

Live skill inventory discovered on 2026-05-17:

- `~/.codex/skills`: 24 skills
- `~/.agents/skills`: 52 skills
- `~/.claude/skills`: 14 legacy skills
- unique live skill names across those surfaces: 84

Reference-only/snapshot surfaces:

- `~/friday-meeting/skills`: 21 files
- `~/agent-prompts` and `~/Prompts`: shared prompt libraries and drafts

Core active rules:

- `~/AGENTS.md`
- `~/.codex/rules/tdd-enforcement.md`
- `~/.codex/rules/no-mocks.md`
- `~/.codex/rules/task-verification.md`
- `~/.codex/rules/no-emojis.md`
- `~/.codex/rules/model-selection.md`

Core active hooks:

- `~/.codex/hooks/session-context.sh`
- `~/.codex/hooks/post-compact-reinject.sh`
- `~/.codex/hooks/protect-infra.sh`
- `~/.codex/hooks/watchdog-verify.sh`
- `~/.codex/hooks/rtk-bash-guard.sh`
- `~/.codex/hooks/coverage-enforcer.sh`
- `~/.codex/hooks/snapshot-state.sh`
- `~/.codex/hooks/stop-checklist.sh`
- `~/.codex/hooks/verification-before-completion.sh`

## Current Boundary

Implemented v1:

- systemd scheduled Codex jobs
- project Hive manifests
- local beads
- report-and-route automation mode
- prompt drift and security/testing pyramid sweeps

Not yet implemented:

- ADO webhook bead listener
- eval-row failure auto-beads
- App Insights production-error auto-beads
- Obscura screenshot evidence gate
- HyperAgents-style adversarial bead-close gate
- GBrain-style replay set auto-growth from production failures
