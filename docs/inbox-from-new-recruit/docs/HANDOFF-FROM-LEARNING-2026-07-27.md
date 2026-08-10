# Handoff to the resume engine session, from the learning platform session

Written 2026-07-27. Everything below is measured or quoted, not inferred. Read
this before touching a resume variation.

## 1. How to actually know him, from evidence rather than self-report

**The degree transcript** (`C:\Users\shova\Documents\מדעי נתונים\ממוצע תואר.xlsx`,
120 credits, average 79). Do not copy grades into any artifact; the repo is
published. The banded conclusion is what matters:

- **Applied layer, exceptional.** Business intelligence 100, NLP 100, AI 99,
  machine learning 98, big-data analytics 97, final project 95 and 95.
- **Code and algorithms, mid.** Algorithms 75, complexity 69, computational
  models 65. **Data structures was graded pass/fail**, so there is no signal at
  all on the single most interviewed CS subject.
- **Formal maths, weakest.** About 71 across 13 courses, with 60s in linear
  algebra 1, calculus 2, differential equations and numerical analysis.

**His own words, 2026-07-27, and they match the transcript almost exactly:**
"if you give me interview questions i probably fail miserbly on my own with no
ai at them, the actual writing code ones, on understanding concepts and
creativity im top, and on math related parts i consider myself below mediocore."

**A gap nobody had spotted.** He asked what SSH stands for and found he could not
define shell, terminal, or compile. His degree never taught systems vocabulary.
This is a live interview risk on any DevOps-adjacent question, and it is not
visible from his resume or his repos.

**The ledger** (`daily-deep-learning/skills.json`): 45 skills, **29 flagged
resume_risk**, meaning claimed at level 1 to 3 while a claim needs level 4. Real
level-4 skills, only five: agents-orch, mcp, evals, prompt-eng, azure-functions.

## 2. What he can sell that is not currently being sold

**The headline, and it is badly under-sold.**

`RUC-NLPIR/Awesome-Long-Horizon-Agents` (589 stars, MIT, pushed 2026-07-26)
divides the field into three stages: prompt engineering 2020 to 2023, context
engineering 2023 to 2025, and **runtime harnesses, 2025 to present**. Its Pillar
I, "Externalizing Long-Horizon Capability", has six subsections: Loops and
Workflows, Context and Memory, Tools MCP and Skills, Orchestration, Hooks and
Middleware, Verification.

`C:\Users\shova\claude-setup` holds 67 docs and 103 tools, an intent-control-plane,
hooks, skills, schedulers, a quality contract, and a review fabric. His own
description: "I own the harness: rules, hooks, skills, notification rails, A2A
bridges, schedulers, approvals, and the review fabric."

That is a one-to-one map onto Pillar I. **He independently built what the field
calls its current frontier stage, and there is no resume line that says so.**
Every arm currently sells "agentic systems" generically. The specific,
defensible, dated claim is: *built a runtime harness with hooks, verification
gates and orchestration before the term was in common use, and can name every
component against the literature.*

**Second under-sold asset: verification discipline.** The learning repo carries a
`quality-contract.json` with ten gate domains, a real gate run recorded in
`state/gate-runs.jsonl`, and Stop hooks that block completion claims lacking
executable evidence. Most mid candidates cannot show a single artifact where they
built the thing that tells them they are wrong. He has three.

**Third: evals is his level-4 skill and it is the field's live bottleneck.** The
literature is explicit that pass^4 runs 15 to 25 points below pass^1, so a 90%
benchmark score can mean 70% production reliability. He can speak to that from
`agenteval-bench` rather than from reading.

## 3. Market fact worth acting on

From the 2026 interview-question research: **scaleups interview on agent design
and evaluation; incumbents interview on RAG and integration.** Agent design and
evals are exactly his two genuine level-4 skills. Single secondary source, so
treat as directional, but it argues for weighting arms A and E over C and G.

## 4. GitHub, measured 2026-07-27, and two findings are urgent

| Repo | README bytes | Issue |
|---|---|---|
| `ShovalBenjer/ShovalBenjer` | **1** | The profile README is the first thing a recruiter sees and it is empty. Highest return per minute on the whole board. |
| `matchiq` | **9** | No README, no description, and it is his flagship modelling project, named in `course_plan.json` projects. Invisible. |
| `sqltok` | 22,398 | Substantial README but **no repo description**, so the card is blank in listings and search. |
| `deep_learning_neural_networks` | 7,693 | **Credibility risk.** Described as "comprehensive deep learning study guide", but the README is upstream Keras-language-models text written in another author's first person, referencing their laptop and their TitanX. A reviewer who reads it sees someone else's words under his name. Fix the description or the file. |
| `Machine_Learning_Study_Guidebook` | substantial | Genuinely his, genuinely good, covers supervised learning through PCA and clustering. Under-used in every variation. |

Star counts across all repos are 0 to 2, so stars are not the signal; README
quality and description lines are.

## 5. What this session did not check

Resume text itself, ATS behaviour, arm-by-arm keyword coverage, and the current
`loop_config.json` weights. Those are this session's job, not mine. Also
unchecked: a parallel Codex task he ran over `new-recruit` and OneDrive that may
overlap or contradict this. Reconcile rather than stack.
