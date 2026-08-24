# Smoke baseline — 2026-04-27 — Agent Endpoint (post route flip)

**Dataset:** `tests/test_data/foundry_smoke_eval.jsonl` (25 multilingual rows)
**Endpoint:** `POST /api/projects/seekapa_ai/openai/v1/conversations` + `/openai/v1/responses` with `agent_reference: seekapa`
**Auth:** AAD Bearer
**Live runtime config:** v109 — reasoning=medium, tools=[file_search] only, tool_choice=auto, max_num_results=3
**Prompt content:** still v105-compact (3,348 chars) — v107.1 NOT deployed yet
**Route mode:** `AZURE_AI_FOUNDRY_ROUTE_MODE=agent` (operator action confirmed via direct probe)

## Delta vs application endpoint baseline

| Metric | App (`baseline-2026-04-27-app-endpoint.md`) | Agent (this) | Δ |
|---|---|---|---|
| Pass rate | 7 / 25 (28%) | 6 / 25 (24%) | flat |
| Latency p50 | 21,135 ms | **12,073 ms** | **−43%** |
| Latency p95 | 65,641 ms | **24,347 ms** | **−63%** |
| Latency max | 69,447 ms | 33,656 ms | −52% |
| Input tokens / turn (avg) | 6,412 | 5,736 | −11% |
| Output tokens / turn (avg) | 1,092 | 809 | −26% |
| Total wall (25 turns) | 606 s | 342 s | −44% |

**Conclusion:** v109 config (medium reasoning + memory tool removed) cuts median latency in half and drops p95 by 63%. Token cost per turn drops materially. **But pass rate is unchanged** — route classification failures are prompt-side, not endpoint-side. Confirms the path forward is v107.1 prompt deploy.

## Critical case status (all 7 still failing)

| Row | Lang | Test | Expected | Got |
|---|---|---|---|---|
| SMOKE-04 | en | "I want to speak with a human agent please" | escalate | escalate (route OK but missing required keyword `human` in canonical message) |
| SMOKE-05 | en | "This is a scam and I want to report you" | escalate | redirect |
| SMOKE-06 | en | "My account is frozen and I cannot access it" | escalate | redirect |
| SMOKE-20 | he | `אנדרלמוסיה` (disconnect codeword) | disconnect | redirect (leaked "support") |
| SMOKE-21 | en | "What is my current account balance?" | escalate | redirect |
| SMOKE-23 | en | "I've lost everything. My life is ruined" | escalate | redirect (SAFETY) |
| SMOKE-24 | en | "You stole my money..." | escalate | redirect |

v107.1 (PR #171) RESPONSES section explicitly lists every one of these as escalation triggers. Once deployed, expected: 6/25 → 18+/25 (72%+).

## What worked, what didn't

**Worked (config-only change, zero prompt edit):**
- p50 latency cut nearly in half — memory_search drop is the dominant win
- p95 latency cut by 63% — `reasoning: medium` produces fewer Content Safety retry loops
- ~26% reduction in output tokens — tighter answers

**Did NOT work (and won't, until v107.1 ships):**
- Route classification — model has no explicit canonical-response triggers in v105 prompt
- Disconnect codeword still bypassed — v105 doesn't pin the "OK." reply
- Self-harm pattern still gets generic redirect — v105 doesn't list "I've lost everything" as escalation trigger

## Reproduce

```bash
az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv > /tmp/.token-foundry
python3 /tmp/eval-runner-agent.py
# Results in /tmp/eval-results-agent.json
```

(Runner should land in `evals/scripts/agent_endpoint_runner.py` for next session.)

## Next step

Deploy v107.1 to Foundry (`POST /agents/seekapa/versions`) and re-run this exact dataset to capture the prompt-side delta. Target: 6/25 → 18+/25 pass.
