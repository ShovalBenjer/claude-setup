# Customer-facing FAQ — Knowledge Base content

This page mirrors the content of [`Seekapa_FAQ_KB_v2.txt`](../../Seekapa_FAQ_KB_v2.txt) in human-readable form for the wiki. The bot does **not** read this page — its grounding comes from the Foundry vector store. See [Knowledge Base](./Knowledge-Base.md) for how content flows from this wiki page through the FAQ source file into the live agent.

> **Source-of-truth caveat (2026-05-04):** the live Foundry vector store `vs_BhDnWqMdIsxjgv1f0sQOuwX6` reports **578.5 KB** for `Seekapa_FAQ_KB`, while the repo's `Seekapa_FAQ_KB_v2.txt` is **21 KB**. The expansion factor isn't accounted for by the `.docx` (208 KB) or `.pdf` (34 KB) variants either. **The live store may contain content this page does not mirror.** Action item: export the live vector store file via the Foundry portal and reconcile with the repo before treating this page as canonical.

## Brand metadata

- **Brand:** Seekapa (operated by BluePine LTD)
- **Regulation:** Financial Services Authority (FSA) of Seychelles
- **License Number:** SD183 (Securities Dealer)
- **Company Registration:** 8431012-1 (BluePine LTD)
- **Registered Office:** Abis Centre (2), Providence Industrial Estate, Mahé Island, Seychelles
- **Support Email:** support@seekapa.com
- **WhatsApp:** +44 7441 940574
- **Website:** [seekapa.com](https://seekapa.com)
- **Effective Date:** 2026-04-27 (FAQ v2)
- **Languages of delivery:** English source; bot replies in English, Arabic, Spanish or Portuguese.

**About Seekapa:** CFD trading platform across forex, indices, stocks, commodities, metals, cryptos, and ETFs.

---

## Section 1 — Withdrawals & Deposits

### Q1 — Withdrawal processing time
Withdrawals are usually approved within **1-3 business days** after KYC verification is complete. After approval, time to receive depends on payment method: cards take several working days, bank wires can take up to a week.
- Internal review (KYC, balance, free margin, no compliance issues): 1-3 business days
- Card refunds: 3-5 business days at payment provider
- Bank wires: up to 7-10 business days

### Q2 — Why deposits arrive faster than withdrawals
Deposits typically arrive within **2-4 hours** because payment providers credit funds immediately. Withdrawals take longer (3-5 business days) because they require KYC, anti-fraud review, and bank settlement at the payment provider.

### Q3 — $100 withdrawal fee — when it applies
A **$100 fee** can apply when there's little or no trading activity for at least one full month before withdrawal, or when verification documents weren't properly provided. Covers admin + payment-processing costs on refund-style withdrawals. Charged once per qualifying withdrawal.

---

## Section 2 — Account Status, Verification & AML

### Q4 — Why ID and proof of address are required
Seekapa is legally required by FSA Seychelles to verify identity and address under AML / Counter-Terrorism Financing rules.
- Government-issued photo ID (passport, ID card, driving licence)
- Proof of address (utility bill, bank statement; ≤3 months old)
- Confirms age (18+), account ownership, PEP screening
- Without KYC: trading restricted, withdrawals blocked, possible account closure

### Q5 — What happens without verification
If verification is incomplete: account limited, withdrawals delayed/rejected, $100 withdrawal fee may apply on refunds, eventual account closure under AML obligations.

---

## Section 3 — Fees, Commissions & Inactivity

### Q6 — Trading fees and commissions
Costs include spread, commission per trade (varies by instrument and account type), overnight/swap fees on positions held past midnight, payment-method fees.
- Round commissions: per full open+close, percentage by asset class
- Commission formula: `volume × contract size × rate × commission %`
- Overnight (swap) charges apply at midnight KSA time on certain products
- Card deposits: up to 3.5%
- Wires: fixed amounts (~30 USD/EUR/GBP)
- E-wallets: roughly 2-3.5%

### Q7 — Inactivity and dormancy fees
- **Trigger:** no deposit, withdrawal, or trade for ≥1 month
- **Fee:** starts at $100/month, progressive increase
- **Dormant threshold:** 12 months (reactivation fee may apply)
- **To reactivate:** deposit or execute a trade and contact support@seekapa.com

---

## Section 4 — Trading Conditions (Leverage, Margin, Rollover)

### Q8 — Leverage and maximum trade size
Maximum trade size and leverage **varies by instrument**.

| Asset class | Max size | Leverage |
|---|---|---|
| Forex | 10-30 lots | 1:200 to **1:400** |
| Indices | 3 lots | 1:25 to 1:100 |
| Stocks | 10 lots | 1:10 to 1:20 |
| Commodities | 20 lots | 1:100 |
| Metals / Energy | 50 lots | 1:100 |
| Cryptos | 20 lots | 1:2 to 1:5 |
| ETFs | 10 lots | 1:30 to 1:50 |

Margin used = `Contract size × lot value ÷ leverage`.

### Q9 — Position closed automatically (margin call / stop-out)
Closed because margin level fell below the platform's stop-out threshold. When equity is too low relative to margin used, the system auto-closes positions starting with the largest losing one.
- Margin level = `Equity / Margin × 100%`
- Margin call: warning when level approaches threshold
- Stop-out: automatic close when level too low
- Required by Client Agreement to control leveraged risk

### Q10 — Rollover on commodity / index contracts
Futures-based CFDs are auto-rolled to the next contract before expiry. You incur the usual spread for closing/opening, possible overnight charges that day, and a price adjustment so the rollover itself is P&L-neutral.

---

## Section 5 — Bonuses, Cash Rebates & Referral Program

### Q11 — Trading bonus / credit — eligibility and withdrawal
Bonuses up to **50% of deposit, max $5,000** for verified, eligible clients. Bonuses are NOT withdrawable as cash; profits are withdrawable only after meeting trading-volume (wagering) requirements.
- Eligibility: verified, 18+, one bonus account per client / IP
- Bonus is trading margin, not real cash
- Removable for abuse, multiple accounts, fraud

### Q12 — Cash Rebate program
Credits cashback to your account based on completed trading volume in eligible instruments.
- Rebate = `closed volume × rate per asset category`
- Deposit methods: card (Visa, Mastercard), bank transfer, e-wallets
- Minimum deposit varies by method (typically from $100)

### Q13 — Friend Referral / IB Program
Approved Introducing Brokers (IBs) earn commission when referred clients deposit and trade through a unique referral link.
- Unique link via Corptracking platform
- Self-referrals and fraudulent referrals: commission withheld or reversed

---

## Section 6 — Trading Alerts & Social Trading

### Q14 — Trading Alerts — are they advice?
**No.** Trading Alerts are SMS market analysis from Trading Central SA, a third party. Informational only — NOT investment advice or buy/sell recommendations.

### Q15 — Social Trading / Copy Trading — risks
Copies trades of Lead Traders automatically. Does NOT guarantee profits. Past performance of a Lead Trader does not guarantee future results.
- Lead Trader = strategy provider; Copier = subscriber
- CFD risks apply at full scale
- Slippage, timing and account-size differences cause performance gaps
- May be unavailable in some jurisdictions

---

## Section 7 — Complaints & Disputes

### Q16 — How to submit a formal complaint
Submit the official Complaint Form by email to **support@seekapa.com**.
- **Acknowledgement:** 2 business days
- **Final response target:** 21 business days
- **Maximum:** 90 business days from holding response
- Treated as closed if you don't respond for 3 months

---

## Section 8 — Risk Warning & Regulation

### Q17 — Is Seekapa regulated? Is CFD trading safe?
**Yes — regulated.** BluePine LTD holds FSA Seychelles license **SD183** (Securities Dealer). CFD trading is high-risk: you can lose your entire balance.
- CFDs are leveraged, speculative products
- Trade only money you can afford to lose
- Seekapa does NOT provide personal investment, legal, or tax advice

---

## Section 9 — Privacy & Data Protection

### Q18 — How personal data is handled
Seekapa collects identification, contact, financial, and technical data to provide services and meet legal obligations. Kept secure; not shared except with authorized third parties (banks, regulators, verification providers).
- **Collected:** name, email, phone, country, age, payment details, transactions, IP, device
- **Used for:** account management, AML compliance, fraud prevention, payments
- **Shared with:** payment providers, banks, KYC vendors, regulators
- Rights to access, correct, delete (where applicable law permits)

---

## Section 10 — Account Manager & Escalation SLA

### Q19 — Account manager not calling back (CALLBACK SLA)
- **Standard SLA:** 24 business hours (excluding weekends and holidays)
- **High-volume:** up to 48 business hours
- **Alternatives:** support@seekapa.com, WhatsApp +44 7441 940574
- **Reassignment:** request via customer support

### Q20 — Bonus eligibility
Requires: (1) verified account, (2) phone verification with account manager, (3) explicit opt-in, (4) only one bonus per client. At company's discretion.

### Q21 — Speak with company management
Direct contact with management is generally NOT available for routine inquiries. Senior support is reachable at support@seekapa.com; unresolved issues escalate via the formal Complaint Procedure (Q16).

### Q22 — Account "closed" or "zero balance"
Causes: (1) inactivity fees exceeding balance, (2) bonus forfeiture, (3) stop-out from margin call, (4) administrative closure for terms violation or AML concerns.

### Q23 — "I lost money trading — is this your fault?"
CFDs involve significant risk. Clients are responsible for their own trading decisions. Seekapa does not guarantee profits and is not liable for losses. If you allege misconduct by your account manager, submit a formal complaint via the Complaint Procedure.

### Q24 — Withdrawal taking too long (TIMELINE BREAKDOWN)
- Internal: 1-3 business days
- External (bank / payment provider): 5-10 business days
- Total max: ~14 business days (excludes weekends and holidays)

### Q25 — Account manager won't respond
Same as Q19. Escalate to support@seekapa.com / WhatsApp +44 7441 940574; request reassignment.

---

## Out-of-scope (escalate, don't FAQ)

These are **not** FAQ — they're escalations. The bot's classifier handles routing.

- Customer asks for human / agent / live person / supervisor / manager → **escalate**
- Account-specific lookup (my balance, my positions, my KYC status, my password, my OTP) → **escalate** (account-specific human agent access required)
- Fraud / theft / scam allegation → **escalate** (compliance team)
- Account locked / frozen / suspended → **escalate** (specialist team)
- Self-harm / extreme distress signal → **escalate urgent**
- Disconnect codeword `אנדרלמוסיה` → reply only "OK."
- Off-topic (weather, restaurants, sports) → "I can only help with Seekapa account questions."

---

## Cross-language anchor phrases

The bot translates / partially translates these on demand. Source values for AR/ES/PT below.

### Arabic (العربية)
- معالجة السحب: 1-3 أيام عمل (KYC مطلوب) — طريقة الدفع تحدد المدة
- رسوم الحساب الخامل: شهرياً لمدة 12 شهراً — أعد التفعيل بإيداع أو تنفيذ صفقة أو تواصل مع الدعم
- لإعادة تنشيط الحساب: تسجيل دخول وإيداع أو تنفيذ صفقة، وتواصل مع support@seekapa.com
- شكوى رسمية: 2 أيام عمل للإقرار، 21 يوم عمل للرد النهائي، support@seekapa.com
- الرافعة المالية تختلف حسب الأداة: فوركس 1:400 كحد أقصى

### Spanish (Español)
- Métodos de depósito: tarjeta (Visa, Mastercard); transferencia bancaria; e-wallets. Mínimo desde $100, varía por método y tipo de cuenta.
- Apalancamiento: 1:400 máximo en forex; varía por instrumento.
- Procesamiento de retiro: 1-3 días hábiles (KYC requerido).
- Queja formal: 2 días hábiles para acuse de recibo, 21 días hábiles para respuesta final, support@seekapa.com.

### Portuguese (Português)
- Alavancagem máxima: até 1:400 no forex; varia por instrumento.
- Métodos de depósito: cartão, transferência bancária, e-wallets.
- Procedimento de reclamação formal: 2 dias úteis para confirmação, 21 dias úteis para resposta final, support@seekapa.com.

---

## Known gaps (audit)

- **Markets / Jurisdictions** — no section in the current FAQ. Bot hallucinates country names (Yasha's 2026-05-04 test). Tracked in [Markets and Jurisdictions](./Markets-and-Jurisdictions.md).
- **Live vs repo size mismatch** — see source-of-truth caveat at top of this page.

## Channels

- Support email: **support@seekapa.com**
- WhatsApp: **+44 7441 940574**
- Account manager callback SLA: **24 business hours**
- Formal complaint: **2 business days acknowledgement / 21 business days final response**
