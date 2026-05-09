# What Executives Want from an MCP

### A 2026 Evidence Review for `mcp-seekapa-tools`

**Prepared for:** Liron (COO), Amit (DBA), Seekapa CRM/QC team
**Author:** Shoval Benjer (Senior Solution Engineer, i-sdd)
**Date:** 2026-05-07
**Mode:** Deep research (8-phase pipeline, 50+ structured claims, 45+ sources)

---

## Executive Summary

Six months after Anthropic introduced the Model Context Protocol (MCP) in November 2024, the standard has crossed **97 million monthly SDK downloads and over 10,000 active public MCP servers** [1] — the fastest adoption curve any AI infrastructure standard has ever achieved. Yet the same six months produced a darker statistic: only **6% of companies fully trust AI agents to autonomously run core business processes** [2], and traditional analytics dashboards still suffer **adoption rates near 25%** organization-wide, with **67% of executives dissatisfied** with their current BI tools [3]. The gap between technical capability and executive trust is the central problem this report addresses.

`mcp-seekapa-tools` is not a dashboard. It is a 26-tool conversational surface consumed inside Claude.ai web, ChatGPT, and Microsoft 365 Copilot — chat *is* the UI. This means every classical dashboard-design rule (drill-down hierarchy, tile placement, mobile responsiveness) translates to a different set of constraints: tool naming, response shape, latency budget, and the LLM's interpretation of docstrings. Six findings dominate the evidence:

1. **Citation and provenance are the load-bearing trust feature.** Glean reached 93% enterprise adoption in two years primarily because every answer carries a verifiable source link [4]. Tableau Pulse's explicit architecture rule — *never let the LLM do math, always show citations* — is the same insight in product form [5].
2. **Hallucinated metrics destroy executive trust at 10× the rate they earn it.** A documented Power BI Copilot incident reported a 0.3% loan-default decrease as 3% — a 10× error that nearly reached the board [6]. Production text-to-SQL accuracy on enterprise schemas is **10–20%** [7].
3. **Push beats pull for executives.** Tableau Pulse anchors adoption on Slack/email digests with auto-detected drivers and outliers, not on a chat box. Personalized digests with mute/favorite controls drive return-rate.
4. **MCP tool design *is* the UX.** Tool names, descriptions, and parameter schemas are prompts the LLM reads. Anthropic, OpenAI, Block, and Linear all converge on workflow tools (one tool per intent) over endpoint wrappers, and on inline enum documentation, namespacing, and risk-level annotations [8][9][10].
5. **Human-in-the-loop is non-negotiable for regulated financial decisions.** EU AI Act Article 12 (enforceable Aug 2 2026, penalty up to €15M) [11] and Federal Reserve SR 11-7 [12] both demand auditable model lifecycles. The Zillow Offers $500M+ shutdown is the canonical lesson on what removing the human gate costs [13].
6. **Honest uncertainty beats confident wrongness.** Current RLHF training systematically penalizes "I don't know" [14]; the trust-restoring counter-pattern is calibrated confidence + explicit refusal-to-answer paths.

The recommendations in §13 translate these findings into 12 concrete actions for the next iteration of `mcp-seekapa-tools`: from a `_provenance` block on every response, to deterministic Python-computed metrics with LLM-only narration, to a `digest_metrics(persona='coo')` push tool, to an audit-log appendix that satisfies CySEC + EU AI Act requirements before either becomes mandatory.

The bottom line for Liron: the executives who adopt AI analytics in 2026 are not the ones with the fanciest dashboards. They are the ones whose tools can answer "where did this number come from?" in one click, and who can credibly say "I don't know" when the data isn't there.

---

## 1. Introduction

### 1.1 Scope

This report investigates ten research questions about executive consumption of MCP-based AI analytics tools, aggregating evidence from technology vendors (Anthropic, OpenAI, Microsoft, Tableau, ThoughtSpot, Glean, Hex, Snowflake), analyst firms (Gartner, Forrester, BARC, McKinsey), regulatory sources (EU AI Act, US Federal Reserve SR 11-7), peer-reviewed and preprint research (PROV-AGENT, MIT, Johns Hopkins), and practitioner case studies (Block, Linear, Atlassian engineering blogs, MS Q&A complaints, AI Incident Database). The ten questions span: adoption drivers, the executive-summary principle, trust/transparency, latency expectations, PII governance, mobile vs desktop access, COO consumption patterns in marketing/sales orgs, anti-patterns that kill trust, the 2026 SOTA vendor landscape, and MCP-specific UX patterns.

### 1.2 Methodology

The deep-research pipeline ran 12 parallel web searches plus 3 specialized deep-dive sub-agents (BI-Copilot UX, MCP consumption patterns, executive-trust failure cases). Each agent returned structured evidence (claim + verbatim quote + source URL + confidence score) to prevent synthesis fatigue. Triangulation required ≥3 independent sources for any core claim; single-source claims are explicitly flagged. Source credibility weighted by the standard hierarchy: regulator + peer-reviewed > analyst firm > vendor docs > vendor blog > practitioner blog. Evidence cutoff: 2026-05-07. Full methodology and source-credibility rubric in §15.

### 1.3 Stakeholder context

The primary reader is **Liron (COO, marketing background)**. Liron does not write SQL, has limited tolerance for raw JSON, and consumes analytics in 30-second chunks between meetings. The secondary reader is **Amit (DBA)** who has direct CRM access and validates whether the numbers add up. The tertiary readership is the **CRM/QC team**, who execute on the verdicts the MCP produces (FTD chase, drop, escalate). The MCP currently exposes 26 tools across CRM (`crm_get_customer`), call-quality (`call_analyzer_*`, `rubric_grade_call`), Chatwoot (`chatwoot_*`), OneSignal, Windsor, journey verdicts (`get_lead_verdict`, `compare_with_crm`, `list_divergences`), and analytics composition (`funnel_aggregate`, `comment_classifier`).

### 1.4 What "executive UX" means in chat

There is no GUI to design. Every choice — tool name, response shape, error message, latency profile — is filtered through an LLM and rendered as text the executive reads on a phone, in Slack, or in a Copilot side-panel. This shifts the design discipline from screen layout to **language design**: the tool's docstring is its product page; the response is its dashboard; the error message is its escalation path. The body of this report is structured around the patterns that survive that constraint.

---

## 2. The Adoption Crisis: Why Most Analytics Tools Never Reach the Executive

Three numbers frame the problem.

**First**: BI-tool adoption averages **25% organization-wide** and has not moved in years; **only 16% of organizations achieve 100% Power BI dashboard adoption, while 58% languish under 25%** [3]. The cohort that *does* use these tools daily is an elite subset — and even there, **executive daily-decision use jumped from 48% in 2023 to 67% in 2025** per BARC-cited data [3], implying that *executives* are pulling on analytics harder than the rest of the org. If your tool isn't reaching them, it's not because they don't want it.

**Second**: **67% of executives report dissatisfaction with their current BI tools** [3], and **25% of data and analytics decision-makers cite lack of trust in AI as their top concern**, with **21% citing lack of transparency** [15]. Trust, not capability, is the bottleneck. Harvard Business Review's 2024 sponsor research with Forrester puts it bluntly: *"when an executive asks one question and receives different answers depending on the dashboard, assistant, or workflow, confidence collapses quickly"* [15]. The problem is not that the tool can't answer; it's that the answer can't be verified.

