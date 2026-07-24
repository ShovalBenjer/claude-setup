# Jira comment, AI storage consolidation onto stsentimarkv2

**Paste below into the task comment.**

---

**Done. AI consolidated under `stsentimarkv2`. AZAI_group SAs: 7 -> 3.**

**Final 3 SAs:**
- `stsentimarkv2`: canonical AI home (everything new lands here)
- `azaigroup8dc3`: deployment packages + Function host state for live apps
- `jiralogicappdev326413`: Jira Logic App, not AI

**Migrated to stsentimarkv2 (verified count + byte-sum match):**
- 5 AI data containers, 434 blobs, 1.8 GB: `qc-transcripts`, `call-recordings`, `exam-reports`, `handover-diagrams`, `sales-agent-calls`
- 12 marketing-newsletter archive containers, 2,339 blobs, 3.34 GB under `mn-*` prefix: `mn-marketing-assets`, `mn-videos`, `mn-thumbnails`, `mn-landing-pages`, `mn-x-bundles`, `mn-silver-campaign`, `mn-email-charts`, `mn-newsletters`, `mn-brand-assets`, `mn-charts`, `mn-baselines`, `mn-static-web`

**Deleted SAs (4):** `stmarketdailyreports`, `stphonespamcheckerprod`, `stmarketingnewsletter`, `stseekapatrainingprod`. Sources had soft-delete OFF, permanent. 14-day soft-delete now enabled on `stsentimarkv2` as safety net.

**Deleted sites (4):** `func-training-prod`, `COMP-SEEKAPAAITRAININGAPI-PROD`, `app-realtime-monitor`, `mcp-seekapa-tools` (the `:latest` duplicate running same `campaignanalytics` image as `COMP-CAMPAIGN-PROD`).

**ASP-AZAIPROJECTS:** P1v3, 5 sites (was 9). SKU held. Memory peak 4.3 GB (3.2 GB OS/runtime + 1.1 GB apps), too tight for P0v3 4-GB cap. Real saving path is Functions onto Consumption plan, not SKU downgrade.

**Canonical campaign-analytics app:** `COMP-CAMPAIGN-PROD`, intentionally Stopped (Shoval dev'ing it), domain `mcsrv01.corp-domain.com`, pinned to `campaignanalytics:12298`.

**Public-URL break:** `exam-reports` + `handover-diagrams` were public-blob, now private (destination SA blocks public access, kept that posture). Hard-coded external URLs to `azaigroup8dc3.blob.core.windows.net/...` are dead. Internal account-key/SAS readers still work.

**Out of scope:** Foundry KB / vector stores (Microsoft-managed inside `brn-azai`), sentimark-rg workloads (RBAC denied).

**Pending Yasha:** sentimark-rg Reader access requested. Once granted: audit EP1 workloads + lift-and-shift plan to `sentimark-env` Container Apps (the real money, ~$130-210/mo per Function App).

**Open items:**
- Duplicate Durable hub `qcanalyzertaskhubv2-applease` on `azaigroup8dc3` (stale 6 mo) and `stsentimarkv2` (active). Clean next sweep.
- Functions to Consumption plan migration: deferred.

**Cost:** today's direct savings ~$0.30/mo total (immaterial). Strategic value is "one canonical SA, one ASP, one Foundry project" cleanup. Real money sits behind sentimark-rg access.

**Rollback:** 14 days soft-delete on stsentimarkv2. Deleted SAs and sources permanent.
