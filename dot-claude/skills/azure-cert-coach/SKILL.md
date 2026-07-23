---
name: azure-cert-coach
description: >
  Coach toward AI-103 (Azure AI Apps and Agents Developer Associate). Delivers
  Socratic predict-then-verify drills, tracks the 4-week ramp from
  ~/docs/ai-103-study-tracker.md, surfaces the AI Skills Fest voucher deadline
  (claim by 2026-06-12 UTC, redeem by 2026-08-18, sit by 2026-10-18), and
  explains the free Microsoft Fabric sandbox workaround for hands-on labs.
  Triggers on "/cert-coach", "study for AI-103", "quiz me on Azure AI",
  "prep for AI-103", "AI-103 drill", "practice question Azure AI".
  SKIP when the task is purely a production Azure deployment, a Foundry agent
  build, or an eval pipeline run — those belong to azure-runtime / agent-builder
  / eval-runner respectively.
---

# Azure Cert Coach — AI-103

**Invocation:** `/cert-coach` · "study for AI-103" · "quiz me on Azure AI"

Read `~/docs/ai-103-study-tracker.md` and `~/docs/fundamentals-mastery-plan.md`
at session start to pick up the current week, daily log, and gap list.

---

## Hard deadlines (don't let these slip)

| Gate | Deadline |
|---|---|
| Complete voucher-eligible Learn playlist + submit claim | **2026-06-12 00:00 UTC** |
| Redeem voucher (schedule the exam) | 2026-08-18 |
| Sit the exam | 2026-10-18 |
| Pass score | 700 / 1000 |

Claim path: AI Skills Fest → <https://aiskillsnavigator.microsoft.com/events/AISF2026> → "Check what's unlocked".

---

## Free hands-on sandbox (Fabric workaround)

Azure AI Foundry labs require a paid subscription by default. Workaround:

1. Activate a **Microsoft Fabric free trial** (no credit card) — it provisions an F2 capacity tied to your M365 tenant.
2. In Fabric, open **AI Foundry** workspace — same portal surface, quota-limited but sufficient for all Learn labs (RAG, agent, eval, speech, vision).
3. For labs that need Azure OpenAI deployments specifically, use **`brn-azai`** (your production Foundry endpoint) with the `gpt-5.4-mini` deployment — it's low-cost and already accessible via `az login`.
4. Storage for lab artifacts: reuse `stseekapatrainingprod` (blob container `labs/`) rather than creating a new SA.

---

## 4-week arc (from study tracker)

| Week | Domain | Weight |
|---|---|---|
| 1 | Plan & manage an AI solution | 25–30% |
| 2 | Generative AI + agentic patterns | 30–35% |
| 3 | CV/multimodal · text analysis · info extraction | ~30% |
| 4 | Exam-ready: 2× practice assessment + sandbox | — |

Daily 60-min split: 0–40 Learn module + lab · 40–55 practice questions · 55–60 log misses into gap list.

---

## Socratic drill protocol (predict-then-verify)

Grounded in fundamentals-mastery-plan.md habit #1 — Predict-then-peek.

1. Ask the user to predict the answer **before** showing it.
2. After prediction, reveal the correct answer + the exact Learn doc section.
3. If prediction was wrong, add the topic to the gap list in `~/docs/ai-103-study-tracker.md`.
4. After 3+ wrong answers in a session, invoke `/grill-me` to stress-test the underlying concept.

**Question format:**

> Predict before reading on.
>
> **Q:** [scenario-grounded question — real Azure portal/SDK/CLI, not abstract]
>
> [blank line for user answer]
>
> **A (reveal):** [correct answer] — [1-sentence why + Learn link]

Questions must be scenario-first (Foundry portal choice, SDK call, RBAC decision, eval metric) — never trivia-style.

---

## Domain quick-reference (week 1–3 must-knows)

