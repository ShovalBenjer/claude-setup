---
name: case-ledger-post
description: Turn a long working session into an interactive illustrated case-ledger post: the route taken, dead ends with receipts, measured cost from the transcript, and lessons. Manim-style diagrams, interactive explainers, real screenshots. Triggers on "write this up as a blog post", "showcase this session", "case ledger", "post-mortem with visuals", "turn this into a writeup".
model: opus
---

# Case Ledger Post

Turn a session that actually happened into a publishable, interactive story: the
route, the wrong turns, the break, the measured cost, and what survived.

The genre is a **case ledger**, not a tutorial. A tutorial pretends the path was
straight. A ledger shows the dead ends, because the dead ends are the content.
If the session went straight to the answer, this is the wrong skill.

## The rule that makes it good

**Only real material.** Real screenshots from the work, real numbers parsed from
the transcript, real quotes from the operator, real wrong turns named as wrong.
No reconstructed "and then I cleverly realised". If a claim cannot be traced to
something in the session, cut it.

The self-deprecation is the engine. The failures carry the story and buy the
credibility that makes the win land.

## Step 1: mine the session for real numbers

Never estimate what can be parsed. The transcript is at
`~/.claude/projects/<project-slug>/<session-id>.jsonl`, one JSON record per line.

```python
import json, collections, datetime
tot=collections.Counter(); models=collections.Counter(); tools=collections.Counter()
first=last=None; n=0
for line in open(PATH, encoding="utf-8"):
    try: d=json.loads(line)
    except: continue
    n+=1
    ts=d.get("timestamp")
    if ts:
        first = first or ts; last = ts
    m=d.get("message") or {}
    if isinstance(m,dict):
        if m.get("model"): models[m["model"]]+=1
        for k,v in (m.get("usage") or {}).items():
            if isinstance(v,int): tot[k]+=v
        c=m.get("content")
        if isinstance(c,list):
            for b in c:
                if isinstance(b,dict) and b.get("type")=="tool_use": tools[b.get("name","?")]+=1
```

Report wall clock, record count, `output_tokens`, `input_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`, the model mix, and the
tool histogram.

**Do not print a percentage of the plan's weekly allowance.** Quota lives
server-side and is not exposed to the session. Say so plainly and point at
`/usage`. Inventing that number would poison every real number next to it.

## Step 2: reconstruct the route honestly

Walk the session start to finish and write down, in order: every hypothesis,
what killed it, and what the operator said that redirected you. Operator
one-liners that collapsed hours of work are the best beats in the piece; quote
them verbatim and date them by hour.

Then classify each node: `dead` (pursued and killed), plain (a step), `hit`
(the break). That classification drives the graph colouring.

## Step 3: anonymise before writing a word

- People: initials or a letter (`ע.`), never full names.
- Home addresses, apartment numbers, door codes: **omit entirely**, never
  partially redact.
- The final location: name the kind of place, not the street, unless the
  operator says otherwise.
- Private photos stay out. Public street-level imagery is fine.
- Say explicitly at the end what was withheld and that no private content left
  the machine.

## Step 4: design

Follow the operator's own design system if one exists (for הסדנה, that is
`DESIGN.md`: illuminated ledger, ink and gold, Frank Ruhl Libre display /
Rubik body / IBM Plex Mono data, and the named avoid-list). This skill's default
merges that with Manim's visual grammar, which is the same language: dark
ground, line-work that draws itself, staged reveals.

Tokens that worked:

See "Match the operator's design system exactly" below for the real token
values. Red is used only as rubrication (dead ends, struck rules), never as
decoration; green marks the break.

Both themes are required. Define tokens on `:root`, redefine under
`@media (prefers-color-scheme: light)` **and** `:root[data-theme="light"]` so
the viewer's toggle wins in both directions.

Numbered markers are legitimate here: an investigation genuinely is a sequence.
Do not number things that are not.

## Step 5: build the interactive pieces

Four carry their weight. Each must explain something the prose cannot.

1. **Structure inspector.** Tabs over the real anatomy of the artefact you
   examined (JPEG segments, DB header, packet). Mark the *absent* thing in
   rubric red with a dashed border. Absence is the finding.
2. **Route graph.** Hand-authored inline SVG, nodes plus bezier edges, each path
   animated with `stroke-dasharray`/`stroke-dashoffset` and a staggered
   `animation-delay`. Dead-end nodes get a rubric stroke, the hit gets the find
   colour. Wrap in `overflow-x:auto` with a `min-width`.
