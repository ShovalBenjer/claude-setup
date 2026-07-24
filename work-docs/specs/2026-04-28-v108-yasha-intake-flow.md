# v108 — Yasha Intake Flow (Seekapa / Nissreen)

**Status:** Draft, not deployed. Awaiting Yasha + Shoval review.
**Source:** Yasha's 2026-04-28 dictation (`yasha_conversational_style_2804.txt`).
**Replaces:** v107.3 (deployed via PR 175) and v107.4 (local draft).
**Scope:** Seekapa only. AxiaCS untouched.

## Why this change

v107.x was titled "Yasha-style" and explicitly forbade asking for name or email outside the escalation flow. Yasha's 2026-04-28 dictation reverses that. He now wants a structured 4-section intake **before** KB lookup or handoff so that every escalation arrives at the human queue with `{name, email, reason}` already captured.

## The four sections (from Yasha's text)

1. **Intake** — bot greets, asks for name, then email, then reason. Re-ask reason once if missed.
2. **KB lookup** — answer FAQ-grade questions from the vector store. Yasha flagged "Needs full verification against Oded's past v80 remote-deployed KB file by file" — see Open Questions.
3. **Handoff** — pass to human agent and wait.
4. **Inheritance** — the human agent inherits **only** `{client_name, client_email, reason_of_request, meta}`. Nothing else.

## Default assumptions (override before deploy)

These are explicit so they can be redlined. None are decided.

| # | Question | Default |
|---|---|---|
| 1 | When Chatwoot prefix already provides name+email, does bot still ask? | **No** — skip name/email questions, ask only for reason if not stated. |
| 2 | Pure FAQ first turn ("how long do withdrawals take?") — intake first or answer first? | **Answer first.** Intake fires when the customer's intent is action-oriented (withdraw, deposit issue, account problem, complaint) AND prefix lacks name/email. Pure informational asks bypass intake. |
| 3 | Disconnect codeword `אנדרלמוסיה`, off-topic, fraud (Var B), self-harm (Var C), account-locked (Var D) — bypass intake? | **Yes, all bypass.** They fire their canonical message verbatim, intake never runs. |
| 4 | "v80 remote deployed KB" — different vector store than `vs_yuCtQgmt2I9W0wTCMBnyP1hf`? | **Unknown.** Treat as TBD. Keep current vector store for v108 unless Yasha points to a different one. |
| 5 | Eval suite — re-baseline now or accept regression? | **Add new rows for intake flow, keep existing.** Multi-turn eval infra does not exist yet — see Risks. |

## Pre-mortem (top 5 failure modes)

1. **Intake friction on FAQ users.** Customer asks "what's the inactivity fee?" — under naive intake, bot asks for name+email+reason, customer churns. *Mitigation:* Default #2 — FAQ-only intent bypasses intake.
2. **Loop with escalation triggers.** Bot asks "Could you please provide your full name?" — if escalation classifier ever watches for "please provide" or "name", self-escalation loop. *Mitigation:* Audit `_should_escalate` keyword list against intake phrases before deploy. v107.4 escalation triggers are customer-side phrases ("speak to a human") — safe today, but invariant must be enforced.
3. **Multi-turn state drift.** Bot has no durable memory across turns. If customer says "withdraw" → bot asks name → customer says "actually deposit" — does bot still hold "withdraw" as the reason? *Mitigation:* Each turn re-classifies intent from the latest message; intake state is held only in the most recent customer message + Chatwoot conversation history.
4. **Eval pass rate regression.** Current 64% pass rate was measured against v107.3's answer-first behavior. Adding intake will fail rows that expect a direct answer. *Mitigation:* Mark known-failing rows; add intake rows; rebaseline only after Yasha confirms behavior.
5. **Anonymous-user identity leak.** If bot asks for email in plain channel and customer types it, the email is logged in transcripts. Compliance has not signed off on collecting email pre-handoff. *Mitigation:* Confirm with Shoval that prompted email collection is OK under FSA SD183 + GDPR.

## Behavior table (decision matrix)

