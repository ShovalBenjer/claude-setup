# Compliance

![AI Department Logo](../../ai_department_logo.png =96x)

This page keeps the minimum set of guardrails operators and reviewers need to understand before changing the CS Agents system.

## Core Rules

| Control Area | Current Rule |
|---|---|
| Secrets | never commit keys, tokens, or local settings with secrets |
| Runtime safety | webhook must validate event type, message direction, sender type, inbox, privacy flag, and assignee |
| Escalation | explicit human requests and operational failure modes must not be silently dropped |
| CI | protected branches require build validation before merge |
| Evaluation | prompt and agent changes require Foundry evaluation, not just unit tests |
| Data minimization | pass only the context needed for routing and evaluation |

## Human Handoff Standard

The system must prefer a safe handoff over a silent failure.

Current escalation model (signal-driven, no turn counter):

- **Assignee gate**: when `conversation.meta.assignee` is non-null, a human agent has taken over. Bot goes silent. CW is responsible for routing — the bot does not pre-check the CW API or filter by conversation status.
- **Customer escalation phrase**: phrases like "talk to a human", "hablar con alguien", "agente humano" trigger an immediate handoff message and conversation reopen.
- **Agent response keywords**: if the Foundry agent's own reply contains escalation language, the conversation is toggled to open for human pickup.
- **Disconnect keyword**: the Hebrew word אנדרלמוסיה hard-stops the bot and toggles status without sending any message.

Escalation must succeed or the error must be logged — silent drops are not acceptable.

## Routing Model

Chatwoot controls what traffic reaches the webhook. The bot trusts CW routing.

- Do not add status-based skip gates (`if status in ("open", "resolved"): skip`). CW may send valid traffic in any status.
- New conversations arrive as `pending` in the API (or `open` in some inbox configurations). Both must be processed.
- The only bot-side routing decision is the assignee check: `meta.assignee != null` means a human owns it.

## AI Quality Standard

The main failure modes observed in evaluation:

- task completion
- task adherence
- groundedness
- relevance

The release gate emphasizes those categories before style-only concerns.
The active prompt is Seekapa v97 with DECISION POLICY, PRIMARY OPERATING RULES, and DEFAULT RESPONSE SHAPE.

## Evaluation Standard

| Layer | Requirement |
|---|---|
| deterministic tests | must run first |
| smoke eval | must run in CI on the 25-row frozen multilingual dataset |
| nightly eval | should cover broader multilingual and escalation scenarios |
| continuous eval | should be sampled and cost-capped |

Current approved evaluator deployments:

- `grok-4-1-fast-reasoning-2-eval`
- `DeepSeek-V3.2`

## Privacy And Security

- keep Foundry and Chatwoot credentials in secure secret storage
- use function keys or equivalent for internal function-to-function paths
- avoid leaking internal traces into customer-visible responses
- sender name and email are passed to the agent as a context prefix — not stored, not logged at info level

## Change Policy

If a change affects one of these areas, it is not a docs-only change:

- escalation behavior (gate order, phrases, assignee logic)
- webhook acceptance rules (inbox list, event type filter)
- evaluator deployments or token budgets
- branch validation behavior
- the active system prompt version

## Source Documents

- [Architecture](./Architecture)
- [Deployment](./Deployment)
