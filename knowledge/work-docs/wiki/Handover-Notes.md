# Handover Notes

![AI Department Logo](../../ai_department_logo.png =96x)

This page stays intentionally short. It exists to give the next owner a fast operational entry point.

## If You Have Five Minutes

Read these in order:

1. [Home](./Home)
2. [Architecture](./Architecture)
3. [Deployment](./Deployment)
4. [Compliance](./Compliance)

## Current Reality

The system is a Chatwoot + Foundry support-agent stack with CI, evaluation, and signal-driven escalation as first-class concerns.

- Active prompt (live in Foundry): **`seekapa:111` (v107.3 yasha-style)** at `agent-prompts/seekapa-system-prompt-v107.3-yasha-style.md`. Deployed 2026-04-27 via PR #175. Eval pass rate 64% (16/25 smoke), p50 latency 7.9s, p95 12.6s. Vector store: `vs_yuCtQgmt2I9W0wTCMBnyP1hf` (Seekapa_FAQ_KB_v2). Rollback path: POST `seekapa:109` definition (preserved in PR #175 commit message). Always verify version in the Foundry portal before changing prompt logic.
- Escalation: **assignee-gate** — bot goes silent when `conversation.meta.assignee` is non-null. No turn counter. CW controls routing.
- Deploy: **AzureCLI@2** service principal — no Kudu basic auth

## What Matters Most Operationally

- webhook intake must stay strict — gate order matters, do not add status-based filters
- escalation must never silently fail — assignee gate + customer phrase gate + agent keyword detection
- pre-merge validation must include deterministic tests plus Foundry smoke eval (25 rows)
- the interactive architecture lives in repo HTML assets, not in the wiki renderer
- **Foundry has TWO endpoint surfaces with independent configs (agent vs application).** Direct probes must hit the same surface as production. PATCHing `/agents/seekapa` does NOT change the `/applications/seekapa/protocols/openai/responses` config. See Architecture → Foundry Endpoint Routing.

## Operational Knobs

| Setting | Where | Why it matters |
|---|---|---|
| `AZURE_AI_FOUNDRY_ROUTE_MODE` | Function App `func-cs-agents-dev` → Configuration → Application Settings | Set to `agent` to force traffic through the agent endpoint (controllable via `/agents/seekapa` PATCH/POST). Default `auto` sends history-bearing channels (Telegram) to the application endpoint, which is portal-managed-only. As of 2026-04-27, recommended value is `agent`. |

## Ownership Map

| Concern | Canonical Place |
|---|---|
| setup | [Getting Started](./Getting-Started) |
| runtime design and gate model | [Architecture](./Architecture) |
| deployment and release | [Deployment](./Deployment) |
| guardrails and routing model | [Compliance](./Compliance) |
| deeper repo docs | `docs/` in the repository |

## Key Files

| File | What It Is |
|---|---|
| `azure-function-crm/chatwoot_handler/` | webhook handler **package** (4 modules; see Architecture → Handler Package Structure). `__init__.py` holds `main()` and the 9-gate chain |
| `azure-function-crm/channel_router/__init__.py` | Foundry agent routing |
| `agent-prompts/seekapa-system-prompt-v107.3-yasha-style.md` | **content currently live in Foundry as `seekapa:111`** (since 2026-04-27 16:00, PR #175) |
| `agent-prompts/seekapa-system-prompt-v107.2-yasha-style.md` | content of `seekapa:110` (interim, deployed 14:55 same day, superseded by 111) |
| `agent-prompts/seekapa-system-prompt-v107-yasha-style.md` | original Yasha-style draft, not deployed (predecessor of v107.1/2/3) |
| `agent-prompts/seekapa-system-prompt-v105-compact.md` | content of `seekapa:109` (rollback target — preserved for emergencies) |
| `Seekapa_FAQ_KB_v2.txt` | KB v2 source (live, vector store `vs_yuCtQgmt2I9W0wTCMBnyP1hf`) |
| `scripts/foundry_eval_gate.py` | CI eval gate script |
| `tests/test_data/foundry_smoke_eval.jsonl` | 25-row multilingual eval dataset |
| `azure-pipelines.yml` | CI/CD pipeline |

## Interactive Assets

- [Interactive system architecture](../diagrams/system-arch-interactive.html)
- [Interactive function flow](../diagrams/yasha-function-io-flow.html)
