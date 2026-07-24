# Weekly Plan — Week of 2026-05-10 (Sun–Thu)

**Owner:** Shoval Benjer · **Audience:** Liron · **Source of truth:** this page
**Last update:** 2026-05-10 (post-PST scan)

## Heads-up

- **Liron weekly meeting set for this week.** Meeting invite landed today 11:45 — this page is the agenda.
- **Production issue Sun/Mon:** Training Platform API (`COMP-SEEKAPAAITRAININGAPI-PROD`) has been returning HTTP 403 since 2026-05-08. Root cause looks like missing `AzureWebJobsStorage` + sitecontainer inheritance. Restoring this is the first priority before HCTA / ORM work.

## What's live now (shipped these last 2 weeks)

- **Customer Support Agent v110 — live in production.** Verifies customer identity before sharing any account info. Answers in **Hebrew, Arabic, English**. Refined response style we tested with Yasha.
- **FAQ + Knowledge Base now in our wiki.** Sales and CS can self-serve customer questions.
- **Customer-data redaction hardened.** No PII reaches the AI; long-lived secure tokens replace ad-hoc keys.
- **Marketing analytics surface — 27 tools live in one place.** Calls (Call-Analyzer), ad spend (Windsor), push notifications (OneSignal — Seekapa + Axia), CRM, Chatwoot — all reachable from Foundry agents and the operator console.
- **Pipelines reliable.** CS agent + campaign-analysis pipelines both green.

## What I do this week

| Day | Outcome | Track |
|---|---|---|
| **Sun** | **Restore Training Platform PROD** (HTTP 403 since 2026-05-08). Walk you through this page in the weekly meeting. | Production / weekly |
| **Sun** | Polish CS welcome message (Yasha ask) | CS Agent |
| **Mon** | Verify CS agent quality holds post-v110; close any retest gaps | CS Agent |
| **Tue** | CS agent in steady state. Support Nadav on **Hiya call-branding** rollout (Bluepine LTD company / VAT details to vendor → 48hr to live) | CS Agent / Voice |
| **Wed** | **Deliver HCTA to Yasha** (overdue) | Yasha deliverable |
| **Wed** | Ship 2 marketing-analytics fixes (call-lookup precision + OneSignal email-template content) and strip a small "BI-collision" surface so we don't publish numbers conflicting with BI's | Marketing analytics |
| **Wed** | **Video Flows decision call** with Adnan + you (see decision #4 below) | Video Agents |
| **Thu** | **ORM** — scope-lock session with Mohammad Da + you | ORM Discovery |
| **Thu** | FAQ → CRM hand-off spec drafted (Q2 board commitment) | CS / CRM |
| **Thu** | Marketing Newsletter container migration — kickoff (Yasha asked 2026-05-06; lift off EP1 → Docker on `sentimark-env`, our largest persistent cost line) | Cost / infra |

## ORM-Agent — what it does, where it runs, who uses it

**The pitch:** auto-moderate negative or critical comments on our social pages so the team stops the "check pages every few hours" loop.

### Scope
Detect → hide → DM the commenter for contact → delete after reply → hand off to Sales (CRM email template). High-severity items pause for human review in the existing chat UI (operator console — no new tool to learn).

### Channels
| Platform | Handle | MVP |
|---|---|---|
| Facebook | seekapaofficial | yes |
| Instagram | seekapaofficial | yes |
| Twitter / X | SeekapaOfficial | post-MVP |

### Languages
EN + AR for MVP. HE + ES post-MVP.

### Compliance — already designed in
No financial advice. No account-specific info echoed. Risk warnings preserved. Restricted-country detection. EU/IL data residency. Retention 90d / 12mo.

### Volume baseline
**TBD — Mohammad Da to provide Q1 page-comment volume.** This sets auto-action vs human-review threshold.

### What I do on ORM this week
1. Walk you and Mohammad through the existing design (`~/projects/ORM-AGENT/ORM-PLAN.md`).
2. Lock 5 open questions: auto-hide threshold, sales hand-off channel, DM-ask phrasing legal sign-off, X scope, operator console reuse.
3. If signed off Thu: start KB indexing (Phase 1 — 1–2 days, no customer-visible change yet).

## Active threads I'm carrying (for context)

- **Hiya call branding** (vendor: Olanda Katuruza). Pricing locked: €750/mo for 5,000 calls + €0.15–0.16/call. Multi-brand (Seekapa + Axia) supported with one number per brand. **Outstanding:** Bluepine LTD company / VAT / signatory details to vendor — Nadav owns; I support if technical bridge needed. 48 hours to live after signed.
- **Compliance Exam re-engaged.** Karim emailed 2026-05-07: he sees it as the 3rd pillar (Training → Call Analyze → Compliance Exam → improve agents) and delegated to **Nissreen S. (Axia)** for the user-readiness gap list. Decision should wait on Nissreen's reply — not "leave standalone" as I previously suggested.
- **Video Flows** (ElevenLabs / HeyGen). Adnan reviewed 2026-05-05 and pushed back: generation failed errors, AI reading its own prompt, "hard for marketing users". His ask: simplify to a 6-step flow (fields → preview → avatar → generate → edits → download) or kill the project. Decision call this Wed.

## Decisions waiting on you

| # | Question | My recommendation |
|---|---|---|
| 1 | **Daily Market Overview** — ship to floor (Karim/Amir asked) or kill? | **Kill.** No internal owner; Oded's prod variant already stopped. |
| 2 | **Compliance Exam** — what next? | **Chase Nissreen S.** for the user-readiness gap list (per Karim 2026-05-07). Don't decide integrate-or-leave until we have her list. |
| 3 | **Calls + CRM analytics** — sales scope or retention scope? | **Need by Wed** so it lands in the next sprint. |
| 4 | **Video Flows** — rebuild simplified UI per Adnan's 6-step flow, or kill the project? | **Decide together on Wed call.** I lean toward simplify-then-pilot with one marketing user; if no adoption in 2 weeks, kill. |

ORM is no longer in this list — I'm scoping it actively. Your ORM ask is the Thu walkthrough + sign-off on the 5 open questions.

## Risks I'm tracking

| Risk | What I do about it |
|---|---|
| Training Platform PROD stays down | Sun fix + post-mortem; if not back by EOD Sun, escalate to Yasha Mon AM. |
| CS agent quality slips post-v110 | Daily quality check Mon–Tue; one-prompt rollback path ready. |
| HCTA further delay | Wed slot reserved; no other deliverables that day. |
| BI publishes a conflicting customer-funnel number | Already strip "industry benchmark" outputs from the MCP this week (PR 247). |
| ORM scope drift before any code | Lock 5 open questions Thu; no implementation until Mohammad + you sign off. |
| Video Flows direction stays ambiguous | Wed decision call closes it one way or the other this week. |

## Reference

- This page: `Corp-AI/_wiki/Weekly-Plans/Week-of-2026-05-10`
- CS Agent FAQ + KB: `Corp-AI/_wiki/CS-Agents/`
- ORM design (engineering detail): `~/projects/ORM-AGENT/ORM-PLAN.md`
- Board deck (May): `~/AI_Status_Meeting_May_2026 - Copy.pptx`