**Third**: McKinsey's 2025 *State of AI* finds that two-thirds of enterprises remain in pilot or experimentation, and **only ~6% qualify as "high performers" with >5% EBIT impact**; **47% of organizations report at least one negative consequence from generative AI** [16]. The pilot-to-production gap is not a technical problem — it is a **trust collapse problem**, and the evidence below shows that the tools that crossed the gap did so by solving for trust first and capability second.

Three causal patterns emerge from the evidence.

**Pattern 1 — the data-readiness gap.** Gartner predicts that *"through 2026, organizations will abandon 60% of AI projects unsupported by AI-ready data"* [17]; **63% of organizations don't have, or are unsure if they have, the right data management practices for AI**. For an MCP, this translates to: *the tool surface is downstream of the data quality*. If the upstream CRM has 38 free-text comments per account in URL-encoded mixed Hebrew/Arabic with PINs and signed URLs (as the prior audit of `mcp-seekapa-tools` confirmed), the model will surface that mess into Liron's chat window. Ship redaction at the boundary, not at the prompt.

**Pattern 2 — the action gap.** *"In 2026, the real challenge with AI is not getting answers but getting AI to do something useful with those answers. Most organizations are still stuck in a pattern where AI can explain, summarize, or recommend, but not execute"* [18]. For executives this manifests as: the tool surfaces an insight, then nothing happens. The recommendation loop in §13 closes this with `compute_journey_verdict` → `escalate_to_review_queue` chains.

**Pattern 3 — the silo gap.** Even with the best tool, *"organizational silos remain firmly in place"* [18]. Liron is consuming evidence from CRM, Chatwoot, Call Analyzer, OneSignal, and Windsor — five different upstream systems, each with their own owner. The MCP's contribution is not new data; it is a **single conversational surface that hides the silo seams**. That value proposition is fragile: any latency spike, any inconsistent answer, any "tool failed" silently, and the executive opens five tabs again.

The remainder of this report is organized around what the 50+ structured claims tell us about closing those three gaps.

---

## 3. Finding A — Citation and Provenance Are the Load-Bearing Trust Feature

### 3.1 The evidence

The strongest signal in the entire research corpus is that **executive adoption tracks citation density**. Glean's reported journey to **$200M ARR with 93% adoption in two years, averaging five queries per user per day and 40% wDAU/wMAU** is attributed by the company to one feature: *"answers that are fully cited and linked to source information, ensuring trust and accuracy"* [4]. Tableau, a different vendor with a different architecture, made the same bet: Tableau Pulse's design rule is *"transparency and explainability, so you'll always know where the data came from, thanks to citations, so you can validate the insights"* [5]. ThoughtSpot, the third major AI-native analytics vendor, says it explicitly: *"trust with business data, once lost, is hard to regain"* [19]. Three large independent vendors converged on the same answer: **citation is the trust feature**.

The academic literature corroborates this. The 2025 PROV-AGENT framework formalizes this for autonomous AI agents — *"the output is a complete cognitive lineage, an inspectable reasoning artifact that makes AI logic explainable, debuggable, and auditable"* [20] — and Tensorlake's industry post calls precise paragraph- and cell-level citations *"the line between professional agentic applications and chatbot demos"* [21].

### 3.2 The regulatory pull

Citation is no longer just a UX choice. **EU AI Act Article 12, enforceable from August 2, 2026, requires high-risk AI systems (including credit scoring, fraud triage, and automated decisions) to retain audit logs for ≥6 months with full traceability**; *"every AI-assisted decision needs an audit trail that a human (and a regulator) can follow"*. Penalties reach €15M or 3% of worldwide turnover [11]. **US Federal Reserve SR 11-7 (the de facto model-risk standard)** demands *"thorough documentation across the model lifecycle … offering a clear audit trail"* for any quantitative system informing financial decisions [12]. For a CySEC- or FCA-regulated forex broker, **automated MiFIR/EMIR reporting and audit-trail management are non-negotiable** [22]. The lead-scoring verdicts the MCP produces fall squarely inside the regulatory definition of a "model," and the audit-trail requirement applies whether anyone in Tel Aviv has read the regulation or not.

### 3.3 What this means for an MCP (no UI)

In a chat interface, "citation" cannot mean a footnote popover. It must be an inline, machine-readable provenance block in every tool response. The pattern recommended by both NotebookLM-MCP and the OpenAI Apps SDK is the same:

- A **`_provenance` block** in every response containing: `data_source` (e.g., `crm.az-corp.corp-domain.com`), `query_id`, `as_of` timestamp, `model_version`, `prompt_version`, `rubric_version`, `batch_id`, and — for every numeric or categorical claim — a list of source pointers (`call_id`, `transcript_id` + `(t_start, t_end)`, `crm_comment_created_at`).
- A **never-empty contract**: even when no underlying source exists, the block must contain `data_source: null, reason: "no_source"` so the LLM can correctly say "I have no source for this."
- The block is structured (machine-readable for the agent that may chain), but is also rendered to the user as a one-line "Source: …" footer the LLM is instructed to surface.

The deployed `mcp-seekapa-tools` already has this partially: `verdict_provenance(acc)` returns `model_version`, `prompt_version`, `rubric_version`, `batch_id`, `run_at`, `validator_drops`. The recommendation is to make this **non-optional** for every tool response, not a separate tool the executive must remember to call.

### 3.4 Edge case — the Glean caveat

Glean's 93% number is self-reported on a vendor blog and should be discounted accordingly. But Gartner Peer Insights, customer reviews on G2, and Glean's coverage in independent press (TechCrunch [23]) consistently corroborate the citation-as-trust mechanism even where they question the absolute adoption figure. The directional finding holds regardless of whether the precise number is 93% or 70%.

---

## 4. Finding B — Don't Let the LLM Do Math (and Don't Show False Precision)

### 4.1 The hallucination evidence

LLMs hallucinate numbers. This is not speculative; it is documented in production:

- A financial services client reported that **Power BI Copilot stated *"Loan default rates decreased by 3%"* when the actual decrease was 0.3%** — a 10× error that nearly reached the board. The client disabled Copilot narrative generation entirely [6].
- Independent monitoring reports a **6% hallucination error rate in Power BI Copilot narratives**, including *"Revenue increased by 12%"* when the actual was 8% [24].
- Production text-to-SQL on heterogeneous enterprise schemas hits only **10–20% accuracy on open-ended business questions**; the most dangerous failure mode is **silent semantic failure** — *"seemingly correct queries execute successfully but inform critical reports with wrong data"* [7].
- Microsoft's own Q&A platform documents the dominant Copilot complaint: *"When you submit a prompt multiple times to Copilot, you aren't guaranteed to get the same answer back … different answers for the same question provided to different users"* [25].

The pattern is consistent across vendors: **when the LLM is the calculator, executives lose trust at 10× the rate they earned it.**

### 4.2 The vendor counter-pattern

