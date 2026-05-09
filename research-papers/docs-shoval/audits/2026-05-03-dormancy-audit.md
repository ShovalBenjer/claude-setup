# Azure + DevOps Dormancy Audit — 2026-05-03

Subscription: `U-BTech - CSP (Z-Online)` · `08b0ac81-a17e-421c-8c1b-41b59ee758a3` · tenant `Corp Domain`
Resource group: `AZAI_group` (Sweden Central) — sole non-default RG
DevOps org: `https://dev.azure.com/Corp-domain` · projects: `Corp-AI`, `Corp-domain`
Foundry: `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai`

## TL;DR

- **5 confirmed deletion candidates** (phone-spam stack, app-sentimark-prod) — all sentimark/phone-spam aligned with user's stated migration.
- **3 sentimark side-cars need Dor Cohen confirmation** before deprovision: `sentimark-env`, `sentimark-v2-cache`, `stsentimarkv2`*.
- **`stsentimarkv2` storage MUST stay** — despite the misleading name, it backs 12 of 13 production function apps (`AzureWebJobsStorage`). Renaming first is preferable to deletion.
- **10 of 13 function apps show 0 `FunctionExecutionCount` over 30d.** Several are likely event/timer-triggered, but worth a per-function trigger review before mass deletion.
- **17 DevOps repos in `Corp-domain`** have not received a commit in > 6 months. Most are WordPress sites and old landing pages.
- **1 Foundry agent** (`figma`/Ashley). User's CLAUDE.md references prod agents `seekapa` + `AxiaCS` — they are NOT in `seekapa_ai` Foundry project. Likely on a different endpoint or migrated to function-hosted code.

## 1. Azure resources — usage signals

### 1.1 Function apps (last 30d)

| Function app | State | FuncExec/30d | Reqs/30d | 5xx | Verdict |
|---|---|---|---|---|---|
| func-phone-spam-checker-prod | **Stopped** | 0 | 11 | 0 | **DELETE** (user-confirmed migrated) |
| func-client-eval-prod | Running | 0 | 12 | 0 | review trigger type before action |
| func-automation-fabric-prod | Running | 0 | 12 | 0 | review trigger type |
| func-qc-telephony-prod | Running | 0 | 12 | 0 | review trigger type (QC = call analyzer) |
| func-seekapa-sales-agent-prod | Running | 0 | 12 | 0 | review trigger type |
| func-aeo-competitor-prod | Running | 0 | 12 | 0 | review trigger type |
| func-aeo-api-prod | Running | 0 | 12 | 0 | likely fronted by `aeo-api` ContainerApp |
| func-compliance-exam-prod | Running | **12** | 12 | 0 | **active** |
| func-training-prod | Running | **43** | 12 | 0 | **active** |
| func-cs-agents-dev | Running | 0 | 12 | 0 | dev env — keep |
| func-marketing-newsletter | Running | **12** | 12 | 0 | **active** |
| func-aeo-audit-prod | Running | 0 | 12 | 0 | review trigger type |
| func-market-reports-prod | Running | 0 | 12 | 0 | review trigger type |

**Note**: ~11–12 Requests/30d is the Azure platform health-probe floor across all sites. `FunctionExecutionCount` is the more reliable invocation signal.

**Storage backing**: 12 of 13 function apps point `AzureWebJobsStorage` at `stsentimarkv2`. `func-marketing-newsletter` uses `stmarketingnewsletter`. Therefore deleting `stsentimarkv2` would break the entire CS/Sales/AEO/Compliance/Training stack.

### 1.2 Web apps (last 30d)

| Web app | State | Reqs/30d | Verdict |
|---|---|---|---|
| COMP-CAMPAIGN-PROD | Running | 0 | review |
| **app-sentimark-prod** | **Stopped** | 4 | **DELETE** (user-confirmed migrated) |
| mcp-seekapa-tools | Running | 0 | review (has `staging` slot — dev tool?) |
| app-realtime-monitor | Running | 15 | active (probe-floor) |
| app-anychat-prod | Running | 16 | active |
| COMP-AEO | Running | 16 | active |
| COMP-SEEKAPAAITRAININGAPI-PROD | Running | 16 | active |

