# ADO PR Review via Foundry gpt-5.5 — Integration Bundle

**Date:** 2026-05-13
**Owner:** Shoval Benjer
**Target Rig:** `cs-agent` (`Corp-domain/Corp-AI/axia-seekapa-cs-agents`) — pilot first, then clone to other 3 Rigs.
**Status:** Spec only. Nothing is committed or deployed by this bundle.

This adds a `codex_review` stage to the existing `azure-pipelines.yml` that, on every PR build, calls Foundry gpt-5.5 with the diff and posts a markdown comment to the PR via the ADO REST API using `System.AccessToken`. No webhook, no PAT, no admin involvement (assuming permission check below passes).

---

## What's in this bundle

| File | What it is | Where it lands when applied |
|---|---|---|
| `README.md` | This file. Integration steps + permission check. | (stays in `~/docs/specs/`) |
| `pipeline-delta.yml` | The ~90-line stage to append to the existing `azure-pipelines.yml`. | Appended to `azure-pipelines.yml` at repo root. |
| `review-prompt.md` | The system + user prompt template the pipeline pipes to gpt-5.5. | Committed to repo at `scripts/codex-review-prompt.md`. |

## Pre-flight (do these in order before the first PR)

### 1. Permission check — the make-or-break step

Web UI path:
```
dev.azure.com/Corp-domain/Corp-AI/_settings/repositories
  → axia-seekapa-cs-agents
  → Security tab
  → search for "Project Collection Build Service (Corp-domain)"
  → confirm "Contribute to pull requests" = Allow
```

If you can see this page → set it to `Allow` if not already → proceed to step 2.
If you cannot see this page at all → you need Yasha (Project Admin) for this one toggle. The ask is "set Contribute to pull requests = Allow for Project Collection Build Service on cs-agent" — it's a single click, never needs changing again.

### 2. Foundry deployment access

Confirm the existing `managecorpairegistry` service connection (used by your current pipeline) has access to call `gpt-5.5` on Foundry. Verify with:
```bash
az role assignment list \
  --assignee <service-connection-spn-object-id> \
  --scope /subscriptions/<sub>/resourceGroups/AZAI_group/providers/Microsoft.CognitiveServices/accounts/brn-azai \
  --query "[].roleDefinitionName" -o tsv
```
You should see `Cognitive Services User` (or higher). If not, the call will 403 — easy to add via Azure portal IAM.

### 3. Variable group sanity

Your existing `cs-agents-secrets` variable group is used by the pipeline. The new stage does NOT need new secrets — it auths via the service connection. So no changes to the variable group needed for v1.

(Optional: if you later want to skip the service connection and call Foundry directly with an API key, add `FOUNDRY_API_KEY` to `cs-agents-secrets` and swap the `AzureCLI@2` task for a `Bash@3` task. Less professional; don't unless forced.)

### 4. Scripts directory

Confirm `scripts/` exists at the repo root (your existing pipeline already references `scripts/**` in its `trigger.paths.include`, so it almost certainly does). The review prompt lands at `scripts/codex-review-prompt.md`.

## Integration steps

1. Read both `pipeline-delta.yml` and `review-prompt.md`; edit the prompt's voice/focus to match how you want gpt-5.5 to review.
2. Commit on a feature branch:
   - Append `pipeline-delta.yml` content to the END of `azure-pipelines.yml`.
   - Add `scripts/codex-review-prompt.md` (copy of `review-prompt.md`).
3. Push the feature branch. **Do NOT merge yet.**
4. Open a PR from the feature branch → `master`. Watch the pipeline run.
   - Expected: a comment from the build identity appears on the PR with a TL;DR + concerns + verdict.
   - If you get `403 Forbidden` in the POST step → permission check (step 1 above) is the cause.
   - If you get `401 Unauthorized` from the Foundry call → service connection IAM (step 2) is the cause.
   - If the comment posts but is empty or malformed → review-prompt logic, iterate.

## Roll-out to the other 3 Rigs

Once cs-agent is green:
- Copy the same `codex_review` stage to:
  - `Corp-domain/Corp-AI/<campaign-analysis repo>`
  - `Corp-domain/Corp-AI/<qc-telephony-api repo>`
  - `Corp-domain/Corp-AI/<seekapa-training-platform repo>`
- Each repo gets its own copy of `scripts/codex-review-prompt.md` — you can tune the prompt per-Rig (e.g., for `campaign-analysis`, emphasize MCP-gateway contract changes).
- Permission check (step 1) must be repeated per repo — `Contribute to pull requests` is a per-repo setting.

## Cost envelope

Per PR review:
- Input: diff (≤5000 lines, truncated) + prompt ≈ 8–15K input tokens.
- Output: review markdown ≈ 1–2K output tokens.
- gpt-5.5 rate × that = small fraction of a cent. 50 PRs/week = pennies/week.

Well inside your "$0 extra spend" envelope — Foundry tokens come from the existing AZAI_group budget you already pay against.

## Failure handling

The pipeline stage is `dependsOn: []` so it runs in parallel with your existing stages and **never blocks merges**. If gpt-5.5 is unavailable or the call fails, the stage logs the error and exits 0 — your tests + build stages are unaffected.

## What this does NOT do (deliberate)

- Does not do **inline file-line comments** (yet). v1 posts a single thread comment with the whole review. Inline support requires parsing diff hunks and is twice the YAML; defer.
- Does not deduplicate on re-runs. Every push to the PR triggers a new comment. After it works, we can add a "find existing thread by marker and update" pass.
- Does not block merges on review verdict. Codex is advisory.
- Does not call Codex CLI on the build agent. Direct Foundry REST via `az rest` is cleaner and matches the spec hardening item (skip CLI on cloud, use SDK/REST).
- Does not run for non-PR builds. `condition: eq(variables['Build.Reason'], 'PullRequest')`.

## After it works

This unblocks the "Codex reviews on ADO" headache. The same `System.AccessToken` + `az rest` pattern then composes naturally with the Hive: a Polecat triggered by a `dogs` bead can ALSO post a follow-up comment to the originating PR via the same endpoint. The whole loop closes.
