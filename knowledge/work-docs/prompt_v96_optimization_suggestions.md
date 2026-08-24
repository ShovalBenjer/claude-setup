# Prompt Optimization Suggestions for Current Seekapa Support Prompt

## Scope

This note audits the current production-style prompt in `/home/shovalbe/projects/cs-agent/agent_prompt.md`.

I could not find a file explicitly labeled `v96`, so this document assumes the current prompt to optimize is `agent_prompt.md`. If `v96` exists outside this repo, the same recommendations still apply, but the line-by-line mapping may differ.

---

## What The Eval Taught Us

From `/home/shovalbe/projects/cs-agent/eval_f3859661e28d4ebc8814dc5f98e6397b.md`:

- 67 continuous eval runs were exported.
- The biggest weaknesses were not safety failures.
- The main failure clusters were:
  - `task_completion`
  - `task_adherence`
  - `groundedness`
  - `relevance`
- Safety-style checks were mostly strong:
  - hate/unfairness
  - self-harm
  - sexual
  - violence
  - indirect attack
- Tooling quality was mostly acceptable, with some weaker spots in:
  - `tool_output_utilization`
  - `tool_selection`

## Bottom Line

The prompt does not primarily need stronger safety constraints.

It needs a stronger resolution policy:

- answer sooner
- ask less
- infer more from context/tools
- escalate more cleanly
- remove prompt patterns that cause over-classification and procedural drift

---

## What The Reference Docs Say

From `How a Great AI Support Bot Should Work.md`:

- infer before asking
- do not interrogate the customer
- ask at most 1-2 clarifying questions
- escalate after repeated failure instead of looping
- preserve full context in handoff
- reduce customer effort above all else

From `Revolut Chat Support Bot  How It Works & Best Practices.md`:

- resolve routine cases directly
- use live account context when available
- escalate immediately for human-sensitive or high-risk cases
- preserve continuity when handing off
- do not force the user through bot layers when intent is already clear

These principles align directly with the eval results. The current prompt is strongest on risk control, but weaker on fast, low-friction resolution.

---

## Audit of Current Prompt

## 1. The prompt is too procedural and too rigid

The current prompt forces a long ordered flow:

- Pre-step off-topic detection
- Step 0 hard escalation gate
- Step 0.5 answer-first exception logic
- Step 1 silent diagnosis
- Step 2 KB search
- Step 3 classification
- Step 4 verification
- anti-hedging enforcement

This structure is detailed, but it increases the chance the model follows the framework instead of solving the user's actual problem. That maps directly to lower task adherence and completion.

## 2. The hard escalation gate is too broad

Several triggers are reasonable, but some are overly aggressive:

- emotional intensity after 2+ messages
- all-caps / exclamation intensity logic
- broad technical-limit matching
- broad fraud/legal language matching

These rules likely push the model toward escalation even when a direct answer or first-step resolution would be better.

This hurts:

- task completion
- relevance
- customer effort

## 3. The prompt lacks a strong “infer before asking” master rule

The prompt does contain context-aware behavior, but it does not elevate this into a short, dominant operating rule.

The result is that the model may still ask for details that it could have:

- inferred from session auth
- pulled from CRM
- answered from KB
- narrowed with one precise clarifying question

## 4. The anti-hedging rule is too absolute

The current anti-hedging section forbids mentioning escalation during resolution and forbids any troubleshooting during escalation.

The intent is good: avoid mushy mixed answers.

But the current formulation is too hard-edged. It can suppress useful fallback phrasing like:

- "If you'd prefer, I can create a support ticket."
- "If this is urgent, I can connect you with our team."

Best-in-class support bots keep a visible escape route without turning every answer into an escalation.

## 5. The prompt does not define a simple ideal response shape

There is a lot of policy, but not enough guidance on the best default answer structure.

For routine support, the ideal structure should usually be:

1. brief acknowledgment
2. direct answer
3. exact next step
4. one clarifying question only if needed

Without this, the model is more likely to:

- over-explain policy
- front-load internal process
- ask too much
- answer late

## 6. The escalation threshold should be based on failure, not intensity alone

The reference docs support escalation after repeated failure to resolve, not merely after emotional wording.

Current prompt logic risks escalating:

- angry but solvable queries
- forceful complaint procedure questions
- users who simply want a clear answer fast

Better rule:

- if issue is high-risk, escalate immediately
- otherwise answer first
- if unresolved after 2 failed turns, escalate

## 7. The prompt over-optimizes for policy safety and under-optimizes for grounded answer quality

The eval suggests groundedness and relevance are weaker than safety.

That usually means the prompt should do more of this:

- use KB first for policy/process
- use CRM first for account facts
- avoid speculative reasoning
- say "I can't verify that yet" when the tool did not confirm it

The prompt partly says this, but not in a concise dominant way.

---

## Recommended Prompt Changes

## Priority 1: Add A Short Operating Policy At The Top

Insert a short section near the top of the prompt:

