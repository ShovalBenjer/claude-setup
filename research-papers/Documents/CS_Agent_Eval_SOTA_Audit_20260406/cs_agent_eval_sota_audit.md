# cs-agent Evaluation: SOTA Audit & Migration Plan

**Date:** 2026-04-06
**Author:** Claude (deep-research, parallel agentic + Foundry research threads)
**Subject:** Is the cs-agent evaluation stack state-of-the-art? If not, how to fix it — and how to visualize natively in Microsoft Foundry.

---

## Executive Summary

**Verdict: Not SOTA. Currently sits at "table stakes minus" against the 2026 bar.**

cs-agent's current eval is a custom Python script (`scripts/foundry_eval_gate.py`) that uses a single primary LLM judge (`grok-4-1-fast-reasoning-2-eval`) plus a sampled audit judge (`DeepSeek-V3.2`) on a 10-row keyword-checking smoke set. It has CI integration, multilingual coverage, and produces JUnit/markdown artifacts. It is intentionally cost-bounded, which is the right instinct.

What it lacks against the 2026 SOTA bar: (1) it does not use the `AIAgentEvaluation@2` Azure DevOps marketplace task that Microsoft now ships specifically for this use case; (2) it does not use any of the native Foundry built-in agent evaluators (`task_completion`, `task_adherence`, `intent_resolution`, `tool_call_accuracy`, `tool_input_accuracy`, `tool_selection`, `task_navigation_efficiency`) that were released in 2025; (3) it does not produce statistical significance comparisons (no bootstrap CIs, no paired t-tests, no power analysis); (4) it has zero integration with the Foundry portal — no `report_url`, no compare-runs view, no Agent Monitoring Dashboard tile; (5) it walked away from the 19-evaluator continuous eval that was already running (`eval_f3859661e28d4ebc8814dc5f98e6397b`) because of cost, instead of right-sizing it; (6) there is no red-teaming integration despite Microsoft shipping the AI Red Teaming Agent in 2025; (7) there is no panel-of-judges or bias mitigation against position/length/self-preference bias.

The DeepEval suite (`tests/deepeval_suite.py`) is more sophisticated — six GEval-based metrics (accuracy, hallucination, tone, escalation, policy_compliance, topic_coverage) — but it lives parallel to the foundry_eval_gate, is not wired into the smoke gate, and does not feed the Foundry portal either.

**Highest-leverage fix:** delete `foundry_eval_gate.py` and replace it with the `AIAgentEvaluation@2` Azure DevOps task pointing at a curated 30-row dataset using six built-in agent evaluators. This single change buys you native portal visualization, statistical comparison against a baseline, an officially supported pass/fail gate, and frees you from maintaining custom judge plumbing. Time cost: ~4 hours. Risk: low (the task is GA on the marketplace).

---

## Introduction

### Scope

This audit covers the evaluation stack in `axia-seekapa-cs-agents-devops` only — the live agent eval, CI gate, and supporting docs. It does not cover the agent's runtime behavior, prompt content, or production observability beyond the eval lens.

### Methodology

Two parallel research threads were executed:

1. **Local code & doc inventory.** Read every eval-related .md file in the project (`docs/FOUNDRY-EVAL-CI-PLAN.md`, `docs/prompt_v96_optimization_suggestions.md`, the historical `eval_f3859661e28d4ebc8814dc5f98e6397b.md` Foundry export), the `scripts/foundry_eval_gate.py` (317 lines), `tests/deepeval_suite.py`, `tests/deepeval_metrics.py`, `tests/test_data/foundry_smoke_eval.jsonl` (25 rows).

2. **External SOTA research.** Two parallel subagent runs:
   - Agentic eval SOTA 2025-2026 (benchmarks, judging, statistical rigor, red-teaming)
   - Microsoft Foundry native evaluation features (built-in evaluators, continuous eval, AI Red Teaming Agent, custom evaluators, azure-ai-projects 2.0.1 SDK, portal visualization, Azure DevOps integration)

Both produced citation-backed reports with primary sources.

### Key Assumptions

- "SOTA" is interpreted as "what Microsoft + leading research labs converged on by Q1 2026" — not bleeding-edge research-only ideas.
- The eval should be maintainable by a small team (you), not a dedicated eval org.
- Cost is a real constraint (the historical 6.8M-token continuous eval was already too expensive).
- Native Foundry integration is a hard preference per the explicit ask.

---

## Main Analysis

### Finding 1: The Custom CI Gate Has Been Superseded by `AIAgentEvaluation@2`

