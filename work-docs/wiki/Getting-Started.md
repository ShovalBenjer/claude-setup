# Getting Started

![AI Department Logo](../../ai_department_logo.png =96x)

This page is the shortest path from clone to a working local validation of the CS Agents stack.

## Fast Path

1. Clone the repo.
2. Load required secrets into local settings.
3. Run the Azure Function app locally.
4. Validate `channel_router` first.
5. Validate the Chatwoot webhook flow second.

## Prerequisites

| Tool | Notes |
|---|---|
| Python 3.11 | Required for the function app |
| `uv` | Standard Python package workflow in this repo |
| Azure Functions Core Tools v4 | Local function runtime |
| Azure CLI | Deployment and key retrieval |
| Access to Azure AI Foundry project | For live end-to-end checks |
| Access to Chatwoot dev environment | For webhook validation |

## Clone And Install

```bash
git clone https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents
cd axia-seekapa-cs-agents
cd azure-function-crm
uv pip install --system -r requirements.txt
```

## Required Local Configuration

Create `azure-function-crm/local.settings.json` with the values needed for:

- Chatwoot API access
- Foundry project endpoint and API key
- Function-to-function auth
- Allowed inbox IDs

Minimum fields usually required:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_OPENAI_ENDPOINT": "<foundry-or-openai-endpoint>",
    "AZURE_OPENAI_API_KEY": "<secret>",
    "CHATWOOT_BASE_URL": "<secret>",
    "CHATWOOT_API_ACCESS_TOKEN": "<secret>",
    "CHATWOOT_ALLOWED_INBOX_IDS": "4",
    "FUNCTIONS_EXTENSION_VERSION": "~4"
  }
}
```

## Run Locally

```bash
cd azure-function-crm
func start
```

The default local endpoint is `http://localhost:7071`.

## Validate The Agent Path First

Use the normalized router before testing Chatwoot. It isolates agent behavior from webhook delivery issues.

```bash
curl -X POST "http://localhost:7071/api/channel-router?code=<FUNCTION_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel":"widget",
    "brand":"seekapa",
    "user_id":"demo-user",
    "message":{"message":"My account is locked. What should I do?"}
  }'
```

Expected result:

- HTTP `200`
- structured JSON response
- agent answer in the response body

## Validate The Chatwoot Path Second

Once the router works, validate the webhook contract. The `meta` field controls the assignee gate — omit it or set `assignee: null` to let the bot process:

```bash
curl -X POST "http://localhost:7071/api/chatwoot-webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "message_created",
    "id": 123,
    "message_type": 0,
    "private": false,
    "content": "I need help with my withdrawal",
    "conversation": {
      "id": 555,
      "status": "pending",
      "inbox_id": 4,
      "meta": {"assignee": null}
    },
    "inbox": {"id": 4},
    "sender": {"type": "contact", "id": 999, "name": "Test User", "email": "test@example.com"}
  }'
```

Expected result:

- webhook accepted
- message routed to Foundry with `[Customer: Test User <test@example.com>]` prefix
- response posted back to Chatwoot

To test the assignee gate (bot should stay silent):

```bash
# Set meta.assignee to a non-null user object
"meta": {"assignee": {"id": 1, "name": "Support Agent"}}
# Expected: {"ok": true, "skipped": true, "reason": "assigned"}
```

## Recommended Local Checks

```bash
# From repo root
python3 -m pytest tests/test_chatwoot_webhook.py --noconftest
python3 -m pytest tests/test_create_ticket.py --noconftest
python3 -m pytest tests/test_message_normalizer.py --noconftest
python3 -m pytest tests/test_foundry_eval_gate.py --noconftest
python3 -m py_compile scripts/foundry_eval_gate.py

# Full suite (excludes deepeval)
python3 -m pytest tests/ -k "not deepeval" -x -q --noconftest
```

## Where To Go Next

- [Architecture](./Architecture)
- [Deployment](./Deployment)
- [Compliance](./Compliance)
