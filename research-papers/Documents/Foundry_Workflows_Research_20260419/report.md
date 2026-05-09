# Azure AI Foundry Workflows and Agents — SOTA Design for Marketing-Funnel-Test

**Date:** 2026-04-19
**Author:** Claude (deep-research)
**Audience:** Shoval (principal engineer), Seekapa AI team
**Scope:** Move Marketing-funnel-test workflow beyond the trivial `OnConversationStart → InvokeAzureAgent → SendActivity` pattern. Research the right functional design as of April 2026.

---

## Executive Summary

Microsoft has positioned Foundry Agent Service as the **unified control plane for AI agents**, with multi-agent workflows, conversations API, observability, and evaluations now generally available as of March 2026 [1][6]. For your current Marketing-funnel-test workflow (one agent, two OpenAPI tools, `ManagerReply` strict JSON), the SOTA recommendation is **NOT to jump to multi-agent immediately** — industry guidance strongly warns against it until a single well-equipped agent has been pushed to its limits [4][7].

Instead, the right v4 design is a **single-agent workflow with four functional enhancements**:

1. **Conditional branching** (if/else on route_chosen) so live vs batch paths are explicit in the YAML, not buried in prompt
2. **Human-in-the-loop clarification node** for ambiguous queries (e.g., scope inferred but not confirmed)
3. **Error handling with explicit retry** using Power Fx conditions on tool-call failures
4. **Observability wiring** — Application Insights tracing + Foundry evaluations with alert rules on quality regressions

Multi-agent orchestration should come later (v5+) when: (a) the agent's tool count exceeds ~10-15 (we have 2), (b) clear domain boundaries emerge (compliance specialist, coaching specialist, campaign specialist), or (c) auditability/compliance forces separation of concerns [7][8]. Connected Agents is the current primary pattern for that future state; A2A Tool is its "structured evolution" and sits at Preview [1][2][3].

This report delivers a concrete v4 YAML + SDK layout, with citations to current Microsoft docs and industry best practices.

---

## 1. Multi-Agent Orchestration Patterns — Where Foundry Stands in April 2026

As of Dec 2025 / Jan 2026, Foundry exposes four distinct orchestration modes [1][2][6]:

**Connected Agents** is the most mature pattern — a primary agent delegates to specialist sub-agents via natural language routing, handling ~80% of multi-agent needs with no custom orchestrator code. Sub-agents appear as tools on the primary; the thread stays coherent. Microsoft's guidance: "the simplest way to break down complex tasks into coordinated, specialized roles" [1][2].

**A2A Tool (Agent2Agent)** is described as *the structured evolution of Connected Agents* [1]. Control flow is call-and-return — Agent A calls Agent B, B's answer returns to A, A synthesizes the final user response [2]. This preserves thread ownership in the orchestrator, which is cleaner for audit and for conversation continuity. A2A is Preview as of April 2026.

