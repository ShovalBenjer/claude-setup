# Pocock's skills repo, measured against ours

Source: `mattpocock/skills` v1.1.0, MIT, unpacked at `~/.claude/downloads/skills-1.1.0`.
Read in full: `CLAUDE.md`, `CONTEXT.md`, `.agents/invocation.md`, `.agents/writing-docs.md`,
`.agents/adr/0001`, `.claude-plugin/plugin.json`, all 38 skill frontmatters,
`writing-great-skills/{SKILL.md,GLOSSARY.md}`, `wayfinder/SKILL.md`, `ask-matt/SKILL.md`,
`docs/engineering/wayfinder.md`.

The linked video is `F3lL98Pj90o`, "/wayfinder: Nothing is too big to plan anymore", Matt Pocock
(title read from YouTube's oembed endpoint). **The transcript could not be fetched** and no
transcript was read: `youtubetranscript.com` returned YouTube's own block message, and a plain
WebFetch of the watch page returns the SPA footer with no metadata. The `youtube-distill` skill
would have worked but drives Chrome to Gemini, which is outside a single analysis pass. So the
video's argument here is reconstructed from the two primary artifacts the video demonstrates,
`skills/engineering/wayfinder/SKILL.md` and `docs/engineering/wayfinder.md`. Anything in the
video that is not in those two files is not in this document.

## 1. The number

Every skill description sits in the context window on every turn. That is the tax a
model-invoked skill charges. Measured 2026-08-01:

| tree | skills | description chars | approx tokens/turn | user-invoked |
|---|---|---|---|---|
| ours, live `~/.claude/skills` | 38 | 11,709 | ~2,930 | **0** |
| ours, canonical `dot-claude/skills` | 71 | 22,694 | ~5,670 | **0** |
| pocock, model-invoked only | 17 of 38 | 1,971 | ~490 | 21 of 38 |

He ships the same number of skills as our live tree and pays **one sixth** the standing context
for them. Two independent factors produce that, and they compound:

- **Invocation.** 21 of his 38 carry `disable-model-invocation: true`, which strips the
  description from the agent's reach entirely. Ours: zero, in either tree. We have never used
  the field.
- **Description length.** Even counting only his model-invoked skills, his average description
  is 116 chars against our 308. His stated cause is duplication: synonyms that rename one
  trigger branch rather than adding a branch. Ours are full of it (`azure-runtime` at 736 chars
  lists five ways of saying "call Azure runtime" plus a four-item SKIP list).

`disable-model-invocation` is not his invention and not speculative. Anthropic's own official
plugin marketplace uses it, at
`~/.claude/plugins/marketplaces/claude-plugins-official/plugins/claude-security/skills/claude-security/SKILL.md`
and in `plugin-dev/command-development`.

Our gate is compatible with the change. `tools/map/codemap.py` derives a skill directory's
purpose from its SKILL.md `description` frontmatter (`from_frontmatter`, line 137), and the
convention keeps the description while making it human-facing, so nothing in `codemap check`
breaks. `PRIOR_ART_LOC = 300` counts Python LOC, so a markdown-only skill does not owe a
prior-art record however long it gets.

## 2. The pattern set worth generalizing

### 2.1 Invocation is a two-load trade, and both loads are real

The insight our setup has never made explicit: a skill that only the human can invoke costs
**zero context load** and spends **cognitive load** instead, because the human becomes the index
that has to remember it exists. Model-invocation buys agent discovery at a permanent per-turn
price.

His framing that we lack: cognitive load is **not a cost to minimise**. It is the price of human
agency, and the reason some skills should stay user-invoked even when auto-firing would work.
Spend it where human judgement matters.

Consequence we would inherit: a user-invoked skill has no description, so **nothing but the
human can reach it**, including other skills. Chains have to be re-checked before flipping
anything. That is the one hard constraint on the refactor in section 4.

### 2.2 The router skill

When user-invoked skills multiply past what a human can hold, the cure is one user-invoked
**router** naming the others and when to reach for each. His is `ask-matt`. It is not a menu: it
is a map of *flows*, a main flow (idea to ship) with named on-ramps merging onto it, plus
standalones and a vocabulary layer underneath.

We have 38 live skills, 71 canonical, and roughly 30 agent types, and no router at all. This is
the largest immediate gap, and it is larger for us than for him because our surface is bigger.

His maintenance rule is the part that keeps a router honest, and it is enforced in `CLAUDE.md`:
whenever a user-reachable skill is added, renamed, removed, or changes how it fits the flows,
re-read the router and update it. *A router that lies is worse than no router.* That sentence
belongs in our gate, not just in a doc, since it is exactly the class our `pointers.py` already
checks for hooks.

### 2.3 The information hierarchy, and progressive disclosure as its defence

A three-rung ladder: in-skill step, in-skill reference, disclosed reference behind a pointer.
The load-bearing claim is that in-file reference which *should* be disclosed **buries the steps
and turns attending to them into a coin flip**. Disclosure is a variance lever, not a token
optimisation.

Measured against us: 22 of our 38 live skills have `SKILL.md` as the entire skill, no disclosed
files at all. Our longest are `shoval-voice-draft` at 477 lines and `case-ledger-post` at 394,
both a single flat file. His longest `SKILL.md` is `teach` at 140 lines, and `triage` is a
112-line SKILL.md disclosing a 207-line `AGENT-BRIEF.md` and a 105-line `OUT-OF-SCOPE.md`. His
whole 38-skill corpus is 4,507 lines.

The disclosure test he gives is sharper than "is it long": **branching**. Inline what every
branch needs; push behind a pointer what only some branches reach.

### 2.4 Leading words

A **leading word** is a compact concept already in the model's pretraining that the agent thinks
with while running the skill (his: *tight* loop, *red*, *deep module*, *fog of war*, *tracer
bullets*). Repeated as a token rather than restated as a sentence, it accumulates a distributed
definition and anchors a region of behaviour in the fewest tokens, because it recruits priors
the model already holds.

It pays twice. In the body it anchors execution. In the description it anchors invocation, and
not only inside the skill: when the same word lives in your prompts, your docs, and your
codebase, the agent links that shared language to the skill and fires it more reliably.

The refactor move he names, which applies directly to our corpus: hunt triads spelled out at
three sites and collapse them into one pretrained token. "fast, deterministic, low-overhead"
becomes *tight*. "a loop you believe in" becomes *red*.

We already do this accidentally and inconsistently. `lane`, `oracle`, `gate`, `ledger`, `fog`,
`drift`, `payload` are our leading words and none of them is declared anywhere as such.

### 2.5 The failure-mode vocabulary

Six named failure modes, each paired with the lever that cures it. Four of them describe
conditions our corpus demonstrably has:

- **Sediment.** Stale layers that settle because adding feels safe and removing feels risky. The
  default fate of any skill without a pruning discipline. Our canonical tree has 71 skills and
  our live tree has 38; the 35-skill delta is sediment with a name.
- **Sprawl.** Length itself, even when every line is live and unique.
- **No-op.** A line the model already obeys by default. The test is model-relative and settled by
  running the skill, not by argument. Notably: *a leading word too weak to beat the default is a
  no-op*, and the fix is a stronger word, not a different technique.
- **Negation.** Steering by prohibition drags the forbidden behaviour into context and makes it
  more available. Prompt the positive.

**Negation is where our own rule files are worst.** `~/.claude/rules/` is written almost entirely
in prohibitions: no decorative emoji, no mocks, do not present a truncated read as exhaustive,
avoid absolute completion language. Every one of those names the elephant. Whether that costs us
anything is measurable and unmeasured; it is the first thing to test rather than assume.

### 2.6 The repo's own consistency contract

His `CLAUDE.md` is a set of enforceable invariants, not advice. Promoted buckets must appear in
the top-level README and `plugin.json`; non-promoted buckets must not appear in either; each
promoted skill owes a docs page; the router must be re-synced on any change. Buckets
(`engineering`, `productivity`, `misc`, `personal`, `in-progress`, `deprecated`) give
work-in-progress and dead skills a place to live that is not the live tree.

We have no bucket concept, which is why our canonical tree carries 71 skills with no signal
about which are live, which are drafts, and which are dead.

### 2.7 The soft/hard dependency split (his ADR-0001)

Skills that cannot function without per-repo config carry an explicit "run `/setup` if not"
pointer. Skills that only use the config to sharpen output reference it in vague prose and
degrade gracefully. The split keeps the setup pointer out of places where it is not
load-bearing. This is the same reasoning as our waiver-with-expiry discipline, applied to
prose pointers.

## 3. The wayfinder concept, generalized, without the tags

The operator's constraint: not the `wayfinder:` label namespace. The concept is more general
than what we have.

Stripped of the tracker mechanics, the idea is a **shared map with a named destination and an
explicit fog boundary**, worked one decision per session:

- **Destination.** Named first, before any ticket exists, because it fixes the scope every
  ticket is measured against. Not the deliverable; the point at which nothing is left to decide.
- **Plan, do not do.** Every ticket resolves a *decision*. The pull to just do the work is the
  signal you have reached the edge of the map and it is time to hand off.
- **Index, not store.** A decision lives in exactly one place, its ticket. The map gists and
  links, never restates. Sessions load the map at low resolution and zoom on demand.
- **Fog of war.** What you can tell is coming but cannot yet phrase sharply. The test for
  ticket-versus-fog is whether you can *state the question precisely now*, not whether you can
  answer it. Resolving a ticket graduates whatever is now specifiable.
- **Frontier.** Open, unblocked, unclaimed. Rendered by native blocking so the human sees what is
  takeable without opening the map.
- **Out of scope.** Ruled beyond the destination. Closed, never graduates, and deliberately kept
  out of the decision index because a scope boundary is not a step on the route.
- **HITL versus AFK per ticket**, with the hard rule that the agent never answers the human's
  side of a HITL ticket.
- **One ticket per session, always.**
- **Refer by name, never by bare id.** A wall of `#42, #43, #44` is illegible.

Four of these we have nothing equivalent to: the fog boundary as a written artifact, the
sharpness test that governs it, out-of-scope as a closed non-route record, and the one-ticket-
per-session bound.

**This is not adopted here, on purpose.** Mapping it onto our setup is a design decision, not an
import, because it would have to reconcile four surfaces that already overlap:

1. `TODO.md`, the single ticket list, grouped by layer and ticket-tagged.
2. `state/claims.jsonl`, the per-session lane claim.
3. `tools/selfimprove/scan.py`, which ranks what to pick up next.
4. The Zion GitHub Project, which already carries `Priority`, `Ingestion` (S1 to S6),
   `Estimate (min)`, `Status` including `Review`, and native `Parent issue` /
   `Sub-issues progress` per `docs/specs/archive/2026-07-31-zion-board-as-product-instrument.md`.

Zion is the natural host, and the mapping is nearly free: destination becomes an epic body
section, frontier becomes a saved view over unblocked-and-unassigned, fog becomes a board field
or a body section on the epic, out-of-scope becomes `Status: Closed` plus a one-line epic note.
No new label namespace is required, which is what the operator asked for. But the *choice* of
which of the four surfaces owns the map, and whether the other three collapse into it or stay,
is a `/diverge` decision under the out-of-distribution rule. Left for the operator.

## 4. What was changed, and what was not

Applied in this pass, canonical tree only (`dot-claude/skills`), listed in the commit:

- Imported `writing-great-skills` adapted, with MIT attribution.
- Added `skillmap`, a router over the user-reachable skills.
- Flipped a measured tranche of skills to `disable-model-invocation: true`.

**Staged, not live.** All three land in `dot-claude/skills`, which is payload. The live tree at
`~/.claude/skills` is unchanged and still pays the full 11,709 chars per turn until deployed.
`python tools/audit/skills_sync.py check` already reports 49 drifting items before this change,
so the drift count moves and that is expected, not a regression.

Not done, and each is its own decision:

- The description-pruning pass. Cutting 308 chars average to his 116 means rewriting 38 to 71
  descriptions, and a description rewrite changes when a skill fires. That is a behaviour change
  per skill, not a mechanical edit.
- Buckets. Our 71-versus-38 sediment wants his `in-progress` / `deprecated` split, but sorting
  71 skills into buckets is an operator judgement about what is dead.
- The negation audit of `~/.claude/rules/`. Testable, untested.
- Wayfinder-onto-Zion, per section 3.
- Any gate rule enforcing router freshness. `tools/audit/pointers.py` is the obvious host, since
  a router naming a skill that does not exist is the same class it already catches for hooks.
