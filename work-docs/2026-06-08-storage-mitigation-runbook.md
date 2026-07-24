# Morning Storage Mitigation Runbook — 2026-06-08

Author: Claude (orchestrator), continuing Codex's stalled AEO migration session.
Scope: the **entire remaining AZAI_group storage estate**, not only Yasha's Cosmos.
All facts below were verified against live Azure on 2026-06-07 evening.

---

## 0. State snapshot (verified 2026-06-07)

**Storage estate is now only 3 data stores** (the marketing/spam SAs + training SAs from the
May consolidation are already gone — single subscription `08b0ac81…`, RG `AZAI_group`):

| Store | Type | Role | Public access | Status tonight |
|-------|------|------|---------------|----------------|
| `aeo-seekapa-db` | Cosmos | Yasha's AEO data (6 containers in db `aeo_data`) | Net: `0.0.0.0` only (Azure-internal) | **Firewall exposure REMEDIATED** ✅ |
| `azaigroup8dc3` | Storage | Dead WebJobs store (QC analyzer / sales-training / sales-webhook) | `allowBlobPublicAccess=true`, net `Allow` | No live leases (stale since Feb 2026); ORM rerouted off it |
| `stsentimarkv2` | Storage | **Canonical / KEEP** — WebJobs + archive target | `allowBlobPublicAccess=false` | Healthy; `aeo-archive` container ready |

**Identity facts for `shoval.be@i-sdd.com` (oid `f71d0e70-5b5c-484e-a683-e3b98685cc91`):**
- ✅ Cosmos **Built-in Data Reader** on aeo-seekapa-db → Cosmos read works.
- ❌ **No blob data-plane RBAC** on either storage account → Entra blob write 403s.
- ✅ **Contributor** (key retrieval works) → blob write must use **account key**.
- ❌ Not Owner/User-Access-Admin (can't self-grant blob RBAC; can't enumerate role assignments).
- Access is **group-mediated** (so `az role assignment list --assignee` shows empty — ignore that, it lies).

**Why Codex's run died:** opened Cosmos firewall to office IP `199.203.90.233`, then ran out of
workspace credits + lost sandbox DNS *before* the cleanup ran → firewall left open. **I closed it
tonight** (`ipRules` back to `[0.0.0.0]`, provisioningState Succeeded).

---

## 1. Pre-flight (run first)

```bash
# 1a. Confirm login + correct subscription
rtk az account show --query "{user:user.name,sub:name}" -o table
# expect: shoval.be@i-sdd.com / U-BTech - CSP (Z-Online); else: rtk az login

# 1b. Confirm the Cosmos firewall is still clean (should be [0.0.0.0] only)
rtk az cosmosdb show -g AZAI_group -n aeo-seekapa-db --query "ipRules[].ipAddressOrRange" -o tsv

# 1c. Venv check — /tmp is wiped on reboot, so recreate if missing
/tmp/aeo-cosmos-export-venv/bin/python -c "import azure.cosmos,azure.identity,azure.storage.blob; print('deps OK')" 2>/dev/null \
  || { rtk uv venv /tmp/aeo-cosmos-export-venv --python 3.13 \
       && rtk uv pip install --python /tmp/aeo-cosmos-export-venv/bin/python azure-cosmos azure-identity azure-storage-blob; }
```

---

## 2. PART A — AEO Cosmos export → stsentimarkv2  *(Yasha's ask)*

The original `export_aeo_cosmos_to_blob.py` writes blobs via Entra and **will 403** for your
identity. Use the **key-auth variant** I wrote: `export_aeo_cosmos_to_blob_keyauth.py`
(Cosmos read = Entra, blob write = account key). Pick ONE run option.

### Option 1 — Azure Cloud Shell  *(RECOMMENDED — zero firewall exposure)*
The `0.0.0.0` rule already allows Azure-internal traffic, so Cloud Shell reaches Cosmos with
**no firewall change at all**. Nothing to clean up afterward.