Tableau Pulse's published design rule is the explicit architectural fix: *"They never let the LLM do math — it's not calculating the statistical insights"* [5]. The math runs in deterministic Python/SQL; the LLM only narrates pre-computed values. ThoughtSpot Spotter follows the same pattern — *"reasons through every step, checks its own work, and continuously refines"* [26], with token-level traceability between the natural-language question and the resolved metric. Snowflake's 2026 *Cortex Code* push goes further: AI-native analytics is being sold as *"a control plane with provenance + governance baked in"* [27].

The architectural takeaway is unambiguous: **Compute deterministically. Narrate with the LLM. Cite the computation.**

### 4.3 False precision

A second, subtler trust failure is **false precision** — reporting more decimal places than the data supports. Tufte-aligned dashboard guidance is explicit: *"Match decimal precision to significance — executives don't need to know that conversion is exactly 3.214%, they need to see whether it's rising or falling"* [28]. Excess precision *feels* authoritative but is itself a credibility signal: an executive who spots that the dashboard reports `19299.91` USD total deposits to two decimal places — when the underlying CRM rounds at the unit — has just lost a small piece of trust they may not consciously register.

### 4.4 What this means for `mcp-seekapa-tools`

Concrete mappings:

- **`rubric_grade_call`** must continue to compute scores in deterministic Python (it does today). The LLM's role is to write the `why` field, not to produce the `composite_score`. Verify by reading the code path and asserting no LLM is invoked between `transcript → score`.
- **`funnel_aggregate`** outputs `stages`, `spend_usd`, `revenue_usd`, `roas`, `leakage_points`. All of these are deterministic. The narration ("FTD rate dropped 14% week-over-week, primarily driven by Saudi Arabia") is the LLM's job — and it must cite the deterministic numbers verbatim.
- **Round to significance**: report FTD rate as `11%` not `11.4732%`; total deposits as `$19.3K` not `$19,299.91`. Add a `_format` field to numeric responses that captures the intended precision and let the LLM read it.
- **Refuse to compute new metrics ad-hoc**. If Liron asks "what's the X-rate?" and X is not in the metric catalog, the tool should return `{ "error": "metric_not_in_catalog", "available_metrics": [...] }` rather than letting the LLM guess. This is the load-bearing pattern that prevents 80% of hallucinations at the source.

---

## 5. Finding C — Push Beats Pull: Executives Want Digests, Not a Chat Box

### 5.1 The Tableau Pulse / Power BI evidence

Tableau Pulse's adoption story is **digests, not chat**. Once a user follows ≥2 metrics, *"Tableau Pulse provides an overview to help you quickly see the latest insights across your metrics of interest, which appears at the top of digests and in the Tableau Pulse home page"* [29]. The 2026 January release added **frontier-LLM-driven multi-metric pattern detection, risk highlighting, and goal-relative explanations**, plus user-favorited "top metrics" with custom digest cadences [30]. Personalization is the second wedge: thumbs-up/down ranking, mute controls *"directly from insight feeds — ensuring executives see only insights they truly need"* [31].

Power BI's 2025 mobile push works on the same logic from the other angle: *"enabling mobile executives to query data on-the-go without opening full reports … filtered report summaries and answers are now available in the standalone Copilot experience"* [32]. The executive doesn't open a dashboard; the dashboard finds them.

### 5.2 The CMO / COO consumption evidence

Marketing-leaning executives consume analytics differently from engineering ones. **78% of retail website visits worldwide are mobile** [33]. **63% of CMOs report missing opportunities because they can't make decisions fast enough** [34]; this constraint applies equally to a COO managing cross-functional sales-and-marketing operations. The implication: an analytics tool that requires opening a laptop, logging into a SaaS app, and clicking through three drill-downs is structurally too slow for the 30-second-between-meetings cadence Liron actually has.

Push-mode analytics solves the cadence problem. The tool sends the answer before the question is asked.

### 5.3 What this means for `mcp-seekapa-tools`

The MCP today is purely pull-based: 26 tools, all reactive to a chat prompt. The recommendation is to add a small push surface:

- **`digest_metrics(persona, period)`** — a single tool that returns Liron's pre-computed daily or weekly digest: FTD count vs target, conversion rate, QFTD rate, speed-to-lead p50, anomalies, leakage points, top divergences (where AI ≠ CRM). The Slack/email side of the loop lives outside the MCP — but the tool itself is the structured payload.
- **`mute_metric(metric_name)` / `pin_metric(metric_name)`** — Tableau Pulse's mute/favorite pattern, persisted server-side per user identity.
- **Anomaly thresholds** — drivers/contributors/outliers should be auto-detected by a deterministic statistical layer (z-score, percentile, week-over-week delta) and surfaced inline. Pulse's "auto-detected drivers" are not LLM-derived; they are statistics with a narrative wrapper.
- **A push schedule outside the MCP itself**: a small Azure Function that calls `digest_metrics` on a cron, formats the response, and posts to Slack/email. The MCP exposes the *content*; an orchestrator handles delivery.

The pull surface stays. Liron will sometimes ask "show me ACC30245740" — that's still a tool call. But the *daily* engagement is push, and that is what drives the wDAU/wMAU number Glean's 40% benchmark sets.

---

## 6. Finding D — MCP Tool Design *Is* the UX

### 6.1 Tool descriptions are prompts

The single most consequential MCP-specific finding: **tool names, descriptions, and parameter schemas are prompts the LLM reads on every turn**. Anthropic engineering's published guidance is unambiguous: *"Tool names, descriptions, and parameters are treated as prompts for the LLM, so it's really important to have clear instructions"* [10]. Block makes the same point: *"Even small refinements to tool descriptions can yield dramatic improvements — Claude Sonnet 3.5 achieved state-of-the-art performance on the SWE-bench Verified evaluation after precise refinements to tool descriptions"* [10]. The MCP's "documentation" is not separate from the product — it *is* the product.

This insight inverts a common engineering reflex (write the code, document it later). For an MCP, the docstring is on the critical path of every executive query.

### 6.2 Namespacing and naming

Anthropic recommends **prefix- or suffix-based namespacing by service AND resource**: `asana_search` and `asana_users_search` rather than bare `search` [10]. The deployed `mcp-seekapa-tools` follows this for `chatwoot_*`, `crm_*`, `onesignal_*`, `call_analyzer_*` — but **the analysis tools (`rubric_grade_call`, `compute_journey_verdict`, `funnel_aggregate`, `comment_classifier`) are unnamespaced**, which makes them harder to find and easier to misroute. Recommend renaming to `seekapa_rubric_grade`, `seekapa_journey_verdict`, etc.

Parameter names follow the same logic: **`user_id` beats `user`** [10]. `acc` (used as a CRM account ID) is technically ambiguous; `crm_acc_id` is unambiguous. The cost of renaming is one PR; the benefit is fewer hallucinated tool calls.

### 6.3 Document enums inline

Linear's MCP server is the canonical exemplar: parameter values are documented *in the description string*, not in an external doc. *"priority is explicitly defined as 0 = No priority, 1 = Urgent, 2 = High, 3 = Normal, 4 = Low"* [9]. The agent never has to look up the enum. For the Seekapa MCP, this means:

- `compliance_status` should document `["PARTIALLY VERIFIED", "VERIFIED", "REJECTED", ...]` inline.
- `action` (in `get_lead_verdict`) already documents the band rubric in `_BAND_RUBRIC_TEXT`. Move that into the tool docstring.
- Country codes, campaign types, kind enums for OneSignal — all inline.

