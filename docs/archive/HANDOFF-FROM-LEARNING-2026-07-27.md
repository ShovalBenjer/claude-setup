# Handoff to the Claude-setup session, from the learning-platform session

Written 2026-07-27. Everything is measured, with the command that produced it.
Nothing here has been built except where stated.

## 1. Measured defects in the current setup

| Finding | Evidence | Severity |
|---|---|---|
| **Every guard fires at exit, none at entrance.** settings.json wires SessionStart, PreToolUse, PreCompact, Stop, Notification. All three quality gates (completion_gate, ship_gate_stop, prior_art_gate) are Stop hooks. | `settings.json` hooks block | HIGH |
| **UserPromptSubmit is not wired anywhere**, yet the `voice-explainer` skill's own description says it triggers from a UserPromptSubmit hook. That skill's trigger does not exist. | `grep -rl UserPromptSubmit` over every settings file returns nothing | HIGH |
| **11 skills exist twice**, in user scope and in the new-recruit project scope: agent-builder, azure-activity-watch, azure-audit, azure-runtime, codex-call, coverage-enforcer, dispatch, openai-agents, persona, premortem, refactor-pre-push. No precedence rule is written down. | `comm -12` over both skill directories | MEDIUM |
| **daily-deep-learning has no `.claude` directory at all.** Zero project skills for a live production app. | `ls` on the repo | MEDIUM |
| **The daemon's critic is the same model as its author**, and neither call site names a model. | `daily-deep-learning/daemon/server.ts:92,112` | MEDIUM |

## 2. The operator, measured from 212 of his own prompts

Extracted from the Claude transcripts, deduped, pastes trimmed.

- **Median prompt length: 170 characters.** P90 624. He writes two sentences and
  expects a specification.
- **20% demand evidence** ("did you", "are you sure", "prove", "verify"). That is
  his single most common move.
- **18% manually fight convergence**, typing "widen", "full extent", "deep".
- **9% reject, 6% approve.** Rejections outnumber approvals 19 to 13.
- 17% ask for explanation, 13% name a gap or express self-doubt, 9% cite a
  source, 5% contain Hebrew.

**The diagnosis this supports:** the rejection rate is caused by structural
under-specification, not by unclear thinking. 170 characters cannot carry the
intent behind a fifteen-section spec, so the model fills the gap with
assumptions and he rejects the result. He then pays 18% of his typing to say
"widen" because nothing in the system does it for him.

## 3. What to build, ranked

### 3.1 The entrance guard, UserPromptSubmit

Free real estate, and it attacks the measured failure directly. Two jobs:

1. **Inject standing preferences automatically** so he stops paying 18% of his
   typing for "widen" and 20% for "prove it". These are already written down in
   the global CLAUDE.md and the rules directory; nothing reads them at prompt
   time.
2. **Surface assumptions before work starts** when a short prompt meets a large
   scope. Not rewriting his intent, annotating it. A prompt under ~200 characters
   that triggers a multi-file or multi-hour task should force an explicit
   assumption list first.

Do **not** build a prompt "enhancer" that guesses more. Enhancement means more
unfounded assumptions, which is the disease rather than the cure.

### 3.2 The mechanism-claim gate

`prior_art_gate` guards claims of absence. `completion_gate` guards "it works".
**Nothing guards "here is a method."**

Of four errors I made in one session, three were mechanism claims asserted on
thin evidence: an attention ratio taken from a blog, a trend heuristic validated
circularly on the case it was derived from, and a workshop pick made by diffing
non-consecutive years. Only one was an absence claim, and only that one would
have been caught.

Rule to enforce: **a claim that something is a method, a mechanism, a rule, or a
pattern requires a primary source, a backtest against data not used to build it,
or an explicit n=1 label.**

### 3.3 Instrument the operator, not just the agent

The prompt corpus analysis is the most useful thing produced this session and it
had never been run. Every harness logs agent behaviour; almost none analyse the
human's side to find where the system fails its user.

Make it a scheduled job: extract typed prompts, report length distribution,
rejection-to-approval ratio, and the share spent on preferences the system should
already know. **The rejection ratio is a system health metric**, not a mood.

### 3.4 The published-list diff, as a general primitive

The workshop signal generalises. The mechanism is: **take a list that a third
party publishes on a schedule, diff consecutive editions, and treat what is new
as signal.** It works for conference workshop tracks, arXiv category listings,
the AI-103 exam objectives (which are re-published annually and currently drift
silently), and his own skills ledger against his resume claims.

Two hard-won rules attached to it:

- **Consecutive editions only.** Skipping a year produces false positives; this
  cost one wrong pick today when ICML 2026 was diffed against ICML 2024 while
  NeurIPS 2025 held the missing ancestor.
- **It is a scheduled event, not a poll.** Calls for workshops close on dates.

### 3.5 Every signal carries a measured base rate

The novel discipline, and the one worth keeping. A heuristic without a base rate
is a story. Measured today: **a first-instance workshop has roughly a one-in-four
chance of still existing two years later** (5 to 7 survivors out of about 26 at
ICML 2024). That number turns "read new workshops" from a slogan into an
instrument with known precision.

Rule: any signal the system acts on must state how often it is right, or be
labelled unvalidated.

### 3.6 Ingest his self-chat as a discovery source