```bash
# In https://portal.azure.com Cloud Shell (bash):
#  - upload export_aeo_cosmos_to_blob_keyauth.py via Cloud Shell "Upload"
pip install --quiet azure-cosmos azure-identity azure-storage-blob
export AZURE_STORAGE_KEY="$(az storage account keys list --account-name stsentimarkv2 -g AZAI_group --query '[0].value' -o tsv)"
python export_aeo_cosmos_to_blob_keyauth.py --run-id 20260608-aeo-cosmos-to-stsentimarkv2
unset AZURE_STORAGE_KEY
```

### Option 2 — Office workstation  *(self-contained, firewall hole CANNOT be orphaned)*
Use the wrapper `run_export_from_office.sh`. It does add-IP → export → remove-IP in one process
with a `trap` cleanup + post-run verification (retries 5×, screams if the IP survives).

```bash
bash ~/tmp/aeo-migration/run_export_from_office.sh
# On success: ends with "[*] Firewall confirmed clean."
# If you EVER see the "CRITICAL: temp IP STILL ON COSMOS FIREWALL" banner, run the printed fix.
```

### A-verify (either option)
```bash
set +x; KEY=$(rtk az storage account keys list --account-name stsentimarkv2 -g AZAI_group --query "[0].value" -o tsv)
rtk az storage blob show --account-name stsentimarkv2 --container-name aeo-archive \
  --name "cosmos-export/run_id=20260608-aeo-cosmos-to-stsentimarkv2/manifest.json" \
  --account-key "$KEY" --query "{name:name,bytes:properties.contentLength}" -o json
# Then read total_documents from the manifest:
rtk az storage blob download --account-name stsentimarkv2 --container-name aeo-archive \
  --name "cosmos-export/run_id=20260608-aeo-cosmos-to-stsentimarkv2/manifest.json" \
  --account-key "$KEY" --file /tmp/aeo-manifest.json --only-show-errors && \
  rtk python3 -c "import json;m=json.load(open('/tmp/aeo-manifest.json'));print('docs:',sum(x['documents'] for x in m['exports']));[print(' ',x['container'],x['documents'],'docs',x['parts'],'parts') for x in m['exports']]"
unset KEY
```
✅ Pass = manifest exists, all 6 containers listed, doc counts > 0.

---

## 3. PART B — azaigroup8dc3 (dead WebJobs store)

Verified dead: no live leases (all applease blobs stale since Feb 2026), no Function App setting
references it, ORM pilot already rerouted to stsentimarkv2. Historically held secrets for
`qc-call-analyzer-func`, `sales-training-platform`, `sales-agent-webhook` — all migrated off.

### B1 — Immediate safe hardening *(do now; reversible, reduces exposure)*
```bash
# Turn OFF public blob access (it's currently ON — pointless exposure on a dead account)
rtk az storage account update -n azaigroup8dc3 -g AZAI_group --allow-blob-public-access false \
  --query "{name:name,publicAccess:allowBlobPublicAccess}" -o json
```

### B2 — Backup before any deletion *(cheap insurance — mirrors the May consolidation pattern)*
```bash
# Archive azaigroup8dc3 contents into stsentimarkv2 before decommission.
set +x
SRCKEY=$(rtk az storage account keys list -n azaigroup8dc3 -g AZAI_group --query "[0].value" -o tsv)
DSTKEY=$(rtk az storage account keys list -n stsentimarkv2 -g AZAI_group --query "[0].value" -o tsv)
rtk az storage container create --account-name stsentimarkv2 --name azaigroup8dc3-archive --account-key "$DSTKEY" --only-show-errors
for c in $(rtk az storage container list -n azaigroup8dc3-noop 2>/dev/null; rtk az storage container list --account-name azaigroup8dc3 --account-key "$SRCKEY" --query "[].name" -o tsv); do
  rtk az storage blob copy start-batch --account-name stsentimarkv2 --account-key "$DSTKEY" \
    --destination-container azaigroup8dc3-archive --destination-path "$c" \
    --source-account-name azaigroup8dc3 --source-account-key "$SRCKEY" --source-container "$c" --only-show-errors
done
unset SRCKEY DSTKEY
```

