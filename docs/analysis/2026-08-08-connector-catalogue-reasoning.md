# Connector catalogue reasoning: which of the ~850 earn a place

Point-in-time reasoning pass, 2026-08-08, lane A. Extends
`docs/analysis/2026-08-08-connector-usage.md`, which measured that nine already
connected connectors were called zero times across 1183 transcripts. That number
is the prior for this file: most things in the directory will not get used even
after being turned on, so a connector needs a specific named task, not a general
plausibility argument. This pass does not call any connector to see what it does;
it reasons from the tool's own MCP instructions text (visible in this session)
and from each project's own AGENTS.md, PRD, and charter row.

No settings were changed. `disabledMcpServers` recommendations below are
proposals for whoever owns lane B, C, and D to apply in their own project,
consistent with the charter rule that a cross-lane need is a proposal, not an
edit (`docs/analysis/2026-08-08-connector-usage.md` did the same for lane A).

## Method and its limit

Grounded on: `docs/charters.md` (lane definitions), `new-recruit/AGENTS.md` and
`new-recruit/docs/prd/job-search-loop.md` (VERIFIED by reading, not summarized
from memory), `daily-deep-learning/AGENTS.md`, and the MCP server instruction
blocks injected into this session for Context7, Zapier, Roboflow, Microsoft
Learn, alphaXiv, HyperFrames, Learning Commons. For connectors with no
instruction text visible in this session (Indeed, Dice, ZipRecruiter, Ashby,
CB Insights, ZoomInfo, Similarweb, Calendly, Google Calendar, FMP, Coursera,
O'Reilly, Canva, Cloudflare Developer Platform, Lucid, Wolfram, Twilio, Google
Cloud BigQuery, Mermaid Chart, CoCounsel Legal), every claim about what the
connector does or costs is ASSUMED from its name and category, not from a read
instruction block. That is stated per row below rather than smoothed over.

## claude-setup (lane A): zero new recommendations

Checked the visible catalogue against what this repo actually does: verify its
own hooks, oracles, and gate; no served app; no external data domain (no
finance, HR, medical, legal, CV, or telephony surface touched anywhere in
`tools/` or `docs/`; ASSUMED from directory inspection, not from an oracled
grep, since a plain-text search for these terms returns "resume" as a false
positive and nothing else). Context7, Exa, and Microsoft Learn are already kept for
library docs, search, and Azure reference, per the prior scan, and nothing in
the newly visible catalogue (Canva, Cloudflare Developer Platform, Lucid,
Wolfram, Zapier, Roboflow, Indeed, Dice, ZipRecruiter, FMP, Coursera, O'Reilly,
Google Calendar, BigQuery, Twilio, Mermaid Chart, Learning Commons, HyperFrames,
Ashby, CB Insights, Calendly, CoCounsel Legal, Similarweb, ZoomInfo) does a task
this repo currently does worse or not at all. Diagramming (Lucid, Mermaid
Chart) is the closest near-miss and it is a nice-to-have: `docs/` is prose and
tables by convention, not diagrams, and the instruction bars nice-to-have from
counting. Verdict: zero. A repo whose entire job is local verification against
its own oracles has no import surface for a connector catalogue to fill.

## new-recruit (lane B): 1 recommendation, 1 flagged-not-recommended

Reading the PRD changed the answer the prior scan gave. That scan said "Indeed
is plausibly on-topic" without having read
`docs/prd/job-search-loop.md`. The PRD's hard constraints (section "Hard
constraints", locked 2026-07-20/21/22) say discovery already runs through
"keyless public ATS JSON APIs. No browser, no login, no ban surface," and names
anti-ban engineering as "binding, not advisory." An Indeed, Dice, or ZipRecruiter
MCP connector is a new login-based surface into a job board, which is the
specific thing the existing architecture was built to avoid. Adding it is not a
default MCP-office call; it is a change to an accepted architecture block
(`accepting-architectures.md`) and needs the operator's own yes, not mine. Ashby
is additionally redundant on top of that: it would duplicate a keyless ATS
scanner that is already built and running. Correcting the earlier framing here
rather than repeating it.

CB Insights and ZoomInfo are enterprise data products (funding data, B2B
contact graphs) priced for teams, not a solo job search, and they contradict the
PRD's own "$0 external spend" target (hard constraint 2, capped Apify fallback
only). Similarweb's company-research value is already covered by free web
search. None of the five clear the bar.

