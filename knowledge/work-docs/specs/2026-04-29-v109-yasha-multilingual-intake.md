# v109 — Yasha Multilingual Intake + Repetitive-Failure + Identity Guard

**Status:** Draft. Awaiting Shoval sign-off before any prompt or eval rows are written.
**Source:** Yasha's 2026-04-29 dictation (`yasha_conversational_2904_style.txt`) — v1 + v2 sections.
**Replaces:** v108 (deployed 2026-04-29, 48%-headline-misleading eval).
**Scope:** Seekapa only. AxiaCS untouched.
**Author:** Claude (cs-agent session, branch TBD).

---

## 1. Why this change

v108 shipped the 4-section intake (greet → name → email → reason → KB/escalate). Yasha's 2026-04-29 dictation introduces three behaviors v108 does not handle and one constraint that invalidates last session's eval:

| # | New thing | v108 behavior | v109 target |
|---|---|---|---|
| 1 | Repetitive-failure escalation | None — bot keeps trying KB | Detect 2+ "this isn't helping" / "I tried that" variants → step 3 (handoff) |
| 2 | Identity-test guard for private info | Variant E fires verbatim (account lookup) | When user asks about their own account/private data, ask for approval *before* answering or escalating |
| 3 | Post-escalation "already forwarded" | Bot may re-fire escalation variant or loop | If user asks for human after handoff already triggered, acknowledge "already forwarded, response may be slower, here's what you can try meanwhile" |
| 4 | Language coverage | EN default, AR/ES/PT translation blocks present but PT was an open question | EN/AR/ES/PT explicit; **English fallback for any other language**. Hebrew is **not primary** in eval. |

The v2 behaviors close real failure modes seen in production (loops, escalation churn, privacy leaks).

---

## 2. Acceptance criteria (numbered, each maps to a test)

Format: `AC{n} — {behavior} — {evidence requirement}`.

