# DEV-4942 follow-up to Yasha — unblock campaign-analysis production (DRAFT — review before sending)

Context: storage consolidation under `stsentimarkv2` is done (per my 2026-05-26 report on this
ticket). To stand up the campaign-analysis production app I need one access grant + a small
identity setup — no new infrastructure (the env and app already exist).

## 1. The grant already pending on this ticket (please action)

Reader on `sentimark-rg` so I can audit EP1 workloads and deploy into the existing
`sentimark-env` Container Apps environment:

```
az role assignment create \
  --assignee f71d0e70-5b5c-484e-a683-e3b98685cc91 \
  --role "Reader" \
  --scope /subscriptions/08b0ac81-a17e-421c-8c1b-41b59ee758a3/resourceGroups/sentimark-rg
```
Read-only; no changes made before review + approval.

## 2. To run COMP-CAMPAIGN-PROD as the live app (no new resources)

- Start `COMP-CAMPAIGN-PROD` (currently intentionally stopped) once my image is ready, OR let
  me deploy a new revision of `campaignanalytics:` to it. Confirm I have push rights to the ACR
  holding that image.
- Confirm the `sentimark-env` Container Apps environment is the target for new Jobs (the
  pipeline/orchestrator tasks) — I'll deploy into it rather than create a new env.

## 3. Identity + secrets (for SSO + MSI, least-privilege)

- One Entra app registration for the dashboard SSO (tenant-pinned to corp-domain).
- User-assigned managed identities for: the app, and the pipeline Jobs. Role assignments:
  - `Storage Blob Data Contributor` on `stsentimarkv2` (scoped to our containers)
  - `Cognitive Services User` on the `brn-azai` Foundry project (agent runtime)
  - `Key Vault Secrets User` on the vault holding DB/API creds
- DB creds (read-only `avi_lior`) + Call-Analyzer token moved to Key Vault (no secrets in image).

## What I am NOT asking for
- No new storage account (all under `stsentimarkv2`, per the consolidation).
- No Cosmos account (app-state goes in `stsentimarkv2` blob/Table or the qc_analyzer Postgres).
- No new Container Apps environment (use existing `sentimark-env`).

Net: one Reader grant + an Entra app-reg + a couple of managed identities with scoped roles.
That unblocks the hosted, SSO'd, agent-backed dashboard.