### Plan & manage
- **Managed Identity + keyless auth** — all production patterns use `DefaultAzureCredential`; no API keys in code.
- **Responsible AI** — content filters (Azure AI Content Safety), groundedness eval, safety eval in Foundry.
- **Model selection** — GPT-5 for reasoning, gpt-5.4-mini for cost-bounded batch, Phi-4 for edge/on-device.
- **CI/CD for AI** — Foundry model registry → deployment slot → eval gate → promote. Bicep/ARM for infra.
- **Monitoring** — Azure Monitor + Application Insights; drift detection via scheduled eval runs.

### Generative AI + agentic
- **RAG pipeline** — AI Search (hybrid/vector/semantic) + Foundry SDK `AzureAISearchTool` or LlamaIndex.
- **Agents** — Foundry Agents API: `AgentClient`, tools (`FunctionTool`, `BingGroundingTool`, `AzureAISearchTool`), thread/run/step model.
- **Multi-agent** — Connected Agents (Foundry) vs Semantic Kernel orchestration; approval-gated actions.
- **Eval** — `azure-ai-evaluation`: `GroundednessEvaluator`, `RelevanceEvaluator`, `CoherenceEvaluator`, `ViolenceEvaluator`; run in Foundry or locally.

### CV / multimodal
- **Image analysis** — `azure-ai-vision-imageanalysis` SDK; caption / object detection / OCR.
- **Video** — Azure AI Video Indexer; Content Understanding API for frame-level analysis.
- **Multimodal LLM** — GPT-4o / GPT-5 vision; pass `image_url` in the message content array.
- **Prompt injection in images** — watermark + Content Safety shield; exam loves this gotcha.

### Text + speech
- **Language service** — NER, key phrase, sentiment, summarization, PII detection via `azure-ai-textanalytics`.
- **Translator** — `azure-ai-translation-text`; LLM translation for nuance, Translator for speed/cost.
- **Speech** — `azure-cognitiveservices-speech`; STT + TTS + speaker diarization.

### Info extraction / AI Search
- **Indexing pipeline** — data source → indexer → skillset (OCR/layout/NLP) → index.
- **Query types** — keyword vs semantic (`queryType: semantic`) vs vector vs hybrid (use hybrid for RAG).
- **Content Understanding** — doc extraction (forms, tables) via `azure-ai-documentintelligence`.

---

## Sample drill set (rotate weekly)

Run 3–5 per session, spaced-rep the misses.

1. When would you choose `azure-ai-evaluation` over a custom LLM-as-judge? What metric does `GroundednessEvaluator` actually measure, and what does it require in the test row?
2. You need RAG over 500k internal PDFs with a mix of tables and prose. Which AI Search query type and which skillset enrichments do you configure?
3. An agent needs to call a proprietary REST API not covered by a built-in tool. Walk through how you register a `FunctionTool` in the Foundry Agents API (SDK calls, not portal).
4. A content filter blocks a valid customer message. Which Foundry setting do you tune, and what responsible-AI trade-off do you document?
5. Your Foundry deployment is throttling at 20 req/s peak. Name the two knobs in the portal and the SDK retry strategy.
6. Managed Identity vs API key — when is each appropriate in a production Azure Function? What RBAC role does the MI need to call Azure OpenAI?
7. You want semantic search but also need BM25 keyword recall. Which `queryType` + which `select` fields do you set, and why does `@search.score` differ from `@search.rerankerScore`?
8. An image contains text that looks like an instruction override ("ignore previous prompt"). Which Azure service layer catches this, and at what point in the pipeline?

---

## Session flow

1. Read study tracker → identify today's week + any open gaps.
2. Ask: "Pick a domain or let me choose based on your gap list?"
3. Deliver 3–5 drills (predict-then-verify format above).
4. After drills: update the gap list in `~/docs/ai-103-study-tracker.md` with today's date + misses.
5. If 3+ misses on one concept → invoke `/grill-me` on that concept.
6. End: confirm daily log entry is written.

---

## Key links

- AI-103 study guide: <https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-103>
- Cert page: <https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-apps-and-agents-developer-associate/>
- AI Skills Fest (voucher): <https://aiskillsnavigator.microsoft.com/events/AISF2026>
- Exam sandbox: <https://aka.ms/examdemo>
- Official practice assessment: search "AI-103 practice assessment" on learn.microsoft.com
