---
name: azure-activity-watch
description: Surface Azure Activity-Log events where someone other than the owner (default shoval.be@i-sdd.com) has stopped, restarted, deleted, or resized a resource in AZAI_group. Use after a service goes unexpectedly cold, on the weekly audit, or any time you suspect a teammate touched your stuff without telling you.
allowed-tools: ["Bash", "Read", "Grep", "Glob"]
---

# azure-activity-watch

Forensic skill — answers "who stopped my app?" and "did anyone touch AZAI_group resources I didn't authorize?".

## When to invoke

- **Reactive**: a Shoval-owned app/function/container is suddenly Stopped or missing, and you don't remember stopping it.
- **Proactive**: weekly cadence, alongside `azure-audit`. Catch quiet cleanups (e.g. the 2026-05-03 Yasha incident — see `~/.claude/projects/-home-shovalbe/memory/project_yasha_stop_incident.md`).
- **Pre-deletion sanity**: before deprovisioning a "dormant" resource, confirm someone else didn't already stop or migrate it the same day.

## What it does

Calls `az monitor activity-log list` over the last N days (default 7) on `AZAI_group`, filters to a hand-curated set of "interesting" operation names (stop / restart / delete / serverfarm-write), keeps only EndRequest + Succeeded entries, and excludes events whose `caller` equals the owner. Anything left is a delete/stop you didn't perform yourself.

## Run

```bash
~/.claude/skills/azure-activity-watch/run.sh                    # last 7 days, table
~/.claude/skills/azure-activity-watch/run.sh --since 30d        # widen window
~/.claude/skills/azure-activity-watch/run.sh --since 14d --json # forensic-grade JSON
~/.claude/skills/azure-activity-watch/run.sh --rg some-other-rg # different RG
```

Inputs:

| Flag | Default | Purpose |
|---|---|---|
| `--since` | `7d` | Window. Accepts `Nd` / `Nh`. |
| `--owner` | `shoval.be@i-sdd.com` | Caller to *exclude* (you). |
| `--rg` | `AZAI_group` | Resource group to scope to. |
| `--json` | (off) | Switch to JSON output. Includes correlationId, clientApp (Portal vs CLI vs SP), MFA flag. |

## Reading the output

For each row you should ask:
- **Was this expected?** (planned migration, on-call rotation, owner-coordinated cleanup, etc.)
- **Was it announced?** (Slack / DM / Yasha-style portal raid?)
- **Did it break anything?** (cross-check `azure-audit` Tier-2 or `app-realtime-monitor`-style critical apps.)

If the answer to any is "no", surface the row to the user with:
1. The forensic detail (timestamp, caller, IP, correlationId, clientApp).
2. A draft of a polite reply to the actor — *do not auto-send*. The user prefers to send the message themselves.

## Forensic columns (JSON mode)

| Column | Meaning |
|---|---|
| `when` | UTC timestamp of EndRequest |
| `who` | `caller` (UPN) |
| `ip` | `httpRequest.clientIpAddress` — Azure-internal `20.0.0.0/8` ranges = Portal session |
| `op` | full operation name, e.g. `Microsoft.Web/sites/stop/action` |
| `opName` | localized friendly form |
| `status` | always `Succeeded` after our filter |
| `resource` | full resource ARM id |
| `correlationId` | groups multi-step Portal ops in one user click |
| `clientApp` | `c44b4083-3bb0-49c1-b47d-974e53cbdf3c` is Azure Portal; `04b07795-8ddb-461a-bbee-02f9e1bf7b46` is `az` CLI; anything else = automation |
| `mfa` | `pwd,rsa,mfa` confirms an interactive MFA login (rules out service-principal automation) |

## Known signal-of-concern actors

- `yashako@zonlineltd.com` (Yasha Kohut) — historically performs unannounced portal cleanups. Default to flagging any ops by Yasha on Shoval-owned services. See incident memory.

## Not in scope

- Read operations (we don't care who clicked through Portal).
- Subscription-level activity (skill is RG-scoped).
- Activity older than 90 days — Activity Log retention cutoff.
- Realtime alerting — for that, set up an Azure native Activity Log Alert (see `optional-realtime.md` in this dir).

## Companion: native Azure Activity Log Alert (optional, real-time)

If you want an email or Teams ping the moment someone stops an app, add a native alert. The CLI:

```bash
RG=AZAI_group
EMAIL=shoval.be@i-sdd.com

# Action group — receives the alert
az monitor action-group create -g $RG -n ag-azai-stop-watch \
  --short-name azai-stop \
  --action email shoval-email "$EMAIL"

# Activity Log Alert — fires on every Microsoft.Web/sites/stop/action in the RG
az monitor activity-log alert create -g $RG -n alert-stop-webapp \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG" \
  --condition category=Administrative \
  --condition operationName=Microsoft.Web/sites/stop/action \
  --action-group ag-azai-stop-watch
```

You'll get an email per stop event, including the caller. Caveat: Activity Log Alerts can't natively filter `caller != me`, so you'll get notified about your own stops too. The skill above is the right tool for "exclude me" forensics.

## Failure modes

- **Empty output despite known stop event** → 99% of the time this is the `--max-events` cap. We use `--max-events 5000`, but if a noisy day exceeds even that, narrow the window with `--since 24h`.
- **`az` token expired** → run `az login`.
- **Operation listed in CLI table without an `EndRequest` row** → the change is still in flight. Re-run in 1–2 minutes.

## Related memories / references

- Incident: `~/.claude/projects/-home-shovalbe/memory/project_yasha_stop_incident.md`
- Audit skill: `~/.claude/skills/azure-audit/SKILL.md`
- Last forensic report on Yasha's stops: rendered inline in the conversation that created this skill.
