# Knowledge Base

Index of every document the cs-agent draws on. The bot's grounding lives in three layers — this page is the map.

## Layer 1 — Foundry vector store (live, customer-facing)

The bot's `file_search` tool queries this store on every "pure FAQ" turn (case 12).

| Source file | Vector store ID | Status |
|---|---|---|
| [`axia-seekapa-cs-agents/Seekapa_FAQ_KB.txt`](../../axia-seekapa-cs-agents/Seekapa_FAQ_KB.txt) | `vs_BhDnWqMdIsxjgv1f0sQOuwX6` | Live (since v108 deploy 2026-04-29). Re-uploaded manually when content changes — there is no auto-sync. |
| `Seekapa_FAQ_KB_v2.txt` (in `axia-seekapa-cs-agents-devops` root) | `vs_yuCtQgmt2I9W0wTCMBnyP1hf` | Staged for v107.3 baseline; not currently the primary store. See Conversation-Design changelog v1.2 for history. |

**To update the FAQ KB:** edit `Seekapa_FAQ_KB.txt`, then re-upload to the Foundry vector store via the portal (`https://ai.azure.com/.../seekapa_ai/data/vectorstores`). The agent will see the new content on the next request without a redeploy.

## Layer 2 — KB ANCHOR FACTS in the system prompt

Inlined facts the bot should answer **without** calling `file_search`. These are facts that change rarely and matter constantly (withdrawal SLA, leverage cap, regulator name, etc.). Source: [agent-prompts/seekapa-system-prompt-v109-multilingual.md § KB ANCHOR FACTS](../../agent-prompts/seekapa-system-prompt-v109-multilingual.md).

Why anchor facts and not just KB? Two reasons: (a) latency — no tool call needed for high-traffic answers; (b) reliability — the FAQ KB sometimes returns no relevant chunk, and we'd rather answer correctly than redirect.

The current anchor list covers withdrawal/deposit timing, leverage cap, inactivity fees, complaint SLA, callback SLA, regulator info, Arabic equivalents. **Jurisdiction info is NOT yet anchored** — see the [Markets and Jurisdictions](./Markets-and-Jurisdictions.md) page for the gap analysis from Yasha's 2026-05-04 production test.

## Layer 3 — Wiki pages (developer-facing only — bot does NOT read these)

This wiki is for engineers, ops, and compliance. The bot has no access to it. If a wiki page contains information the bot needs at customer-reply time, that information must also exist in Layer 1 (vector store) or Layer 2 (anchor facts).

| Page | Purpose |
|---|---|
| [Home](./Home.md) | Orientation, runtime snapshot, operator shortcuts |
| [Architecture](./Architecture.md) | Request lifecycle, boundaries, diagrams |
| [FAQ](./FAQ.md) | Customer-facing FAQ content (markdown mirror of `Seekapa_FAQ_KB_v2.txt`) for wiki readers |
| [Conversation Design](./Conversation-Design.md) | Both layers (sanitizers + prompt) and their dual-enforcement contract; full v107–v109 changelog |
| [Markets and Jurisdictions](./Markets-and-Jurisdictions.md) | DRAFT — supported / excluded markets. Awaits compliance review before flowing into Layer 1. |
| [Compliance](./Compliance.md) | Guardrails, escalation policy, regulator info |
| [Deployment](./Deployment.md) | CI/CD, environments, rollback, eval gate |
| [Getting Started](./Getting-Started.md) | Local setup, secrets, smoke tests |
| [Handover Notes](./Handover-Notes.md) | Operator handoff |

## How content gets from a wiki page into the bot's knowledge

1. **Compliance / SME approves the wiki content** (this is the gate that's missing for `Markets-and-Jurisdictions.md` right now).
2. **A maintainer copies relevant facts** into either:
   - `axia-seekapa-cs-agents/Seekapa_FAQ_KB.txt` (for full-paragraph FAQ entries the bot retrieves on demand), OR
   - The KB ANCHOR FACTS section of `seekapa-system-prompt-v109-multilingual.md` (for short, always-applied facts).
3. **For Layer 1**: re-upload the .txt to the Foundry vector store via portal.
4. **For Layer 2**: re-deploy the prompt via `scripts/deploy_seekapa_prompt.py` (POST `/agents/seekapa/versions` on api-version `2025-11-15-preview`).
5. **Verify** with `python evals/scripts/v109_runner.py --suite v109_only` against the live agent.

## Gaps surfaced by production tests (audit log)

| Date | Source | Gap | Status |
|---|---|---|---|
| 2026-05-04 | Yasha CW conv 1366 | Bot hallucinated Jamaica country name; treated Dubai as separate from UAE; hedged jurisdiction list with "and some other regions" | DRAFT doc at [Markets and Jurisdictions](./Markets-and-Jurisdictions.md); awaits compliance signoff before going to Layer 1 |
| 2026-05-04 | Yasha CW conv 1366 | Bot replies too verbose / formal vs Yasha .txt style | Addressed in v109.5 (canonical-reply refinement); deploys via post-merge prompt swap |
