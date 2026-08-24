# CS Agents — Azure Compliance Audit

**Date**: 2026-03-02
**Auditor**: worker-alpha (automated)
**Rules Reference**: `~/.claude/configs/azure-compliance-rules.json` v1.0.0

## Executive Summary

CS Agents has a minimal Azure footprint with only **2 function apps** (`func-cs-agents-dev` and `func-cs-agents-ai-dev`), both in `dev` environment. There are no legacy non-compliant resources to migrate. Both apps are **Running** on the shared ASP-AZAIPROJECTS plan with correct tags. The project also has a separate CRM-focused Azure Function project (`azure-function-crm/`) with its own Dockerfile and deploy scripts.

**Overall Status**: MOSTLY COMPLIANT (naming correct, dev-only deployment)

---

## Rule-by-Rule Assessment

### R001 — Resource Group (CRITICAL)

| Status | Detail |
|--------|--------|
| PASS | Both CS Agents resources are in `AZAI_group` |

### R002 — Region (CRITICAL)

| Resource | Location | Status |
|----------|----------|--------|
| func-cs-agents-dev | swedencentral | PASS |
| func-cs-agents-ai-dev | swedencentral | PASS |

**All resources in swedencentral. PASS.**

### R003 — Naming Convention (HIGH)

Expected pattern: `[type]-[project]-[env]`

| Resource | Current Name | Target Name | Status |
|----------|-------------|-------------|--------|
| Function App (main) | `func-cs-agents-dev` | `func-cs-agents-dev` | COMPLIANT |
| Function App (AI) | `func-cs-agents-ai-dev` | `func-cs-agents-ai-dev` | COMPLIANT |

**Note**: Both follow the `func-[project]-[env]` pattern correctly. When promoting to production, target names would be `func-cs-agents-prod` and `func-cs-agents-ai-prod`.

### R004 — Required Tags (HIGH)

| Resource | Brand | Project | Environment | Status |
|----------|-------|---------|-------------|--------|
| func-cs-agents-dev | Seekapa | CS-Agents | dev | PASS |
| func-cs-agents-ai-dev | Seekapa | CS-Agents | dev | PASS |

**All tags present and correct. PASS.**

### R005 — Shared Storage (MEDIUM)

| Status | Detail |
|--------|--------|
| N/A | CS Agents does not have a dedicated storage account |

### R006 — Shared App Service Plan (MEDIUM)

| Resource | App Service Plan | Status |
|----------|-----------------|--------|
| func-cs-agents-dev | ASP-AZAIPROJECTS | COMPLIANT |
| func-cs-agents-ai-dev | ASP-AZAIPROJECTS | COMPLIANT |

### R007 — SWA Free Tier (LOW)

| Status | Detail |
|--------|--------|
| N/A | CS Agents does not use Static Web Apps |

### R008 — Shared PostgreSQL (MEDIUM)

| Status | Detail |
|--------|--------|
| PASS | Uses `axia_seekapa_chatbot` database on shared PostgreSQL server |

---

## Resource Inventory

### Active (Running)

| Resource | Type | Name | Environment |
|----------|------|------|-------------|
| Function App | Microsoft.Web/sites | `func-cs-agents-dev` | dev |
| Function App | Microsoft.Web/sites | `func-cs-agents-ai-dev` | dev |

### Stopped / Legacy

None. No legacy resources to decommission.

---

## Production Promotion Plan

CS Agents is currently dev-only. When promoting to production:

| Current (Dev) | Target (Prod) | Action |
|---------------|---------------|--------|
| `func-cs-agents-dev` | `func-cs-agents-prod` | Create new function app |
| `func-cs-agents-ai-dev` | `func-cs-agents-ai-prod` | Create new function app |

Tags for production resources:
- Brand: Seekapa
- Project: CS-Agents
- Environment: prod

## Related Resources (Not Azure-Managed)

| Resource | Notes |
|----------|-------|
| `azure-function-crm/` | Subdirectory with separate CRM function app (has own Dockerfile, deploy.sh). Deployed via `axia-seekapa-crm` App Service. |
| `axia-seekapa-crm` | CRM Web App (Running, swedencentral). Separate from the CS Agents function apps. |

## Codebase Notes

- Project has `.dockerignore` missing from root (only in `azure-function-crm/`)
- Uses `requirements-test.txt` for test dependencies
- Has DeepEval testing integration (`.deepeval/`)
- Database: `axia_seekapa_chatbot` on shared PostgreSQL

---

## Compliance Score

| Rule | Status | Weight |
|------|--------|--------|
| R001 Resource Group | PASS | Critical |
| R002 Region | PASS | Critical |
| R003 Naming | PASS | High |
| R004 Tags | PASS | High |
| R005 Shared Storage | N/A | Medium |
| R006 Shared ASP | PASS | Medium |
| R007 SWA Tier | N/A | Low |
| R008 Shared PostgreSQL | PASS | Medium |

**Score: 6/6 applicable rules passing. CS Agents is the most compliant project in this audit batch. Only gap is dev-only deployment (no prod resources yet).**
