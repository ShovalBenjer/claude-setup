# v110.1 — Email-OTP Verification Flow (supersedes v110)

**Author:** Shoval / cs-agent
**Date:** 2026-05-10
**Status:** SPEC — pending approval before implementation
**Supersedes:** [`docs/specs/2026-05-06-seekapa-account-verification-flow.md`](./2026-05-06-seekapa-account-verification-flow.md) (v110 with email + last-deposit-amount factors)

## Why this spec exists

v110 shipped 2026-05-10 with two factors:
1. Customer claims email
2. Customer claims last deposit amount in USD (within ±$1)

Yasha's review same-day:

> "last deposit is generic — anybody can text any email and get account data. We need to send a short code to that email so we make sure it's a real client. Like *Mas Hahnasa* (income tax) or *Bituah Leumi* (national insurance) login."

He's right. Both v110 factors are **knowledge factors**, and the second one is weak: deposit amounts are commonly known (round numbers, customer told family/accountant, leaked in transaction emails). Two knowledge factors stacked is not 2FA in any meaningful sense.

Industry standard for this risk class (information disclosure of trading account state, no withdrawal/login access) is **knowledge + control**: prove you control the email inbox by reading a code only deliverable to it.

**Production state during this spec:**
- `SEEKAPA_VERIFY_ENABLED=false` on `func-cs-agents-dev` (flipped 2026-05-10 ~14:30 UTC after Yasha's feedback). Bot falls back to v109 prompt-side identity-guard ("verify your identity first — would you like me to proceed?") which doesn't actually do anything beyond ask. No real account data leaks while we build v110.1.

## Goal

Replace the deposit-amount second factor with an email-OTP factor:
- Customer claims email → CRM lookup → if compliance OK, send 6-digit code to that email → customer pastes code back → if matches, `VERIFIED` and bot reveals account data in CRM-recorded language.

## Decision rationale (locked)

| Choice | Decision | Why |
|---|---|---|
| Replace, not stack | Drop deposit factor entirely. Keep email + OTP. | Adding OTP on top of deposit is more friction, not more security. The OTP-control alone is sufficient at this risk tier. |
| Code length | 6 digits (numeric, 100,000 – 999,999) | Easy to type on Telegram, 1-in-900,000 random-guess rate, matches Israeli bank/tax precedent Yasha referenced |
| Code TTL | 5 minutes | Same as overall session TTL. Single timer to reason about. |
| Max attempts | 3 wrong codes → session locked, Variant A. (vs. v110's 2-attempt cap on deposit) | OTP brute-force concern: 3 attempts × 1/900,000 ≈ negligible. 3 also matches common UX (one mistype, one resend confusion, one final). |
| Resend allowed? | NO in v110.1. Only `cancel` exits. | Resend opens email-bombing abuse vector without a per-email rate limit, which we don't have ready. Defer to v110.2. |
| Email provider | Brevo (smtp-relay.brevo.com:587, STARTTLS) | Already provisioned by user. Free tier sufficient (300/day, plenty for QA + initial). |
| Sender | `sender@mail.mailseekapa.com` (Seekapa) / `sender@axiaemail.com` (Axia) | Pre-verified at Brevo. SPF/DKIM presumed configured. |
| Failure on send | Variant A degrade, session cleared, log a warning. | Don't punish the customer for our infra failure. Log loud so we notice. |
| Code delivery latency | Bot says "I sent a code to your email — paste it here when it arrives." Don't include the email in the message (already known to bot/Chatwoot). | Set expectation. Avoid the "did the email send?" UX. |

## State machine

```
[customer sends possessive+financial trigger]
    │
    ▼
ASK_EMAIL_REPLY ──► customer types email
                        │
                        ├── invalid format ──► INVALID_EMAIL_REPLY (retry, session preserved)
                        │
                        └── format OK ──► CRM lookup
                                            │
                                            ├── 404 / errors[] ──► variant_a(lang) (NOT_FOUND, session cleared)
                                            ├── compliance not in whitelist ──► variant_a(lang) (NOT_VERIFIED, session cleared)
                                            ├── 5xx / network ──► variant_a("en") (SERVICE_ERROR, session cleared)
                                            └── compliance ∈ whitelist ──► generate code, send email
                                                                              │
                                                                              ├── send fail ──► variant_a(lang), session cleared, log [VERIFY] OTP send_failed
                                                                              └── send OK ──► ASK_OTP_SENT_REPLY (lang-aware)
                                                                                                    │
                                                                                                    └─► customer types code
                                                                                                          │
                                                                                                          ├── unparseable / not-6-digits ──► INVALID_OTP_REPLY (retry, attempt counter +1)
                                                                                                          ├── matches ──► VERIFIED canonical (lang-aware), session cleared
                                                                                                          ├── wrong, attempts < 3 ──► RETRY_OTP_REPLY (attempt counter +1)
                                                                                                          ├── wrong, attempts == 3 ──► variant_a(lang) (OTP_FAILED, session cleared)
                                                                                                          └── "cancel" ──► CANCEL_REPLY, session cleared
                                                                                          [TTL hit at any step ──► session cleared, customer sees no message; next "what's my balance" restarts the flow]
```

## API contract (Python signatures)

```python
# In azure-function-crm/seekapa_otp.py (new module)
def generate_code() -> str: ...              # secrets.randbelow(900000) + 100000 → str
def hash_code(code: str, salt: bytes) -> bytes: ...  # blake2b(code+salt) — store hash, not raw
def verify_code(claimed: str, stored_hash: bytes, salt: bytes) -> bool: ...  # constant-time

class SmtpClient(Protocol):
    def send_otp(self, to_email: str, code: str, language: str, brand: str) -> bool: ...
        # Returns True on send success, False on failure. Logs detail at WARNING.

class SmtpRelayClient:
    """Production SMTP via Brevo. Uses smtplib + STARTTLS on 587."""
    def __init__(
        self,
        host: str,
        port: int,
        get_login: Callable[[], str],
        get_password: Callable[[], str],
        seekapa_sender: str,
        axia_sender: str,
    ) -> None: ...
```

## State on `_ConvState` (verification_flow.py)

```python
@dataclass
class _ConvState:
    awaiting: _Awaiting             # EMAIL | OTP   (drops AMOUNT)
    state: VerificationState | None  # CRM-derived: customer, balance, etc.
    expires_at: float
    lock: threading.Lock
    # NEW for v110.1
    otp_hash: bytes | None = None    # blake2b digest, never the raw code
    otp_salt: bytes | None = None    # 16 random bytes per session
    otp_attempts: int = 0            # 0..3
```

Code is **never stored in plaintext** in the cache. We hash with a per-session salt; verification is constant-time compare. This means even if the in-memory cache is dumped (not realistic on Azure Functions, but defensive), the OTP can't be recovered.

## Email templates — 4 languages, plain text

The body must:
- Be plain text (not HTML) — Brevo handles either; plain is simpler and avoids spam-trigger HTML quirks for a transactional 1-line message
- Show ONLY the code + brief context — no marketing
- Match v109.5 Yasha-style brevity

### EN
```
Subject: Seekapa verification code: 123456

Your Seekapa verification code is: 123456

Enter this code in chat to confirm your identity. Expires in 5 minutes.

If you did not request this, ignore this email.
```

### AR
```
Subject: رمز التحقق من Seekapa: 123456

رمز التحقق الخاص بك من Seekapa هو: 123456

أدخل هذا الرمز في الدردشة لتأكيد هويتك. ينتهي في غضون 5 دقائق.

إذا لم تطلب هذا، تجاهل هذه الرسالة.
```

### ES
```
Subject: Código de verificación Seekapa: 123456

Tu código de verificación Seekapa es: 123456

Ingresa este código en el chat para confirmar tu identidad. Expira en 5 minutos.

Si no solicitaste esto, ignora este correo.
```

### PT
```
Subject: Código de verificação Seekapa: 123456

Seu código de verificação Seekapa é: 123456

Digite este código no chat para confirmar sua identidade. Expira em 5 minutos.

Se você não solicitou isso, ignore este e-mail.
```

For the Axia brand: same templates with "Axia" substituted, sent from `sender@axiaemail.com`.

## In-chat replies (4 languages)

| Reply | EN |
|---|---|
| `ASK_OTP_SENT_REPLY` | `I sent a 6-digit code to your registered email. Paste it here when it arrives. The code expires in 5 minutes.` |
| `INVALID_OTP_REPLY` | `That doesn't look like a 6-digit code. Try again, or 'cancel'.` |
| `RETRY_OTP_REPLY` | `That code didn't match. Try again, or 'cancel'.` |

For AR / ES / PT, translations follow the same Yasha-style brevity pattern as the existing v110 replies.

## Abuse mitigation

| Vector | Mitigation |
|---|---|
| Brute-force OTP (try all codes) | 3 attempts, then session locked. Random new code per session. Hash storage. |
| Email-bombing (force the bot to send many emails to a victim) | One OTP per session. No resend in v110.1. Per-email rate limit (max 5 OTPs per email per hour) added in v110.2 — out of scope here. |
| OTP intercept | TLS to Brevo (STARTTLS on 587). Email provider's own TLS to recipient. We don't control the recipient's email security; this is the standard limitation of email-OTP. |
| Credential stuffing of CRM emails | CRM lookup happens BEFORE OTP send. If the email isn't in CRM or compliance fails, no OTP is sent — saves cost and avoids confirming-non-customer to attackers. |
| Replay (sniff one OTP, use it) | Single-use: matched code clears the session (`_cache.pop`). Re-sending the same code returns invalid. |
| Timing oracle on hash compare | `hmac.compare_digest` for constant-time. |

## Cost / quota

| Item | Estimate |
|---|---|
| Brevo free tier | 300 emails/day, 9000/month |
| Per OTP send | ~$0 (within free tier) |
| Per Foundry agent call we save by short-circuiting to OTP | ~$0.01 |
| Total monthly at 100 verifications/day | $0 (well within Brevo free tier) |

If verification volume exceeds 300/day, upgrade to Brevo Lite ($15/mo for 5,000/day) — out of spec scope.

## Configuration

### Function App appsettings (new)

```
SMTP_HOST         = smtp-relay.brevo.com
SMTP_PORT         = 587
SMTP_LOGIN        = @Microsoft.KeyVault(SecretUri=https://shoval.vault.azure.net/secrets/SMTP-BREVO-LOGIN/)
SMTP_PASSWORD     = @Microsoft.KeyVault(SecretUri=https://shoval.vault.azure.net/secrets/SMTP-BREVO-PASSWORD/)
SMTP_SENDER_SEEKAPA = sender@mail.mailseekapa.com
SMTP_SENDER_AXIA    = sender@axiaemail.com
```

KV secrets `SMTP-BREVO-LOGIN` and `SMTP-BREVO-PASSWORD` are already populated in `Shoval` vault as of 2026-05-10. The Function App's managed identity already has `Get` on `Shoval` (granted earlier today for `CRM-API-KEY`).

### Existing v110 settings to preserve

`CRM_API_KEY` (KV ref) — unchanged. `SEEKAPA_VERIFY_ENABLED` — flip to `true` after v110.1 deploys.

## Deploy / rollout plan

1. **Implement** `seekapa_otp.py` + update `_verification_flow.py` per this spec. New module, new tests, new state-machine row.
2. **Test** locally with `FakeSmtpClient` capturing send calls. Hit `verified.en@example.com` fixture: should ask for OTP, accept correct code, reject wrong code 3×.
3. **Live SMTP smoke** (one-shot, manual): send a test OTP from a tmp script to Shoval's own email via Brevo. Confirm delivery + the email-template UX.
4. **PR + CI**, deploy via pipeline 121 with flag still OFF (`SEEKAPA_VERIFY_ENABLED=false`). Code lands but doesn't run.
5. **Flip flag ON** with operator at Telegram for live QA against `messaoudi.yahia13@gmail.com` — does the OTP arrive at the customer's actual inbox? (Need Yasha's OK to use a real customer or to use a tester address.)
6. **Notify Yasha**, Telegram QA from his side, get sign-off.
7. **Open** for general traffic.

## Test plan

### Unit (FakeSmtpClient + recorded fixtures)
- ✅ `verify_first_factor` for ADVANCED VERIFIED → triggers `send_otp` once → returns NEEDS_OTP outcome
- ✅ Customer types correct code → VERIFIED canonical, balance/equity/pnl from snapshot
- ✅ Customer types wrong code → RETRY (1, 2 attempts), then variant_a on 3rd
- ✅ INVALID format (e.g., "abc", "12345", "1234567") → INVALID_OTP_REPLY without consuming an attempt
- ✅ "cancel" → CANCEL_REPLY, session cleared
- ✅ TTL expires mid-flow → next message starts fresh
- ✅ SMTP send failure → variant_a, no leakage about why
- ✅ Replay: matched code, then customer sends same code again → no longer recognized

### Integration (live SMTP, one-shot)
- Connect to Brevo, send to a tester inbox, confirm delivery
- Verify SPF/DKIM headers don't trip spam filters

### E2E (Telegram QA on Section 13 of qa-script-v2)
- Replace V1-V18 rows with new OTP-flow rows. Update QA doc.

## Rollback

If the OTP flow misbehaves in prod, **single command** rollback:
```bash
az functionapp config appsettings set -g AZAI_group -n func-cs-agents-dev \
  --settings "SEEKAPA_VERIFY_ENABLED=false"
```
Function App restarts (~30s). v109 prompt-side identity-guard takes over. No customer-data exposure during the rollback window.

## QA-only backdoor: SMTP_TEST_REDIRECT_EMAIL

For end-to-end Telegram QA against a real CRM customer (e.g., messaoudi) without spamming their actual inbox, an env-var backdoor in `seekapa_otp.send_otp()` routes every OTP send to a single test address. The CRM lookup still uses the customer's real email; only the SMTP recipient is overridden.

```bash
# Enable backdoor — every OTP sent goes to shoval.be@i-sdd.com regardless
# of what the customer typed in chat.
az functionapp config appsettings set -g AZAI_group -n func-cs-agents-dev \
  --settings "SMTP_TEST_REDIRECT_EMAIL=shoval.be@i-sdd.com"

# After QA: UNSET (critical — leaving it set causes silent OTP leak for
# every real customer thereafter).
az functionapp config appsettings set -g AZAI_group -n func-cs-agents-dev \
  --settings "SMTP_TEST_REDIRECT_EMAIL="
```

Every redirected send logs a WARNING-level trace at `[VERIFY] OTP REDIRECTED (test mode)` with both addresses redacted (`me***@gmail.com` / `sh***@i-sdd.com`). Look for that line in App Insights AppTraces during QA — if it's NOT there during your QA, the backdoor isn't active (the env var is unset or empty).

The backdoor is gated on the env var being non-empty. Setting it to an empty string explicitly unsets it. Tested in `tests/test_seekapa_otp.py::test_send_otp_no_redirect_by_default` and `::test_send_otp_redirects_to_test_inbox_when_env_set`.

## Open questions for Yasha

1. **Resend the OTP if it doesn't arrive?** Spec says NO for v110.1 to avoid email-bombing. Yasha may want a "resend" command — adds complexity. Confirm.
2. **Use the SAME tester address (e.g., shoval@) for all of Yasha's QA, or send to real-customer addresses with their consent?** Sending real OTPs to real customers without telling them might be alarming.
3. **Brand handling:** OTP from `sender@mail.mailseekapa.com` for Seekapa, `sender@axiaemail.com` for Axia. The bot currently runs under `CHATWOOT_DEFAULT_BRAND=seekapa`. Do we ever need Axia from inbox 4? If yes, how is brand switched per-customer?
4. **Compliance status whitelist** — same as v110 (`{VERIFIED, ADVANCED VERIFIED, FULLY VERIFIED}`)? Or tighten to just `VERIFIED`?
5. **ASK replies in customer's language?** v110 had English-only intermediate prompts. **v110.1 LOCKS this differently** — see Locked Decision below. Confirm with Yasha.

## Locked decision: language routing across the flow

Two language sources are available — the **trigger language** (detected from the customer's first possessive+financial message via `_pre_classifier.detect_language`) and the **CRM language** (`customer.language` from the CRM payload, only known AFTER FACTOR1 succeeds).

| Step | Language source | Why |
|---|---|---|
| `ASK_EMAIL_REPLY` (after trigger, before CRM lookup) | Trigger language | CRM lang isn't known yet. Match the language the customer wrote in. |
| `INVALID_EMAIL_REPLY` | Trigger language | Customer is still pre-CRM. |
| OTP email body (subject + content) | **CRM language** | The email is permanent record; match the customer's profile language so it reads natural in their inbox. |
| `ASK_OTP_SENT_REPLY` (in chat) | CRM language | We just looked up CRM, we know it. Tell the customer "code sent" in their profile language to match the email they're about to receive. |
| `INVALID_OTP_REPLY` / `RETRY_OTP_REPLY` | CRM language | Same — flow is post-CRM-lookup. |
| `VERIFIED` canonical (with balance/equity/pnl) | CRM language | Same as v110. Final answer in profile language. |
| `CANCEL_REPLY` | Trigger language | Lightweight closer; trigger language is fine. |
| `variant_a` (degrade paths: NOT_FOUND, NOT_VERIFIED, SERVICE_ERROR, OTP_FAILED) | Trigger language for NOT_FOUND/SERVICE_ERROR (no CRM data); CRM language for NOT_VERIFIED/OTP_FAILED (we have customer record) | Variant A's existing 4-lang text stays; selector chooses based on what's known |

**UX implication:** A customer who triggers in EN but is registered with `language=ara` will see EN ASK_EMAIL, then switch to Arabic for OTP/VERIFIED. That mid-flow switch is intentional and matches the email body language. If Yasha prefers single-language consistency throughout, the alternate is "trigger language wins for everything except OTP email body" — quicker to spec but less inbox-natural.

## Time estimate

- Spec review + Yasha sign-off: 1 day (this doc)
- Implementation (`seekapa_otp.py`, smtp client, state machine update, 4-lang templates): ~1 day
- Tests (unit + 1 live SMTP smoke): ~0.5 day
- PR + CI + deploy: 0.5 day
- Live QA: 0.5 day

**Total: ~3 working days from spec approval.** Flag stays OFF the whole time. Customer behavior unchanged from v109 prompt-side identity-guard.

---

## Appendix: hygiene note

The Brevo SMTP password was pasted into a Teams chat / IDE input on 2026-05-10. Once v110.1 ships, **rotate the password**:

1. Brevo dashboard → SMTP & API → Generate new SMTP password
2. Run: `az keyvault secret set --vault-name Shoval --name SMTP-BREVO-PASSWORD --file <secure-tmp-file>`
3. Brevo dashboard → revoke old password
4. No Function App restart needed (KV reference resolves the new value at next read).

Tracked as task #19.