| connector | task | auth cost | evidence |
| --- | --- | --- | --- |
| Google Calendar | Track interview slots once the approval-gated pipeline produces interviews; avoid double-booking. Not currently done by any connector. | Simple OAuth, free Google account (already has one) | ASSUMED |

Second and third slot deliberately empty rather than padded. Gmail was
considered (read-only monitoring of recruiter replies, fits the PRD's
"discovery is passive, multi-source read" framing) and is NOT recommended as a
default-on pick: it is already connected with zero calls across 1183 sessions
(the prior scan's own strongest prior against use), and its cost is not simple
OAuth friction but full-mailbox scope, a real PII exposure the
`pii-handling.md` rule treats as a boundary question, not a convenience one.
This is named as an open operator decision (scope a label/filter first, or
decide the exposure is acceptable) rather than either a silent disable or a
silent keep. Cloudflare Developer Platform was also considered, because
new-recruit runs a phone-accessible Cloudflare Pages command center, but
`AGENTS.md` explicitly gates "exposing local services publicly through
ngrok/cloudflared" behind approval, and no deploy command for the command
center is named in `AGENTS.md` the way daily-deep-learning names `wrangler
pages deploy`. Weaker fit than lane C's use of the same connector; left out
here.

## daily-deep-learning, lane C (learning PWA): 2 recommendations

| connector | task | auth cost | evidence |
| --- | --- | --- | --- |
| Cloudflare Developer Platform | Inspect Pages deploys and Worker/KV state directly, replacing the manual `bun x wrangler pages deploy` / log-check loop named in `AGENTS.md`'s own command list. Direct match: this repo's whole deploy stack is Cloudflare Pages plus a Worker, today driven by hand-typed wrangler commands. | ASSUMED simple OAuth or API token against the Cloudflare account already used for the live site (free tier already in use) | ASSUMED |
| Coursera | Source structured syllabi/topic outlines to seed daily lesson content, on top of the hand-authored lessons. Picked over O'Reilly for the auth-cost reason the operator asked to weight: browsing/auditing is free with a simple OAuth sign-in, no subscription required to read a syllabus. O'Reilly is the same idea at higher cost (paid subscription, no real free tier) if Coursera's catalogue proves too shallow. | Simple OAuth, free tier sufficient for the stated task | ASSUMED |

Learning Commons ("production-ready MCP server for knowledge graph access")
was considered because a knowledge graph maps naturally onto the three-tree
talent board, but the instruction text does not name whose graph or which
domain, and the hard rule against calling a connector to see what it does means
this cannot be resolved without either a live call or a clearer description.
Named as a real candidate that was rejected for being unverifiable from the
catalogue alone, not silently dropped.

## content and writing, lane D (hosted in daily-deep-learning/writing/): 1 recommendation

Lane D's charter already names a hand-built `syndication-engine` doing POSSE
projection with per-platform hooks. That is the one place in all four projects
where Zapier's core competency would appear to map directly onto a stated need;
it is addressed in the dedicated Zapier section below rather than here, and the
verdict there is not to add it.

| connector | task | auth cost | evidence |
| --- | --- | --- | --- |
| Canva | Generate header/share images for case-ledger posts that then go out through the syndication engine; most syndication targets (dev.to, social) want an image and nothing today produces one. | Simple OAuth, free tier likely sufficient for basic templates; paid tier only for brand-kit features | ASSUMED |

No second or third pick for lane D. HyperFrames (video) was considered and
rejected: the lane D charter names text (case-ledger-post) and voice
(voice-metrics) explicitly, never video, so a video connector would be solving
a problem nobody stated.

## Loading recommendation: disabledMcpServers per project

`disabledMcpServers` in `~/.claude.json` is per project path, not per lane.
Lane C and lane D share one path (`daily-deep-learning`), so this is three
lists, not four, matching the three repo paths that exist. None of this was
applied; these are the same kind of proposal the prior scan made for lane B.

The IDs below are read verbatim from `~/.claude.json` (VERIFIED: `grep -o
'"claude.ai [^"]*"' ~/.claude.json`, run 2026-08-08), because the disable
mechanism matches on the exact string, and the prior draft of this file wrote
plain names that would silently fail to match. Only 30 connectors have ever
been cached with a `claude.ai <name>` ID in this file; a name mentioned in the
task prompt but never seen locally (Ashby, CB Insights, Calendly, CoCounsel
Legal, Similarweb, ZoomInfo, Coursera, O'Reilly, Google Calendar, Google Cloud
BigQuery) has no ID to paste yet. Those are listed by name only, with a note
that they need disabling through the connector UI directly, or their exact ID
captured the first time this project's tool list includes them. Separately,
`claude-in-chrome` and `sadna` are local servers: they do not appear under
either project's `mcpServers` or `disabledMcpServers` keys at all in this file,
so they are out of scope for this mechanism, not silently kept on by omission.

**`/home/shov/work/repos/new-recruit`** (currently empty `disabledMcpServers`,
inherits every cached connector). Recommended list, using the verbatim cached
IDs:

```json
[
  "claude.ai SNOMED CT Terminology",
  "claude.ai ICD-10 Codes",
  "claude.ai Clinical Trials",
  "claude.ai Mobbin",
  "claude.ai Wolfram",
  "claude.ai Roboflow",
  "claude.ai Twilio",
  "claude.ai HyperFrames by HeyGen",
  "claude.ai Lucid",
  "claude.ai Mermaid Chart",
  "claude.ai Learning Commons",
  "claude.ai Semrush",
  "claude.ai Dice",
  "claude.ai ZipRecruiter",
  "claude.ai Indeed",
  "claude.ai Canva",
  "claude.ai Cloudflare Developer Platform",
  "claude.ai FMP",
  "claude.ai Microsoft Learn",
  "claude.ai alphaXiv",
  "claude.ai Scholar Gateway",
  "claude.ai PubMed",
  "claude.ai Scite",
  "claude.ai Consensus",
  "claude.ai bioRxiv",
  "claude.ai Anthropic Economic Index",
  "claude.ai Zapier",
  "claude.ai Gmail"
]
```

Plus, by name only, no cached ID yet: Ashby, CB Insights, ZoomInfo, Similarweb,
Coursera, O'Reilly, Calendly, Google Cloud BigQuery. Keep on (not in the
disable list): Context7 and Exa (this repo does real software engineering: the
CDP driver, the SQLite ledger, the scheduler), plus Google Calendar per the
table above. Gmail is deliberately in the disable list, not the keep list: see
the open-decision note above the table.

