# Codex Scheduled Automations

This directory contains local systemd-backed Codex automations migrated from:

`~/.claude/docs/CODEX_AUTOMATIONS_PROPOSAL.md`

## Active Bundles

- `c01-platform-hygiene-sweep` replaces A1, A3, and A12.
- `c02-engineering-review-sweep` replaces A2, A4, A7, A8, A9, A10, A11, and the D-series review/drift timers.
- A5 email action mining is disabled. PST/email ingestion remains handled by the existing Claude PST pipeline around `/home/shovalbe/shoval.be@i-sdd.com.pst`.

## Layout

- `prompts/` - one editable Markdown prompt per automation.
- `run-codex-automation.sh` - shared unattended runner.
- `logs/` - timestamped stdout/stderr logs per run.
- `last-messages/` - final Codex response for each run.

Systemd unit files live in `~/.config/systemd/user/`.

## Running One Job Manually

```bash
~/.codex/automations/run-codex-automation.sh a01-memory-curator-sweep
```

## Timer Behavior

The timers use `Persistent=true`, so if the computer is powered off or asleep at the scheduled time, systemd will run the missed timer after the user manager is available again.

Important: user timers generally require the user systemd manager to be running. If you need these to run after reboot before login, enable user lingering:

```bash
loginctl enable-linger shovalbe
```

## Safety

The runner adds unattended-mode guardrails to every prompt. The original prompts still decide whether a job is read-only, proposal-only, or allowed to file ADO work items.
