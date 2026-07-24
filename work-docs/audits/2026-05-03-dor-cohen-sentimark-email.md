# Email draft — Dor Cohen · Sentimark deprovision sign-off

**To:** Dor Cohen `<dor.co@...>`  *(confirm address)*
**From:** Shoval Benjer `<shoval.be@i-sdd.com>`
**Subject:** Sentimark resources on `Corp-AI` / `brn-azai` — sign-off to deprovision

Hi Dor,

Per our migration off of Sentimark, I'd like to confirm everything is fully cut over so I can deprovision the leftover Azure resources from the `AZAI_group` subscription. Could you reply with a quick ✅ on each item below, or flag any that still need to stay up?

## Items I plan to delete

| Resource | Type | Current state |
|---|---|---|
| `app-sentimark-prod` | Azure Web App (Linux) | Stopped, ~4 probe req / 30d |
| `sentimark-v2-cache` | Azure Cache for Redis | Cost-bearing |
| `sentimark-env` | Container Apps environment | Empty? please confirm |

## Items I will NOT touch (because they're shared with live workloads)

| Resource | Why kept |
|---|---|
| `stsentimarkv2` | Shared `AzureWebJobsStorage` for 12 of 13 production function apps (CS-agents, Sales, AEO, Compliance, Training, …). Renaming alone would force redeploys. |
| `sentimarkregistry` (ACR) | Image source for `COMP-AEO` and `COMP-SEEKAPAAITRAININGAPI-PROD` web apps. |

## DevOps repos in scope

Both project repos remain available for history but I'd like your call on archiving:

- `Corp-AI/sentimark` — last commit 2026-03-09 (oded ben-yair)
- `Corp-AI/sentimark-docker-deploy` — last commit 2026-03-03
- `Corp-domain/sentimark` — last commit 2026-04-30 (yasha)

Default plan: **disable** (read-only, reversible) rather than delete. Let me know if you'd prefer a different approach.

## Wiki

`Corp-AI.wiki` already has the subtree `/Oded - Archived work/Sentimark - Archive Work/` — I'll leave that alone unless you want it pruned.

If I don't hear back by EoW I'll hold off on all of the above.

Thanks,
Shoval