**`/home/shov/work/repos/daily-deep-learning`** (currently empty
`disabledMcpServers`, covers both lane C and lane D). Recommended list:

```json
[
  "claude.ai SNOMED CT Terminology",
  "claude.ai ICD-10 Codes",
  "claude.ai Clinical Trials",
  "claude.ai Mobbin",
  "claude.ai Wolfram",
  "claude.ai Roboflow",
  "claude.ai Twilio",
  "claude.ai HyperFrames by HeyGen",
  "claude.ai Lucid",
  "claude.ai Mermaid Chart",
  "claude.ai Learning Commons",
  "claude.ai Semrush",
  "claude.ai Dice",
  "claude.ai ZipRecruiter",
  "claude.ai Indeed",
  "claude.ai FMP",
  "claude.ai Microsoft Learn",
  "claude.ai alphaXiv",
  "claude.ai Scholar Gateway",
  "claude.ai PubMed",
  "claude.ai Scite",
  "claude.ai Consensus",
  "claude.ai bioRxiv",
  "claude.ai Anthropic Economic Index",
  "claude.ai Zapier",
  "claude.ai Gmail"
]
```

Plus, by name only, no cached ID yet: Ashby, CB Insights, ZoomInfo, Similarweb,
Calendly, Google Calendar, Google Cloud BigQuery. Keep on: Context7 and Exa
(Worker/wrangler/D1/KV code and boundary tests still need library docs and
search even though the app itself has "no bundler, no framework, by design"),
Cloudflare Developer Platform, Coursera, Canva.

**`/home/shov/work/repos/claude-setup`**: no change recommended to the list
already applied today (see the prior analysis file); nothing in this pass
found a reason to add anything back.

## The do-not-add list, with reasons

- **Indeed, Dice, ZipRecruiter (new-recruit)**: contradict the PRD's locked
  "keyless, no login, no ban surface" discovery architecture and its binding
  anti-ban constraint. Adding any of them is an architecture change, not a
  connector toggle, and needs the operator's own yes.
- **Ashby (new-recruit)**: redundant with a keyless public ATS JSON scanner
  that already exists and runs today.
- **CB Insights, ZoomInfo (new-recruit)**: enterprise-priced data products,
  contradict the PRD's explicit $0 external spend target, disproportionate to
  a solo job search.
- **Similarweb (new-recruit)**: the company-research value it offers is
  already covered by free web search; no gap it closes.
