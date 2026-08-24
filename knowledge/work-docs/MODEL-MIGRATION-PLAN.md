# Model Migration: GPT 5.2 → GPT 5.4 Nano (High Reasoning), Per-Project Deployments

**Owner:** Shoval
**Created:** 2026-04-06
**Goal:** Cut Foundry model spend by replacing the shared `gpt-5.2` deployment with per-project `gpt-5.4-nano-{project}` deployments at high reasoning effort. Per-project naming gives full traceability in the Azure Monitor `TokenTransaction` metric.

---

## Why

### Current state
- `gpt-5.2` deployment burned **60.2M tokens** in the last 30 days, costing **$293.26** (86.8% of `brn-azai`).
- The deployment is **unattributed** — no Foundry agent uses it. Some function app/script is calling it directly via the Azure OpenAI SDK.
- `brn-azai` has **no diagnostic settings** so we cannot see which caller is using which deployment.
- Daily pattern (Mar 9-19, 5-7M tokens/day, then near-zero) suggests a batch job.

### Why per-project deployments
- **Traceability**: each deployment shows up as a separate dimension in `TokenTransaction` metric, so cost is attributable without needing per-call diagnostic logs.
- **Quota isolation**: a runaway batch job in one project does not starve other projects of TPM.
- **Independent rollback**: a bad prompt or bad model version on one project does not block all projects.
- **Easier deprecation**: when a project is decommissioned, just delete its deployment.

### Why gpt-5.4-nano with high reasoning
- gpt-5.4-nano is roughly **5x cheaper per token** than gpt-5.2 based on our actual cost data:
  - gpt-5.2 effective rate (blended I/O): $293.26 / 60.2M = **$4.87 / 1M tokens**
  - gpt-5.4-nano effective rate (blended I/O): $2.16 / 2.4M = **$0.90 / 1M tokens**
- High reasoning effort uses more reasoning tokens (chain-of-thought) but each token is still nano-priced.
- Reasoning effort = "high" recovers most of the quality gap between nano and full-size models on multi-step tasks.

---

## Cost Reduction Estimate

### Current spend (last 30 days, gpt-5.2 deployment)
- Tokens: 60.2M
- Cost: $293.26/month
- Annualized: $3,519/year

### Projected spend (if migrated to gpt-5.4-nano-* with high reasoning)

| Scenario | Reasoning multiplier | Effective tokens | Monthly cost | Savings | Saving % |
|---|---|---|---|---|---|
| **Conservative** (same workload, no reasoning overhead) | 1.0x | 60.2M | **$54** | **$239** | **82%** |
| **Realistic** (high reasoning ≈ 1.5x token usage) | 1.5x | 90.3M | **$81** | **$212** | **72%** |
| **Pessimistic** (high reasoning ≈ 2.5x token usage) | 2.5x | 150.5M | **$135** | **$158** | **54%** |

### Realistic estimate

**Monthly savings: $158 – $239** (~54-82%)
**Annualized savings: $1,896 – $2,868**

The wide range reflects uncertainty about how much reasoning the workload actually needs. Whichever batch job is currently calling `gpt-5.2` likely doesn't need maximum reasoning — that was just the default. Even at the pessimistic 2.5x reasoning multiplier, the migration saves more than half.

### Other downstream savings (compound effect)
- **`gpt-5` deployment** (used by training, AxiaCS, seekapa-backend): 717K tokens, ~$2.50/month. Migrating to per-project gpt-5.4-nano-* saves ~$1.50/month per project consumer.
- **`gpt-4.1` / `gpt-4o`** (compliance-exam): low volume, but still candidate for migration.

---

## Per-Project Migration Tasks

Each project has a self-contained task. Each task is:
1. Create a new deployment named `gpt-5.4-nano-{project}` on `brn-azai`.
2. Update the project's environment config to point at the new deployment.
3. Set `reasoning_effort: "high"` in the project's model invocation code.
4. Verify token attribution in `TokenTransaction` metric.
5. Delete or downgrade the old deployment (only after all consumers migrated).

### Common steps (copy into each task)

**Create deployment** (Azure CLI):
```bash
az cognitiveservices account deployment create \
  --resource-group AZAI_group \
  --name brn-azai \
  --deployment-name "gpt-5.4-nano-${PROJECT}" \
  --model-name gpt-5.4-nano \
  --model-version "2026-03-17" \
  --model-format OpenAI \
  --sku-capacity 50 \
  --sku-name "GlobalStandard"
```

