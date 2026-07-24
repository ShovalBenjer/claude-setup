# CRM Query Allowlist — Yasha follow-up #1

**Date:** 2026-05-12
**Owner:** Shoval Benjer
**Source of truth:** `azure-function-crm/seekapa_verifier.py` + `agent-prompts/seekapa-system-prompt-v109-multilingual.md` IDENTITY GUARD section
**Yasha meeting:** 2026-05-11 18:15 — "Defining information & action boundaries for the bot"

This doc enumerates what the CS agent may ask of the CRM, what it may echo back to the customer, and what it must never echo regardless of context. Audit deliverable per Yasha's follow-up #1.

## Reading principles (from Yasha 2026-05-11)

1. Bot returns **profile and action-status info**, never derived recommendations.
2. Bot **does not make decisions** (e.g., "withdraw now", "you should switch broker") and does not express opinions.
3. Bot **does not echo sensitive identifiers** (access keys, tokens, full email of others, opaque CRM IDs).
4. Bot only reads CRM **after a successful two-factor verification** (`SEEKAPA_VERIFY_ENABLED=true` + email + OTP).

## CRM endpoint

- **URL:** `https://az-corp.corp-domain.com/api/v1/ai-agent/customer`
- **Auth:** bearer token via `CRM_API_KEY` env var, resolved from Key Vault `Shoval/CRM-API-KEY`
- **Request body:** `{"email": "<customer email>", "broker": "<seekapa|axia>"}`
- **Compliance gate:** customer's `compliance_status` must be one of `{VERIFIED, ADVANCED VERIFIED, FULLY VERIFIED}` (see `seekapa_verifier.COMPLIANCE_VERIFIED_VALUES`); anything else → `NOT_VERIFIED` → Variant A degrade.

## Read allowlist (post-2FA)

| CRM field | Used for | Echoed to customer? |
|---|---|---|
| `customer.compliance_status` | Gate check (verify/not) | No — internal only |
| `customer.account_status` | Sub-route (active vs. dormant) | No — internal only |
| `customer.language` | Reply language switch (`ara/eng/spa/por`) | No — drives bot behavior |
| `trading_accounts[0].balance` | Reveal post-verify | Yes — as USD value or "n/a" if null |
| `trading_accounts[0].equity` | Reveal post-verify | Yes — same |
| `trading_accounts[0].pnl` | Reveal post-verify | Yes — same; renders "n/a" if null |
| `deposits.items[].amount_usd` | Last-deposit factor + retrieval timeline | Bot may confirm "your last deposit of $X arrived on Y" |
| `deposits.items[].confirmation_time` | Same | Same |
| `deposits.ftd_amount_usd` | Fallback if `items` empty | Bot may confirm FTD amount |
| `errors[]` (present + non-empty) | `NOT_FOUND` signal — degrade Variant A | No |

## Read deny-list (must never echo even if reachable)

| CRM field | Why never echo |
|---|---|
| `customer.email` | Bot already knows the address (customer typed it); never echo to confirm — leak vector if conversation history is compromised |
| `customer.name`, `customer.phone`, `customer.address`, `customer.country` | Bot uses these for routing/language only; echoing is a PII exposure |
| Internal CRM IDs (`customer.id`, `customer.account_id`, `trading_accounts[].external_id`) | Opaque — no customer value, leakable secret surface |
| Any field labeled `secret`, `token`, `key`, `password`, `2fa_*` | Per Yasha 2026-05-11: bot must not echo sensitive identifiers regardless of source |
| Other customers' data | Verifier scope is one email at a time; cross-customer queries are out of bounds |

## Action allowlist (what the bot may DO with CRM data)