```md
## PRIMARY OPERATING RULES

Your main goal is to resolve the customer's issue with the least possible effort from the customer.

Always follow these rules:

1. Infer before asking.
2. Use authenticated session data and CRM data before asking the customer for information you can retrieve.
3. For policy or process questions, answer from the KB first.
4. Ask at most one clarifying question at a time, and only when the answer cannot be given safely without it.
5. If the issue is not resolved after 2 failed turns, escalate with full context.
6. If the user explicitly asks for a human, escalate immediately.
7. Never guess account facts, policy facts, or regulatory facts.
```

Why this matters:

- raises adherence
- reduces unnecessary questioning
- improves task completion
- improves groundedness

## Priority 2: Narrow The Hard Escalation Gate

Keep immediate escalation only for clearly high-risk categories:

- account locked / frozen / compromised
- fraud / scam / unauthorized access
- legal / regulatory / GDPR / data deletion
- self-harm or extreme distress
- high-value withdrawals
- third-party / inherited / POA
- identity change / official legal identity matters

Move these out of the hard escalation gate and into answer-first or standard escalation logic:

- emotional intensity by itself
- all caps / punctuation intensity
- broad technical wording
- complaint procedure questions
- "speak with manager" informational questions
- callback delay questions

Why this matters:

- fewer false escalations
- better relevance
- lower customer effort

## Priority 3: Replace The Long Ordered Flow With A Simpler Decision Policy

The current step stack is too heavy. Replace it with:

```md
## DECISION POLICY

1. If there is a hard-risk trigger or explicit human request, escalate immediately.
2. Otherwise, if the answer can be given from KB or CRM, answer immediately.
3. Otherwise, ask one precise clarifying question.
4. If clarification still does not unlock a confident answer after 2 failed turns, escalate with context.
```

This should replace the strict "follow these steps in exact order, no skipping" framing.

Why this matters:

- better completion
- less prompt drift
- more natural support behavior

## Priority 4: Introduce A Standard Response Template

Add a response-shape section:

```md
## DEFAULT RESPONSE SHAPE

For routine support issues, structure the reply as:

1. Acknowledge the issue briefly.
2. Give the direct answer first.
3. State the exact next step.
4. Ask one clarifying question only if required.

Do not front-load internal process, policy boilerplate, or escalation language unless needed.
```

Why this matters:

- reduces rambling
- improves relevance
- improves perceived competence

## Priority 5: Replace Anti-Hedging With Anti-Confusion

Current anti-hedging is too strict. Replace it with:

```md
## ANTI-CONFUSION RULE

Do not mix a full troubleshooting flow with a full escalation flow in the same answer.

Allowed:
- answer + optional human route if the user wants it
- answer + one fallback option

Not allowed:
- long troubleshooting sequence plus immediate escalation in the same reply
- contradictory messaging about whether the issue is resolved
```

This keeps the answer clean without hiding the human escape route.

## Priority 6: Make “Infer Before Asking” Explicit In Authenticated Flows

Add a direct rule under authentication/session logic:

```md
When SESSION_LOGIN is available, do not ask for:
- login ID
- email
- balance-related facts
- transaction status
- KYC state

unless the tool call failed or the user is referring to a different account.
```

Why this matters:

- directly follows the reference docs
- reduces interrogation behavior
- improves customer trust

## Priority 7: Tighten Complaint / Manager / Senior Support Handling

Keep answer-first for:

- complaint procedure
- callback timing
- manager availability
- escalation path questions

Then escalate only if:

- the user explicitly asks for it
- the case includes a hard-risk trigger
- the issue remains unresolved after the answer

Why this matters:

- many users just want the process, not immediate handoff
- reduces unnecessary ticket volume

## Priority 8: Add A “Did I Actually Resolve It?” Final Check

Add this to the final verification:

```md
- Did I answer the user's actual question directly?
- Did I minimize customer effort?
- Did I avoid asking for information I could retrieve?
- Did I avoid policy dumping?
- If I escalated, did I explain why in one sentence and preserve context?
```

This check matters more than broad tone checks.

---

## Concrete Prompt Edits To Make Now

## Remove Or Downgrade

- emotional-intensity-only hard escalation
- all-caps / punctuation intensity logic
- broad technical-limit escalation wording
- "follow steps in exact order, no skipping"
- anti-hedging wording that hides escalation as an available option during normal support

## Add

- primary operating rules block
- infer-before-asking rule
- one-question-at-a-time rule
- two-failed-turns escalation rule
- default response shape
- anti-confusion rule
- direct final quality checks

---

## Suggested New Prompt Positioning

The prompt should describe the agent as:

- a low-effort resolver
- context-aware
- answer-first
- strict on high-risk escalation
- calm and factual
- never speculative

Not as:

- a classifier first
- a router first
- a compliance gate with support attached

That change in hierarchy should improve:

- task completion
- task adherence
- groundedness
- relevance

without weakening safety.

---

## Proposed V97 Goal

If you create a revised prompt, the goal should be:

**Resolve ordinary support questions in one turn whenever possible, ask fewer questions, and reserve hard escalation for truly high-risk or unresolved cases.**

That is the clearest path suggested by:

- the eval results
- the current prompt audit
- the Revolut reference pattern
- the general “great support bot” design doc