`wa-export-archive/SENSITIVE-self-chat/_chat.txt`: 556KB, 8,546 lines, **75 saved
GitHub links, 54 unique, across 14 months, of which 33 are July 2026 alone.** His
save rate rose five to ten times this month.

This is better curated than the learning platform's 11 world-scan sources because
it is filtered by his actual attention. It is unwired. Ingest links and dates
only; the file is marked SENSITIVE and its message content must not leave it.

### 3.7 Cross-domain transfer, on a schedule

The single most valuable product idea today came from him mentioning his wife's
work: clinical assessment protocol maps onto the placement diagnostic, and the
mature form is item response theory. A periodic prompt asking **"which mature
discipline already solved this?"** would systematise what currently depends on a
chance remark.

## 3b. Addendum, later on 2026-07-27, after two workflow runs

Five findings that change harness design, all with evidence.

### A1. Critics must flag, not fix. This is a live bug.

`daily-deep-learning/daemon/server.ts:118` ends its verify pass with
`if (refined && refined.length > 20) result = refined`. It **replaces the
teacher's answer with the critic's rewrite** whenever the rewrite exceeds 20
characters. A length heuristic is the only gate.

The literature says that is the dangerous half. "Detection Without Correction: A
Two-Parameter Decomposition of Multi-Stage LLM Pipelines" (2026-05-26)
decomposes multi-agent pipelines and finds detection is the load-bearing
operation with **conditional miscorrection dominant at 53 to 94 per cent**. A
critic that rewrites introduces more error than it removes.

Rule for the review fabric: a critic returns a verdict and a reason. It does not
return replacement text that is silently substituted.

### A2. One independent critique beats debate, at lower cost

"Debate Helps Weak Judges Reward Stronger Models" (2026-05-26): **a single
independent critique recovers the bulk of debate's benefit at lower inference
cost.** Do not build multi-agent debate into the review fabric. One
cross-family critic is the right shape, which is what the model-stack
recommendation already says.

### A3. The critic seat has an admission requirement

"When Helping Hurts and How to Fix It" (2026-06-01) gives the benefit condition:
critique helps **only when the critic's verification odds exceed its
miscorrection risk**. A critic that is worse at verifying than the generator is
at being right makes output worse.

This constrains model choice for that seat specifically. It does not follow from
"open model, free tier, family independence" that any model can hold it. The
seat needs measuring before it is filled.

### A4. A single fan-out can exhaust a session-wide budget and silently degrade everything after it

Measured today. One workflow ran 20 agents with 420 tool calls and consumed the
**entire session WebSearch budget, 200 of 200.** Every later agent, including a
second workflow launched afterwards, now runs without search and falls back to
WebFetch or to unverified recall.

Nothing warned. Nothing degraded loudly. The second run is producing
lower-confidence output for a reason invisible in its own transcript.

The harness needs a shared-resource guard: budget visible before launch, a
reserve that fan-outs cannot touch, and a loud notice when a run is operating
degraded. This is a capacity-planning failure mode, not a bug in either workflow.

### A5. Workflows have no shared workspace, and the J-space paper says why that matters

Anthropic's "A global workspace in language models" (2026-07-06) identifies the
J-space, named for the Jacobian lens used to find it, and the properties that
make it valuable are **reportability, controllability and causal intervention**.

Our workflows pass results between agents as return values. No agent can see
another's reasoning, and the operator cannot inspect or intervene mid-run. The
architectural analogue is the **blackboard**, classical AI from HEARSAY-II, which
is the systems ancestor of Global Workspace Theory. A shared, inspectable,
writable run state would give a fan-out exactly the three properties the paper
found worth having.

### A6. Resolve endpoints, never hardcode a loopback address

Chrome bound its debug port to IPv6 loopback only. Every tool here hardcoded
`127.0.0.1` and got connection-refused while the browser was plainly running,
which cost a working browser capability for part of the session.
`daily-deep-learning/tools/cdp.py` now probes four ports across three hosts and
returns whatever answers. That pattern belongs in the harness, not in one repo.

### A7. The mechanism-claim gate now has hard evidence

Previously argued from three of my own errors. Now measured: a ten-cluster
cross-domain sweep produced 70 candidate transfers, 30 reached adversarial
refutation, and **30 of 30 were refuted.** The two failure modes were consistent:
the transfer was already infrastructure, or the analogy broke at the
load-bearing point.

Those two are a reusable checklist and belong in the gate:

- Does a survey, a handbook, a standard or free tooling already exist for it? Then
  it is infrastructure, not insight.
- Where exactly does the analogy carry the weight, and does it hold there? The
  covering-arrays transfer died because a covering array supplies coverage but no
  oracle, and the binding cost in LLM evaluation is stochastic sampling, not row
  count.

## 4. Housekeeping

- Write a precedence rule for duplicated skills, or delete one copy of the 11.
- Give `daily-deep-learning` a `.claude/skills/` and move today's repeatable
  procedures into it: gate run, CDP screenshot at 390px, curriculum budget check,
  workshop diff. All four exist as scripts in that repo already.
- Name the model at `daemon/server.ts:92` and `:112`, and move the critic to a
  different family. NVIDIA Build's free tier hosts DeepSeek V4 and GLM-5.2 at
  40 RPM, which is ample for verification and useless for generation.
