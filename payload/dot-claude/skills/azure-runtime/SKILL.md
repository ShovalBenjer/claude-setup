---
name: azure-runtime
description: Call Azure AI runtime from CLI — Azure OpenAI chat completions against deployed GPT models in brn-azai AND Azure AI Foundry agents (ORM-FLAGGING-AGENT, seekapa, AxiaCS) with thread/run streaming. Auth via az login, no API keys. Triggers on "/azure-runtime", "/foundry-runtime", "chat with gpt-5.5", "call my Foundry agent", "stream foundry run", brn-azai or services.ai.azure.com references. SKIP for authoring agents (agent-builder), evals (eval-runner), raw az ops, or OpenAI's platform.openai.com.
model: opus
allowed-tools: ["Bash", "Read", "Grep", "Glob"]
---

# Azure Runtime — call Azure AI from CLI

**Invocation:** `/azure-runtime` or any task that calls deployed Azure OpenAI models or Foundry agents.

## Auth — no keys, ever

`DefaultAzureCredential` reads your existing `az login` session. Verify before running anything:

```bash
az account show --query "{user:user.name, sub:name}" -o tsv
```

If empty → `az login`. Tenant must have access to `AZAI_group` / `brn-azai`.

## Two surfaces

### A. Azure OpenAI chat (deployed GPT models)

Same `openai` Python lib, but `AzureOpenAI` client class. For raw chat against `gpt-5.5`, `gpt-4.1`, etc.

**List your deployments first:**
```bash
az cognitiveservices account deployment list \
  --resource-group AZAI_group --name brn-azai \
  --query "[].{name:name, model:properties.model.name, version:properties.model.version}" -o table
```

**Quick chat (one-shot, AAD auth):**
```bash
uv run --quiet --with "openai>=1.50" --with "azure-identity>=1.21" python <<'PY'
import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default",
)
client = AzureOpenAI(
    azure_endpoint="https://brn-azai.openai.azure.com/",
    azure_ad_token_provider=token_provider,
    api_version="2025-04-01-preview",
)
r = client.chat.completions.create(
    model=os.environ.get("DEPLOYMENT", "gpt-5.5"),  # set DEPLOYMENT=<name> first
    messages=[{"role": "user", "content": "hello"}],
)
print(r.choices[0].message.content)
PY
```

**Streaming chat:** add `stream=True` and iterate `for chunk in r: print(chunk.choices[0].delta.content or "", end="", flush=True)`.

### B. Foundry agents (deployed)

For `ORM-FLAGGING-AGENT:7`, `seekapa`, `AxiaCS`, etc. Uses `azure-ai-projects` SDK against a project endpoint.

**Stream a run with full observability** (tool calls + reasoning + message deltas):
```bash
~/.claude/skills/azure-runtime/agent_run.py \
  "https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai" \
  "ORM-FLAGGING-AGENT" \
  "your prompt"
```

Stdout = assistant message (pipe-safe). Stderr = `[thread]`, `[step]`, `[tool_call: name]`, `[run] completed|failed`.

**List agents in a project:**
```bash
uv run --quiet --with "azure-ai-projects>=1.0" --with "azure-identity>=1.21" python <<'PY'
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
p = AIProjectClient(
    endpoint="https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai",
    credential=DefaultAzureCredential(),
)
for a in p.agents.list_agents():
    print(f"{a.id}\t{a.name}\t{a.model}")
PY
```

**Get an existing agent:**
```python
agent = p.agents.get_agent("ORM-FLAGGING-AGENT")  # latest version
# pinned version: "ORM-FLAGGING-AGENT:7"
```

## Project endpoints (house catalog)

| Project | Endpoint |
|---|---|
| seekapa_ai | `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai` |

## Boundaries

- **Authoring** (create new agent, update instructions, delete) → `agent-builder` skill
- **Eval pipelines** → `eval-runner` skill
- **OpenAI's platform.openai.com Assistants/AgentKit** → not reachable, no key, refuse
- **Costs** — chat completions and agent runs cost money. For write-tool agents (e.g., Meta Ads, payments), apply HITL: dry-run first, explicit operator OK before each write step

## Verification

```bash
az account show --query name -o tsv
az cognitiveservices account deployment list --resource-group AZAI_group --name brn-azai --query "[0].name" -o tsv
[ -x ~/.claude/skills/azure-runtime/agent_run.py ] && echo "runner ok"
```