### 1.3 Container apps

| Container app | Status | Verdict |
|---|---|---|
| aeo-api | Running | active |
| video-orchestra-renderer | Running | review (no traffic data captured) |

### 1.4 Storage accounts (txns last 30d)

| Storage | Txn/30d | Verdict |
|---|---|---|
| azaigroup8dc3 | 0 | **review for delete** (auto-created with RG) |
| logicapp881525891519 | 0 | **review for delete** (logic app present but idle) |
| stmarketdailyreports | 0 | review (does `func-market-reports-prod` actually run?) |
| stmarketingnewsletter | 4297 | active |
| **stphonespamcheckerprod** | 0 | **DELETE** (paired with phone-spam fn) |
| stseekapatrainingprod | 0 | review (does training fn use it?) |
| **stsentimarkv2** | 14211 | **KEEP** — backs 12 prod function apps despite name |

### 1.5 Sentimark side-cars (need Dor confirmation)

| Resource | Type | Notes |
|---|---|---|
| app-sentimark-prod | Web app | Stopped — confirmed migrated |
| sentimark-env | Container App env | Inspect what (if anything) is deployed in it |
| sentimark-v2-cache | Redis | Cost-bearing — confirm no client connects |
| sentimarkregistry | ACR | **KEEP** — used by `webappCOMPAEO` + `webappCOMPSEEKAPAAITRAININGAPIPROD` |
| stsentimarkv2 | Storage | **KEEP** — see 1.4 |

### 1.6 Phone-spam stack (full deletion bundle)

```
func-phone-spam-checker-prod                # Stopped, 0 exec
appi-phone-spam-checker-prod                # paired App Insights
Failure Anomalies - appi-phone-spam-checker-prod   # smart-detector
stphonespamcheckerprod                      # paired storage, 0 txn/30d
```

## 2. DevOps repos — last commit (>180 days = dormant threshold)

Today: 2026-05-03. Dormancy threshold: last commit before 2025-11-03.

### Corp-AI (29 repos) — all active

Most active commit dates within last 30–60 days. No dormants in this project.

### Corp-domain (76 repos) — 17 dormant

| Repo | Last commit | Size (bytes) | Notes |
|---|---|---|---|
| axia-new | 2023-06-19 | 78239105 | likely superseded by `axia_landing` / `axiainvestments_v2` |
| axia_landing | 2023-09-12 | 143206400 | review |
| axia_services | 2024-11-11 | 35711470 | review |
| axiainvestments_platform_wp | 2024-12-11 | 53581227 | superseded by `axiainvestments_v2`? |
| **corp-domain** | 2023-07-24 | 32139377 | superseded by `corp-domain-v2` (last commit 2026-04-28) |
| gccmarkets_wp | 2023-10-05 | 224628172 | review (huge, likely WP backup) |
| lps-we-leads | 2023-10-11 | 63928016 | review |
| milestone | 2023-09-12 | 40169623 | review |
| **mysignals_wp** | 2023-08-22 | 730 | **empty / placeholder** — safe delete |
| online_education | 2023-11-09 | 96701417 | review |
| seekapa_ai_assistant | 2025-07-02 | 43209 | review |
| seekapa_platform_wp | 2024-05-16 | 48386477 | review |
| sikapa | 2023-10-05 | 172878941 | superseded? |
| traderschool_academy | 2023-09-12 | 150592072 | review |
| clocker_wp | 2025-06-12 | 47038065 | borderline |
| dailyvesting_blog_wp | 2025-09-29 | 65814995 | borderline |
| trdmch_education_wp | 2025-05-01 | 54385946 | review |

### Empty / placeholder repos in Corp-AI (size 0)

These have recent commits but zero content — possibly init-only:

```
anychat-docker-deploy        client-eval-docker-deploy
brokershub-latam             compliance-exam-docker-deploy
cs-agents-docker-deploy      kever-rachel
realtime-docker-deploy       seekapa-training-docker-deploy
```

The `*-docker-deploy` pattern looks like a deploy-pipeline placeholder convention. Confirm before deletion.

## 3. Wikis

| Wiki | Last activity | State |
|---|---|---|
| Corp-AI.wiki | 2026-04-30 (Shoval) | Active |
| Corp-domain.wiki | 2026-05-01 (Vladyslav) | Active |

Notable dormant subtrees inside `Corp-AI.wiki`:

- `/Oded - Archived work/Sentimark - Archive Work/*`
- `/Oded - Archived work/Client-Evaluation/*`
- `/Oded - Archived work/AEO/*`

Recommendation: leave as-is — already named `Archived`. No deletion needed.

## 4. Foundry — `seekapa_ai` project agents

| Agent ID | Name | Model | Verdict |
|---|---|---|---|
| asst_fwBvrSbgNM2nN1gsga9WeSbv | figma (Ashley) | gpt-5.2-figma | active (Figma4All) |

**Gap vs CLAUDE.md**: prod agents `seekapa`, `AxiaCS` are not in this Foundry project. Either they live in a different Foundry project / endpoint, or the agent code now runs inside `func-cs-agents-dev` / `axia-seekapa-cs-agents` repo without a Foundry assistant record. Worth confirming.

## 5. Recommended action plan (per-deletion OK required)

### Phase A — phone-spam stack (full delete, user-cleared)

```bash
RG=AZAI_group
az functionapp delete -g $RG -n func-phone-spam-checker-prod
az resource delete -g $RG -n appi-phone-spam-checker-prod \
  --resource-type microsoft.insights/components
az storage account delete -g $RG -n stphonespamcheckerprod -y
# repos in Corp-AI: nothing to delete — phone-spam may be inside cs-agents repo
```

### Phase B — sentimark side-cars (after Dor Cohen confirms migration complete)

```bash
RG=AZAI_group
az webapp delete -g $RG -n app-sentimark-prod
az redis delete -g $RG -n sentimark-v2-cache -y
az containerapp env delete -g $RG -n sentimark-env -y
# DO NOT touch stsentimarkv2 (shared storage)
# DO NOT touch sentimarkregistry (used by COMP-AEO + COMP-SEEKAPAAITRAININGAPI-PROD)
```

### Phase C — repo dormancy review

For each dormant Corp-domain repo above, decide: archive (set repo to disabled) vs delete.
Archive is reversible:

```bash
az repos update --repository <name|id> --project Corp-domain --default-branch refs/heads/master  # no-op example
# disable via REST:
az rest --method patch \
  --uri "https://dev.azure.com/Corp-domain/Corp-domain/_apis/git/repositories/<id>?api-version=7.1" \
  --body '{"isDisabled": true}'
```

### Phase D — function-trigger sweep

For each function app with 0 exec/30d, list trigger types:

```bash
for fn in func-client-eval-prod func-automation-fabric-prod func-qc-telephony-prod \
          func-seekapa-sales-agent-prod func-aeo-competitor-prod func-aeo-api-prod \
          func-aeo-audit-prod func-market-reports-prod; do
  echo "== $fn =="
  az functionapp function list -g AZAI_group -n $fn --query "[].{name:name, type:config.bindings[0].type}" -o table
done
```

If a function has only HTTP triggers and zero traffic, it's a stronger dormant signal than timer-triggered.

## 6. Hard rules (do not violate)

- **Never delete `stsentimarkv2`** — shared backing store.
- **Never delete `sentimarkregistry`** — pulled by `COMP-AEO` and `COMP-SEEKAPAAITRAININGAPI-PROD`.
- **Never delete `kv-seekapa-apps`** — central key vault, not flagged here, but assume in-use.
- Per-action explicit OK required for every deletion.
