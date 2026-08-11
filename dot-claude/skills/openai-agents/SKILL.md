---
name: openai-agents
description: Call OpenAI agents that live on platform.openai.com — Assistants API and AgentKit-published agents — from the CLI with full step observability. Stream runs with reasoning, tool calls, and citations rendered. List/inspect/diff assistants. Triggers on "/openai-agents", "run my OpenAI agent", "call my Assistant", "list my assistants", "stream agent_xxx", references to platform.openai.com/agents or /playground/assistants. SKIP when working with Anthropic Claude SDK (use claude-api), Azure Foundry agents (use eval-runner / az SDK), or ChatGPT consumer "My GPTs" (no API access — refuse with explanation).
model: opus
---

# OpenAI Agents — Request Doc

**Invocation:** `/openai-agents` or any task that calls Assistants/AgentKit agents on platform.openai.com.

## Surface map (which agents are reachable)

| Where built | URL | API? | Use which |
|---|---|---|---|
| Assistants | platform.openai.com/playground/assistants | ✅ | `client.beta.threads.runs.*` (Assistants API, asst_*) |
| AgentKit / Agent Builder | platform.openai.com/agents | ✅ after publish | `client.responses.create(...)` (Responses API, agent_*) |
| ChatGPT "My GPTs" | chatgpt.com | ❌ | refuse + explain |
| ChatGPT Agent (browse mode) | chatgpt.com | ❌ | refuse + explain |

If the user names a "GPT" or "ChatGPT agent" without an `asst_` / `agent_` id, ask which surface before assuming.

## Auth (never pass keys on CLI)

```bash
# Pull from Shoval KV at session start (matches house pattern)
export OPENAI_API_KEY=$(az keyvault secret show --vault-name Shoval --name openai-api-key --query value -o tsv)
# verify
[ -n "$OPENAI_API_KEY" ] && echo "ok" || echo "missing"
```

If the secret doesn't exist yet:
```bash
az keyvault secret set --vault-name Shoval --name openai-api-key --value "<paste>"
```
Never echo `OPENAI_API_KEY` value. Never write it to files. Never commit.

## Tools available globally

- `openai` CLI — installed via `uv tool install openai`, on PATH
- Python SDK — use `uv run --with openai python -c "..."` for ad-hoc, no global pollution
- Helper script: `~/.claude/skills/openai-agents/run.py` (PEP 723 deps, auto-resolves)

## Common operations

### List assistants
```bash
uv run --with openai python -c "
from openai import OpenAI
c = OpenAI()
for a in c.beta.assistants.list(limit=50).data:
    print(f'{a.id}\t{a.model}\t{a.name or \"\"}')"
```

### Run an Assistant (one-shot, stream with observability)
```bash
~/.claude/skills/openai-agents/run.py asst_xxx "your prompt here"
```
Streams `thread.run.step.*` events; prints reasoning to stderr, tool calls as bracketed cards, final text to stdout. Stdout is pipe-safe (only the assistant text).

### Run an AgentKit agent (Responses API)
```bash
uv run --with openai python -c "
from openai import OpenAI
c = OpenAI()
r = c.responses.create(agent={'id': 'agent_xxx'}, input='your prompt', stream=False)
print(r.output_text)"
```
Field name (`agent`, `agent_id`) varies by SDK minor version — check `c.responses.create.__doc__` if it errors.

### Compare two agents on the same prompt (eval-shape)
```bash
~/.claude/skills/openai-agents/run.py asst_A "prompt" > /tmp/a.txt &
~/.claude/skills/openai-agents/run.py asst_B "prompt" > /tmp/b.txt &
wait
diff -y /tmp/a.txt /tmp/b.txt
```

## When the user wants to "run a preview" of a ChatGPT agent

Their preview button is in the OpenAI builder UI — Claude can't trigger it. Either:
1. They publish/deploy the agent so it has an `agent_xxx` id, then we call via Responses API
2. We simulate the run locally as a few-shot exemplar (no network)

Always ask which they want.

## Boundaries (refuse / redirect)

- **Custom GPT on chatgpt.com** — no API. Explain the surface map; if they want programmatic access, recommend rebuilding in AgentKit or Assistants.
- **Costs / production writes** — for any agent that calls write-tools (e.g., Meta Ads, payments), apply HITL: dry-run first, then explicit operator OK before each write step.
- **Token in transcripts** — never paste `OPENAI_API_KEY` into chat, files, or KV value display. Use the `az keyvault secret show ... -o tsv` pull pattern only.

## Verification (after install)

```bash
openai --version              # → openai 2.33.0+
uv run --with openai python -c "import openai; print(openai.__version__)"
[ -n "$OPENAI_API_KEY" ] && uv run --with openai python -c "
from openai import OpenAI; print(len(OpenAI().beta.assistants.list(limit=1).data), 'assistant(s) reachable')"
```