3. **Chain stepper.** Numbered buttons plus Back/Next over the technical
   centrepiece, one stage per screen, each with a short real code line. Mark
   completed stages in the find colour.
4. **Radial candidate chart.** Every place or option checked, plotted by
   distance from the anchor, misses in rubric and the hit in green, with
   hover/focus revealing why each failed. This is the single best "look how much
   was eliminated" device.

Plus animated count-ups for the cost figures, fired on `IntersectionObserver`.

Accessibility and hygiene: `role`/`aria-label` on every SVG and control,
`tabindex="0"` on interactive SVG nodes, keyboard focus visible, and everything
gated behind `prefers-reduced-motion`.

## Step 6: build reproducibly

Keep the template and the assets separate:

- `post_src.html` with `__TOKEN__` placeholders for images.
- `blogassets/` with screenshots resized to ~900px, JPEG quality ~60.
- `build.py` base64-inlines each asset into its token and writes the final file.

The Artifact CSP blocks every external host, so all imagery must be data URIs
and no font CDN may be linked. Use local-first font stacks.

`build.py` must self-check and print: unreplaced tokens, tag balance for
`section`/`div`, and a count of em/en dashes (including `&mdash;` entities,
which a naive regex misses).

## Step 7: publish

Load `artifact-design` first, then publish with the Artifact tool. Keep the same
file path to redeploy to the same URL. Favicon stays stable across redeploys.

## Structure that worked

Masthead with a dropped capital and a real opening sentence, the brief, why the obvious approach failed
(inspector), the route (graph), the dead ends with expandable exhibits, the
technical turn (stepper), how the search narrowed (radial), the find with real
imagery, what it cost (counters plus tables plus the quota caveat), the defects it
exposed, the research questions it leaves open, what survived.

## Voice

Shoval's register: direct, dry, no corporate filler, no hedging, short sentences
next to long ones. Funny by being accurate about the failures, never by adding
jokes. **No em dashes or en dashes anywhere**, including HTML entities: use
colons, commas, parentheses, or a full stop.

Never write "seamlessly", "leverage", "delve", "comprehensive", "it's not just X
it's Y", or a rule-of-three list.

## Autoplay, not click-to-reveal

Every apparatus plays on its own, like a looping animation, and pauses when the
reader engages. Click-only interactives read as unfinished, because most readers
never click. Drive each one from an `IntersectionObserver` so it starts when
scrolled into view and stops when it leaves, and cancel the timer on
`mouseenter` or on any explicit selection. Reduced motion skips straight to the
final frame.

## Match the operator's design system exactly, not approximately

Read the real stylesheet, not just the design document. For הסדנה that means
`~/Downloads/daily-deep-learning/style.css`: exact ground `#0b0911`, panels
`#191622`/`#211d2e`, well `#08070d`, ink `#e7dcc2`, gold `#c9a86a`/`#e8c988`,
green `#79b791`, red `#c96a5e`, lines `#332e44`/`#262234`, radii of **3px**, and
grain at `.03` tinted gold rather than neutral.

Two signatures carry the identity and both are cheap:

```css
/* engraved display voice: headings and numerals only, never body text */
text-shadow: 0 1px 0 var(--engrave-lo), 0 -1px 0 var(--engrave-hi);
/* the ONE spring family: every entrance and settle, no other easing */
--spring: linear(0,0.062,0.226,...,1);
```

Light theme flips the engrave values rather than inverting the palette.

## Named bans for this genre

No rotated or skewed "stamp" badges, no spec-sheet metadata rows under the
headline, no centred hero. These read as generated. Open with a dropped capital
and a real first sentence instead, and let a narrow measure (about 64
characters) with wide apparatus blocks do the structural work.

## Prose: write a blog, not a log

The failure mode is bullet-shaped narration that reads like a transcript
summary. Fix it by writing continuous paragraphs in first person, admitting the
error before explaining it, and keeping lists for data only. If a section could
be read aloud and sound like a person talking, it passes.

## Two closing sections that make it worth publishing

**Defects, not lessons.** Name what the session exposed about the agent's
architecture, with evidence from the transcript for each. Structural claims
only: things that are not user error and not fixable by prompting.

**Research questions.** Each one paired with the observation from this session
that motivates it. This is what turns an anecdote into a contribution.

## Name the AI tells, do not just avoid them vaguely