**Set reasoning effort** (Python OpenAI SDK):
```python
response = client.responses.create(
    model="gpt-5.4-nano-${PROJECT}",
    input=[{"role": "user", "content": message}],
    reasoning={"effort": "high"},
)
```

**Verify attribution** (after migration):
```bash
python3 axia-seekapa-cs-agents-devops/scripts/foundry_cost_audit.py --days 7
# Look for `gpt-5.4-nano-${PROJECT}` row in the "Token usage by deployment" table.
```

---

### Project 1: marketing-newsletter (PRIMARY SUSPECT for gpt-5.2 burn)

**Owner:** ?
**Function App:** `func-marketing-newsletter`
**Plan:** premium-marketing-plan (EP1, $153/mo)
**Current model:** unknown (no `MODEL` env var — hardcoded in code)
**Suspected because:** uses `MarketingNewsletter-AzureOpenAiEndpoint` from KV; daily batch pattern matches gpt-5.2 spike.

#### Tasks
- [ ] **Audit source code** in `func-marketing-newsletter` repo for hardcoded `gpt-5.2` model name. Likely in the newsletter generation script.
- [ ] Create `gpt-5.4-nano-marketing-newsletter` deployment on brn-azai (capacity 100, the current biggest consumer).
- [ ] Add `AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.4-nano-marketing-newsletter` to function app settings.
- [ ] Update generator to read `os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]` instead of hardcoded value.
- [ ] Set `reasoning_effort: "high"` in the API call.
- [ ] Deploy + monitor for 7 days.
- [ ] Verify the new deployment shows in `TokenTransaction` metric.
- [ ] **Bonus**: move function app from EP1 ($153/mo) to Y1 Consumption (~$13/mo) if newsletter generation is not latency-critical → +$140/mo savings.

**Estimated savings:** $200/month (largest single contributor)

---

### Project 2: automation-fabric

**Owner:** ?
**Function App:** `func-automation-fabric-prod`
**Current model:** unknown (uses shared `MarketingNewsletter-AzureOpenAiEndpoint`)

#### Tasks
- [ ] Audit code for hardcoded model names.
- [ ] Create `gpt-5.4-nano-automation-fabric` deployment.
- [ ] Set `AZURE_OPENAI_DEPLOYMENT_NAME` in function app settings.
- [ ] Update code to read env var + set high reasoning.
- [ ] Verify attribution after 7 days.

**Estimated savings:** $20-50/month (depends on actual usage)

---

### Project 3: market-reports

**Owner:** ?
**Function App:** `func-market-reports-prod`
**Current model:** unknown (uses shared MarketingNewsletter endpoint from KV)

#### Tasks
- [ ] Audit code for hardcoded model.
- [ ] Create `gpt-5.4-nano-market-reports` deployment.
- [ ] Update env vars + code.
- [ ] Verify attribution.

**Estimated savings:** $10-30/month

---

### Project 4: training-prod

**Owner:** ?
**Function App:** `func-training-prod`
**Current model:** `gpt-5` (explicit env var: `GPT5_DEPLOYMENT_NAME=gpt-5`)
**Token volume (last 30d):** 717K on shared `gpt-5` deployment (small)

#### Tasks
- [ ] Create `gpt-5.4-nano-training` deployment.
- [ ] Update env vars: `GPT5_DEPLOYMENT_NAME=gpt-5.4-nano-training` (rename for consistency, or add `MODEL_DEPLOYMENT_NAME`).
- [ ] Update code to set `reasoning_effort: "high"` for hard tasks (compliance content), default for easy ones.
- [ ] Verify training content quality after 1 week.

**Estimated savings:** $2-5/month (low volume, but cleaner attribution)

---

### Project 5: compliance-exam

**Owner:** ?
**Function App:** `func-compliance-exam-prod`
**Current model:** `gpt-4.1` with fallback `gpt-4o`

#### Tasks
- [ ] Create `gpt-5.4-nano-compliance` deployment.
- [ ] Update `AZURE_OPENAI_DEPLOYMENT` env var + fallback.
- [ ] Re-run any existing exam-grading test set against the new model to confirm quality before flipping prod traffic.
- [ ] Set high reasoning (this workload needs it for grading nuance).

