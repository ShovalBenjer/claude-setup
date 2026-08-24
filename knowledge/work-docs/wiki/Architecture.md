# Architecture

![AI Department Logo](../../ai_department_logo.png =96x)

This page is the static architecture source of truth for the CS Agents system.
The interactive HTML remains in the repo and is linked below because Azure DevOps wiki doesn't support JavaScript or iframes.

## System Overview

::: mermaid
graph LR;
    TG[Customer channel] --> CW[Chatwoot Inbox 4]
    CW --> WH[chatwoot_handler]
    WH --> CR[channel_router]
    CR --> FD[Azure AI Foundry project]
    FD --> CR
    CR --> WH
    WH --> API[Chatwoot reply API]
    WH -->|Escalation| ESC[toggle status → open]
:::

## Request Lifecycle

::: mermaid
sequenceDiagram
    participant U as Customer
    participant C as Chatwoot
    participant W as chatwoot_handler
    participant R as channel_router
    participant F as Foundry Agent

    U->>C: Send support message
    C->>W: Webhook (message_created)
    W->>W: Gate 1 — event type (message_created only)
    W->>W: Gate 2 — message direction (incoming only)
    W->>W: Gate 3 — private note (skip)
    W->>W: Gate 4 — inbox allowlist
    W->>W: Gate 5 — assignee (human assigned → silent)
    W->>W: Gate 6 — empty content
    W->>W: Gate 7 — sender type (contact only)
    W->>W: Gate 8 — disconnect keyword (Hebrew hard stop)
    W->>W: Gate 9 — customer escalation phrase → handoff
    W->>R: Normalize + prepend sender context
    R->>F: Create or continue conversation
    F-->>R: Agent response
    R-->>W: Normalized answer
    W->>C: Post reply
    W->>W: Check agent response for escalation keywords
    W->>C: Toggle status open if escalation detected
:::

## Gate Model

CW controls which traffic reaches the webhook. The bot does not second-guess CW routing.
Gates are processed in order. The first matching gate short-circuits the request.

| Gate | Signal | Action |
|---|---|---|
| Event type | event != message_created | skip |
| Message direction | message_type != 0 (incoming) | skip |
| Private note | private: true | skip |
| Inbox allowlist | `int(inbox.id)` not in `CHATWOOT_ALLOWED_INBOX_IDS` set | skip (defensive int cast — Chatwoot may send id as str or int) |
| Assignee | conversation.meta.assignee != null | skip — human owns it |
| Empty content | content blank | skip (attachment gets a text prompt) |
| Sender type | not contact/incoming | skip |
| Disconnect keyword | Hebrew אנדרלמוסיה | stop, toggle status open |
| Customer escalation phrase | "talk to a human" etc. | send handoff message, toggle open |

After all gates: call Foundry agent, post reply, check agent response for escalation keywords.

## Sender Context

When Chatwoot provides sender name and email, the handler prepends a context line:

```
[Customer: Name <email@example.com>]
<customer message>
```

The Seekapa v97 prompt reads this prefix and uses the name directly, skipping the collection step.

## Core Components

| Component | Responsibility | Key Risk |
|---|---|---|
| `chatwoot_handler` (package) | Webhook intake, gate processing, sender context, reply delivery, escalation | false positives on customer phrases, gate ordering |
| `channel_router` | Brand-aware normalization and Foundry request orchestration | malformed payloads, conversation continuity |
| `create_ticket` | Human escalation artifact creation | missed handoff, wrong ticket metadata |
| Foundry agent (seekapa) | Final answer generation. Live: `seekapa:111` (v107.3, deployed 2026-04-27 — eval 64% pass rate, p50 7.9s). Vector store: `vs_yuCtQgmt2I9W0wTCMBnyP1hf` (Seekapa_FAQ_KB_v2). Rollback to `seekapa:109` available. | task completion, task adherence, groundedness |
| CI + eval gate | Catch regressions before merge | evaluator drift, under-sampled smoke sets |

### Handler Package Structure

`chatwoot_handler` is a Python package, not a single file. Module layout:

| Module | LOC | Responsibility |
|---|---:|---|
| `chatwoot_handler/__init__.py` | ~480 | `main()` entry, env-derived config (`ALLOWED_INBOX_IDS`, `DEFAULT_BRAND`), test-injectable overrides, in-memory state (`_response_ids`, `_seen_message_ids`), `_call_agent_with_retry`, `_get_bot_user_id`, `_has_bot_replied`, `_build_stateless_message_history` |
| `chatwoot_handler/_constants.py` | ~85 | Static keyword lists (`ESCALATION_KEYWORDS`, `CONTENT_SAFETY_REFUSALS`, `CUSTOMER_ESCALATION_PHRASES`, `IDENTITY_COLLECTION_PATTERNS`), regex (`_INVENTED_MONEY`, `_BANNED_ACTION_VERBS`, `_GREETING_VARIANTS_TO_NORMALIZE`, `_AI_ISMS`, `_HEDGING`, `_IDENTITY_SOLICITATION_ANY_TURN`), timing budgets |
| `chatwoot_handler/_gates.py` | ~86 | Pure gate functions: `_is_assigned`, `_is_content_safety_refusal`, `_is_disconnect`, `_is_customer_escalation`, `_should_escalate`, `_build_context_prefix`, `_validate_signature` (HMAC-SHA256) |
| `chatwoot_handler/_sanitize.py` | ~95 | Deterministic post-processors. `_sanitize_response` chains: `_normalize_greeting` → `_strip_identity_solicitation_any_turn` → `_strip_ai_isms` → dash hygiene → invented-money guard → banned-verb redirect → ¶ cap. Also exports `_sanitize_first_turn_identity_request` (called separately at handler level with turn context). |

All test-imported symbols are re-exported via `__all__` in `__init__.py`. Tests do `from chatwoot_handler import _is_disconnect` — no internal-module imports needed.

Total: ~745 LOC across 4 files (down from 954 LOC in a single file as of PR #161).

### Foundry Endpoint Routing — IMPORTANT

The Foundry project exposes the same agent via TWO independent surfaces, and **they use different runtime configs**. Discovered 2026-04-27 via direct probe.

| Surface | URL pattern | Config source | Allows per-request overrides |
|---|---|---|---|
| **Agent endpoint** | `/openai/v1/conversations` + body `{"agent_reference": {"name": "seekapa"}}` | Agent registry (`/agents/seekapa` PATCH/POST) — versioned, currently `seekapa:109` | Yes for some fields; reasoning/tools controlled by registry |
| **Application endpoint** | `/applications/seekapa/protocols/openai/responses` | Application config (portal-only, NO REST API surface as of 2026-04-27) | NO — `reasoning`/`tools` in body return HTTP 400 "Not allowed when agent is specified" |

`channel_router._should_use_application_endpoint` decides which one based on env var `AZURE_AI_FOUNDRY_ROUTE_MODE`:

| Value | Behavior |
|---|---|
| `application` | Always use application endpoint |
| `agent` | Always use agent endpoint |
| `auto` (default) | Application endpoint if `message_history` is provided, otherwise agent endpoint |

**Operational gotcha:** PATCHing the agent registry has NO effect on traffic that goes through the application endpoint. Verify via direct probe (`/applications/<name>/protocols/openai/responses`) before claiming a config change has taken effect in production.

**Recommended setting for production:** `AZURE_AI_FOUNDRY_ROUTE_MODE=agent` so all traffic uses the controllable agent registry. Set on the Function App via Portal Configuration (not CLI per `production-safety.md`).

## Current Boundaries

### In Scope

- inbound customer support messages via Chatwoot
- Chatwoot webhook processing
- Foundry-based response generation
- automated reply delivery
- human escalation workflow (assignee gate + keyword detection)
- CI and evaluation gates (25-row multilingual smoke dataset)

### Out Of Scope

- custom JavaScript inside the wiki
- CRM or account-data lookups (bot has no CRM access)
- duplicating every repo doc into wiki form

## Interactive Architecture

Use these repo assets when you need deeper walkthroughs:

- [Interactive system architecture](../diagrams/system-arch-interactive.html)
- [Interactive function I/O flow](../diagrams/yasha-function-io-flow.html)

## Runtime Topology

::: mermaid
graph TD;
    DEV[Azure DevOps] --> CI[azure-pipelines.yml]
    CI --> FUNC[func-cs-agents-dev]
    FUNC --> CH[chatwoot_handler]
    FUNC --> RO[channel_router]
    FUNC --> TK[create_ticket]
    RO --> FOUND[seekapa_ai Foundry project]
    CH --> CHAT[Chatwoot]
    TK --> CHAT
    CI --> EVAL[Foundry smoke eval gate]
:::

## Evaluation Architecture

The production-quality path is:

1. deterministic tests first
2. small-budget Foundry smoke evaluation in CI (25-row multilingual dataset)
3. broader nightly Foundry evaluation
4. optional continuous evaluation on sampled traffic

Current evaluator deployments:

- primary: `grok-4-1-fast-reasoning-2-eval`
- audit subset: `DeepSeek-V3.2`

## Why The Wiki Uses Mermaid Instead Of The HTML App

Azure DevOps wiki supports Markdown, Mermaid, images, and limited HTML, but not JavaScript or iframes.
That means the wiki should hold the static explainers, while the repo keeps the interactive architecture asset.