"Make it sound less AI" is not actionable. These patterns have names, and naming
them is what keeps them out. Catalogue:
[LLM_PROSE_TELLS](https://git.eeqj.de/sneak/prompts/src/branch/main/prompts/LLM_PROSE_TELLS.md).

The ones that recur in this genre:

- **Dramatic Fragment.** A clipped phrase appended for emphasis ("Full stop.",
  or a trailing `, with no hints` after a clause). It performs significance and
  carries none. Test: delete it. If nothing is lost, it was decoration.
- **Em-Dash Pivot.** Negation, dash, reframe. Already banned here outright.
- **Negative parallelism.** "It's not X, it's Y." Never write it.
- **Triple Construction.** Exactly three parallel items, always three. Break the
  count or the parallelism.
- **The Pivot Paragraph.** A one-line paragraph carrying no information
  ("But here is where it gets interesting").
- **Throat-Clearing Opener.** A first paragraph that adds nothing. Start on the
  fact.
- **Symmetrical Section Length.** Sections all landing in the same word range.
  Let importance set length.
- **Absence of Mess.** No contradictions, no tangents, no rough edges. In a case
  ledger this one is fatal, because the mess *is* the subject.

**Staccato Burst** deserves care: real bursts and generated ones look similar.
The tell is evenness. Generated cadence is matched and parallel; real writing is
lopsided.

## Position the work against live research, not against nothing

A trace is an anecdote until it is placed. Before writing the defects section,
search the current workshop landscape for the vocabulary the field is already
using, then label each failure with the pattern it instantiates.

This worked because the mapping was real, not decorative. The ICML 2026
[FAGEN](https://fagen-workshop.github.io/) workshop on failure modes in agentic
AI names four recurring patterns, and a single long session had produced all of
them: **latent contamination** (a bad assumption at step 3 poisoning step 50),
**confirmation bias** (landing early, then defending), **self-pollution**
(reading back memory the agent degraded itself), and **budget misallocation**.

Two rules:

1. **Only claim a mapping that holds.** If the failure does not actually match
   the named pattern, do not label it. A forced citation is worse than none.
2. **Say what the piece contributes.** Not the finding, the artefact: a fully
   logged, cost-accounted trace in which the known failure modes co-occur.

Also reposition the operator. A session where a human withholds ground truth,
runs an external verification gate, forces transcript-parsed cost accounting and
demands a harder post-mortem is an **evaluation protocol**, not a chat. Describe
it as one, with the four design decisions named. Otherwise the piece reads as
someone idly prompting, which misrepresents the work.

## Do not ship the boxed card, and do not leave the desktop margin empty

Two defects showed up in review of the first post, both worth encoding.

**The card was generated-design house style.** The apparatus blocks were filled
rounded rectangles on a cream ground with a notched corner tab holding a
small-caps label. That specific combination, warm cream plus serif display plus
`rounded-lg` plus an accent rail on a card, is the current default look of
generated design, and it reads as such however good the content is. Replaced
with a typographic aside: a rule above, a rule below, no fill, no radius, and
the label in the margin. Same "this is an instrument, not prose" signal, none of
the packaging.

Interactive controls got the same treatment. Six floating pills became one
bordered strip of square cells sharing their rules, with selection expressed as
ground and weight rather than a coloured capsule.

**The desktop layout was a phone layout in a wide window.** A 720px column
centred in 1440 with dead space either side, and a hero clamped at `7.4vw` that
hit its cap on every desktop and filled the first screen. Reading measure should
stay near 65 characters, but that is an argument for what to do with the
remaining width, not for wasting it. Above 1180 the shell shifts left and the
freed margin becomes a rail carrying apparatus labels and captions, which is how
[Tufte CSS](https://edwardtufte.github.io/tufte-css/) and
[gwern's sidenotes](https://gwern.net/sidenote) use it. Below that width the
rail content falls back inline.

**Check it with a picture, not with source.** `shots.py` renders the URL at
several widths, reports horizontal overflow, and takes scroll-offset captures so
mid-page sections can be inspected:

```bash
python shots.py <url> --widths 1440,834,390 --scroll 0,4200 --out shots
```

Run it before calling a post done. Both defects above were invisible in the CSS
and obvious in the screenshot.

`shots.py` now audits three things, because page-level overflow missed two real
defects on this post:

- **content clipped inside an `overflow-x:auto` container.** The page does not
  overflow, the container absorbs it, and the reader sees a truncated sentence
  with no scroll affordance. A 560px table on a 390px phone.
- **elements stuck at opacity 0 while in the viewport.** Scoped to the viewport:
  an unscoped version flagged every scroll-reveal section below the fold, which
  are meant to be invisible until reached.
- `--measure <selector>` prints the element's used width and every ancestor's,
  with the `width`/`min-width`/`max-width` that set them.

**Cascade order beats media queries.** A `@media` block placed *before* the base
rules it overrides loses at equal specificity, silently. On this post the phone
table rules sat above `.corr td.q{width:42%}` and never applied: the cell
measured 144px of a 342px row while its own labels ran full width, and it looked
like a mysterious wrapping bug. Put responsive overrides *after* the rules they
override, and confirm with `--measure` instead of reasoning about specificity.

**Separate "my CSS is wrong" from "the deploy has not landed."** Render the local
file with a `file://` URL when a deploy is slow. And when waiting on a deploy,
grep for a marker unique to *this* change: grepping for a string that already
existed passes instantly and screenshots stale content.

## Grade the draft against how the field actually publishes

Taste arguments go in circles. Score it instead. The rubric below is derived
from three posts that demonstrably work: JFrog's
[model routing](https://jfrog.com/blog/why-model-routing-backfires/) analysis,
JFrog's [NuGet typosquat](https://jfrog.com/blog/nuget-typosquat-targets-betting-platform/)
research, and Cloudflare's
[18 Nov 2025 outage](https://blog.cloudflare.com/18-november-2025-outage/) writeup.

Score each 0-3. Under 20/30 is not ready.

1. **Subject legible in 10 seconds.** A cold reader can say what this is from
   the first screen. A story hook is not a subject.
2. **Lead with finding, not setup.** Cloudflare opens with impact and timestamp,
   then root cause, then narrative.
3. **Named target.** Name the exact system and disambiguate it from its
   siblings. "WhatsApp" is three clients and only one keeps a local store.
4. **Artifacts, not descriptions.** JFrog pastes the IL transpiler and the C2
   POST with its hardcoded key. Describing a mechanism is an assertion; showing
   it is evidence. This is the criterion drafts fail most often.
5. **Structured evidence.** Tables where the data is tabular: timelines,
   version matrices, cost breakdowns.
6. **Section arc.** Headings form a progression, not a list of topics. The
   typosquat piece runs The Bait / The Evolution / The Trigger / The Patch.
7. **Depth layering.** Casual reader gets the top, expert gets the mechanism,
   neither is blocked by the other.
8. **Quantified everywhere.** Numbers with provenance, never adjectives.
9. **Synthesis block.** Takeaways that survive being read alone.
10. **Ends with agency.** What changes, not how it felt.
11. **Internal consistency.** No claim is contradicted by the piece's own
    evidence. Added after a 26/30 piece was caught claiming "no hints /
    uncontaminated" while its own reproduced table showed the operator's
    verbatim hints, one labelled "a final hint". A structural rubric will not
    catch a thesis-level self-contradiction; check it explicitly, and check any
    cited external source actually says what you attribute to it (a workshop
    "lists four patterns" claim turned out to be four contribution *types*).

Record the score in the draft folder with the before/after, so the next session
inherits the diagnosis instead of re-deriving it.

**Where a case ledger can beat the reference set:** none of those three turns
its own mistakes into named, citable failure modes. If the piece has a real
failure taxonomy, that is the contribution, and it should lead the syndication
copy rather than the story.

## Before publishing

- Every number traceable to the transcript, and the quota caveat present.
- Names, addresses and the exact location anonymised; withholding stated.
- Both themes checked; nothing unreadable in light mode.
- No horizontal body scroll at 390px; wide diagrams scroll in their own box.
- Reduced-motion path verified.
- Zero em/en dashes, entities included.
- No Dramatic Fragments: no trailing clipped phrase that survives deletion.
- Each named defect actually matches the research pattern it cites.
- The operator's methodology is described as a protocol, not as prompting.
- No filled rounded card with a corner-tab label; asides are rules and margin labels.
- Rendered at 1440 and 390 with `shots.py`, no horizontal overflow at either.
- The desktop margin does work; it is not dead space around a phone column.
- Scored against the 10-criterion rubric, 20/30 or better, score recorded.
- The raw artifacts are shown, not characterised: prompts, code, keys, tables.
- The target system is named and disambiguated from its siblings.