**Estimated savings:** $5-15/month

---

### Project 6: AEO (Answer Engine Optimization)

**Owner:** ?
**Function Apps:** `func-aeo-api-prod`, `func-aeo-competitor-prod`, `func-aeo-audit-prod`
**Container App:** `aeo-api`
**Current model:** mixed — `aeo-api` container uses raw OpenAI key (not Azure), function apps use brn-azai.

#### Tasks
- [ ] Decide whether to consolidate to Azure (predictable cost) or keep on raw OpenAI (cheaper for some models).
- [ ] If consolidating: create `gpt-5.4-nano-aeo` deployment on brn-azai.
- [ ] Update all 3 function apps + container app to use the new deployment.
- [ ] Set high reasoning for competitor analysis (needs it), default for simple lookups.

**Estimated savings:** $10-30/month

---

### Project 7: seekapa-backend

**Owner:** ?
**Container Instance:** `seekapa-backend`
**Current model:** `gpt-5` (and `gpt-5-pro`, `gpt-5-codex`)

#### Tasks
- [ ] Create `gpt-5.4-nano-seekapa-backend` deployment.
- [ ] Add `BACKEND_DEPLOYMENT_NAME` env var.
- [ ] Update container code to use new deployment.
- [ ] **Keep** `gpt-5-pro` deployment for premium-tier requests (no nano equivalent).

**Estimated savings:** $5-10/month

---

### Project 8: SIU + SIU-FLOW

**Owner:** Shoval
**Foundry Agents:** `SIU`, `SIU-FLOW`
**Current model:** `gpt-5.4-nano-cs-agent` (SHARED with seekapa cs-agent)

#### Tasks
- [ ] **Critical**: SIU is currently sharing the cs-agent deployment, which contaminates attribution.
- [ ] Create `gpt-5.4-nano-siu` deployment.
- [ ] Update SIU agent definition in Foundry portal (Build → SIU → Settings → Model) to point at the new deployment.
- [ ] Update SIU-FLOW agent similarly.
- [ ] After migration, the cs-agent deployment will only show seekapa traffic (clean attribution).

**Estimated savings:** $0 direct, but enables clean per-project tracking.

---

### Project 9: seekapa (cs-agent) — ALREADY DONE ✓

**Owner:** Shoval
**Foundry Agent:** `seekapa` (v97 with Yasha flow)
**Current model:** `gpt-5.4-nano-cs-agent`

This is already on a per-project nano deployment. No action needed.

**Recommended improvement:**
- [ ] Set `reasoning_effort: "high"` in `channel_router/__init__.py:198` body construction. Currently uses default reasoning. High reasoning helps with the new identification flow + escalation classification.

---

### Project 10: AxiaCS

**Owner:** ?
**Foundry Agent:** `AxiaCS` v77
**Current model:** `gpt-5` (full-size, not nano)

#### Tasks
- [ ] Create `gpt-5.4-nano-axia-cs` deployment.
- [ ] Update AxiaCS agent definition in Foundry portal to use new deployment.
- [ ] Run eval comparison (v77 on gpt-5 vs new version on gpt-5.4-nano + high reasoning) before switching prod.

**Estimated savings:** $1-3/month (low current volume)

---

### Project 11: Olson-Funnel

**Owner:** ?
**Foundry Agent:** `Olson-Funnel` v7
**Current model:** `gpt-5.4` (full-size)
**Token volume:** 7.6M / 30 days ($15.53/month)

#### Tasks
- [ ] Test workload on gpt-5.4-nano + high reasoning. If quality holds, migrate.
- [ ] Create `gpt-5.4-nano-olson-funnel` deployment.
- [ ] Update agent definition.

**Estimated savings:** $10/month (~65% of current Olson cost)

---

### Project 12: Call-analyser-agent (qc project)

**Owner:** Yasha
**Foundry Agent:** `Call-analyser-agent` v54
**Function App:** `func-qc-analyzer-prod`
**Current model:** `gpt-5.4-nano-call-analysis-agent` (already on per-project nano)
**Token volume:** 12.6M / 30 days

This is already on a per-project nano deployment. **Low priority** — already optimized.

#### Tasks
- [ ] Verify `reasoning_effort: "high"` is set on the eval-related calls (they need it more than transcription analysis).
- [ ] No deployment changes needed.

