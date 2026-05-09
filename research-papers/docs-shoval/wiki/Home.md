# CS Agents

![AI Department Logo](../../ai_department_logo.png =120x)

Azure Functions plus Azure AI Foundry runtime for Chatwoot customer support automation for Seekapa.

## At a Glance

| Area | Current Standard |
|---|---|
| Product scope | Chatwoot webhook intake, Foundry agent routing, reply delivery, human escalation |
| Runtime | Azure Functions on `func-cs-agents-dev` |
| Active functions | `chatwoot_handler`, `channel_router`, `create_ticket` |
| Primary brand | `seekapa` |
| Source of truth | This wiki plus repo docs under `docs/` |
| Architecture asset | [Interactive architecture](./Architecture#interactive-architecture) |

## Start Here

| Read This | Why |
|---|---|
| [Getting Started](./Getting-Started) | Local setup, required secrets, smoke test flow |
| [Architecture](./Architecture) | Request lifecycle, boundaries, Mermaid diagrams, interactive map |
| [Deployment](./Deployment) | CI/CD, environments, rollout, rollback, eval gate |
| [Compliance](./Compliance) | Guardrails, escalation policy, privacy, operational controls |
| [Handover Notes](./Handover-Notes) | Fast operator handoff and ownership map |

## What This System Does

The CS Agents stack receives inbound customer messages from Chatwoot, validates that the event is in scope, routes the message into the Foundry-backed support agent, and posts the answer back into the same conversation.  
When a conversation should move to a human, the stack reopens the Chatwoot thread and creates the escalation path through `create_ticket`.

## Canonical Documentation Model

This wiki intentionally keeps only a small set of canonical pages:

1. `Home` for orientation
2. `Getting Started` for setup and local validation
3. `Architecture` for how the system works
4. `Deployment` for release and runtime operations
5. `Compliance` for rules and guardrails
6. `Handover Notes` for fast operational context

Anything else should live as supporting repo documentation, not as another top-level wiki branch.

## Runtime Snapshot

| Item | Value |
|---|---|
| Function app | `func-cs-agents-dev` |
| Base URL | `https://func-cs-agents-dev.azurewebsites.net` |
| Allowed inbox IDs | `4` |
| Chatwoot account | `1` |
| CI pipeline | `azure-pipelines.yml` |
| Primary smoke eval | Azure Foundry small-budget gate with `grok-4-1-fast-reasoning-2-eval` |
| Secondary audit eval | Azure Foundry audit subset with `DeepSeek-V3.2` |

## Design Principles

- Keep the wiki operational, not historical.
- Prefer one canonical page per concern.
- Keep interactive assets in the repo and link to them from the wiki.
- Put Mermaid in the wiki for static understanding.
- Use build validation and eval gates before merge, not only after merge.

## Operator Shortcuts

- [Repo README](../../README.md)
- [Architecture doc](../ARCHITECTURE.md)
- [Foundry eval CI plan](../FOUNDRY-EVAL-CI-PLAN.md)
- [Interactive function flow](../diagrams/yasha-function-io-flow.html)
- [Interactive system architecture](../diagrams/system-arch-interactive.html)
