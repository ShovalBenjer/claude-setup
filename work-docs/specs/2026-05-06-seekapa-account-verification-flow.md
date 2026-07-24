# Spec — Seekapa account verification via email + CRM lookup

**Date:** 2026-05-06
**Branch:** `feat/v109-yasha-multilingual` (parent of next feature branch)
**Status:** Draft — needs user sign-off before TDD begins
**Forge axes covered:** SPEC ✓ · PREMORTEM ✓ · others (RED, GREEN, REFACTOR, COVERAGE, REFLECT, CI BIND) follow implementation

---

## 1. Goal

Let the bot move from "I cannot answer account-specific questions" to a controlled, identity-verified flow where it can answer with real CRM data **after** the customer provides an email Seekapa can resolve. This closes the v109 AC10 / AC12 loop where the identity guard currently fires and forwards to a human regardless of whether the customer is verifiable.

## 2. Primitive

`POST https://az-corp.corp-domain.com/api/v1/ai-agent/customer`

| Field | Type | Required |
|---|---|---|
| `email` | string (valid email) | yes |
| `broker` | enum: `axia` \| `seekapa` | yes |

Auth: `Authorization: Bearer <CRM-API-KEY>` — secret in `kv-seekapa-apps` (canonical name TBD; do **not** read or echo).

Response (observed shape, see `crm_api_Ref - Copy.txt`):

```jsonc
{
  "customer": {
    "email": "...",
    "language": "ara|eng|...",
    "compliance_status": "PARTIALLY VERIFIED|VERIFIED|...",
    "trades_number": 0,
    "ftd": true|false
  },
  "comments": [{ "content": "url-encoded", "created_time": "ISO" }],
  "deposits": {
    "ftd_amount_usd": 0.0,
    "total_deposits_usd": 0.0,
    "items": [{ "confirmation_time", "status", "payment_type", "amount_usd", "ftd" }]
  },
  "trading_accounts": [{ "balance": 0, "equity": 0, "pnl": 0 }]
}
```

## 3. Flow integration with v109

```
state machine (extends v109 AC10):

  user_msg = possessive + financial term
    → identity_guard fires        (existing, unchanged)
    → bot: "I can verify your identity to answer that. Reply with the
            email registered with Seekapa, or 'cancel' to keep this generic."
    → user supplies email
    → email validated locally (RFC 5321 cheap check)
       fail  → "That doesn't look like an email. Try again or 'cancel'."
       pass  → call CRM endpoint (broker=seekapa)
                  404 / not found        → Variant E forward + email captured
                  5xx / timeout (>3s)    → Variant E forward + retry-after note
                  200 + compliance ≠ VERIFIED → Variant E with KYC-incomplete tag
                  200 + compliance = VERIFIED  → ANSWER MODE (see §4)
    → user replies 'cancel'   → "OK — anything else?"
```

The identity-guard prompt branch is added in `seekapa-system-prompt-v110-verified-answer.md` (next prompt version). Existing AC10 keyword detection is unchanged.

## 4. Answer mode capabilities (post-verification)

After `compliance_status == VERIFIED`, the bot may answer **only** these classes from CRM data:

| Question class | CRM field |
|---|---|
| Current balance | `trading_accounts[0].balance` |
| Equity / floating P/L | `trading_accounts[0].equity`, `pnl` |
| Number of trades on record | `customer.trades_number` |
| Whether first deposit completed | `customer.ftd` |
| Total deposits | `deposits.total_deposits_usd` |
| Last deposit time | `deposits.items[-1].confirmation_time` |
| Preferred contact language | `customer.language` (use as language hint) |

**Forbidden in answer mode** (still escalate):
- Trade history details, individual order numbers, P/L per trade
- Personal data the customer didn't provide in this conversation (name, phone, address)
- Anything from `comments[]` (raw URL-encoded sales notes — internal only)
- KYC document statuses, compliance flags beyond pass/fail

After 5 minutes of inactivity OR conversation close, drop the cached CRM record from session state.

## 5. Pre-mortem (5 failure modes)

1. **Email-only identity is too weak.** A bot that answers balance to anyone who guesses an email is a leak vector. **Mitigation:** treat the bot as one factor; require `compliance_status == VERIFIED` AND restrict to non-PII numerical fields above. Log every CRM call. Add a second factor (last deposit amount confirmation) before exposing balance — RED test in §6.
2. **Wrong broker leak.** A user emails an address that exists at Axia, not Seekapa, but `broker=seekapa` returns a stale/cross-broker record. **Mitigation:** treat any `compliance_status` value the spec doesn't explicitly enumerate as "do not answer"; log the unknown value for audit. Require the response to contain a `broker` echo in future API versions and ask CRM team to add it.
3. **CRM endpoint flakes / latency.** v109 already has slow-perception complaints from Yasha. A 2-second CRM round-trip stacks on top. **Mitigation:** 3-second timeout, single retry, then degrade to Variant E. Track p50/p95 in observability.
4. **Secret rotation breaks the bot silently.** Bearer token expires, all calls 401, bot quietly forwards everything. **Mitigation:** dedicated alert on any sustained 401 from this endpoint; KV secret name pinned in the code constant; `/azure-keyvault-secrets` sync runbook entry.
5. **PII leakage in logs.** Email + balance + trade count flowing to App Insights = data-protection liability under FSA Seychelles + GDPR-style obligations. **Mitigation:** scrub `email` to `<email-redacted>` and bucket `balance` to nearest $100 in logs; keep raw values only in encrypted CRM-call cache, never in stdout/stderr.