- **Calendly (new-recruit)**: duplicates Google Calendar for the one task that
  matters (track his own interview times) while additionally exposing a public
  booking link, which is an outward-facing surface closer to "third-party
  publication" than personal scheduling.
- **CoCounsel Legal**: no legal work in any of the four projects. Same class
  as SNOMED CT / ICD-10 / Semrush, already correctly scoped off for lane A.
- **Wolfram**: no math-verification need identified anywhere; the gate's
  oracles are assertions, not the kind of computation Wolfram is for.
- **Twilio**: no SMS/telephony surface in any of the four projects.
- **Google Cloud BigQuery**: no GCP data warehouse anywhere; the one project
  with a real data store (daily-deep-learning) uses Cloudflare D1/KV.
- **Roboflow**: computer vision platform, no CV task in any of the four
  projects.
- **Lucid, Mermaid Chart**: diagramming with no stated need in any project;
  nice-to-have class, excluded per the instruction that nice-to-have does not
  qualify.
- **HyperFrames by HeyGen**: no stated video-content need; lane D's own
  charter names text and voice only. Also crosses into Voice and Media
  Studio's owned surface, not something MCP office should wire speculatively.
- **FMP (financial data)**: marginal company-health-check value, already
  achievable with free web search; not proportionate to add a new API-key
  surface for.
- **Semrush**: SEO, no project here runs paid search or organic-traffic
  optimization work.
- **Learning Commons**: real candidate, rejected for being unverifiable from
  its own description without a live call, which the task rules out.

## Verdict on Zapier

Zapier is already connected and has been called zero times across 1183
sessions (VERIFIED, prior scan). Its own MCP instructions, visible in this
session, show the "9000+ apps" number is less alarming than it sounds
mechanically: actions are not all loaded into context at once, they are opt-in
per action through `discover_zapier_actions` and `enable_zapier_action`, so
the standing context cost of having it connected is a handful of meta-tools,
not one tool per app (VERIFIED from the instruction text). That addresses the
"makes the tool list enormous" half of the concern. Whether the free tier
covers multi-step automation, or a paid Zapier plan is required for anything
beyond a single trivial zap, is ASSUMED from general knowledge of Zapier's
pricing model, not read from the connector itself.

It does not address the "force multiplier or not" half. Checked against all
four projects specifically:

- claude-setup: no cross-app automation need; the repo verifies itself.
  (ASSUMED from repo inspection, same caveat as the claude-setup section
  above.)
- new-recruit: the opposite of what Zapier offers. The PRD is built around a
  bespoke, anti-ban-engineered, approval-gated pipeline with a $0 spend target
  (VERIFIED by reading `docs/prd/job-search-loop.md`); Zapier is a generic,
  ASSUMED typically-paid-tier, opaque automation layer, which is the wrong
  shape for a project whose whole design point is precise control.
- daily-deep-learning: "no bundler, no framework, by design" is the stated
  architecture ethos (VERIFIED, `AGENTS.md`); Zapier is an external SaaS
  dependency layer, which is what that ethos is explicitly built to avoid.
- content/writing (lane D): the one place a case could be made, since
  `syndication-engine` already does cross-platform posting (VERIFIED,
  `docs/charters.md` lane D row). But that engine already exists, is in-repo,
  testable, and reviewable, matching this operator's own boundary-contracts
  standard (typed, tested, no raw passthrough). A Zapier zap is a black box
  relative to that standard: its execution is not captured by
  `state/*.jsonl`, not covered by the gate, and not code-reviewable the way
  `syndication-engine` is (ASSUMED characterization of what a Zapier zap looks
  like from the outside, not measured against this repo's own gate, since
  none is wired). Routing lane D's cross-posting through Zapier would mean
  running two automation paths in parallel or replacing a reviewable one with
  an opaque one, not multiplying anything.

Verdict: not a force multiplier for this operator's actual four projects, each
of which already has a purpose-built path for the thing Zapier would offer
generically, and each purpose-built path was a deliberate choice (anti-ban
architecture, no-framework minimalism, boundary-contract discipline) that
Zapier would sit against rather than with. This is not a generic anti-Zapier
claim; a different operator with genuinely ad hoc cross-app needs and no
existing automation would get a different answer. Recommend: leave it
connected only for a genuine one-off integration task with no existing path,
used narrowly for that task, not treated as a standing default for any of the
four projects. Consistent with the repo's own "MCPs are default-off, activate
only what's needed for the current task" rule.