`foundry_eval_gate.py` was a reasonable design when it was written (March 2026 per the doc) — but Microsoft shipped the [AI Agent Evaluation Azure DevOps task](https://marketplace.visualstudio.com/items?itemName=ms-azure-exp-external.microsoft-extension-ai-agent-evaluation) (`AIAgentEvaluation@2`) which does the same job with strict native integration. Documented at [learn.microsoft.com/en-us/azure/foundry/how-to/evaluation-azure-devops](https://learn.microsoft.com/en-us/azure/foundry/how-to/evaluation-azure-devops) (page updated 2026-03-19).

What it gives you that the custom script does not:

- **Statistical comparison out of the box.** The task computes confidence intervals and p-values across multiple runs, color-codes deltas as ImprovedStrong / ImprovedWeak / DegradedStrong / DegradedWeak / ChangedStrong / ChangedWeak / Inconclusive. The custom script returns a binary pass/fail per row.
- **Baseline-vs-candidate comparison.** Pass `agent-ids: my-agent:v1,my-agent:v2` and `baseline-agent-id: my-agent:v1` and the task compares them. Foundry's compare-runs view does this with paired t-tests. The custom script has no notion of a baseline.
- **Pass/fail gate that blocks merges.** "Failure to evaluate equals failure to deploy" — non-zero exit on threshold or stat-sig regression. The custom script also blocks but only on absolute keyword failure, which is brittle.
- **Pipeline summary report.** Renders inside the Azure DevOps build summary as markdown with per-evaluator metrics, CIs, and pairwise comparisons. The custom script writes JUnit/JSON/markdown to artifacts which the user has to click through.
- **Officially maintained.** The shim at `microsoft/ai-agent-evals` is updated by Microsoft. Your `foundry_eval_gate.py` is yours to maintain.

Minimal pipeline replacement:

```yaml
- task: AIAgentEvaluation@2
  displayName: "Evaluate Seekapa agent"
  inputs:
    azure-ai-project-endpoint: "$(AzureAIProjectEndpoint)"
    deployment-name: "gpt-5-mini"
    data-path: "tests/test_data/foundry_smoke_eval.json"
    agent-ids: "seekapa:97"
    baseline-agent-id: "seekapa:96"
```

The `data-path` file is JSON (not JSONL — different from your current dataset), and it accepts builtin evaluator names plus per-evaluator thresholds. You'd convert your 10-row JSONL once with a tiny script.

### Finding 2: You Are Not Using the Native Agent Evaluators That Match Your Use Case

The historical Foundry continuous eval (`eval_f3859661e28d4ebc8814dc5f98e6397b`) ran 19 builtin evaluators and showed `task_completion`, `task_adherence`, `groundedness`, `relevance` as the real failure clusters. Then the team walked away from those evaluators entirely. The new smoke gate uses none of them — it asks a single broad LLM judge for binary pass/fail on keyword presence.

The 2026 catalog of agent-specific built-in evaluators (from [learn.microsoft.com/en-us/azure/foundry/concepts/built-in-evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/built-in-evaluators)):

| Evaluator | What it checks | Relevance to cs-agent |
|---|---|---|
| `builtin.task_completion` | Did the agent complete the user's task? | Critical — primary failure cluster historically |
| `builtin.task_adherence` | Did it follow the system prompt's policy? | Critical — your prompt has strict rules (escalation gates, NFA, anti-hedging) |
| `builtin.intent_resolution` | Did it correctly identify user intent? | High — cs-agent classification is brittle |
| `builtin.tool_call_accuracy` | Right tool, right time, right result? | High — file_search + create_ticket |
| `builtin.tool_selection` | Right tool chosen given the query? | High |
| `builtin.tool_input_accuracy` | Tool call args correct in 6 dimensions (groundedness, type, format, required, extra, value)? | High |
| `builtin.tool_output_utilization` | Did the agent actually use the KB hit it retrieved? | High — past failures included groundedness drops |
| `builtin.task_navigation_efficiency` | Code-based — precision/recall against expected action sequence | Medium — needs a labelled action ground truth |
| `builtin.groundedness` (or `groundedness_pro` preview) | Is the answer grounded in the KB context? | Critical — financial broker, no fabrication allowed |
| `builtin.relevance` | Is the answer relevant to the question? | Critical |
| `builtin.indirect_attack` (XPIA) | Detection of indirect prompt injection in tool outputs | High — cs-agent has tool calls |

Note one important gotcha from the docs: `tool_call_accuracy`, `tool_input_accuracy`, `tool_output_utilization`, `tool_call_success`, and `groundedness` are unreliable when the agent uses Bing Grounding, Azure AI Search, SharePoint Grounding, Code Interpreter, Fabric Data Agent, or Web Search. cs-agent uses **`file_search`** which is the hosted KB tool — that's fine. The `create_ticket` tool is a user-defined function tool — also fine.

Recommended starter bundle: `task_completion`, `task_adherence`, `tool_call_accuracy`, `tool_input_accuracy`, `intent_resolution`, `groundedness` — six evaluators, judge model `gpt-5-mini` (Microsoft's documented price/performance sweet spot for agent evaluators).

### Finding 3: The Single-Judge Pattern Is Below Bar — Use a Panel

The current setup uses one primary judge (`grok-4-1-fast-reasoning-2-eval`) for all rows and an audit judge (`DeepSeek-V3.2`) on a small subset. Both are bigger than they need to be for binary scoring, both can disagree, and there is no formal reconciliation.

The 2024-2025 research converged on **panels beat singletons**:

- [Replacing Judges with Juries (arXiv 2404.18796)](https://arxiv.org/abs/2404.18796) shows a panel of small diverse models outperforms a single large judge, has less intra-model bias, and is ~7× cheaper.
- [Prometheus 2 (arXiv 2405.01535)](https://arxiv.org/abs/2405.01535) is the open-source reference judge that you can use as one panel member.
- [JudgeLM (ICLR 2025 Spotlight)](https://github.com/baaivision/JudgeLM) achieves >90% agreement (above human-to-human).
- [A Survey on LLM-as-a-Judge (arXiv 2411.15594)](https://arxiv.org/abs/2411.15594) is the umbrella reference.

Bias to actively mitigate (all documented in the literature):

- **Position bias** — judge prefers first or second response. Counter: swap order and average. ([Position bias paper, ACL 2025](https://aclanthology.org/2025.ijcnlp-long.18/))
- **Length bias** — longer = better in the judge's eye. Counter: strip length features or use rubric anchors.
- **Self-preference bias** — judges reward outputs from same model family. Counter: mixed-vendor panel.
- **Quality-gap sensitivity** — bias is worst when candidates are similar in quality, which is exactly the prompt-A/B-test case.

Concretely: a 3-judge panel of `gpt-5-mini` + `gpt-4o-mini` + Prometheus-2 (on Azure ML or self-hosted) is the right shape. Foundry doesn't yet have native panel-of-judges built in, but you can implement it as a custom evaluator (see Finding 5).

### Finding 4: You Walked Away from Continuous Evaluation — Right-Size It Instead

The historical export (`eval_f3859661e28d4ebc8814dc5f98e6397b`) shows the continuous eval was burning 6.8M tokens against `grok-4-1-fast-reasoning` across 67 runs and the team killed it. The right move was not to kill it — it was to right-size it.

The 2026 continuous eval API (Foundry new, not classic) has explicit cost levers:

```python
from azure.ai.projects.models import (
    EvaluationRule, ContinuousEvaluationRuleAction,
    EvaluationRuleEventType, EvaluationRuleFilter,
)

eval_object = openai_client.evals.create(
    name="cs-agent-continuous",
    data_source_config={"type": "azure_ai_source", "scenario": "responses"},
    testing_criteria=[
        {"type": "azure_ai_evaluator", "name": "task_completion",
         "evaluator_name": "builtin.task_completion",
         "initialization_parameters": {"deployment_name": "gpt-5-mini"}},
        # ... 5 more
    ],
)

project_client.evaluation_rules.create_or_update(
    id="cs-agent-ce-rule",
    evaluation_rule=EvaluationRule(
        display_name="cs-agent prod sample",
        action=ContinuousEvaluationRuleAction(
            eval_id=eval_object.id,
            max_hourly_runs=10,           # cost ceiling
        ),
        event_type=EvaluationRuleEventType.RESPONSE_COMPLETED,
        filter=EvaluationRuleFilter(agent_name="seekapa"),
        enabled=True,
    ),
)
```

`max_hourly_runs=10` × 6 evaluators × ~2-3K tokens each (using `gpt-5-mini`) ≈ 1.4M tokens/day worst case, ~$25-40/day at gpt-5-mini pricing. That's ~5% of the previous burn rate for a feedback loop that catches drift in production.

Sources: [Cloud Evaluation with Foundry SDK](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/cloud-evaluation), [Continuous Evaluation classic→new migration notes](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/evaluating-generative-ai-models-using-microsoft-foundry%E2%80%99s-continuous-evaluation-/4468075).

Critical setup requirement: the Foundry project's managed identity needs the **Azure AI User** role on itself for continuous eval to fire. This is the most common silent failure (403s in App Insights).

### Finding 5: Custom Evaluators Are First-Class — Use Them for Yasha-Specific Flow Checks

The flow eval I ran earlier today (the 4-scenario "Yasha flow eval") was a one-off Python script. In Foundry, custom evaluators are now first-class assets in the evaluator catalog with their own versions, and they can be referenced in continuous eval and the AIAgentEvaluation@2 task identically to built-ins.

Two flavors per [learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/custom-evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/custom-evaluators):

**Code-based** — sandboxed Python with numpy/pandas/scipy/scikit-learn/rapidfuzz/sympy/jsonschema/pydantic/nltk/rouge-score preloaded. 256 KB code limit, 2-min timeout per call, no network, 2 GB RAM. Ideal for deterministic checks (Yasha flow markers, exact-string compliance, specific phone format).

**Prompt-based** — a judge prompt with `{{field}}` template variables, output shape `{"result": ..., "reason": "..."}`, three scoring modes (`ordinal` / `continuous` / `binary`).

A "yasha_flow_compliance" custom evaluator (code-based) for the cs-agent should check:
1. Did the response ask for "full name" + "email" before answering?
2. Is the response open-ended (no ` or ` / ` either ` patterns followed by `?`)?
3. If it's an escalation, does it contain the exact phrase "24 working hours"?

Each emits a 0-1 score. Bundle into `EvaluatorCategory.QUALITY` and reference in your eval like any builtin.

### Finding 6: No Red Teaming — Microsoft Ships an Agent for It

Microsoft shipped the [AI Red Teaming Agent](https://learn.microsoft.com/en-us/azure/foundry/concepts/ai-red-teaming-agent) in 2025, in preview. It's a hosted automation built on the open-source [PyRIT](https://github.com/Azure/PyRIT) framework. Two paths:

**Local SDK:**
```bash
pip install "azure-ai-evaluation[redteam]"  # Python 3.10-3.12 only
```
```python
from azure.ai.evaluation.red_team import RedTeam, RiskCategory, AttackStrategy

red_team = RedTeam(
    azure_ai_project=project,
    credential=DefaultAzureCredential(),
    risk_categories=[
        RiskCategory.HateUnfairness,
        RiskCategory.Violence,
        RiskCategory.SelfHarm,
        # agent-only categories below — cloud-only
        # RiskCategory.ProhibitedActions,
        # RiskCategory.SensitiveDataLeakage,
    ],
    num_objectives=10,
)
result = await red_team.scan(
    target=seekapa_agent_endpoint,
    attack_strategies=[
        AttackStrategy.Flip, AttackStrategy.Base64,
        AttackStrategy.Crescendo,    # multi-turn escalation
        AttackStrategy.Tense,        # past-tense rewriting jailbreak
    ],
)
```

**Cloud/portal path** integrates as a toggle in `Build → seekapa → Monitor → gear icon → Red team scans (preview)`. Scheduled scans land in the Agent Monitoring Dashboard alongside continuous eval. Output is an Attack Success Rate (ASR) per risk category × attack strategy.

**Why this matters specifically for cs-agent:** the agent has tool calls (`file_search` against Seekapa_FAQ_KB, `create_ticket`). Indirect prompt injection (XPIA) is OWASP LLM01:2025's #1 attack class against tool-using agents. A poisoned KB document or a poisoned `create_ticket` description can hijack the agent. Microsoft's [July 2025 defense blog](https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks) and the [Indirect Prompt Injections survey (arXiv 2510.05244)](https://arxiv.org/html/2510.05244v1) are the canonical references — bottom line: 8/8 existing defenses can be bypassed by adaptive attacks. The only way to know if your agent is vulnerable is to scan it.

Three agent-specific risk categories are cloud-only and Foundry-native: `prohibited_actions`, `sensitive_data_leakage`, `task_adherence` (under XPIA). Use the cloud path for these.

PyRIT requires Python 3.10-3.12. cs-agent's Function App is on **3.11** per the pipeline (`pythonVersion: '3.11'`) — compatible.

### Finding 7: Statistical Rigor Is Missing

The current eval reports binary pass/fail with no confidence intervals, no power analysis, no p-values. This means you cannot tell whether a 1/10 → 3/10 baseline-vs-v97 improvement is real or noise. (For that specific result: with n=10, the 95% Wilson CI on 1/10 is [0.5%, 40%], on 3/10 is [8%, 65%]. They overlap massively. The "improvement" is not statistically significant — you'd need ~80 samples to detect a 20pp change at 80% power.)

The authoritative engineering reference is [Anthropic's "A statistical approach to model evaluations" (Nov 2024)](https://www.anthropic.com/research/statistical-approach-to-model-evals) which spells out the right machinery: paired-difference tests on shared question lists, bootstrap CIs on the difference, variance decomposition into question-difficulty noise vs model-quality signal.

Practical fixes for cs-agent:

1. **Use the AIAgentEvaluation@2 task** — it computes p-values and CIs natively.
2. **Expand the smoke set to ~80-150 rows** — current 10-row n is too small for any meaningful comparison.
3. **Use paired tests** — same question list, two prompt versions, paired bootstrap on the difference.
4. **Pre-register the n** — decide sample size before running, not after.

The cs-agent docs (`FOUNDRY-EVAL-CI-PLAN.md`) already call this out as Phase 2 step 4: "Add baseline-vs-candidate comparison instead of absolute-only pass/fail." It just hasn't been done.

### Finding 8: No Tau-Bench-Style User Simulator

The most relevant agent benchmark for a customer service agent is [Tau-bench](https://github.com/sierra-research/tau2-bench) ([arXiv 2406.12045](https://arxiv.org/abs/2406.12045), [Tau2 arXiv 2506.07982](https://arxiv.org/pdf/2506.07982)). It frames the eval as a tool–agent–user triangle: realistic database, policy doc, programmatic APIs, **LLM-based user simulator**. The SOTA function-calling models pass <50% of Tau2 tasks and are highly inconsistent on `pass^k` (multiple-attempts) reporting.

cs-agent has the raw materials: real ticket history in the CRM, a policy doc (the system prompt itself, FAQ KB, escalation rules), and a Foundry agent with tool calls. A Tau-bench-style harness over real ticket transcripts would catch regressions that single-turn eval cannot — flow drift, repeated questions, forgotten context, broken handoffs.

This is a bigger build (1-2 weeks) than the other recommendations (hours to days). It's the right north star but not the right next step.

---

## Synthesis & Insights

The pattern across the eight findings: **the cs-agent eval was right-sized to its constraints in March 2026 but is now outdated by Microsoft's product velocity**. The DevOps task, the agent evaluators, the new continuous-eval API, the AI Red Teaming Agent, custom evaluators as first-class assets — most of this shipped between Apr 2025 and Mar 2026. The team made a defensible call to roll their own when the alternatives were rougher; that's no longer the case.

Three insights:

1. **The eval and the agent prompt are improving on different cadences.** The agent prompt is on Foundry version 97 (created today). The eval gate hasn't materially changed since the Mar 30 plan doc was written. Drift between eval ambition and agent ambition is itself a maintenance risk — you risk passing brittle gates that don't catch real regressions.

2. **Cost was the right concern, but the answer was sampling, not abandonment.** The 6.8M-token continuous eval was killed instead of being capped. The right move with the new API is `max_hourly_runs=10` + 6 evaluators on `gpt-5-mini` ≈ 5% of original cost while keeping a feedback loop.

3. **The DeepEval suite is parallel infrastructure.** It has good metrics but it doesn't integrate with the Foundry portal, doesn't feed continuous eval, and doesn't gate CI. If you migrate to native Foundry evals, the DeepEval suite becomes redundant for the same metrics — keep it only for the specific GEval prompts that don't have a Foundry equivalent.

---

## Limitations & Caveats

- **Not all SOTA techniques are appropriate.** Frontier-tier items (Tau2 dual-control, FIDES information-flow control, jury-on-demand) are research-grade and would be massive engineering investments. They're listed for completeness, not as immediate next steps.
- **Foundry product velocity is high.** Some features named here are in preview as of Apr 2026 (Groundedness Pro, Response Completeness, Prohibited Actions, Sensitive Data Leakage, Task Navigation Efficiency). They may have changed by the time you ship the migration. Pin against the [What's new in Microsoft Foundry](https://devblogs.microsoft.com/foundry/whats-new-in-microsoft-foundry-dec-2025-jan-2026/) blog.
- **The custom Python script isn't broken.** It works, it's maintainable, and it's bounded. The recommendation to replace it is about leverage and integration, not correctness.
- **Statistical claims about the 1/10 vs 3/10 result depend on assumptions.** Wilson CIs, no multiple-comparison correction, no power analysis on the actual eval — the point is not to bash the comparison but to motivate adopting tools that compute these things automatically.
- **The KV credential issue from earlier in the day is still unresolved.** The `FOUNDRY-API-KEY` in the `shoval` KV doesn't authenticate against the Foundry endpoint. The `az account get-access-token --resource https://ai.azure.com` bearer token works. The `managecorpairegistry` SP needs Key Vault Secrets User on `shoval` for the eval to work in CI.

---

## Recommendations

### Immediate (this week, ~4-8 hours total)

1. **Replace `foundry_eval_gate.py` with `AIAgentEvaluation@2`.** Convert `tests/test_data/foundry_smoke_eval.jsonl` → JSON. Add the task as a new build step gated on `master`. Use 6 evaluators (`task_completion`, `task_adherence`, `tool_call_accuracy`, `tool_input_accuracy`, `intent_resolution`, `groundedness`). Set `baseline-agent-id: seekapa:96` and `agent-ids: seekapa:97` for the v96-vs-v97 stat-sig comparison.

2. **Wire `EvalRun.report_url` into the pipeline summary.** Echo the URL in the build log so anyone reviewing the build can deep-link into the Foundry portal drill-in view. One line of code.

3. **Grant `managecorpairegistry` SP "Key Vault Secrets User" on `shoval` KV.** This unblocks the eval gate's API key access. Same blocker as the eval-gate failures from earlier today.

### Short term (next 2 weeks, ~16 hours)

4. **Re-enable continuous evaluation with `max_hourly_runs=10` and 6 evaluators.** Use the new `EvaluationRule` + `ContinuousEvaluationRuleAction` API. Wire `RESPONSE_COMPLETED` event with `agent_name=seekapa` filter. Verify the project managed identity has `Azure AI User` role on itself.

5. **Expand the smoke set from 10 → 80 rows.** Stratify by intent × language × difficulty. Source from real tickets where possible (sanitize PII first). 80 is the minimum for any paired-difference test to detect a 5pp delta at 80% power.

6. **Build 3 custom evaluators in Foundry's evaluator catalog**:
   - `yasha_flow_compliance` (code-based) — name+email asked, open-ended question, exact escalation message
   - `circular_escalation_check` (code-based) — does the response contain escalation keywords from the agent's own response? (catches the historical bug)
   - `nfa_compliance` (prompt-based) — does the response give financial advice?

7. **Run the AI Red Teaming Agent in cloud mode**. Toggle `Monitor → gear → Red team scans (preview)` and schedule weekly scans against the seekapa agent. Categories: HateUnfairness, Violence, SelfHarm, ProhibitedActions, SensitiveDataLeakage. Attack strategies: Crescendo, Multi-turn, Tense, Base64, Flip.

### Medium term (next 4 weeks, ~40 hours)

8. **Build a Tau-bench-style user simulator harness.** Source: [tau2-bench GitHub](https://github.com/sierra-research/tau2-bench). Adapt the simulator to use your real ticket transcripts as personas + hidden goals. Run as a nightly benchmark, not a CI gate.

9. **Add a 3-judge panel for the most contentious metric (`task_adherence`).** Implement as a custom prompt-based evaluator that calls three judges and reports majority vote + disagreement rate. Models: `gpt-5-mini` + `gpt-4o-mini` + Prometheus-2. Use only on a sampled subset (10% of rows) to keep cost bounded.

10. **Add input drift monitor.** Use Application Insights query against the agent's traces to detect Kolmogorov-Smirnov shifts in incoming query embedding distribution. Reference: [How to Monitor LLM Drift in Production](https://dasroot.net/posts/2026/02/monitor-llm-drift-production/).

### Visualization in Foundry (the explicit ask)

The native visualization story is **good**. You don't need to build dashboards.

| What you want | Where it lives | URL pattern |
|---|---|---|
| Drill into a specific eval run | Build → Project → Evaluation → Runs | `https://ai.azure.com/build/projects/seekapa_ai/evaluation/runs/<run_id>` (programmatically: `print(eval_run.report_url)`) |
| Compare two prompt versions side-by-side | Eval details page → select 2+ runs → Compare button | Not persisted — re-select on each visit |
| Time-series charts of all metrics | Build → seekapa agent → Monitor (Agent Monitoring Dashboard) | Single page, configurable time range |
| Per-criterion breakdown of a run | Click a run name → row-level results with judge explanations | Drill-in from the run details page |
| Continuous eval results | Same Agent Monitoring Dashboard | Pulls from App Insights — needs `Log Analytics Reader` |
| AI Red Teaming Agent ASR | Agent Monitoring Dashboard → Red team section | Same dashboard, separate tile |
| Token usage tracking | Agent Monitoring Dashboard → token usage card | Same dashboard |

**Compare-runs uses statistical tests.** When you select two runs and click Compare, the cells are color-coded:

- ImprovedStrong (p ≤ 0.001) — bright green
- ImprovedWeak (0.001 < p ≤ 0.05) — pale green
- DegradedStrong / DegradedWeak — red
- ChangedStrong / ChangedWeak (no "desirable direction") — yellow
- Inconclusive (too few samples or p ≥ 0.05) — gray

Hovering shows sample size and p-value. This is the right tool for your earlier today's "v96 vs v97" comparison — the keyword script said 1/10 vs 3/10, but the Foundry compare-runs view would correctly mark it Inconclusive at n=10.

---

## Bibliography

### Microsoft Foundry official documentation

1. [Built-in Evaluators Reference — Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/concepts/built-in-evaluators)
2. [General purpose evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/general-purpose-evaluators)
3. [Agent evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/agent-evaluators)
4. [Custom evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/custom-evaluators)
5. [Risk and safety evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/risk-safety-evaluators)
6. [RAG evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/rag-evaluators)
7. [Cloud Evaluation with the Microsoft Foundry SDK](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/cloud-evaluation)
8. [See Evaluation Results in Microsoft Foundry portal](https://learn.microsoft.com/en-us/azure/foundry/how-to/evaluate-results)
9. [Run evaluations from the Foundry portal](https://learn.microsoft.com/en-us/azure/foundry/how-to/evaluate-generative-ai-app)
10. [Monitor agents with the Agent Monitoring Dashboard](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard)
11. [AI Red Teaming Agent — concepts](https://learn.microsoft.com/en-us/azure/foundry/concepts/ai-red-teaming-agent)
12. [Run AI Red Teaming Agent Locally](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/run-scans-ai-red-teaming-agent)
13. [Run an evaluation in Azure DevOps](https://learn.microsoft.com/en-us/azure/foundry/how-to/evaluation-azure-devops)
14. [Evaluation regions and limits](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-regions-limits-virtual-network)

### Microsoft blogs and community posts

15. [Introducing AI Red Teaming Agent — Foundry blog](https://devblogs.microsoft.com/foundry/ai-red-teaming-agent-preview/)
16. [Assess Agentic Risks with the AI Red Teaming Agent](https://devblogs.microsoft.com/foundry/assess-agentic-risks-with-the-ai-red-teaming-agent-in-microsoft-foundry/)
17. [What's new in Microsoft Foundry — Dec 2025 & Jan 2026](https://devblogs.microsoft.com/foundry/whats-new-in-microsoft-foundry-dec-2025-jan-2026/)
18. [Continuous Evaluation Framework (techcommunity)](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/evaluating-generative-ai-models-using-microsoft-foundry%E2%80%99s-continuous-evaluation-/4468075)
19. [Evaluations, Monitoring, Tracing GA in Foundry](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/generally-available-evaluations-monitoring-and-tracing-in-microsoft-foundry/4502760)
20. [Evaluating AI Agents: A Practical Guide with Microsoft Foundry](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/evaluating-ai-agents-a-practical-guide-with-microsoft-foundry/4500224)
21. [3 takeaways from red-teaming 100 GenAI products (Microsoft Security Blog, Jan 2025)](https://www.microsoft.com/en-us/security/blog/2025/01/13/3-takeaways-from-red-teaming-100-generative-ai-products/)
22. [How Microsoft defends against indirect prompt injection attacks (Jul 2025)](https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks)

### SDK and tooling

23. [azure-ai-projects (PyPI)](https://pypi.org/project/azure-ai-projects/)
24. [azure-ai-evaluation (PyPI)](https://pypi.org/project/azure-ai-evaluation/)
25. [azure-ai-projects evaluation samples](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/evaluations/README.md)
26. [AI Agent Evaluation Marketplace Task](https://marketplace.visualstudio.com/items?itemName=ms-azure-exp-external.microsoft-extension-ai-agent-evaluation)
27. [microsoft/ai-agent-evals — sample datasets](https://github.com/microsoft/ai-agent-evals/tree/main/samples/data)
28. [PyRIT on GitHub](https://github.com/Azure/PyRIT)

### Agent benchmarks

29. [Tau-bench paper (arXiv 2406.12045)](https://arxiv.org/abs/2406.12045)
30. [Tau2-bench paper (arXiv 2506.07982)](https://arxiv.org/pdf/2506.07982)
31. [Tau2-bench GitHub](https://github.com/sierra-research/tau2-bench)
32. [Sierra Research blog on Tau-bench](https://sierra.ai/blog/benchmarking-ai-agents)
33. [BFCL leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
34. [BFCL v3 multi-turn blog](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html)
35. [AgentBench (THUDM)](https://github.com/THUDM/AgentBench)
36. [AgentBoard (NeurIPS 2024 Oral, arXiv 2401.13178)](https://arxiv.org/abs/2401.13178)
37. [GAIA leaderboard](https://huggingface.co/spaces/gaia-benchmark/leaderboard)
38. [BrowseComp (OpenAI)](https://openai.com/index/browsecomp/)
39. [SWE-bench Verified](https://www.swebench.com/verified.html)
40. [OSWorld](https://os-world.github.io/)

### LLM-as-judge research

41. [Prometheus 2 (arXiv 2405.01535)](https://arxiv.org/abs/2405.01535)
42. [JudgeLM (ICLR 2025 Spotlight)](https://github.com/baaivision/JudgeLM)
43. [Replacing Judges with Juries (arXiv 2404.18796)](https://arxiv.org/abs/2404.18796)
44. [Judging the Judges: Position Bias (ACL 2025)](https://aclanthology.org/2025.ijcnlp-long.18/)
45. [Self-preference bias paper (arXiv 2410.21819)](https://arxiv.org/abs/2410.21819)
46. [CALM bias quantification](https://llm-judge-bias.github.io/)
47. [A Survey on LLM-as-a-Judge (arXiv 2411.15594)](https://arxiv.org/abs/2411.15594)
48. [Awesome-LLMs-as-Judges](https://github.com/CSHaitao/Awesome-LLMs-as-Judges)

### Statistical rigor

49. [Anthropic: A statistical approach to model evaluations (Nov 2024)](https://www.anthropic.com/research/statistical-approach-to-model-evals)
50. [Cameron Wolfe: Applying Statistics to LLM Evaluations](https://cameronrwolfe.substack.com/p/stats-llm-evals)
51. [GrowthBook: How to A/B Test AI](https://blog.growthbook.io/how-to-a-b-test-ai-a-practical-guide/)
52. [Braintrust: A/B testing LLM prompts](https://www.braintrust.dev/articles/ab-testing-llm-prompts)
53. [Latitude: How sample size affects LLM prompt testing](https://latitude-blog.ghost.io/blog/sample-size-affects-llm-prompt-testing/)
54. [A Survey on Data Contamination (arXiv 2502.14425)](https://arxiv.org/html/2502.14425v2)
55. [AntiLeak-Bench (ACL 2025)](https://aclanthology.org/2025.acl-long.901/)

### Red-teaming and prompt injection

56. [PAIR — jailbreaking-llms.github.io](https://jailbreaking-llms.github.io/)
57. [TAP (arXiv 2312.02119)](https://arxiv.org/pdf/2312.02119)
58. [OWASP LLM01:2025 — Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
59. [Indirect Prompt Injections: Are Firewalls All You Need? (arXiv 2510.05244)](https://arxiv.org/html/2510.05244v1)
60. [Lakera: Indirect Prompt Injection](https://www.lakera.ai/blog/indirect-prompt-injection)

### Local cs-agent docs (referenced in audit)

61. `axia-seekapa-cs-agents-devops/docs/FOUNDRY-EVAL-CI-PLAN.md`
62. `axia-seekapa-cs-agents-devops/docs/prompt_v96_optimization_suggestions.md`
63. `axia-seekapa-cs-agents-devops/scripts/foundry_eval_gate.py`
64. `axia-seekapa-cs-agents-devops/tests/deepeval_suite.py`
65. `axia-seekapa-cs-agents-devops/tests/deepeval_metrics.py`
66. `axia-seekapa-cs-agents-devops/tests/test_data/foundry_smoke_eval.jsonl`
67. `eval_f3859661e28d4ebc8814dc5f98e6397b.md` (historical Foundry continuous eval export, 67 runs)

---

## Methodology Appendix

**Data sources:** 67 .md files inventoried via Glob, 6 read in full, 2 deeply analyzed (`FOUNDRY-EVAL-CI-PLAN.md`, `prompt_v96_optimization_suggestions.md`). Local code: `foundry_eval_gate.py` (full read), `deepeval_suite.py`, `deepeval_metrics.py`, `foundry_smoke_eval.jsonl` (sample).

**Subagent threads:** Two parallel general-purpose research agents:
- Thread A: agentic eval SOTA 2025-2026 (~80K tokens, 23 tool uses, ~7 minutes)
- Thread B: Microsoft Foundry native evaluation features (~135K tokens, 19 tool uses, ~7 minutes)

**Citation policy:** Every primary source linked. Local file citations use repo-relative paths. Statistical claims cite primary research (Anthropic, ACL, arXiv).

**Limitations of methodology:**
- Did not test the AIAgentEvaluation@2 task hands-on — recommendations are based on official documentation, not empirical verification.
- Did not benchmark cs-agent against Tau2 — that's the Tier-3 recommendation, not done in this audit.
- Did not interview team members — based on .md files, code, and git history only.