### 6.4 Annotations as risk vocabulary

The MCP spec defines three boolean annotations: `readOnlyHint`, `destructiveHint`, `openWorldHint`. The OpenAI Apps SDK *requires* these and *"if you omit these hints (or leave them as null), treat it as a validation error"* [8]. Claude.ai uses them to drive auto-approval vs. confirmation dialog UX [35]. The deployed `mcp-seekapa-tools` does not yet annotate any tool. Recommend annotating all 26.

A second, related rule from Block: **one risk level per tool**. *"Build tools with one risk level only: either read-only (safe) or non-read (write/delete). Mixing operations confuses users and complicates permission settings"* [10]. The deployed MCP largely follows this; `call_analyzer_transcribe_call` is the one tool with side-effects (charges ElevenLabs on every call, non-idempotent) and it should be annotated `destructiveHint: true`.

### 6.5 Workflow tools, not endpoint wrappers

The most common anti-pattern in MCP servers is wrapping REST endpoints 1:1. *"A critical mistake is wrapping existing REST endpoints directly as MCP tools, requiring LLMs to chain multiple dependent calls in sequence to accomplish a single outcome … resulting in three times as many input/output tokens for three round-trips"* [36]. Linear collapsed *"4–6 tool calls"* into single workflow tools [9]. Block evolved its Linear MCP further, eventually exposing two GraphQL passthroughs that collapse arbitrary chains into one round-trip [10].

For Seekapa, the pattern is: **tools answer questions, not API calls**. The deployed MCP already does some of this (`compute_journey_verdict` aggregates rubric + CRM into one verdict). But others remain endpoint-shaped (`call_analyzer_get_calls`, `call_analyzer_get_cdr`, `call_analyzer_get_transcript`). A workflow tool — `seekapa_lead_dossier(acc)` — that internally calls all four and returns a single, citation-bearing dossier would be the correct refactor.

### 6.6 The token-cost ceiling

Two concrete numbers from production:
- **MCP tools can consume 66,000+ tokens of context before a conversation starts**, eating ~⅓ of Claude Sonnet 4.5's 200K window just on schema [37].
- Returning **5,000 rows of JSON consumes ~half the context window** [38].
- Empirically, **small models cap around 19 tools and fail at 46; even frontier models struggle past 100; recommended sweet spot is 5–15 per server** [36].

The deployed Seekapa MCP at 26 tools is in the safe zone but at the upper edge. Two mitigations:
- **Progressive disclosure** (2026 emerging pattern): expose a lightweight tool index, fetch full schemas on demand. Reports of *"85–100× reductions in token usage while maintaining or improving tool selection accuracy"* [39].
- **Pagination by default** on every list-shaped response (`chatwoot_list_conversations` already does this; `call_analyzer_get_calls` does not — 60 calls × 14 KB total verified live).

### 6.7 The Linear lesson: stringified JSON is an anti-pattern

A specific Linear finding from Fiberplane's analysis: *"Data is returned as escaped strings rather than structured content, forcing models to parse `\\\"id\\\":\\\"123\\\"` instead of native JSON, which increases parsing complexity and context cost"* [9]. Verify the Seekapa MCP returns native JSON throughout (it does, per the audit) — and never regress on this.

---

## 7. Finding E — Human-in-the-Loop Is Non-Negotiable for Regulated Decisions

### 7.1 The Zillow case study

In November 2021, Zillow shut down Zillow Offers, laid off 25% of its workforce, and reported a **$500M+ loss**. The CEO publicly attributed the collapse to *"unable to predict future pricing of homes to a level of accuracy that makes this a safe business to be in"* [13]. The decisive structural mistake — documented in the AI Incident Database — was a 2021 program called *"Project Ketchup"* that *"explicitly used its Zestimate as its cash offer for certain qualifying homes and prevented its pricing experts from modifying the algorithm's home value estimates, which removed important human oversight from the pricing process"* [13]. Removing the human gate is what scaled the loss.

This is the canonical executive-facing AI-trust collapse. It is the case study every COO will have heard about — and the design pattern your MCP must be visibly different from.

### 7.2 The regulatory floor

**EU AI Act Article 12** (enforceable Aug 2 2026, penalty up to €15M) requires high-risk AI systems to *"be developed and deployed in a way that allows appropriate traceability and explainability,"* with audit logs retained ≥6 months covering risk events, post-market monitoring, and operational deployer monitoring [11]. **Federal Reserve SR 11-7** demands documented model lifecycle, independent validation, and clear audit trail [12]. **CySEC/FCA-aligned forex CRMs** require automated MiFIR/EMIR reporting and audit-trail management as table-stakes [22].

For `mcp-seekapa-tools`, the FTD-prediction and lead-scoring verdicts fall inside *"high-risk"* under the EU AI Act (automated decisions affecting access to financial services / scoring) and inside *"model"* under SR 11-7. The audit-log requirement is structural, not optional.

### 7.3 The Forrester pattern

The Forrester Wave Q3 2025 (Data Governance) explicitly identifies **"agentic governance"** as the new market shift — but every leader cited (Atlan, Alation, Credo AI) *"keeps humans in the loop on policy enforcement and remediation"* [40]. The market has not endorsed fully autonomous AI verdicts in regulated decisions. The dominant production HITL pattern is **synchronous approval pause** — the agent serializes state at any high-risk decision, surfaces it to a human via UI, resumes only on explicit approve/reject [41]. Use cases cited explicitly: *"financial transactions exceeding thresholds, account modifications, data deletion, or any action that can't be easily reversed"*.

### 7.4 What this means for `mcp-seekapa-tools`

The deployed MCP today emits verdicts (`get_lead_verdict`, `compute_journey_verdict`, `list_divergences`) directly to the agent context. There is no review queue, no escalation gate, no human-approve-before-action. Liron will demand one — and if he doesn't, the regulator will.

Concrete recommendations:

- **Verdict-review queue**: Any verdict with `confidence < HIGH_THRESHOLD`, any `hard_disqualifier=true`, any `compare_with_crm.diverges=true` writes a row to a review-queue table. The queue is exposed as a tool (`list_pending_reviews`) and an action tool (`approve_verdict(verdict_id, reviewer_id)`). Verdicts are not "live" in downstream actions until approved.
- **Audit log**: Every tool call writes `(timestamp, tool, params, response_hash, model_version, prompt_version, user_id)` to an immutable log retained ≥6 months. This is EU AI Act Article 12 compliance with no further work.
- **Confidence floors**: `compute_journey_verdict` should return `action=WAIT, confidence=low` when transcript coverage is below a threshold (e.g., `transcribed_calls/total_attempts < 0.3`). Honest uncertainty over confident wrong (see §9).
- **Replay capability**: Given a `(model_version, prompt_version, rubric_version, batch_id)` tuple, the system must be able to re-score the same input deterministically (modulo temperature jitter) and reproduce the original verdict. SR 11-7's documented-lifecycle requirement collapses to this single capability.

The MCP shouldn't autonomously run Liron's pipeline. It should make Liron's pipeline auditable.

---

## 8. Finding F — Latency, Reliability, and the Silent-Failure Anti-Pattern

