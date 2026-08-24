# Markets and Jurisdictions

**Status:** DRAFT — needs compliance/legal review before publishing to customer-facing KB.

**Why this exists:** Yasha's 2026-05-04 production test (Telegram conversation) exposed a knowledge gap: the bot was making up countries ("please confirm you're joining from Jamaica" — Jamaica was never mentioned), treating Dubai as separate from UAE, and hedging the unsupported-jurisdiction list with "and some other regions". None of this was grounded in any document the bot could retrieve. This page is the first step toward fixing that.

## Authority

Seekapa is operated by **BluePine LTD**, FSA Seychelles License **SD183**. The authoritative source for which jurisdictions are eligible is the **Client Agreement** signed by every customer at registration. This page summarizes that agreement for cs-agent grounding, but the agreement itself remains the legal source of truth. If this page disagrees with the Client Agreement, the Client Agreement wins.

## Ineligible jurisdictions (best-known list, 2026-05-04)

These are the regions the bot has historically cited as excluded. Sourced from the bot's own production replies (which read from the Client Agreement at deployment time). **Compliance must verify this list against the current Client Agreement before this doc moves from `docs/wiki/` into the customer-facing FAQ KB.**

- **EEA member states** (European Economic Area — all EU countries plus Iceland, Liechtenstein, Norway)
- **United States** (USA)
- **British Columbia** (province of Canada — listed separately from Canada because BC has stricter securities regulations)
- **Japan**
- **Canada** (entire country, which makes British Columbia redundant — flagged for legal cleanup)
- **Australia**
- **Israel**
- "and some other regions" — **unacceptable hedge, must be enumerated by compliance**

## Eligible jurisdictions (positive list — TODO)

This is the gap. The bot today only knows what it CAN'T support, not what it CAN. Compliance to provide:
- Definitive country allow-list, OR
- Confirmation that allow-list = anything not in the deny-list above.

## Common-knowledge geography rules

The cs-agent must know these unambiguous facts to avoid the kind of confusion the 2026-05-04 conversation showed:

| Customer says | Bot must understand |
|---|---|
| "I'm from Dubai" | Dubai is one of the seven emirates of the **United Arab Emirates (UAE)**. Treat as UAE. Do NOT ask "UAE or Dubai (UAE)?" |
| "I'm from Abu Dhabi" / "Sharjah" / "Ajman" / "Umm Al Quwain" / "Ras Al Khaimah" / "Fujairah" | Other UAE emirates. Same as Dubai → UAE. |
| "I'm from Hong Kong" | Hong Kong SAR — distinct jurisdiction from China for most regulatory purposes. Treat separately. |
| "I'm from Macau" | Macau SAR — distinct from China. Treat separately. |
| "I'm from Scotland / Wales / N. Ireland / England" | Part of the **United Kingdom (UK)**. Treat as UK. (The UK is no longer in the EEA post-Brexit; check Client Agreement for UK-specific rules.) |
| "I'm from California / Texas / Florida" / any US state | Part of the **United States (USA)** — currently in the deny-list. Treat as USA. |
| "I'm from British Columbia / BC" | Canadian province; deny-listed. |
| "I'm from Quebec / Ontario / Alberta" | Canadian provinces; Canada is deny-listed → deny. |

## Bot grounding rules (for v109 prompt KB ANCHOR FACTS)

When a customer mentions a jurisdiction the bot must:

1. **Never invent a country name.** If the customer hasn't said where they're from, ASK — don't guess.
2. **Resolve city/state/region to country first.** "Dubai" → "UAE". "California" → "USA". "Edinburgh" → "UK".
3. **Check the deny-list**, not a fuzzy memory.
4. **If unsure**, redirect to compliance: "I can't confirm jurisdiction eligibility from chat. Please check the Client Agreement at registration, or contact support@seekapa.com."
5. **Don't use "and some other regions"** as a hedge. Either the country is on the list or it isn't.

## Open questions for compliance / legal

1. Is the deny-list above current as of 2026-05? Last verified date?
2. What's the EXACT wording in the Client Agreement for the unsupported regions?
3. Is the EEA list identical to the EU member states list?
4. Are there sub-national exclusions besides British Columbia (e.g., specific US states with extra restrictions)?
5. How does Brexit affect UK eligibility? (Pre-2020 the UK was in the EEA; post-Brexit it's not — the bot should know.)
6. What about post-2026-04 changes — Cyprus, Malta, etc.?

## Until this doc is approved by compliance

- **Do NOT add this content to `Seekapa_FAQ_KB.txt`** (the production vector store).
- The cs-agent will continue to default to "depends on account type — check your dashboard or contact support@seekapa.com" for jurisdiction questions.
- The v109 prompt's KB ANCHOR FACTS section gets the **Dubai = UAE rule** + the **never-invent-country rule** added immediately (those are unambiguous and don't need compliance signoff).

## See also

- [Knowledge Base](./Knowledge-Base.md) — index of all KB sources
- [Compliance](./Compliance.md) — escalation policy, privacy, regulator info
- [Conversation Design](./Conversation-Design.md) — how the cs-agent handles jurisdiction questions today
