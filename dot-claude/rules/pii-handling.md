# PII Handling — general rule

Applies to every project and session. Companion to org data-protection policy and
the conversation-security rule.

## Two non-negotiables

1. **Mask PII at the model boundary.** No raw PII enters any LLM context — Claude,
   GPT batch/global, Foundry agents, or MCP tool payloads returned to a model.
   Mask by **reversible tokenization**, not redaction: replace the value with a
   stable vaulted token (`<TYPE_xxxxxx>`) and keep the token->value map outside any
   model call. The model reasons over tokens; it never sees the name/phone/email.

2. **Never hurt or remove production data.** Masking is performed on a derived,
   model-facing copy ONLY. Production sources — CRM (az-corp / vTiger / PandaCRM),
   PostgreSQL (qc_analyzer, panda_db), the call-analyzer API, KV, lake `bronze/` —
   are read-only from this work. Do not delete, mutate, truncate, overwrite, or
   strip PII from any production store. The original always stays intact; the
   bypass exists so the model is blind to PII, not so the data loses it.

## What counts as PII

Person names (customer + agent), phone numbers, emails, national IDs, and any
nominative identifier in free text (transcripts, CRM comments) or structured fields.
ACC / lead_id is a surrogate key, kept in clear unless org reclassifies it.

## Rehydration

PII is re-hydrated only in non-LLM output builders (xlsx/html), plain Python, no
model call. Selective: customer PII rehydrated where the deliverable needs it;
**agent identity stays pseudonymized even in output** (stable `agent_id` sha1[:6]).

## Reference implementation

`campaign-analysis/docs/2026-06-10-pii-tokenization-gateway.md` — the gateway
module, field inventory, detection tiers, vault, and wiring points. Reuse the
`pii-scrubber` skill (detection) and `score_views._pseudonym` (agent pseudonym).