---

## Migration Order (Highest ROI First)

| Order | Project | Est. Savings | Effort | Risk |
|---|---|---|---|---|
| 1 | **marketing-newsletter** | $200/mo | 4-8h | Medium (find hardcoded model) |
| 2 | **Olson-Funnel** | $10/mo | 1h (Foundry portal only) | Low |
| 3 | **automation-fabric** | $30/mo | 4h | Medium |
| 4 | **market-reports** | $20/mo | 3h | Medium |
| 5 | **compliance-exam** | $10/mo | 4h (need quality validation) | Medium |
| 6 | **AEO (3 apps)** | $20/mo | 8h | Medium |
| 7 | **seekapa-backend** | $7/mo | 4h | Low |
| 8 | **SIU split** | $0 (attribution) | 1h | Low |
| 9 | **training** | $4/mo | 3h | Low |
| 10 | **AxiaCS** | $2/mo | 2h | Low |

**Total estimated monthly savings:** $300/mo
**Total estimated annual savings:** $3,600/year
**Total estimated effort:** ~38 hours

---

## Pre-flight Checklist (Before Starting Any Migration)

- [ ] **Enable diagnostic settings on `brn-azai`** so we can see request attribution per deployment via Log Analytics:
  ```bash
  az monitor diagnostic-settings create \
    --resource "/subscriptions/08b0ac81-a17e-421c-8c1b-41b59ee758a3/resourceGroups/AZAI_group/providers/Microsoft.CognitiveServices/accounts/brn-azai" \
    --name brn-azai-diagnostics \
    --workspace workspace-groupK0Th \
    --logs '[{"category":"RequestResponse","enabled":true},{"category":"Audit","enabled":true},{"category":"Trace","enabled":true}]' \
    --metrics '[{"category":"AllMetrics","enabled":true}]'
  ```

- [ ] **Run baseline cost audit** and save:
  ```bash
  python3 axia-seekapa-cs-agents-devops/scripts/foundry_cost_audit.py --days 30 --out qa_reports/foundry_cost_baseline_$(date +%Y%m%d).md
  ```

- [ ] **Verify gpt-5.4-nano TPM quota** is sufficient for all per-project deployments (sum of capacities ≤ regional cap).

- [ ] **Coordinate with project owners** before changing their model — quality regression risk.

---

## Post-Migration Validation

After each project migrates:

1. Wait 7 days for cost data to settle.
2. Re-run `foundry_cost_audit.py --days 7`.
3. Verify the new deployment shows in the "Token usage by deployment" section.
4. Confirm `gpt-5.2` token volume drops by the expected amount.
5. Run any project-specific eval suite (cs-agent has DeepEval + foundry_eval_gate; others may need to add one).
6. Ask owner to verify quality hasn't regressed for 1 week before deleting the old deployment.

After ALL projects migrate:

- [ ] **Delete `gpt-5.2` deployment** entirely (zero-traffic confirmed by metric).
- [ ] **Delete `sora-2` deployment** if still unused (already at $0/mo).
- [ ] **Delete `gpt-5.2-figma` deployment** if figma agent is decommissioned, or migrate it.
- [ ] **Consolidate eval judges** to a single deployment if possible (Grok + DeepSeek currently both used).

---

## Monitoring & Alerts

Set up after migration:

1. **Budget alert** on AZAI_group: $1000/mo with alerts at 80%/100%/forecast.
2. **Per-deployment token metric alert**: alert if any single deployment exceeds 10M tokens/day for 3 consecutive days (catches runaway batch jobs early).
3. **Weekly cost audit** in CI: schedule `foundry_cost_audit.py` to run every Monday and post the report to a dashboard.

---

## References

- `axia-seekapa-cs-agents-devops/scripts/foundry_cost_audit.py` — re-runnable cost audit
- `~/Documents/CS_Agent_Eval_SOTA_Audit_20260406/cs_agent_eval_sota_audit.md` — eval SOTA audit (separate doc)
- Azure Cost Management Query API: `POST /subscriptions/{sub}/resourceGroups/AZAI_group/providers/Microsoft.CostManagement/query?api-version=2023-11-01`
- Azure Monitor metric: `TokenTransaction` on `Microsoft.CognitiveServices/accounts` resources, with `ModelDeploymentName` as a filter dimension