### B3 — 🛑 DECOMMISSION (DESTRUCTIVE — needs your explicit OK + Yasha awareness)
**Do NOT run until B2 backup verified.** Recommended conservative sequence:
```bash
# Stage 1 (reversible): network lock — deny all, observe for a few days
rtk az storage account update -n azaigroup8dc3 -g AZAI_group --default-action Deny --bypass AzureServices
# If nothing breaks after observation:
# Stage 2 (DESTRUCTIVE): delete the account
# rtk az storage account delete -n azaigroup8dc3 -g AZAI_group --yes   # <-- only on explicit go
```

---

## 4. PART C — verify protected apps still on safe storage

```bash
# All Function Apps' AzureWebJobsStorage target (names+account only, no secrets)
for app in func-qc-telephony-prod func-TrainingWorker-PROD COMP-SEEKAPAAITRAININGAPI-PROD func-cs-agents-dev; do
  echo "=== $app ==="
  rtk az functionapp config appsettings list -g AZAI_group -n "$app" -o json 2>/dev/null \
    | jq -r '.[]|select(.name=="AzureWebJobsStorage")|.value|capture("AccountName=(?<a>[^;]+)").a // "kv-ref-or-none"'
  rtk az functionapp show -g AZAI_group -n "$app" --query "state" -o tsv
done
# Web apps
rtk az webapp list -g AZAI_group --query "[].{name:name,state:state}" -o table
```
✅ Expect: every running app on `stsentimarkv2` (or KV ref), NONE on `azaigroup8dc3`.
(Verified tonight: func-qc-telephony-prod = stsentimarkv2 ✅. Confirm the other three.)

---

## 5. PART D — 🛑 Cosmos aeo-seekapa-db decommission *(only AFTER export verified + Yasha confirms)*

The export (Part A) is the prerequisite. Once the manifest verifies and **Yasha confirms** the
Cosmos can go:
```bash
# Reversible first: lock public network entirely
rtk az cosmosdb update -g AZAI_group -n aeo-seekapa-db --public-network-access DISABLED
# DESTRUCTIVE (only on explicit go):
# rtk az cosmosdb delete -g AZAI_group -n aeo-seekapa-db --yes
```
Do not delete the Cosmos account the same morning as the export — keep both copies until the
archive is independently confirmed.

---

## 6. Decision gates (the only things requiring your judgment)

1. **Export run option** — Cloud Shell (zero exposure) vs office wrapper. → Part A.
2. **azaigroup8dc3 deletion** — after backup + network-lock observation. → Part B3.
3. **Cosmos deletion** — needs Yasha's explicit confirm + verified archive. → Part D.

Everything else (firewall cleanup, hardening, backups, verification) is safe/reversible.

---

## 7. What Claude already did tonight (audit trail)

- **Removed** temp public IP `199.203.90.233` from `aeo-seekapa-db` firewall → back to `[0.0.0.0]`. (the orphaned exposure from Codex's run)
- Verified ORM pilot reroute (Codex's edits) — **zero** `azaigroup8dc3` refs remain in ORM-AGENT.
- Confirmed `stsentimarkv2/aeo-archive` target exists.
- Mapped full storage estate; confirmed marketing/training SAs already gone.
- Established RBAC reality (Cosmos read ✅ / blob Entra ❌ / Contributor-key ✅) via empirical probes (probe blobs cleaned up).
- Proved azaigroup8dc3 has no live leases (stale since Feb 2026).
- Wrote `export_aeo_cosmos_to_blob_keyauth.py` and `run_export_from_office.sh`.

Files: `~/tmp/aeo-migration/{export_aeo_cosmos_to_blob_keyauth.py, run_export_from_office.sh}` · this runbook: `~/docs/2026-06-08-storage-mitigation-runbook.md`