**Multi-Agent Workflows** (Foundry's YAML/visual orchestration) differs from Connected Agents in a crucial way: **Agent B takes full ownership of the thread from the point of handoff; Agent A is out of the loop** [2]. This is appropriate for pipelines (document ingest → OCR → summarize → classify), less so for conversational UX.

**Group Chat** is a dynamic pattern where agents pass control based on runtime context (escalation, expert handoff) [11][15].

**Recommendation for Marketing-funnel-test**: stay on single-agent for v4. The key industry finding for your scale: "the most common mistake is jumping to multi-agent architecture before a single well-equipped agent has been properly pushed. There's a practical ceiling on tool count: around 10-15 function tools before the model starts making poor selection decisions" [7]. You have 2 tools. Room to grow.

When to evolve: add specialist agents only when (a) auditability forces separation — e.g., a Compliance agent that the primary must consult for regulated claims, or (b) a specialist has fundamentally different grounding data (a Coaching agent backed by historical-call vector store, not CRM).

## 2. Conditional Branching in Workflow YAML — Push Logic Up or Keep It In Prompt?

Foundry workflows support three logic node types: **if/else**, **go to**, and **for each** [5][11][12]. These compose with **Power Fx expressions** (Excel-like syntax) for conditions. Variables are scoped as `System.*` (conversation metadata) and `Local.*` (workflow-local) [11].

Example if/else with Power Fx:

```yaml
- kind: IfElse
  id: route_by_path
  condition: =Local.ManagerReplyJson.route_chosen == "batch"
  then:
    actions:
      - kind: SendActivity
        activity: "Batch analysis queued. I'll update when the XLSX is ready."
  else:
    actions:
      - kind: SendActivity
        activity: =Local.ManagerReply
```

**The push-up-vs-keep-in-prompt tradeoff:**

- **Keep in prompt** when the decision is *semantic* — intent classification, extracting entities, picking a tool. LLMs outperform deterministic rules for language-level decisions.
- **Push to YAML** when the decision is *structural and audit-critical* — route live vs batch, enforce a human-approval gate before irreversible actions, dispatch to different agents, log different analytics events. These need deterministic behavior and clean traces.

For Marketing-funnel-test, `route_chosen` is currently a field inside `ManagerReply` (decided by the LLM in prompt). Pushing an if/else over it up to YAML makes the behavior explicit in observability traces, which the "From Zero to Hero: AgentOps" guide calls out as critical for production agents [9].

## 3. Human-in-the-Loop Gates — When and How

Microsoft shipped a formalized HITL pattern in Feb 2026 that pairs Azure Durable Functions with Agent Framework and SignalR [6][13]. This is designed for agents that survive restarts and wait days for human approval — overkill for your chat UX. For a chat agent, the lighter-weight options are:

- **Ask-a-question node** inside the workflow — the simplest HITL primitive, suspends the workflow until the user replies in the same conversation [11][12]
- **Branch-then-ask pattern** — if/else detects ambiguity → Ask-a-question asks a clarifier → resumes with the clarified input

Example for Marketing-funnel-test when scope is ambiguous:

```yaml
- kind: IfElse
  id: ambiguity_check
  condition: =Local.ManagerReplyJson.data_gaps && Count(Local.ManagerReplyJson.data_gaps) > 0 && Local.ManagerReplyJson.route_chosen == "refuse"
  then:
    actions:
      - kind: AskAQuestion
        question: "I need more context. What should I analyze — specific ACC IDs, a date range, or a manager name?"
        saveAs: Local.ClarifiedScope
      - kind: InvokeAzureAgent
        agent: {name: Call-analyser-agent}
        input:
          messages: =Concatenate("Original: ", System.LastMessage.Text, " | Clarification: ", Local.ClarifiedScope)
```

Best practice: place HITL gates **only before irreversible or high-cost actions**. For a read-only analyzer like ours, HITL is mostly useful for scope clarification, not for approval-before-action.

## 4. State Management Across Turns — Conversations API vs Local Vars vs Backend

Foundry has moved beyond the thread-based pattern [14]. The current architecture uses the **Conversations API** — durable objects with unique IDs that persist across sessions and store items (messages, tool calls, tool outputs, output items) in Azure Cosmos DB [14][17][19]. The Baseline Foundry Chat Reference Architecture explicitly recommends service-managed conversations for chat history persistence [17].

**Three layers of state, each with a clear purpose:**

| Layer | Lifetime | Scope | Use for |
|-------|----------|-------|---------|
| Conversations API | Persistent (Cosmos-backed) | User conversation | Multi-turn chat history, follow-up queries ("check my analysis") |
| Local.* workflow vars | One workflow run | One response cycle | Passing data between actions in the same turn |
| Backend (Table Storage) | Persistent, external | Batch jobs | Job metadata (job_id → batch_id mapping), longer-than-conversation state |

For Marketing-funnel-test, the right mapping is:
- Use the Conversations API for "I'll update when ready" — user returns, agent re-reads prior ManagerReply from conversation items, extracts job_id, polls backend
- Use `Local.ManagerReplyJson` for in-turn routing (if/else over route_chosen)
- Use Azure Table Storage (per the v3 spec) ONLY for batch job metadata that spans days

The baseline Foundry chat architecture calls out that items (not just chat messages) are stored — tool calls and tool outputs too [14][17]. This means the agent can inspect its own past tool-call history on a follow-up, useful for "what did I tell the user about ACC X last time?".

## 5. Error Handling and Retry Patterns

Microsoft's retry guidance for Foundry agent calls is the standard **exponential backoff with jitter** pattern, max 3 retries, only for transient failures [16]. "Retrying permanent errors just wastes resources and delays error reporting to the caller" [16]. The SDK patterns are:

- `2^attempt * 1000ms` delay with jitter
- Retry on 429 (rate limit), 500, 502, 503, 504
- Do NOT retry on 400, 401, 403, 404, 422 (client-side errors — our CRM 422 "mixed modes" is one of these)

Inside the workflow YAML, error handling is limited — workflows don't expose per-action retry directly. The current pattern is:
- Put retry logic in the backend HTTP layer (the Function App we're planning) for deterministic failures
- Put semantic retry (rephrase query, try a different tool) in the agent prompt
- Use if/else in YAML to branch on `Local.*` sentinels (e.g., error_code) when the agent explicitly surfaces failure

For the v4 workflow, the simplest improvement is to check `Local.ManagerReplyJson.route_chosen == "refuse"` and route to a friendly error SendActivity instead of surfacing raw error JSON.

## 6. Observability and Evaluation Integration

Evaluations, Monitoring, and Tracing in Microsoft Foundry are **generally available as of March 2026** through the Foundry Control Plane [6][18]. The integration points:

**Tracing** [9][19]: captures inputs, outputs, tool usage, retries, latencies, and costs per agent run. Accessible in the Foundry portal and in Azure Monitor Application Insights. Enable via a one-line toggle per project.

**Continuous evaluation** [6][18]: sampled live traffic is auto-evaluated, metrics surfaced over time. Evaluators run at three lifecycle stages:
- Local development (inline during iteration)
- CI/CD pipelines (gate PRs against quality baselines)
- Production traffic monitoring (continuous sampling)

**Alert rule wiring** [6]: Azure Monitor alert rules can trigger on evaluation metrics. Example: "PagerDuty incident when groundedness drops below 0.75" or "Teams notification when safety violations spike." This is the production gate we need.

**GitHub Action integration** [10]: run evaluations on every PR to the stage branch, block merge if thresholds fail.

For Marketing-funnel-test v4, the evaluation integration should be:
1. Wire Application Insights tracing on the `brn-azai` Foundry project (enable in portal)
2. Run the 40-row silver dataset (next task) through `azure-ai-evaluation.evaluate()` with 5 built-in + 4 custom evaluators, push results to Foundry portal via `azure_ai_project=` argument
3. Set up a continuous eval sampling rule (5% of production traffic) with alert thresholds: intent ≥ 0.80, tool_call ≥ 0.85, custom route_selection ≥ 0.95
4. Add a GitHub Action that runs evals on every PR to stage and blocks merge on failure [10]

## 7. Production Deployment Lifecycle — Versioning, Canary, Rollback

Foundry provides built-in versioning (every save creates a new immutable version) and publishing [21][22]. The lifecycle pattern for agents [22]:

1. Save changes as versions — meaningful milestones
2. Evaluate each version — repeatable eval runs to catch regressions
3. Publish a stable endpoint — the "production" pointer
4. Monitor in production — traces, metrics, continuous eval
5. Update and republish — iterate without disrupting consumers

**Canary deployment** is explicitly supported: route 5-10% of traffic to the new version while monitoring error rate, latency, user satisfaction, and cost. Automatic rollback if any metric degrades beyond threshold [23].

**Rollback mechanism**: because each save is a snapshot, you can direct requests to a specific version (e.g., v69 instead of v71) to revert [24]. This is safer than prompt-patching a live agent.

**Architectural tip from MS** [23]: design for version coexistence — baseline and candidate deployments — so cutover and rollback don't require code redeployments. For our workflow, this means:
- Keep Call-analyser-agent v69 (scoring-only) as the rollback target
- Deploy v71+ (unified manager) as the new production version
- If v71 misbehaves, Foundry portal click → "publish v69 as production" restores old behavior

**Feature flags**: CIO guidance [24] emphasizes that agent versioning is more than prompt versioning — it includes schema changes, tool additions, model swaps. Each needs to be testable in isolation. The safe cutover rhythm is: version → eval gate → canary → full rollout, ~1-2 week cadence for minor changes.

For Marketing-funnel-test v4:
- Tag v4 as a new major version (we're at workflow v3, jump to v4)
- Run eval gate against the 40-row dataset
- Deploy as canary (portal-level publish at 10% traffic)
- Monitor for 48h — if groundedness and route_selection hold, promote to 100%

## 8. Single Fat Agent vs Orchestrator + Specialists — Your Current Decision

The decisive finding [4][7][8]:

**Stay with a single agent until you hit one of these triggers:**
- Tool count > 10-15 (LLMs degrade in tool selection past this)
- Clear domain boundaries emerge (compliance vs coaching vs campaign vs risk)
- Auditability forces separation (regulators want a distinct, separately-evaluated Compliance agent)
- A sub-task has fundamentally different grounding data (e.g., Coaching agent needs a vector store of historical calls that the main agent shouldn't see)

**Cost signal** [7]: a 4-agent sequential pipeline uses ~4× the tokens of a single agent. Don't multiply agents until the benefits justify the cost.

For your Marketing-funnel-test today (2 tools, single domain, no regulatory gate): **single-agent is correct**. The v4 improvements in this report (branching, HITL, observability, eval) lift the ceiling of what a single agent can deliver.

When to revisit: after Olson-Funnel re-wires (+Windsor tool), ONE-SIGNAL re-wires (+push tool), Compliance gate lands. If that brings the tool count to 8+ and introduces a regulatory specialist, that's the moment to split.

---

## Synthesis & Insights — The SOTA v4 Design

**Marketing-funnel-test v4** (proposed):

```yaml
kind: workflow
name: Marketing-funnel-test
trigger:
  kind: OnConversationStart
  id: trigger_wf
  actions:
    - kind: InvokeAzureAgent
      id: mgr_invoke
      agent: {name: Call-analyser-agent}
      input:
        messages: =System.LastMessage.Text
      output:
        autoSend: false
        messages: Local.ManagerReply
        responseObject: Local.ManagerReplyJson

    - kind: IfElse
      id: route_dispatch
      condition: =Local.ManagerReplyJson.route_chosen == "refuse"
      then:
        actions:
          - kind: AskAQuestion
            question: "I need more context to help. Please provide specific ACC IDs, an email, or a date range."
            saveAs: Local.ClarifiedScope
          - kind: InvokeAzureAgent
            id: mgr_retry
            agent: {name: Call-analyser-agent}
            input:
              messages: =Concatenate(System.LastMessage.Text, " | Clarification: ", Local.ClarifiedScope)
            output:
              autoSend: false
              messages: Local.ManagerReply
      else:
        actions: []

    - kind: IfElse
      id: batch_path_message
      condition: =Local.ManagerReplyJson.route_chosen == "batch"
      then:
        actions:
          - kind: SendActivity
            activity: =Concatenate("Batch queued: ", Local.ManagerReplyJson.job_id, ". Ask 'check my analysis' when you want the results.")
      else:
        actions:
          - kind: SendActivity
            activity: =Local.ManagerReply
```

**Enhancements over v3:**
1. **Refusal → clarification retry** (Section 3 HITL pattern)
2. **Live vs batch path branching** in YAML, not in agent narrative (Section 2 + 5)
3. **Explicit message crafting** for batch case — surfaces job_id to user predictably

**Out of scope for v4 (deferred to v5):**
- Connected Agents / A2A — not yet needed with 2 tools
- Durable Functions HITL — overkill for chat
- Multi-agent group chat — no clear specialist boundaries yet

**Parallel infrastructure work for v4:**
- Enable Application Insights tracing on `brn-azai` (1 toggle in portal)
- Set up Azure Monitor alert rule: `groundedness < 0.75 → Teams notification`
- Run the 40-row eval dataset (next task #31-32) via `azure-ai-evaluation.evaluate()` with `azure_ai_project=` arg → results to Foundry portal
- Wire GitHub Action to gate PRs to stage on eval thresholds

## Limitations & Caveats

- A2A Tool is Preview as of April 2026 — API may change before GA [1][3]. Do not adopt until stable.
- Multi-Agent Workflows preview since Nov 2025 [25] — evolving. Our YAML syntax may need migration.
- Foundry docs reference **Agent Framework 1.0**, but some samples still use Semantic Kernel or AutoGen primitives. Confirm which surface you're building against [4][7].
- "Durable Agent Orchestration" (Feb 2026) is overkill for chat — reserve for tool-heavy, days-long workflows with approvals [6].

## Recommendations — Apply to v4 Workflow

1. **KEEP** single-agent architecture. Do not split into multi-agent until tool count > 10 or a regulatory boundary emerges.
2. **ADD** IfElse branching on `Local.ManagerReplyJson.route_chosen` to make routing observable in traces.
3. **ADD** an AskAQuestion node for the `route_chosen == "refuse"` path — clarify scope, retry agent once.
4. **ENABLE** Application Insights tracing on `brn-azai` project this week.
5. **WIRE** `azure-ai-evaluation.evaluate()` with 5 built-in + 4 custom evaluators, push to Foundry portal, gate CI on thresholds.
6. **SET UP** continuous evaluation sampling (5% of prod traffic) with Azure Monitor alerts.
7. **PLAN** a canary cutover from v3 → v4 at 10% traffic, 48h bake, then full rollout.
8. **DOCUMENT** when to split to multi-agent — predefined triggers (tool count, domain boundary, regulatory gate) so the team doesn't split prematurely.

---

## Bibliography

[1] Microsoft. "What's new in Microsoft Foundry | Dec 2025 & Jan 2026." *Microsoft Foundry Blog*. https://devblogs.microsoft.com/foundry/whats-new-in-microsoft-foundry-dec-2025-jan-2026/

[2] Microsoft. "Add an A2A agent endpoint to Foundry Agent Service." *Microsoft Learn*. https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/agent-to-agent?view=foundry

[3] Microsoft. "Agent Factory: Connecting agents, apps, and data with new open standards like MCP and A2A." *Microsoft Azure Blog*. https://azure.microsoft.com/en-us/blog/agent-factory-connecting-agents-apps-and-data-with-new-open-standards-like-mcp-and-a2a/

[4] Microsoft. "Introducing Microsoft Agent Framework." *Microsoft Azure Blog*. https://azure.microsoft.com/en-us/blog/introducing-microsoft-agent-framework/

[5] Microsoft. "Build a workflow in Microsoft Foundry." *Microsoft Learn*. https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/workflow

[6] Microsoft. "Microsoft Foundry Observability Generally Available." *TechCommunity Azure AI Foundry Blog*. https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/generally-available-evaluations-monitoring-and-tracing-in-microsoft-foundry/4502760

[7] Microsoft. "AI Agent Orchestration Patterns." *Azure Architecture Center*. https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns

[8] The Power Platform Cave. "AI Agent Architecture Patterns on the Microsoft Stack." https://www.thepowerplatformcave.com/agent-architecture-patterns-microsoft-foundry-fabric/

[9] Microsoft. "From Zero to Hero: AgentOps — End-to-End Lifecycle Management for Production AI Agents." *TechCommunity*. https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/from-zero-to-hero-agentops---end-to-end-lifecycle-management-for-production-ai-a/4484922

[10] Microsoft. "How to run an evaluation in GitHub Action." *Microsoft Learn*. https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/evaluation-github-action

[11] Microsoft. "Orchestrating Multi-Agent Conversations with Microsoft Foundry Workflows." *TechCommunity*. https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/orchestrating-multi-agent-conversations-with-microsoft-foundry-workflows/4472329

[12] Microsoft Learning. "Build a workflow in Microsoft Foundry" (hands-on lab). https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/08-build-workflow-ms-foundry.html

[13] Microsoft. "Building Human-in-the-loop AI Workflows with Microsoft Agent Framework." *TechCommunity*. https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/building-human-in-the-loop-ai-workflows-with-microsoft-agent-framework/4460342

[14] Microsoft. "Build with agents, conversations, and responses in Foundry Agent Service." *Microsoft Learn*. https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components

[15] Microsoft. "Introducing Multi-Agent Orchestration in Foundry Agent Service." *TechCommunity*. https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/building-a-digital-workforce-with-multi-agents-in-azure-ai-foundry-agent-service/4414671

[16] OneUptime. "How to Use the Retry Pattern with Exponential Backoff in Azure Applications." https://oneuptime.com/blog/post/2026-02-16-how-to-implement-the-retry-pattern-with-exponential-backoff-in-azure-applications/view

[17] Microsoft. "Baseline Microsoft Foundry Chat Reference Architecture." *Azure Architecture Center*. https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/baseline-microsoft-foundry-chat

[18] Microsoft. "Evaluating Generative AI Models Using Microsoft Foundry's Continuous Evaluation Framework." *TechCommunity*. https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/evaluating-generative-ai-models-using-microsoft-foundry%E2%80%99s-continuous-evaluation-/4468075

[19] Microsoft. "Agent tracing in Microsoft Foundry (preview)." *Microsoft Learn*. https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-agent-concept

[20] Microsoft. "Microsoft Agent Framework Multi-Turn Conversations." *Microsoft Learn*. https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/multi-turn-conversation

[21] Microsoft. "Agent development lifecycle." *Microsoft Learn*. https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/development-lifecycle

[22] Microsoft. "What is Microsoft Foundry Agent Service?" *Microsoft Learn*. https://learn.microsoft.com/en-us/azure/foundry/agents/overview

[23] Microsoft. "Model Upgrade and Migration Strategy for Microsoft Foundry." *TechCommunity*. https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/model-upgrade-and-migration-strategy-for-microsoft-foundry/4503176

[24] CIO.com. "Why versioning AI agents is the CIO's next big challenge." https://www.cio.com/article/4056453/why-versioning-ai-agents-is-the-cios-next-big-challenge.html

[25] Microsoft. "Introducing Multi-Agent Workflows in Foundry Agent Service." *Microsoft Foundry Blog*. https://devblogs.microsoft.com/foundry/introducing-multi-agent-workflows-in-foundry-agent-service/

## Methodology Appendix

- **Mode:** Standard (6 phases: SCOPE, PLAN, RETRIEVE, TRIANGULATE, SYNTHESIZE, PACKAGE)
- **Retrieval:** 8 parallel WebSearch queries targeting MS Learn, devblogs, TechCommunity, industry tech blogs
- **Triangulation:** Each of the 8 research questions cross-referenced against ≥2 sources (most ≥3)
- **Source credibility:** Primary sources are Microsoft Learn, devblogs.microsoft.com, and techcommunity.microsoft.com (first-party). Secondary: CIO, industry tech blogs, Medium for real-world case studies.
- **Time window:** April 2026 baseline; sources from Dec 2025 - April 2026
- **Scope adjustments:** Did not retrieve Code samples / GitHub repos beyond search hit titles — a follow-up research pass could pull `microsoft/agent-framework` samples directly for deeper YAML/SDK examples.