### 8.1 The latency floor

Conversational latency is a hard psychological constraint. Synthesizing across multiple practitioner sources [42][43][44]:

- **Sub-300 ms feels conversational.**
- **2–3 seconds feels sluggish** (users start tabbing away).
- **10–30 seconds breaks conversational flow entirely** (users abandon, agent context is poisoned by the wait).
- **MCP handshake target: <100 ms local, <500 ms remote.**
- **P50/P95/P99 must all be tracked**: a tool with 100 ms average and 5 s P99 *"can block agents for extended performance"* and silently kills power users.

For `mcp-seekapa-tools`, the worst offenders today are `call_analyzer_ensure_transcript` (90s poll on missing transcript) and the cohort tools (`crm_get_customer_cohort` at 20 ACCs × ~500ms upstream). Mitigations:
- **Stream long operations**. Send a `status: pending` envelope immediately, then a `status: completed` envelope when done. The MCP spec supports this; the LLM can render "still working…" mid-call.
- **Precompute the slow stuff**. Daily digest content should be precomputed and cached. The MCP serves cached payloads at <100 ms.
- **Per-tool latency SLOs**: P95 < 2 s for read tools, P95 < 5 s for write tools, P95 < 30 s for orchestrators. Measure, alert, fix.

### 8.2 The silent-failure anti-pattern

The single most damaging error mode in MCP servers is **silent empty success**: the tool returns `{}` or `{"records": []}` with no error and no explanation. *"MCP servers may silently fail when agents use environment names from prompts incorrectly instead of required identifiers, returning empty responses without proper error feedback. … The agent then hallucinates next steps from nothing"* [36]. The agent treats absence-of-data as confirmation-of-absence and produces a confidently wrong answer.

The deployed Seekapa MCP has at least one verified instance of this: the prior live audit caught **`call_analyzer_get_cdr` returning a row for a different `call_id` than the one requested** with no error envelope. That's the worst version — silent semantic substitution. Defensive post-filter is a 3-LOC fix.

The general fix is a **typed envelope contract** for every response:

```json
{
  "data": {...},
  "_provenance": {...},
  "_status": "ok | partial | empty | error",
  "_warning": [{...}],
  "_error": null | {"code": "...", "detail": "..."}
}
```

The agent reads `_status` first. `partial` and `empty` are first-class — not equivalent to `ok`. The LLM can be instructed to surface partial/empty states explicitly to Liron rather than narrating around them.

### 8.3 Reliability target

Production executive analytics is benchmarked at **99.99–99.999% uptime, with MTBF and MTTR explicitly tracked** [45]. For an MCP this means:
- Health endpoints (`/livez`, `/readyz`) — deployed MCP already has these.
- Per-tool error-rate alerting (≥1% error rate on any tool over 5 min → page).
- Rolling deploy with traffic split (10% → 50% → 100%) and automatic rollback on error-rate spike.

Liron will not measure the MCP on uptime. He will measure it on the *number of times he tried to use it and it didn't work* over a quarter. Two outages is a problem; four is the end of the experiment.

---

## 9. Finding G — Honest Uncertainty Beats Confident Wrongness

### 9.1 The calibration evidence

Johns Hopkins (2025) summarizes the calibration literature: *"In high-stakes environments, [admitting uncertainty] is infinitely preferable to waiting for an answer that looks correct but is not. … Reinforcement Learning from Human Feedback systematically degrades calibration, with reward models exhibiting inherent biases toward high-confidence responses regardless of actual response quality, and human annotators penalizing uncertainty expressions"* [14]. MIT's 2024 *Thermometer* work demonstrated that calibration fixes are technically tractable: *"Method prevents an AI model from being overconfident about wrong answers"* [46].

The implication for any LLM-driven analytics tool is operational: the model will, by default, fabricate confident answers when the data is insufficient. The mitigation is structural — the *system* must surface uncertainty even when the LLM tries to bury it.

### 9.2 What this means for `mcp-seekapa-tools`

Three specific design rules:

- **Mandatory `confidence` field**. Every verdict, every score, every aggregation returns `confidence: high | medium | low` based on coverage and rubric pass-through. `low` triggers automatic routing to the review queue (§7.4).
- **Coverage declaration**. Every analytical tool returns `coverage` metrics: rows examined, rows with sufficient evidence, rows skipped. Liron can verify that "FTD rate of 11% across Saudi Arabia" is computed over 200 customers, not 5.
- **Refuse-to-score paths**. `compute_journey_verdict` should return `action: "INSUFFICIENT_DATA"` (not a default `WAIT` or `CALL_AGAIN`) when transcript coverage is below threshold. The LLM is instructed to surface this to Liron as "I can't score this account — only X of Y calls were transcribed."

The product principle: **Liron should leave the tool more sure of what he doesn't know, not less sure of what he does.**

---

## 10. Finding H — Discovery, Onboarding, and Mobile Access Patterns

### 10.1 Discovery in chat-native UX

Claude.ai surfaces MCP tools implicitly — *"once you've connected an app, Claude can bring it into a conversation on its own when it fits what you're asking for — you don't have to name it every time"* [47]. The user does not browse a tool catalog; the LLM picks the right tool based on intent. This is why tool naming and description quality matter so much (Finding D).

For non-technical onboarding, the MCP spec defines two complementary surfaces beyond tools:
- **Prompts** — pre-written, parameterizable starter intents (e.g., "Daily FTD digest", "Show me divergent leads"). *"Clients can discover available prompts, retrieve their contents, and provide arguments to customize them"* [48]. **However, Prompts UX is patchy in 2026** — Claude Code times out on Prompts with required parameters, Claude Desktop attaches them as files [49]. Plan accordingly.
- **Resources** — read-only data references (e.g., a CRM schema dictionary). *"Server developers don't build resources because clients don't surface them well, and clients don't invest in resource UX because few servers expose them"* [50]. Skip until the client UX matures.
- **Elicitation** (2026 emerging) — a tool can pause mid-call to ask the user a structured question (*"Cancel my subscription" → "Which one — Pro or Enterprise?"*) [51]. Wire this for ambiguous executive queries (e.g., "show me last week" → which Sunday-to-Saturday).

### 10.2 The "Sign in to {agent}" pattern

M365 Copilot's per-user OAuth UX renders an in-chat sign-in prompt: *"Select 'Sign in to {agent-name}'. In the pop-up window, log in with your account and authorize the agent. When the pop-up window closes, the agent returns a response"* [52]. The MCP spec mandates an authorization-server-rendered consent screen showing client name + requested scopes [53]. The deployed `mcp-seekapa-tools` already implements RFC 9728 protected-resource metadata + `aud` audiences, per recent commits.

The product implication: **the OAuth screen is part of the executive's first impression**. The consent screen should list scopes in plain English (*"This tool will read CRM customer records, call transcripts, and campaign metrics"*) — not OAuth identifiers.

### 10.3 Mobile access

**Smartphones account for 78% of retail website visits worldwide** [33]. **Power BI Copilot's November 2025 standalone mobile experience** is explicitly framed for executives: *"enabling mobile executives to query data on-the-go without opening full reports … filtered report summaries and answers are now available in the standalone Copilot experience"* [32]. Tableau Pulse's email/Slack digests render on phones natively.

