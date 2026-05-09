# Deployment

![AI Department Logo](../../ai_department_logo.png =96x)

This page is the release and runtime runbook for CS Agents.

## Environments

| Environment | Purpose | Current Status |
|---|---|---|
| `dev` | active integration and validation environment | active |
| `stage` | PR validation target and release candidate gate | pipeline-driven |
| `master` | protected production promotion path | release-only |

## Primary Runtime

| Item | Value |
|---|---|
| Function app | `func-cs-agents-dev` |
| Resource group | `AZAI_group` |
| Region | `swedencentral` |
| Pipeline | `azure-pipelines.yml` |

## Branch Flow

```
feature/* → PR to stage → CI (lint + tests + eval gate) → merge
stage → PR to master → deploy via AzureCLI@2 service principal
```

CI triggers on: `master`, `stage`, `feature/*`

## Release Flow

1. push changes to a `feature/*` branch
2. open PR into `stage`
3. CI runs deterministic tests and Foundry smoke eval gate
4. merge into `stage` only after passing validation
5. promote to `master` using protected branch flow — deploy runs automatically

## CI And Evaluation Gate

The repo treats evaluation as part of release quality, not as an afterthought.

### Deterministic Gate

- pip-audit security scan (non-blocking)
- lint (ruff)
- type checks (mypy)
- unit tests: `test_chatwoot_webhook.py`, `test_create_ticket.py`, `test_message_normalizer.py`
- integration tests (stage branch only, when `CHATWOOT_WEBHOOK_URL` is set)

### Foundry Smoke Eval Gate

- dataset: `tests/test_data/foundry_smoke_eval.jsonl`
- rows: `25` (EN, AR, AR-Gulf, ES, PT — all routes covered)
- primary evaluator: `grok-4-1-fast-reasoning-2-eval`
- audit evaluator: `DeepSeek-V3.2` (first 3 rows)
- input budget: `1500` tokens per row
- output budget: `120` tokens per row

Routes covered: `resolve`, `escalate`, `redirect`, `no_advice`, `disconnect`

Supporting implementation:

- [Foundry eval CI plan](../FOUNDRY-EVAL-CI-PLAN.md)
- [Eval gate script](../../scripts/foundry_eval_gate.py)

## Deploy Mechanism

Deployment uses `AzureCLI@2` with service principal (`azureSubscription: U-BTech - CSP (Z-Online)`).
No Kudu basic auth. No manual `func azure functionapp publish`.

```yaml
- task: AzureCLI@2
  inputs:
    azureSubscription: '$(azureSubscription)'
    scriptType: 'bash'
    inlineScript: |
      az functionapp deployment source config-zip \
        --resource-group $(resourceGroup) \
        --name $(functionAppName) \
        --src function-app.zip
```

## Post-Deploy Checks

1. confirm function app is healthy
2. run spec-compliance smoke tests (event-gate and assignee-gate checks)
3. verify webhook accepts valid Chatwoot events
4. confirm assignee gate: a payload with `meta.assignee` non-null must return `skipped: true`
5. check pipeline artifacts for the Foundry eval report

## Rollback

```bash
git revert <commit>
git push origin <branch>
```

Then let the normal pipeline redeploy the reverted state.

## Codex CI Reviewer

The pipeline runs a code review pass after each diff using the OpenAI Responses API
(`gpt-5.3-codex-CI-Reviewer`). Findings are posted as a PR comment.
If `codexAgentId` is set, the Foundry Agent API (threads/runs) is used instead.

## Operational Links

- [Home](./Home)
- [Architecture](./Architecture)
- [Compliance](./Compliance)
- [Handover Notes](./Handover-Notes)