| Customer first message | `prefix_has_name`+`prefix_has_email` | Bot reply |
|---|---|---|
| Bare greeting ("hi") | any | "Hello, thank you for contacting Seekapa. I'm Nissreen. How can I assist you today?" |
| Action intent ("I want to withdraw") | both true | "I'll help you with your withdrawal. Could you tell me the reason for the withdrawal?" (skip name/email) |
| Action intent ("I want to withdraw") | name missing OR email missing | "I'll help you with your request. Could you please provide your full name?" (begin intake) |
| Pure FAQ ("how long do withdrawals take?") | any | KB answer, 1–2 sentences. No intake. |
| Disconnect `אנדרלמוסיה` | any | "OK." |
| Off-topic | any | Off-topic line verbatim. |
| Human request, fraud, self-harm, locked account | any | Variant A/B/C/D verbatim with identity-ask-append rule from v107.4. |
| Account-specific lookup (Variant E) | any | Variant E verbatim. |
| Financial advice (Variant F) | any | Variant F verbatim. |

## Intake state machine (simplified)

```
START
  ├── classify(message)
  │     ├── disconnect → "OK." → END
  │     ├── off-topic → off-topic line → END
  │     ├── escalation (A/B/C/D/E/F) → variant verbatim + identity-append → END
  │     ├── pure FAQ → KB lookup → reply → END
  │     └── action intent → INTAKE
  │
  └── INTAKE
        ├── prefix has name+email → ask for reason → reply → END
        ├── name missing → ask for full name → END (next turn picks up)
        ├── email missing → ask for email → END
        └── reason missing → ask for reason (re-ask once if blank) → END
```

State is implicit per turn — derived from `prefix_has_name`, `prefix_has_email`, and whether the latest message contains a name/email/reason.

## Inheritance payload (Section 4)

When the bot fires an escalation variant, the handoff to human agent must include exactly:

```json
{
  "client_name": "<from prefix or intake>",
  "client_email": "<from prefix or intake>",
  "reason_of_request": "<customer's stated reason, ≤140 chars>",
  "meta": {
    "channel": "telegram|whatsapp|web",
    "language": "en|ar|es|pt",
    "first_message_ts": "...",
    "escalation_variant": "A|B|C|D|E|F"
  }
}
```

Anything outside this set is dropped. No prior chat content, no tool-call traces.

## Languages

EN default. AR / ES / PT — bot responds in customer's language. Translation tables for the 4 intake questions live in the prompt (one block per language).

## Open questions

1. Yasha's "v80 remote deployed KB" — which vector store? Same as `vs_yuCtQgmt2I9W0wTCMBnyP1hf` or a separate one?
2. Compliance sign-off on collecting email in chat (Pre-mortem #5).
3. PT (Portuguese) was not in v107.4's anchor facts. Does v108 need PT translations or is it AR/ES/EN only?
4. Should "reason" be free-form, or constrained to a list (withdraw / deposit / KYC / login / other)?

## Eval impact

Existing eval (`eval_dataset.jsonl`, 32 rows) is single-turn `{query, response, context, ground_truth_escalation}`. v108 intake is multi-turn. Two paths:

- **Path A (recommended):** Keep single-turn eval rows for FAQ + escalation classification (these still work, since FAQ bypasses intake). Add a new multi-turn eval file `intake_eval.jsonl` with 6–8 conversation traces. Build a tiny multi-turn runner.
- **Path B:** Rewrite all eval rows as multi-turn. High effort, breaks existing CI baseline.

Going with Path A.

## Rollback

If v108 underperforms in production: Foundry portal → swap agent's system prompt back to v107.3 contents. Keep `seekapa-system-prompt-v107.3-yasha-style.md` and `v107.4-yasha-style.md` files in the repo for that swap.

## Files

- Spec: this file.
- Draft prompt: `axia-seekapa-cs-agents-devops/agent-prompts/seekapa-system-prompt-v108-intake.md` (draft).
- New eval rows: `axia-seekapa-cs-agents-devops/evals/data/intake_eval.jsonl` (draft, single conversation traces).
- v107.x files retained for rollback.