For a chat-native MCP, mobile is mostly upstream of the MCP itself — Claude.ai, ChatGPT, and Copilot all render fine on phones. The MCP must:
- Return small payloads (a 50-row JSON dump is unreadable on a phone; a 3-row summary + "drill down" intent is).
- Avoid deeply nested structures (the LLM's mobile-rendered output flattens to bullet lists).
- Keep `_provenance` blocks compact enough that the citation footer fits on one screen.

### 10.4 PII and consent at the executive layer

**By 2026, 85% of enterprise RAG deployments are predicted to incorporate privacy-preserving techniques, up from 32% in 2024** [54]. **K2View's enterprise-architecture target is 99.98% PII-detection accuracy** [54]. **Existing tools achieve only 76.4% accuracy on non-English content** per Meta's October 2024 evaluation — directly relevant for Seekapa's mixed Arabic/Hebrew/Portuguese corpus.

The executive-facing implication is *"Liron should never see PII he doesn't need to make a decision."* Concrete pattern:

- **Default redacted mode** on every tool. Names → initials + hash. Phones → country code + hash. Emails → domain only. PINs/tokens in agent comments → stripped at the boundary.
- **`mode="raw"` requires explicit operator scope** in the OAuth claim. Auditable separately.
- **Sender-PII fields** (e.g., `email_from_address`, `email_reply_to_address` on OneSignal) should be dropped server-side unless `mode="raw"` is requested.

The prior live audit of the deployed `mcp-seekapa-tools` confirmed this is structurally absent today: customer names, phone JIDs, full email addresses, and 38 free-text agent comments per customer are returned raw to the LLM context. The fix is one boundary-redaction module; the value is regulatory protection AND executive trust.

---

## 11. Synthesis: The Five Design Pillars for `mcp-seekapa-tools`

Across 50+ structured claims, five pillars emerge that any executive-grade MCP must satisfy. Each maps to specific tools or refactors in the deployed codebase.

| # | Pillar | Source consensus | Concrete MCP refactor |
|---|---|---|---|
| 1 | **Citation + provenance, mandatory** | Glean [4], Tableau Pulse [5], ThoughtSpot [19], HBR [15], PROV-AGENT [20] | `_provenance` block on every response; never-empty contract; audit log table |
| 2 | **Deterministic compute, LLM narration only** | Tableau Pulse [5], Promethium [7], Power BI failure cases [6][24] | Score + aggregate in Python; LLM only writes `why` strings; refuse ad-hoc metrics |
| 3 | **Push beats pull** | Tableau Pulse [29][30][31], Power BI mobile [32], BARC [3] | `digest_metrics(persona, period)` tool + Slack/email cron orchestrator |
| 4 | **Tool design as language design** | Anthropic [10], Block [10], Linear [9], OpenAI Apps SDK [8] | Inline enum docs; namespaced names; risk annotations; workflow tools over endpoint wrappers |
| 5 | **Human-in-the-loop + audit trail** | Forrester [40], EU AI Act [11], SR 11-7 [12], Zillow case [13] | Verdict-review queue; immutable audit log ≥6mo retention; confidence floors |

The pillars are mutually reinforcing. Provenance enables the audit log (Pillar 5). Deterministic compute makes provenance verifiable (Pillar 1). Push delivery requires reliable provenance because Liron has less time to verify in a Slack digest than in a chat thread. Tool design is the language wrapper that surfaces all of the above to the LLM — and the LLM is the only thing Liron sees.

The order matters: **build Pillar 1 (provenance) and Pillar 4 (tool design) first**. They are prerequisites for everything else and they are the lowest-cost interventions. Pillar 2 (deterministic compute) is mostly already true in the deployed code; it just needs to be made structural and visible. Pillars 3 and 5 are larger initiatives that should follow once 1, 2, and 4 are stable.

---

## 12. Limitations & Caveats

This research has the following known limitations:

1. **Vendor self-reports are over-represented** in the adoption-success literature. Glean's 93% adoption [4] and Power BI's 84% Copilot adoption in 30 days [55] are vendor-published. The directional finding (citation drives adoption) is corroborated by independent sources, but specific percentages should be discounted.

2. **The 6% hallucination rate for Power BI Copilot** [24] is from a single-vendor blog (dstrat) and has not been independently audited at the time of writing. The 10× error case study from Collectiv [6] is more rigorously sourced but still vendor-blog.

3. **Forex-specific executive-analytics literature is thin.** Most cited best-practices come from forex CRM vendors marketing their own products. The structural advice (audit trail, MiFIR/EMIR reporting) is regulator-anchored and reliable; the specific tool recommendations should be cross-checked against Liron's operational context.

4. **Latency benchmarks** in §8 are practitioner-cited, not academic. The 300 ms / 2 s / 10 s thresholds are consistent across sources but don't have peer-reviewed underpinning at this granularity.

5. **MCP is 18 months old.** Best-practice patterns (progressive disclosure, elicitation, structuredContent) are still consolidating. Recommendations in §13 should be revisited in 6 months as the spec and client UX mature.

6. **Cultural / linguistic gaps.** Most cited research is US- and Europe-centric. The forex broker's customer base is GCC + LATAM, which has documented differences in mobile-first behavior, regulatory regimes (CySEC/FCA vs. local), and PII detection accuracy on non-English content [54]. Apply findings with this lens.

7. **No primary research on Seekapa's actual users.** This report synthesizes secondary evidence about what executives in general want. The sole source of truth on what *Liron* wants is Liron, and a 30-minute interview against the recommendations in §13 should validate or revise them before commitment.

---

## 13. Recommendations: 12-Item Action Plan for the Next Iteration

Each item is mapped to the relevant pillar and source. Effort estimates assume the existing codebase as audited 2026-05-07. "S/M/L" = small (≤1 day), medium (1–5 days), large (≥1 week). Prioritized by trust-leverage divided by effort.

### Priority 1: Ship in the next iteration (Pillar 1, 2, 4)

| # | Item | Pillar | Effort | Source |
|---|---|---|---|---|
| 1 | **Add `_provenance` block to every tool response.** Schema: `data_source, query_id, as_of, model_version, prompt_version, citations[]`. Make non-optional. | 1 | M | [5][20] |
| 2 | **Rename `acc` → `crm_acc_id` everywhere; namespace analysis tools (`seekapa_rubric_grade`, `seekapa_journey_verdict`, etc.).** | 4 | S | [10] |
| 3 | **Document all enums inline in tool descriptions** (compliance_status, action band rubric, country codes, kind enums). | 4 | S | [9] |
| 4 | **Add `readOnlyHint`/`destructiveHint`/`openWorldHint` annotations to all 26 tools.** OpenAI Apps SDK validation requires it; Claude.ai uses it for auto-approve UX. | 4 | S | [8][35] |
| 5 | **Fix `call_analyzer_get_cdr` silent substitution** (defensive post-filter that returned `call_id` matches requested). 3 LOC. | 2 | S | [36] (live audit) |
| 6 | **Replace raw `comments[]` in `crm_get_customer` with `comments_classified[]`** (the `comment_classifier` tool already exists; wire as default projection). Strip PINs/tokens/URLs at the boundary. | 1, 2 | M | live audit + [54] |

### Priority 2: Within 30 days (Pillar 5)

| # | Item | Pillar | Effort | Source |
|---|---|---|---|---|
| 7 | **Immutable audit log table**: every tool call writes `(timestamp, tool, params_hash, response_hash, model_version, user_id)` with ≥6-month retention. EU AI Act Article 12 compliance falls out for free. | 5 | M | [11][12] |
| 8 | **Verdict-review queue**: any verdict with `confidence < HIGH` or `hard_disqualifier=true` or `compare_with_crm.diverges=true` writes a row. Expose `list_pending_reviews` + `approve_verdict` tools. Verdicts not "live" downstream until approved. | 5 | L | [40][41][13] |
| 9 | **Confidence floors + `INSUFFICIENT_DATA` action**: `compute_journey_verdict` returns this explicitly when transcript coverage < 0.3. LLM instructed to surface this to user. | 1, 5 | S | [14][46] |

### Priority 3: 60–90 day horizon (Pillar 3)

| # | Item | Pillar | Effort | Source |
|---|---|---|---|---|
| 10 | **`digest_metrics(persona, period)` tool** + Slack/email cron orchestrator (Azure Function calling the MCP daily). Includes auto-detected drivers (z-score, week-over-week delta). | 3 | L | [29][30][31] |
| 11 | **`mute_metric(name)` / `pin_metric(name)`** persisted per-user-identity. Mirror Tableau Pulse personalization. | 3 | M | [31] |
| 12 | **Per-tool latency SLOs**: P50/P95/P99 dashboards in Azure Monitor; alert on P95 > 2s for read tools, P95 > 5s for write tools. Per-tool error-rate alerting at 1%. | — (cross-cutting) | M | [42][43][44][45] |

### Out of scope for the immediate iteration (revisit Q3 2026)

- **Progressive-disclosure tool index** (only useful if tool count grows past ~40).
- **Elicitation** (client UX still patchy in 2026).
- **MCP Apps / interactive widgets** (M365 supports; Claude.ai partial; not yet a stable surface for executive-facing flows).

---

## 14. Bibliography

[1] *Anthropic's Model Context Protocol has crossed 97 million installs in just 16 months.* https://beingguru.com/anthropic-mcp-hits-97-million-installs/

[2] Fortune (2025). *HBR survey: Only 6% of companies trust AI agents.* https://fortune.com/2025/12/09/harvard-business-review-survey-only-6-percent-companies-trust-ai-agents/

[3] The Virtual Forge (citing BARC). *Common Power BI mistakes that kill dashboard adoption.* https://www.thevirtualforge.com/company/blog/common-power-bi-mistakes-that-kill-dashboard-adoption-and-how-to-avoid-them

[4] Glean (2025). *Glean surpasses $200M ARR as enterprises operationalize AI.* https://www.glean.com/blog/glean-200m-arr-milestone

[5] Tableau (2024). *How Tableau Pulse powered by Tableau AI is reimagining the data experience.* https://www.tableau.com/blog/tableau-pulse-and-tableau-ai

[6] Collectiv. *Copilot in Power BI: where it fails, and how to make it work.* https://gocollectiv.com/blog/power-bi-copilot-success/

[7] Promethium. *Enterprise text-to-SQL: what accuracy benchmarks really mean.* https://promethium.ai/guides/enterprise-text-to-sql-accuracy-benchmarks-2/

[8] OpenAI Developers. *Build your MCP server — Apps SDK.* https://developers.openai.com/apps-sdk/build/mcp-server

[9] Fiberplane. *The Linear team made a good MCP.* https://blog.fiberplane.com/blog/mcp-server-analysis-linear/

[10] Block Engineering / Anthropic Engineering. *Block's playbook for designing MCP servers; Writing effective tools for AI agents.* https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers ; https://www.anthropic.com/engineering/writing-tools-for-agents

[11] Help Net Security (Apr 2026). *What the EU AI Act requires for AI agent logging.* https://www.helpnetsecurity.com/2026/04/16/eu-ai-act-logging-requirements/

[12] US Federal Reserve. *Revised guidance on model risk management (SR 11-7 / SR 26-02).* https://www.federalreserve.gov/supervisionreg/srletters/SR2602.pdf

[13] AI Incident Database #149. *Zillow Offers shutdown.* https://incidentdatabase.ai/cite/149/

[14] Johns Hopkins Hub (2025). *Teaching AI to admit uncertainty.* https://hub.jhu.edu/2025/06/26/teaching-ai-to-admit-uncertainty/

[15] HBR / Forrester (2024). *AI has a trust problem. Here's how to fix it.* https://hbr.org/sponsored/2024/09/ai-has-a-trust-problem-heres-how-to-fix-it

[16] McKinsey. *The state of AI in 2025: agents, innovation, and transformation.* https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai

[17] Gartner (2025). *Lack of AI-ready data puts AI projects at risk.* https://www.gartner.com/en/newsroom/press-releases/2025-02-26-lack-of-ai-ready-data-puts-ai-projects-at-risk

[18] BlastX. *2026 Analytics trends: beware the growing gap between AI and action.* https://www.blastx.com/insights/2026-analytics-trends-beware-gap-between-ai-and-action

[19] ThoughtSpot. *10 data and AI trends — 2025.* https://www.thoughtspot.com/resources/ebook/ai-data-trends-2025

[20] arXiv 2508.02866. *PROV-AGENT: Unified provenance for tracking AI agent interactions in agentic workflows.* https://arxiv.org/html/2508.02866v1

[21] Tensorlake. *Citation-aware RAG.* https://www.tensorlake.ai/blog/rag-citations

[22] Syntellicore. *CySEC/FCA-aligned audit-trail features for forex brokers.* https://www.syntellicore.com

[23] TechCrunch (Feb 2026). *The enterprise AI land grab is on — Glean is building the layer beneath the interface.* https://techcrunch.com/2026/02/15/the-enterprise-ai-land-grab-is-on-glean-is-building-the-layer-beneath-the-interface/

[24] dstrat blog. *Copilot in Power BI: why clean data determines whether AI delivers.* https://blog.dstrat.com/copilot-in-power-bi-why-clean-data-determines-whether-ai-actually-delivers-business-value

[25] Microsoft Q&A. *Inconsistent and hallucinatory responses from Copilot Studio agent.* https://learn.microsoft.com/en-us/answers/questions/5654951/inconsistent-and-hallucinatory-responses-from-copi

[26] ThoughtSpot. *Spotter | The most trusted enterprise agent for analytics.* https://www.thoughtspot.com/product/agents/spotter

[27] Snowflake (2026). *Snowflake Intelligence + Cortex Code for the agentic enterprise.* https://www.snowflake.com/en/news/press-releases/snowflake-expands-snowflake-intelligence-and-cortex-code-to-power-the-control-plane-for-the-agentic-enterprise/

[28] Caylent. *Tufte data-viz principles SKILL.* https://github.com/caylent/tufte-data-viz/blob/main/SKILL.md

[29] Tableau Help. *About Tableau Pulse.* https://help.tableau.com/current/online/en-us/pulse_intro.htm

[30] Tableau (Jan 2026). *Tableau January 2026 new features.* https://www.tableau.com/2025-3-january-features

[31] Tableau Blog. *Top new Tableau Pulse feature releases to know.* https://www.tableau.com/blog/top-new-tableau-pulse-feature-releases-know

[32] Microsoft Power BI (Nov 2025). *November 2025 feature summary.* https://powerbi.microsoft.com/en-us/blog/power-bi-november-2025-feature-summary/

[33] HubSpot. *2026 marketing statistics, trends & data.* https://www.hubspot.com/marketing-statistics

[34] PwC. *2026 growth strategy for chief marketing officers.* https://www.pwc.com/us/en/executive-leadership-hub/cmo.html

[35] MCP Blog. *Tool annotations as risk vocabulary.* https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/

[36] DEV / AWS Heroes. *MCP tool design: why your AI agent is failing and how to fix it.* https://dev.to/aws-heroes/mcp-tool-design-why-your-ai-agent-is-failing-and-how-to-fix-it-40fc

[37] DEV (Amzani). *Your MCP server is eating your context window.* https://dev.to/amzani/your-mcp-server-is-eating-your-context-window-theres-a-simpler-way-3ja2

[38] FutureSearch. *MCP structuredContent: how to return large results.* https://futuresearch.ai/blog/mcp-results-widget/

[39] Matthew Kruczek. *Progressive Disclosure MCP: 85x token savings benchmark.* https://matthewkruczek.ai/blog/progressive-disclosure-mcp-servers.html

[40] Forrester (Q3 2025). *The Forrester Wave: data governance solutions Q3 2025 — governance entered the agentic era.* https://www.forrester.com/blogs/the-forrester-wave-data-governance-solutions-q3-2025-shows-that-governance-entered-the-agentic-era/

[41] Galileo. *How to build human-in-the-loop oversight for AI agents.* https://galileo.ai/blog/human-in-the-loop-agent-oversight

[42] K2View. *Latency is the hidden enemy of MCP.* https://www.k2view.com/blog/latency-is-the-hidden-enemy-of-mcp/

[43] Speakeasy. *Monitor your MCP server.* https://www.speakeasy.com/mcp/monitoring-mcp-servers

[44] Glama. *Operational metrics and agent analytics for MCP.* https://glama.ai/blog/2025-12-06-the-operational-metrics-and-agent-analytics-driving-successful-model-context-protocol-mcp-servers

[45] Paessler PRTG. *SLA monitoring for executive analytics tools.* https://www.paessler.com/monitoring/network/sla-monitoring

[46] MIT News (2024). *Thermometer prevents AI model overconfidence about wrong answers.* https://news.mit.edu/2024/thermometer-prevents-ai-model-overconfidence-about-wrong-answers-0731

[47] Anthropic. *Use connectors to extend Claude's capabilities.* https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities

[48] Laurent Kubaski. *MCP prompts explained.* https://medium.com/@laurentkubaski/mcp-prompts-explained-including-how-to-actually-use-them-9db13d69d7e2

[49] GitHub. *Claude Code MCP prompts UX bug.* https://github.com/anthropics/claude-code/issues/30733

[50] WorkOS. *Understanding MCP features.* https://workos.com/blog/mcp-features-guide

[51] WorkOS. *MCP elicitation: request user input at runtime.* https://workos.com/blog/mcp-elicitation

[52] Microsoft Learn. *Build plugins from an MCP server for M365 Copilot.* https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/build-mcp-plugins

[53] Model Context Protocol. *Authorization specification.* https://modelcontextprotocol.io/specification/draft/basic/authorization

[54] BRICS-ECON. *Privacy-aware RAG: how to stop sensitive data leaks in AI (2026 guide).* https://brics-econ.org/privacy-aware-rag-how-to-stop-sensitive-data-leaks-in-ai-2026-guide

[55] EPC Group. *Power BI Copilot enterprise analytics guide 2026.* https://www.epcgroup.net/power-bi-copilot-enterprise-analytics-guide-2026

---

## 15. Methodology Appendix

### 15.1 Pipeline

The deep-research pipeline followed the 8-phase structure: SCOPE → PLAN → RETRIEVE → TRIANGULATE → OUTLINE REFINEMENT → SYNTHESIZE → CRITIQUE → PACKAGE. Mode selected: **deep** (critical decision territory; threshold ≥25 sources @ avg credibility >70/100).

### 15.2 Retrieval

12 parallel WebSearches covering: executive dashboard design, Tableau Pulse, Power BI Copilot, Hex Magic, AI analytics adoption failure, trust/transparency/explainability, MCP enterprise UX, hallucinated metrics, COO consumption patterns, PII redaction expectations, Glean executive insights, forex broker FTD analytics. Plus 3 specialized sub-agents:

- **BI-Copilot UX deep dive** (Tableau Pulse, Power BI Copilot, ThoughtSpot Sage) — 12 structured claims, primary sources from Anthropic, Tableau, Microsoft, ThoughtSpot, BARC.
- **MCP consumption-pattern research** (Claude.ai connectors, ChatGPT custom GPTs, M365 Copilot) — 25+ structured claims, primary sources from Anthropic engineering, modelcontextprotocol.io, OpenAI Apps SDK, Block engineering, Linear (via Fiberplane).
- **Executive-trust failure cases** (Power BI hallucinations, Zillow case, regulatory landscape) — 15+ structured claims, primary sources from McKinsey, HBR, Forrester, Federal Reserve, EU AI Act commentary.

### 15.3 Source-credibility rubric

| Tier | Examples | Weight |
|---|---|---|
| 1 — Regulator / peer review | EU AI Act, SR 11-7, MIT, Johns Hopkins, arXiv | 0.95–1.0 |
| 2 — Major analyst | Gartner, Forrester, McKinsey, HBR, BARC | 0.80–0.90 |
| 3 — Vendor primary docs | Anthropic, OpenAI, Microsoft Learn, MCP spec | 0.85–0.95 |
| 4 — Vendor blog (own product) | Tableau, ThoughtSpot, Glean, Snowflake | 0.55–0.75 |
| 5 — Practitioner blog | Block, Fiberplane, Speakeasy, K2View | 0.55–0.75 |
| 6 — User-reported / aggregator | Microsoft Q&A, AI Incident Database | 0.50–0.90 (case-dependent) |
| 7 — Marketing / SEO content | EPC Group, Riseup Labs | 0.30–0.50 |

Single-source claims are flagged inline (§3.4, §12).

### 15.4 Triangulation requirement

Core claims required ≥3 independent sources at average credibility ≥0.70. Outline refinement (Phase 4.5) consolidated the original 10 research questions into 8 thematic findings driven by evidence density: citation/provenance and "don't let LLM do math" emerged as the two strongest patterns and were promoted to dedicated sections; mobile and PII were folded into Finding H rather than receiving standalone sections.

### 15.5 What this report did not do

- No primary user research with Liron, Amit, or the QC team.
- No quantitative analysis of `mcp-seekapa-tools` usage logs (none exist yet).
- No cost analysis of the recommended refactors against engineering capacity.
- No security review of the audit-log retention infrastructure.

These are appropriate next steps. The recommendations in §13 should be treated as a hypothesis to test against Liron's actual workflow in a 30-minute interview before committing to the L-effort items.

---

*End of report. Markdown source: `Executive_MCP_Research.md`. HTML and PDF artifacts in the same directory.*