## 6. Test plan (RED → GREEN, vertical bullets)

Each row is one TDD slice — write the failing test, then the smallest code to pass it.

| # | RED test | GREEN scope |
|---|---|---|
| 1 | `test_email_validation_rejects_obvious_garbage` — bot doesn't call CRM on `"hi there"` | local validator |
| 2 | `test_crm_lookup_404_falls_through_to_variant_e` — fixture returns 404 | endpoint client + Variant E branch |
| 3 | `test_crm_lookup_5xx_falls_through_to_variant_e_with_retry_note` | timeout + retry logic |
| 4 | `test_crm_lookup_partially_verified_does_not_expose_balance` | compliance gate |
| 5 | `test_crm_lookup_verified_returns_balance_in_same_language_as_customer_language_field` | language honour rule |
| 6 | `test_crm_call_email_redacted_in_logs` | log scrubber |
| 7 | `test_crm_session_dropped_after_inactivity_window` | session TTL |
| 8 | `test_second_factor_last_deposit_amount_required_before_balance` | 2FA-style guard (per pre-mortem #1) |
| 9 | `test_unknown_compliance_status_logged_and_escalated` | future-proofing (pre-mortem #2) |

Mocks policy: real HTTPS to a recorded fixture file; do **not** mock the HTTP layer in code (per CLAUDE.md TDD rule). Record once with a sandbox CRM email; commit fixture.

## 7. Eval coverage additions to `audit-v109-2026-04-29.md`

New rows for `evals/data/intake_eval_v110.jsonl`:

| trace_id | AC equivalent | turns |
|---|---|---|
| `v110_verify_happy_en` | new — verified balance answer | 3 (my balance? → email → balance reply) |
| `v110_verify_404_fallback` | new — graceful fallback | 3 (my balance? → email → variant E) |
| `v110_verify_partially_verified` | new — gate enforcement | 3 (my balance? → email → KYC-incomplete escalate) |
| `v110_verify_lang_from_crm` | AC15 + new | 3 (my balance? → email of `language=ara` → AR balance reply) |
| `v110_verify_cancel` | AC11 — guard negative | 2 (my balance? → cancel → "anything else?") |

Headline = MIN(per-AC pass, per-language pass), same gate as v109.

## 8. Deploy gates (production-safety per CLAUDE.md)

1. KB additions (Phase A glossary + Phase B objection-handling) deploy first; verification flow ships in a **separate** prompt version (v110) on a **staged Foundry test agent**.
2. CRM client lands behind a feature flag (`SEEKAPA_VERIFY_ENABLED`, default off in prod) so the bot deploys with the dead code dormant.
3. User-gated promotion: only after eval p ≥ v109 baseline AND no p95 latency regression on a 100-conversation soak test.
4. Master FAQ PDF (`Seekapa_FAQ_KB.pdf` in `vs_BhDnWqMdIsxjgv1f0sQOuwX6`) is **not** modified by this work — verification flow is prompt + handler code only.

## 9. Locked decisions (defaulted to safer option, 2026-05-06)

The product side could not answer these at spec time, so they default to the safer option for v110 ship. Revisit at v111 if real-world data justifies relaxing.

1. **Compliance enum:** treat `compliance_status` as a **strict whitelist**. Only the exact string `VERIFIED` unlocks answer mode in §4. Any other value — including `PARTIALLY VERIFIED`, `null`, missing, or unknown strings — falls through to Variant E forwarding. Unknown values logged for audit.
2. **Identity factor count:** **two-factor required** before exposing balance / equity / P&L. Factor 1 = email match in CRM. Factor 2 = customer correctly states their last deposit amount within ±USD 1 of `deposits.items[-1].amount_usd`. If factor 2 fails twice, escalate via Variant E and do not retry.
3. **Session TTL for cached CRM record:** 5 minutes idle, OR conversation close, whichever is sooner. Drop unconditionally on language switch or escalation event.
4. **Audit trail:** internal observability only for v110 — App Insights with email scrubbed (per pre-mortem #5). No public-facing report.
5. **CRM latency:** inline on the verification turn only (one call per identity-guard cycle). 3-second timeout, single retry, then degrade. No sidecar in v110.

## 10. Out of scope

- Changing the deployed FAQ KB content (covered by Phases A + B).
- Multi-factor identity beyond email + last-deposit-amount confirmation.
- Write-side CRM operations (still read-only per CLAUDE.md).
- Telegram-channel-specific identity binding (e.g. tying chat_id to email — separate spec).
