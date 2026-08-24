# v110 Deploy Runbook — Phase F1 + KB additions

**Date:** 2026-05-06
**Branch:** `feat/v109-yasha-multilingual` (parent for v110 work)
**Predecessor spec:** `2026-05-06-seekapa-account-verification-flow.md`

This runbook captures the steps that Claude could not run unilaterally because they touch the live Foundry vector store, the production Function App, or both. Each step lists exact commands and the rollback. **Run them in order.**

---

## 0. Pre-flight (read-only, already done in-session)

- ✅ KB snapshot at `kb-snapshot-2026-05-05/` — captured 18 deployed files via `pull_kb.py`.
- ✅ CRM endpoint probed at `https://az-corp.corp-domain.com/api/v1/ai-agent/customer` — bearer in Shoval KV under secret name `CRM-API-KEY`. Live `compliance_status` for verified FTD customer is `ADVANCED VERIFIED`. Live not-found path returns HTTP 200 + `errors[]`.
- ✅ Local handler bench: ~15μs per 3-turn verification flow with fake CRM; flag-off path ~120ns per Chatwoot message (negligible).
- ✅ Real-network bench: 21–32 ms p50 for 8 not-found CRM calls (well under 3 s timeout).

## 1. Add Glossary + Objection-Handling to the live vector store

These two files are pure additions — no replacement of existing files. Net-new content only.

```bash
cd /home/shovalbe/projects/cs-agent/axia-seekapa-cs-agents-devops

# Confirm what would happen.
python3 kb-source/upload_to_foundry.py
# Plan: upload 2 markdown files (~18 KB total) to vs_BhDnWqMdIsxjgv1f0sQOuwX6.

# Execute when satisfied.
python3 kb-source/upload_to_foundry.py --execute --files glossary,objections

# Verify by re-snapshotting.
python3 kb-snapshot-2026-05-05/pull_kb.py
ls kb-snapshot-2026-05-05/ | grep -E "Glossary|Objection"
```

**Rollback:** the upload script's deletes are gated by `--replace-master`; without that flag, only additions are made. To remove the new files, use the Foundry portal or extend the script to support `--rollback` by file_id.

## 2. (Optional) Replace the master FAQ with v3 ($250 min deposit added)

Only run if you want the deployed `Seekapa_FAQ_KB.pdf` removed and replaced with `Seekapa_FAQ_KB_v3.txt`. The v3 file adds Q26 (minimum deposit $250) and updates the header; otherwise identical.

```bash
python3 kb-source/upload_to_foundry.py --execute --files faq_v3 --replace-master
```

This deletes the existing FAQ from the vector store, deletes the underlying file from `/files`, then uploads the new one. **Irreversible from the script.** Save the old file_id from the dry-run plan before executing if you want to roll back manually via the Foundry portal.

## 3. Configure the Function App for v110 (flag still OFF after this step)

Set the KV reference and the (still-disabled) flag on `axia-seekapa-crm`:

```bash
APP=axia-seekapa-crm
RG=$(az functionapp list --query "[?name=='$APP'].resourceGroup | [0]" -o tsv)

# Confirm the KV secret URI you want to bind to.
az keyvault secret show --vault-name Shoval --name CRM-API-KEY --query "id" -o tsv
# Example: https://shoval.vault.azure.net/secrets/CRM-API-KEY/<version>

# Bind CRM_API_KEY (resolves at app start) and add the flag (still false).
az functionapp config appsettings set \
  --name "$APP" --resource-group "$RG" \
  --settings \
    "CRM_API_KEY=@Microsoft.KeyVault(SecretUri=https://shoval.vault.azure.net/secrets/CRM-API-KEY/)" \
    "SEEKAPA_VERIFY_ENABLED=false"

# Confirm.
az functionapp config appsettings list --name "$APP" --resource-group "$RG" \
  --query "[?name=='CRM_API_KEY' || name=='SEEKAPA_VERIFY_ENABLED'].{name:name, value:value}" -o table
```

**Rollback:** `az functionapp config appsettings delete --name "$APP" --resource-group "$RG" --setting-names SEEKAPA_VERIFY_ENABLED CRM_API_KEY`.

**Important:** the Function App's managed identity needs *Key Vault Secrets User* role on the `Shoval` vault. If absent, the app will see `CRM_API_KEY` as the literal `@Microsoft.KeyVault(...)` string and `get_crm_bearer_from_env()` will raise `RuntimeError`. Verify with:

```bash
APP_ID=$(az functionapp identity show --name "$APP" --resource-group "$RG" --query principalId -o tsv)
az role assignment list --assignee "$APP_ID" \
  --scope $(az keyvault show --name Shoval --query id -o tsv) -o table
```

## 4. (Optional) Stage v110 with flag ON, soak-test 100 conversations

This is the eval gate the spec promised. **Costs LLM tokens** (~$5–30 depending on agent model) and produces real Foundry conversation traces. **Use a non-prod test agent** if available; otherwise document the run and don't repeat.

```bash
# Flip the flag temporarily, restart, then run the test harness.
az functionapp config appsettings set --name "$APP" --resource-group "$RG" \
  --settings "SEEKAPA_VERIFY_ENABLED=true"
az functionapp restart --name "$APP" --resource-group "$RG"

# Run the multi-turn runner against the v110 eval traces.
# (Runner is in evals/scripts/. If absent, see audit-v109-2026-04-29.md §6 step 5.)
python3 evals/scripts/run_intake_eval.py --dataset evals/data/intake_eval_v110.jsonl \
                                         --target https://$APP.azurewebsites.net/api/customer

# Compare p50/p95 latency to the v109 baseline. Acceptance gate: p95 ≤ v109 p95 + 200 ms.

# REVERT the flag immediately after.
az functionapp config appsettings set --name "$APP" --resource-group "$RG" \
  --settings "SEEKAPA_VERIFY_ENABLED=false"
az functionapp restart --name "$APP" --resource-group "$RG"
```

Pass criteria (per spec §8):
- All 5 v110 eval traces pass with `expected_route` honoured.
- p95 latency ≤ v109 baseline p95 + 200 ms.
- No PII leaked in logs (grep App Insights for full email strings).
- Anti-loop AC14 invariant holds: subsequent customer pings after a forwarding reply do NOT re-escalate.

## 5. Promote v110 to prod

**ONLY after Step 4 passes**, flip the flag back on as the durable production state:

```bash
az functionapp config appsettings set --name "$APP" --resource-group "$RG" \
  --settings "SEEKAPA_VERIFY_ENABLED=true"
az functionapp restart --name "$APP" --resource-group "$RG"
```

**Rollback (use if customer reports come in):**

```bash
az functionapp config appsettings set --name "$APP" --resource-group "$RG" \
  --settings "SEEKAPA_VERIFY_ENABLED=false"
az functionapp restart --name "$APP" --resource-group "$RG"
```

The v109 path is preserved bit-for-bit when the flag is off (verified by `test_flag_off_returns_none_no_state_change`).

## 6. Post-deploy verification (15 min after step 5)

- Tail App Insights: `traces | where message startswith "[VERIFY]" | take 50` — should show real verification flow firings.
- Spot-check a handful of conv ids: redacted email pattern (`me***@gmail.com`) appears, full email never appears.
- Verify webhook latency p95 in App Insights matches the soak-test p95 ± 50 ms.
- Wait 24 h before considering Phase F2 (Yasha-style intake refinement) per spec §8.
