# ADR-0006 — One scheduler topology: native cron local + cloud routines

Status: Accepted (2026-07-23)

## Context
Scheduling was split across WSL systemd user timers (dying on a Windows box),
`~/.claude/scheduled_tasks.json` (Gastown portfolio), and plans for Windows Task
Scheduler + `claude -p`. The Cowork session proved cloud-scheduled tasks cannot
drive the logged-in local Chrome (WhatsApp/LoopCV) without a fragile desktop bridge.

## Decision
Two schedulers, by reachability: (a) native local cron (CronCreate) for anything
needing THIS machine — browser, ledgers, WhatsApp, approval-gated actions; (b) cloud
routines (/schedule) for public-source work where laptop-closed wins. WSL systemd is
retired. Long horizons = the LOOP of bounded runs over durable artifacts, not one
heroic session.

## Consequences
+ One mental model; the desktop-bridge fragility is designed out.
+ Cron is subscription-window aware (unlike Task Scheduler), so backoff is native.
- Local crons need an always-on PC (power/wake settings become OS concerns).
- Two schedulers means two places to audit job health; the digest surfaces both.