| Action | Allowed | Notes |
|---|---|---|
| Look up a customer record by email | Yes | After OTP pass only; logged with redacted email (`me***@gmail.com`) |
| Show the customer their own balance / equity / PnL | Yes | Post-2FA, language matches `customer.language` |
| Confirm a deposit arrival | Yes | Specific amount + approximate time; no payment-method details |
| Escalate to support / account manager | Yes | Always allowed; uses `_escalation_note` template |
| **Take a message** to be passed to the account manager | Yes | New in v111 — see `_take_message_flow`; runs in parallel with escalation |
| Change account settings | **No** | Out of scope — escalate |
| Trigger withdrawals or transfers | **No** | Hard-bounded — bot is read-only on CRM |
| Cancel/refund a pending action | **No** | Escalate |
| Update KYC documents | **No** | Customer self-serves in the Seekapa dashboard |
| Bind/unbind a 2FA method | **No** | Security-sensitive — escalate |

## Question routing matrix

Used to decide whether a customer question is answered from CRM, from KB, or routed to escalation. Drives the `_pre_classifier` + Foundry orchestration.

| Customer asks… | Route | Source |
|---|---|---|
| "What's my balance / equity / PnL?" | **CRM** (post-2FA) | `trading_accounts[0]` |
| "When did my last deposit arrive?" | **CRM** (post-2FA) | `deposits.items[]` |
| "Is my account verified?" | **CRM** (post-2FA), translated to plain text | `customer.compliance_status` |
| "What's the minimum withdrawal?" | **KB** | Seekapa_FAQ_KB_v2.txt Q1, Q3 |
| "Why is my withdrawal taking so long?" | **KB** + offer escalate | Q1 + Q24 |
| "What's the dormancy fee?" | **KB** | Q7 |
| "Is Seekapa regulated?" | **KB** | Q17 |
| "Can you change my settings / make this trade for me?" | **Escalate / refuse** | Action deny-list above |
| "I want to talk to my account manager" | **Take-a-message + escalate in parallel** (v111) | `_take_message_flow` |
| "Reset my password / send me an OTP" | **Refuse + redirect to support email / WhatsApp** | Credential refusal canonical |
| "Anything off-topic" | **Redirect** (Variant for off-topic) | "I can only help with Seekapa account questions." |

## Logging discipline

When CRM is queried, AppTraces must include:

- Redacted email pattern (`me***@gmail.com`) — never raw
- Broker (`seekapa` / `axia`)
- HTTP status code
- `compliance_status` value (this is internal classification, not PII)
- Outcome (`NEEDS_SECOND_FACTOR` / `NOT_VERIFIED` / `NOT_FOUND` / `SERVICE_ERROR` / `INVALID_EMAIL`)

Must NOT include:

- Full email
- Customer name, phone, address
- Any field from `deposits.items` other than amount + time
- Trading account IDs
- Bearer token or any header value

## Tests that enforce this

- `tests/test_seekapa_verifier.py` — outcome routing per `compliance_status`
- `tests/test_seekapa_verifier_httpx.py` — wire-format coverage
- `tests/test_pre_classifier.py::TestIdentityGuard` — the verification ask gate
- `tests/test_take_message_flow.py` — v111 take-a-message envelope
- `tests/test_escalation_note.py` — private-note template fields (customer email, brand, link)

## Open follow-ups (need Yasha sign-off)

1. **Reveal-format wording for null PnL.** Current: `"PnL n/a"`. Yasha preference?
2. **Deposit confirmation phrasing.** Current Variant A says "your last deposit of $X arrived on Y". Yasha may want a stricter no-date variant to avoid timestamp PII vectors.
3. **Action allowlist expansion.** As of 2026-05-12 the bot is read-only on CRM. Adding write actions (e.g., "open ticket on behalf of customer") requires a separate spec.

## Provenance

- Yasha meeting transcript: `.claude/paste-cache/bfc4d786496fe0c2.txt` (2026-05-11 18:15)
- Verifier code: `azure-function-crm/seekapa_verifier.py`
- v109 prompt IDENTITY GUARD: `agent-prompts/seekapa-system-prompt-v109-multilingual.md`
- v110.2 conversational style refinement: `agent-prompts/seekapa-system-prompt-v110.2-yasha-conversational.md`