### Intake (carry-over from v108, must still pass)
- **AC1** — Bare greeting ("hi" / "hola" / "مرحبا" / "olá") → "Hello, I'm Nissreen…" in user's language. No name/email asked.
- **AC2** — Action intent + prefix has name+email → skip to "tell me the reason".
- **AC3** — Action intent + prefix missing name → ask for full name (in user's language).
- **AC4** — Action intent + prefix missing email → ask for email.
- **AC5** — Pure FAQ → KB answer, 1–2 sentences, no intake.
- **AC6** — Disconnect `אנדרלמוסיה` → "OK." verbatim.

### v2 — Repetitive-failure escalation (new)
- **AC7** — Customer says "this isn't helping me" / "I tried that, didn't work" / "still not working" twice across the conversation → bot fires step-3 handoff regardless of KB confidence.
- **AC8** — Single "I don't understand" or "can you explain again" is **not** a trigger (legitimate clarifying question, not failure). Verified by negative test.
- **AC9** — Trigger phrases must be detected in all 4 supported langs (EN/AR/ES/PT). English-fallback message handles other langs gracefully.

### v2 — Identity guard (new)
- **AC10** — User asks about their own account ("what's my balance?", "show me my last withdrawal", "what's my plan?") → bot replies with approval request: "To access your account details I need to verify your identity. Can you confirm you'd like me to proceed with verification?"
- **AC11** — Generic FAQ ("what plans do you offer?") → no identity guard, KB answer fires normally. Verified by negative test.
- **AC12** — After user confirms ("yes, proceed") → escalate via Variant E (account lookup) since bot has no live account access. **Never invent account data.**

### v2 — Post-escalation "already forwarded" (new)
- **AC13** — Once any escalation variant (A/B/C/D/E/F or step-3 handoff) has fired in the conversation, subsequent "I want to talk to a human" / "is anyone there?" → bot replies with "already-forwarded" message: acknowledge handoff + warn slower response + suggest one self-serve alternative if applicable.
- **AC14** — Already-forwarded message must **not** itself contain escalation trigger keywords (no "transfer", "human agent", "speak to a person") — prevents re-loop. This is the cs-agent canonical anti-pattern, see `CLAUDE.md`.

### Language (new constraint)
- **AC15** — User writes in EN/AR/ES/PT → bot responds in same language.
- **AC16** — User writes in any other language (HE, RU, FR, ZH, …) → bot responds in **English** with the same content. No silent failure, no Hebrew default.
- **AC17** — Mid-conversation language switch → bot follows the latest user message's language (per-turn classification, no sticky language state).

### Inheritance (carry-over from v108)
- **AC18** — Handoff payload contains exactly `{client_name, client_email, reason_of_request, meta{channel, language, first_message_ts, escalation_variant}}`. Nothing else. Language code is one of `en|ar|es|pt`.

---

## 3. Out of scope (v109 will NOT do)

- AxiaCS prompt changes.
- New vector store / KB rebuild (v80 question stays open from v108).
- Multi-turn state persistence beyond Chatwoot conversation history (still implicit-state per turn).
- Compliance sign-off on email collection (still pending from v108 pre-mortem #5 — flag if blocker).
- Hebrew translations (intentionally dropped from primary; HE users get EN responses per AC16).

---

## 4. Pre-mortem (top 5 failure modes, mandatory per forge-loop step 0c)

> **Assume v109 ships and fails in production 3 months from now (2026-07-29). What are the top 5 reasons it failed?**

1. **Repetitive-failure detector false-positives on legitimate confusion.** Customer says "I don't understand" 2x while bot is genuinely answering well — gets escalated unnecessarily, queue floods. *Mitigation:* AC8 negative test. Detector requires phrases that imply *attempted action failed*, not generic confusion. Phrase list curated from real Chatwoot transcripts, not invented.

2. **Identity guard triggers on benign questions.** "What plans do you offer?" matches "what's my…" too loosely → friction loop. *Mitigation:* AC10 keyword list uses possessive markers (`my account`, `my balance`, `my withdrawal`) not bare "what" — AC11 negative test enforces this.

3. **"Already-forwarded" message contains an escalation keyword and re-triggers self-loop.** This is the documented cs-agent anti-pattern (CLAUDE.md §"Circular Escalation"). *Mitigation:* AC14 dedicated test — grep the already-forwarded template against the escalation detector keyword list at build time AND at eval time.

4. **Language detector misclassifies short messages.** "hola" is ES. "hi" is EN. "ok" is ambiguous in 4 langs → wrong-language reply. *Mitigation:* For ≤3-token messages, default to conversation history language; if no history, EN. Add eval rows for short-message language detection (AC15 sub-cases).

5. **Eval suite still misaligned because we didn't write AC→test map FIRST.** Last session shipped v108 at 48% headline because suite tested v107 behaviors. *Mitigation:* §6 below — every AC mapped to a named test row BEFORE writing the row. Reviewer (you) signs off on the map before any row gets authored. **This is the lever that broke last time.**

---

## 5. Eval suite realignment plan (the 48%-headline fix)

### 5.1 Audit existing rows (do this first, no new rows yet)

For each of the 3 datasets, classify every row into **Keep / Rewrite / Delete**:

| Dataset | Rows | Audit task |
|---|---|---|
| `foundry_yasha_eval.jsonl` | 10 | Last run: 8/10 = 80%. Audit which 2 fails are real v109 misses vs. row-bug. Hebrew rows → translate to EN/AR/ES/PT or delete. |
| `silver_eval_rows.jsonl` | 15 | Last run: 6/15 = 40%, 8 "real fails" uncategorized. **Categorize each fail** — which AC does it test? Is the expected behavior v107-style (delete) or v109-style (rewrite)? |
| `intake_eval.jsonl` (multi-turn) | 8 | Last run: 2/8 pass, 4 infra 500s. **Diagnose the 500s before adding cases** — likely cause: multi-turn runner doesn't handle Chatwoot prefix correctly, or Foundry endpoint timing out on long prompts. |

**Output of audit step:** a table `evals/audit-2026-04-29.md` with `row_id | dataset | current_status | v109_action (keep/rewrite/delete) | reason`. Reviewer signs off before §5.2.

### 5.2 New rows per AC (after audit)

Target: every AC has ≥3 test rows (1 happy, 1 negative, 1 edge). 4-language coverage means AC1/AC15-17 need ≥4 rows each (one per language).

| AC | Dataset | Estimated new rows |
|---|---|---|
| AC1–AC6 (intake carry-over) | foundry + silver | 0 new (covered by rewritten rows in §5.1) |
| AC7–AC9 (repetitive-failure) | intake (multi-turn) | 6: 1 happy ×4 langs + 1 negative + 1 edge (mid-conversation switch) |
| AC10–AC12 (identity guard) | foundry (single-turn) + intake (multi-turn for AC12) | 7: 4 happy ×4 langs + 2 negative + 1 edge |
| AC13–AC14 (already-forwarded) | intake (multi-turn) | 5: 4 happy ×4 langs + 1 anti-loop (AC14 grep test) |
| AC15–AC17 (language) | foundry | 8: 4 supported × happy + 3 unsupported (HE/RU/FR) → EN + 1 mid-conv switch |
| AC18 (inheritance) | snapshot test (not Foundry eval) | 1 schema-validation test |

**Total new rows:** ~27. Multi-turn runner must support all of these (fix infra 500s first per §5.1).

### 5.3 Run protocol

1. **Static** — schema validation on all eval rows (`jsonschema` against a v109 row schema).
2. **Foundry eval** — `client.evals.runs.create()` against deployed agent (per `feedback_pipeline_minimalism.md` — eval lives in Foundry, not CI).
3. **Multi-turn runner** — fix infra 500s first; run intake_eval rows.
4. **Manual smoke** — 6–8 hand-crafted scenarios per language (last session got 6/6 here while suite reported 48% — this gap is what we're closing).
5. **Scorecard** — pass rate per AC, per language, per dataset. **Headline number = lowest of (per-AC pass rate, per-language pass rate)**, not the arithmetic mean. This is the fix for last session's misleading 48%.

---

## 6. AC → Test map (skeleton — to be filled before any row is written)

| AC | Test row id (planned) | Dataset | Language(s) | Type | Priority |
|---|---|---|---|---|---|
| AC1 | `greet_en_01`, `greet_ar_01`, `greet_es_01`, `greet_pt_01` | foundry | each | happy | P0 |
| AC7 | `repfail_en_01`, `repfail_ar_01`, `repfail_es_01`, `repfail_pt_01` | intake | each | happy multi-turn | P0 |
| AC8 | `repfail_negative_clarify_en` | intake | EN | negative | P0 |
| AC10 | `identity_my_balance_en`, `..._ar`, `..._es`, `..._pt` | foundry | each | happy | P0 |
| AC11 | `identity_negative_what_plans` | foundry | EN | negative | P0 |
| AC13 | `already_fwd_en_01`, `..._ar`, `..._es`, `..._pt` | intake | each | happy multi-turn | P0 |
| AC14 | `anti_loop_grep_test` | unit test (not Foundry) | n/a | invariant | P0 |
| AC15 | covered by AC1/AC10 rows | — | — | — | — |
| AC16 | `lang_fallback_he_to_en`, `..._ru`, `..._fr` | foundry | unsupported→EN | happy | P0 |
| AC17 | `lang_switch_es_to_en` | intake | mixed | edge | P1 |
| AC18 | `inheritance_payload_schema` | snapshot | n/a | invariant | P0 |

**Full map (all ~27 rows) to be authored AFTER §5.1 audit completes** — the audit will tell us how many rewrites vs. new rows we actually need.

---

## 7. Defaults locked (user said "Go" — these are my answers, redline at any heidegger checkpoint)

1. **"pr" → Portuguese (`pt`).** Matches v108 §94 + existing `foundry_yasha_eval_multilang.jsonl` (already has PT rows). REDLINE if you meant Persian.
2. **Repetitive-failure phrase list — invented + cross-checked.** Curated phrase list (≤8 phrases per language) cross-checked against v108's escalation keyword set (cases 3–8) at build time to prevent self-loop. Source: common cs-agent failure patterns + transcripts user has shared (e.g., "this isn't helping me", "I tried that but it didn't work", "still doesn't work", "same problem", "didn't work", + AR/ES/PT mirrors). NOT pulling from CRM (out of scope, plus CRM is read-only and querying transcripts at scale is heavy).
3. **Identity-guard scope = TIGHT.** Triggers only on possessive + financial/transactional terms: `my balance`, `my account`, `my withdrawal`, `my deposit`, `my last transaction`, `my position`, `my password`, `my otp`. Does NOT trigger on `my plan` (route to KB), `my email` (intake), `my name` (intake). Possessive marker required — `what plans do you offer?` does NOT trigger.
4. **"Already-forwarded" message = generic.** No KB-specific link. One sentence per language. Acknowledge handoff + mention slower response. Suggest "you can also email support@seekapa.com or WhatsApp +44 7441 940574" (anchor facts already in v108 prompt). Easier to maintain across 4 langs.
5. **Compliance sign-off on email collection — DEPLOY BLOCKER, NOT IMPLEMENTATION BLOCKER.** Continue with prompt + eval work. Mark deploy step as RED in §10. User to resolve before any Foundry portal swap.
6. **Eval baseline.** Accept temporary regression on rows that test v107-style answer-first behavior. v109 deploys when: per-AC pass rate ≥80% AND per-language pass rate ≥80% AND AC14 anti-loop test passes 100%.

### Corrections to spec made during execution

- **Vector store**: v108 deployed prompt uses `vs_BhDnWqMdIsxjgv1f0sQOuwX6`, NOT the `vs_yuCtQgmt2I9W0wTCMBnyP1hf` referenced in the v108 spec. v109 keeps the deployed one.
- **Existing eval inventory** is larger than initially stated: 38 (foundry) + 32 (silver) + 20 (multilang already 4-lang!) + 8 (intake) = **98 rows**, not 33. The 20-row multilang set is a strong base — v109 extends it with v2 behaviors rather than rewriting it.
- **Hebrew claim**: I said "rows are mostly Hebrew." Inspecting actual JSONL files, only `silver_eval_rows.jsonl` has English-primary rows; multilang and intake_eval are already EN/AR/ES/PT. The "Hebrew-primary" framing was wrong — last session's reflection misled me. Fixing.

---

## 8. Files to be created (after sign-off)

- `axia-seekapa-cs-agents-devops/agent-prompts/seekapa-system-prompt-v109-multilingual.md` (new prompt)
- `axia-seekapa-cs-agents-devops/evals/data/intake_eval_v109.jsonl` (multi-turn rows)
- `axia-seekapa-cs-agents-devops/evals/data/foundry_yasha_eval_v109.jsonl` (single-turn rows)
- `axia-seekapa-cs-agents-devops/evals/data/silver_eval_v109.jsonl` (rewritten silver)
- `evals/audit-2026-04-29.md` (the row-by-row audit table, §5.1)
- `tests/test_v109_invariants.py` (AC14 anti-loop grep test, AC18 schema test)

## 9. Rollback

Foundry portal → swap agent's system prompt back to v108 contents. Keep `seekapa-system-prompt-v108-intake.md` in the repo for that swap.

## 10. Honest completion model

This spec is **0% implementation, 100% planning**. Sign-off gates everything in §8. No prompt edit, no eval row, no test runs until you approve §2 (ACs), §6 (test map), and §7 (open questions).
