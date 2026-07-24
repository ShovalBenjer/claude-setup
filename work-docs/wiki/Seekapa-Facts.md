# Seekapa Facts — Numerical Source of Truth

This page is **generated** from [`kb-source/seekapa_facts.yaml`](../../kb-source/seekapa_facts.yaml) via [`sync_facts_to_wiki.py`](../../kb-source/sync_facts_to_wiki.py). Edit the YAML, run the sync script, then commit both. **Do not hand-edit this file.**

> **Effective date:** 2026-05-06
> **Source-of-truth caveat:** every number the bot may quote MUST originate here. If a fact is not on this page, the bot may not invent or estimate it.

---

## Brand & Regulation

| Field | Value |
|---|---|
| Brand | Seekapa |
| Operator | BluePine LTD |
| Company registration | 8431012-1 |
| Regulator | Financial Services Authority (FSA) of Seychelles |
| Licence number | **SD183** |
| Licence type | Securities Dealer |
| Registered office | Abis Centre (2), Providence Industrial Estate, Mahé Island, Seychelles |
| Support email | support@seekapa.com |
| WhatsApp | +44 7441 940574 |
| Website | https://seekapa.com |
| Source PDF | Seekapa Company Information 20250526.pdf |

> Do **not** mention licence SD034 — that is Axia, a different broker.

---

## Deposits

| Fact | Value | Source |
|---|---|---|
| Minimum deposit | **USD 250** | Operational (Confirmed by product owner 2026-05-05; not stated in deployed legal PDFs.) |

---

## Withdrawals

### Minimums

| Currency | Minimum |
|---|---|
| USD | 100 |
| EUR | 90 |
| SAR | 375 |
| KWD | 30 |

Source: Seekapa Client Agreement 20250526.pdf §20.6

### Processing time

| Stage | Duration |
|---|---|
| Internal review (typical) | 1–3 business days |
| Internal review (contractual maximum) | 4 business days (Client Agreement §20.7) |
| External — card | 3-5 business days |
| External — bank wire | up to 7-10 business days |

### USD 100 withdrawal fee

Charged when **either**:

- No or very little trading activity for ≥1 month before request
- KYC documents not properly provided (refund-style withdrawal)

Source: Seekapa General Fees 20250526.pdf.

---

## Inactivity & Dormancy

Trigger: No deposits, withdrawals or trading activity for ≥1 month.

| Period | Monthly fee (USD) |
|---|---|
| 0–1 months | 0 |
| 1–2 months | 100 |
| 2–3 months | 250 |
| 3–4 months | 500 |
| 4–5 months | 750 |
| 5–6 months | 1,500 |
| 6–12 months | 2,000 |
| **Over 12 months — DORMANT** | **2,500** + USD 2,500 reactivation fee |

Source: Seekapa General Fees 20250526.pdf §4.

---

## Bonuses

| Fact | Value |
|---|---|
| Trading bonus cap | 50% of deposit **OR** USD 5,000 — whichever is **lower of the two** |
| Wagering required | Yes (turnover requirement before profits unlock) |
| Source | Seekapa Trading Bonus Policy 20250526.pdf §2.4 |

---

## Leverage & Maximum Trade Size

| Asset | Max Lots | Default Leverage |
|---|---|---|
| Forex | 10-30 | 1:200 to 1:400 |
| Indices | 3 | 1:25 to 1:100 |
| Stocks | 10 | 1:10 to 1:20 |
| Commodities | 20 | 1:100 |
| Metals/Energy | 50 | 1:100 |
| Cryptos | 20 | 1:2 to 1:5 |
| ETFs | 10 | 1:30 to 1:50 |

Source: Seekapa Max Trade Size 20250526.pdf.

---

## Complaints

| Stage | Timeline |
|---|---|
| Acknowledgement | 2 business days |
| Final response (target) | 21 business days |
| Complex case maximum | 90 business days |
| Auto-close on no client response | 3 months |
| Channel | support@seekapa.com (Complaint Form) |

Source: Seekapa Complaint Procedure 20250526.pdf.

---

## Trading Alerts

| Fact | Value |
|---|---|
| Provider | Trading Central SA (third party) |
| Delivery | SMS |
| Investment advice | **No** |
| Accuracy guarantee | **No** |
| Source | Seekapa Trading Alerts 20250526.pdf |

> The bot must **never** claim Trading Alerts have a percentage success rate or are AI-driven.

---

## Account Manager Callback

| Fact | Value |
|---|---|
| Standard SLA | 24 business hours |
| High-volume SLA | 48 business hours |
| Escalation channels | support@seekapa.com · WhatsApp +44 7441 940574 |

---

## Risk disclaimers (must be invoked when relevant)

- CFDs are leveraged, speculative products. You can lose your entire balance.
- Past performance does not guarantee future results.
- Seekapa does not provide personal investment, legal, or tax advice.

Source: Seekapa Risk Disclosure 20250526.pdf.
