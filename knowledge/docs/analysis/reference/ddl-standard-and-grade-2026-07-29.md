# Where the post stands, graded against how the field actually publishes

Read alongside `SYNDICATION-PLAN.md`. This is the quality bar; that one is the
distribution plan. Nothing here is opinion about taste, it is a rubric derived
from posts that demonstrably work, applied to ours.

## The reference set

| source | what it is | what it does better than us |
| --- | --- | --- |
| [JFrog: why model routing backfires](https://jfrog.com/blog/why-model-routing-backfires/) | analysis piece | Opens on a **promise/contradiction**. Headings form a problem → diagnosis → prescription arc: "What You Should Not Do" then "What to Do Instead" |
| [JFrog: NuGet typosquat](https://jfrog.com/blog/nuget-typosquat-targets-betting-platform/) | security research | **Artifacts as proof**: nuspec XML, IL transpiler code, C2 POST with the hardcoded key, SHA256 per payload. Named section arc: The Bait / The Evolution / The Trigger / The Patch / Exfiltration |
| [Cloudflare: 18 Nov 2025 outage](https://blog.cloudflare.com/18-november-2025-outage/) | incident writeup | **Leads with impact, then root cause, before narrative.** Timeline table, service-impact table, the actual Rust panic. Closes on remediation, not reflection |

## The rubric

Ten criteria, drawn from what the three above have in common. Score 0-3.

| # | criterion | test |
| --- | --- | --- |
| 1 | **Subject legible in 10 seconds** | Can a cold reader say what this is about from the first screen? |
| 2 | **Lead with finding, not setup** | Is the outcome stated before the story that produced it? |
| 3 | **Named target** | Is the exact system named and disambiguated from its siblings? |
| 4 | **Artifacts, not descriptions** | Are the raw inputs shown, or only characterised? |
| 5 | **Structured evidence** | Tables/timelines where the data is tabular, rather than prose lists |
| 6 | **Section arc** | Do headings form a progression, or are they a list of topics? |
| 7 | **Depth layering** | Casual reader gets the top, expert gets the mechanism, neither is blocked |
| 8 | **Quantified everywhere** | Numbers with provenance, not adjectives |
| 9 | **Synthesis block** | An explicit takeaways section that survives being read alone |
| 10 | **Ends with agency** | Closes on what changes, not on how it felt |

## The grade

Scored before this session's edits, and after.

| # | criterion | before | after | note |
| --- | --- | --- | --- | --- |
| 1 | Subject legible in 10s | **0** | **3** | Was a story hook with no subject for several screens. Added the brief |
| 2 | Lead with finding | **1** | **2** | Brief states the outcome; the h1 is still narrative. Deliberate, it is a case ledger |
| 3 | Named target | **0** | **3** | "WhatsApp" is three clients; only Desktop keeps a decryptable store. Now named with store, key, read path |
| 4 | Artifacts | **1** | **2** | One prompt shown before. Now the five corrections verbatim. **Still missing: the decryption code** |
| 5 | Structured evidence | **2** | **3** | Cost table existed; corrections table added |
| 6 | Section arc | **1** | **1** | **Unchanged, and the weakest remaining.** Headings are topics, not a progression |
| 7 | Depth layering | **1** | **1** | **Unchanged.** One register throughout; no path for a reader who wants only the finding |
| 8 | Quantified | **3** | **3** | Token counts, wall clock, message counts, all transcript-derived |
| 9 | Synthesis | **3** | **3** | Defects + research questions. Stronger than any post in the reference set |
| 10 | Ends with agency | **2** | **2** | Closes on research questions, which is agency of a kind |
| | **total** | **14/30** | **23/30** | |

**Where the piece is distinctive (corrected 2026-07-29 after a prior-art
search):** NOT the failure taxonomy. Naming agent failure modes is a populated
field, a prior-art search fired all four not-a-gap signals: the FAGEN workshop
(ICML 2026), taxonomy papers (MAST "Why Do Multi-Agent LLM Systems Fail?",
FailureAtlas, Aegis), named benchmarks (TRAIL, Who&When, AgenTracer, AgentDebug),
products (LangSmith, AgentDebugX), and first-person AI-agent postmortem blogs
already exist (Sattyam Jain's "$4,200 in 63 Hours"). What IS distinctive is the
FORM: a first-person narrated case-ledger tied to a single mundane consumer task
with the operator's real one-line corrections shown verbatim. That is a craft
distinction, not a research contribution, and the syndication copy should lead
with the story and the telling, not a claim to name failure modes first.
Queries logged: "LLM agent failure mode taxonomy trace analysis self-report
post-mortem survey" / "AI agent writes its own postmortem first person account
of failures blog" / "agent trace debugging failure taxonomy tool observability
product LangSmith postmortem".

**Where we are still behind:** artifacts and structure, criteria 4, 6 and 7.

## The refactor still owed

Three items, in value order. Not started.

1. **Show the decryption chain as code.** JFrog earns its credibility by pasting
   the IL transpiler, not by describing it. We describe an ODUID → DPAPI-NG →
   AES-OFB chain and show none of it. A dozen lines of the real key-derivation
   walk, with the machine-specific values redacted, converts the central claim
   from assertion to evidence. This is the single highest-value edit left.

2. **Rewrite the headings into an arc.** Currently topics: "The photograph",
   "Ten hours, drawn", "What it cost". The JFrog pattern would be closer to:
   *The ask → The obstacle → Five wrong answers → Why they were all wrong →
   The store → What the corpus showed → What it cost → What broke → What is
   still open.* Same sections, ordered and titled so the table of contents reads
   as an argument.

3. **Add a depth-layered entry.** A reader who wants only the finding should be
   able to stop after the brief; one who wants the mechanism continues. Mark the
   boundary explicitly rather than hoping they scroll.

## How to check it

`case-ledger-post/shots.py` renders at 1440 and 390 and reports horizontal
overflow. Run it after any structural edit. Both defects fixed earlier in this
session were invisible in the CSS and obvious in the screenshot.

```bash
python shots.py <url> --widths 1440,390 --scroll 0,900,4200 --out shots
```


---

## Loop re-grade, 2026-07-29 (ultracode)

Re-scored after closing the three refactors, references read at SOURCE this time
(not summaries): JFrog uses rhetorically-functional headings (setup / mechanism /
diagnosis / prescription); Cloudflare leads impact then root cause, timeline
table near the end.

**26/30, up from 23.** Movers: artifacts 2->3 (decryption chain shown as
redacted code), section arc 1->2 (headings rewritten into an argument), depth
1->2 (depth boundary marker added). Synthesis (9) scored reference-grade: the new
"The one mistake under all five" section names the shared mechanism (resemblance
promoted to identity, held at flat confidence).

**Still capped at 2, structural:** criterion 5 and 8 (time cost carried as prose
estimates, no logged-provenance timeline table) and the arc's "which the next
section takes apart" forward pointer slightly overshoots the success pivot.

### The thing the rubric did not test, and an adversarial critic caught

The re-grade panel flagged HOLD on an **integrity contradiction**, not a rubric
item: the piece claimed "no hints / uncontaminated / unfalsifiable" while the
corrections table (added this session) reproduces the operator's verbatim hints,
one labelled "a final hint". Fixed: reconciled to "withheld the answer, gave
corrective bounds", with the table as evidence. Also corrected a FAGEN
over-attribution (verified against the workshop page: it names four contribution
TYPES, not a four-pattern failure taxonomy). Lesson for the rubric: add an
**11th criterion, internal consistency** (no claim contradicted by the piece's
own evidence), because a structural rubric can score 26/30 on a piece with a
thesis-level self-contradiction.

### Residual (documented, not fixed)

- Research-questions section is overwritten and redundant with the defects
  section; an editor would cut it by half. Kept because it carries the
  "ends with agency" score-3 material; trimming risks that.
- Criteria 5/8: a real timeline table with logged timestamps would lift both.
