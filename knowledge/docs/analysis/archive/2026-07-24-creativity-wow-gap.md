# Creativity / wow / deliberation-texture gap analysis

Point-in-time analysis (docs-control-plane: analysis/, input to TODO). 2026-07-24.
Author: lane-B subagent run. Register: calibrated claims (rules/calibrated-claims.md);
every claim tagged VERIFIED / STAGED / ASSUMED.

Operator statement being analyzed: creativity is what the system lacks MOST, and
specifically (a) a "wow effect in every small thing", one deliberate touch above
functional in every artifact; (b) the extra steps of a human colleague on long-horizon
work: "I talked with other agents, we thought of X, we DISAGREED, I suggested Y",
visible deliberation, dissent, opinion; (c) runs whose size matches the intent, because
fast convergence on a broad ask "feels off by a mile".

---

## 1. The gap, named precisely

The system as built is an immune system without a metabolism. Nearly every creative
control that exists is NEGATIVE: slop_lint removes banned phrases, calibrated-claims
removes inflated register, the aesthetic-anchor card removes generic UI, the charters
remove cross-session sameness. Removal of the bad is enforced by hooks and gates
(ADR-0005 done right). Production of the surprising is enforced by NOTHING. The one
positive-generation asset, /diverge, is operator-interactive by design (its step 4 is
an AskUserQuestion), so it cannot fire in exactly the runs the operator is complaining
about: autonomous, long-horizon, multi-agent work. VERIFIED by reading
dot-claude/commands/diverge.md and the nightly workflow prompt (no diverge, no
deliberation, no craft instruction anywhere in .github/workflows/claude-nightly.yml).

Three distinct sub-gaps, which need three different mechanisms:

**Gap A, craft floor vs craft ceiling.** slop_lint guarantees the floor (no slop). No
mechanism asks for the ceiling (one deliberate touch). So artifacts come out clean and
flat: a digest that is only counters, a PR body that is only what/why/verify. The
operator reads "functional" where a human colleague would have left one fingerprint.
VERIFIED: tools/digest/build_digest.py is deterministic aggregation with no craft
element; the nightly PR-body instruction is "what/why, how to verify, which proposal id"
and nothing above functional.

**Gap B, invisible deliberation.** Multi-agent runs happen (hive-mind rules, fanout,
review personas) but their internal texture is discarded at synthesis. The output is the
converged answer; the disagreement, the overruled option, the road not taken are
compacted away. The operator experiences this as flatness and as distrust: convergence
with no visible dissent is indistinguishable from no deliberation at all. This is also
measured behavior, not a vibe: RLHF agents systematically converge (sycophancy), and
same-context ensembles cannot exceed their correlated-error floor (CLAUDE-OS §2b,
debate-martingale finding). VERIFIED that no output schema anywhere in the repo has a
deliberation/dissent field: grep over dot-claude, tools, .github found none.

**Gap C, run size decoupled from intent size.** kernel-anchor.sh already INJECTS the
RUN CONTRACT prose ("a big-intent request gets a big run... converging fast on a broad
ask is a defect"), VERIFIED at dot-claude/hooks/kernel-anchor.sh line 22. But nothing
MEASURES compliance: there is no intent-size classifier, no minimum-fanout floor, no
run receipt, and the Stop-side enforcement point is dead (dot-claude/hooks/
stop-checklist.sh is a one-line WSL-era path `/home/shovalbe/.codex/hooks/
stop-checklist.sh`, VERIFIED broken on Windows; matches TODO P0 "purge WSL-era paths").
Prose that is injected but never audited is exactly the "advisory rule" ADR-0005 exists
to kill.

Root cause across all three: the Deep Work Protocol table (CLAUDE-OS §2b rows 5-6,
wide-then-curate + defixation) assigns enforcement to a "creative-brief skill +
taste.md file". Neither exists. VERIFIED: no creative-brief skill under
dot-claude/skills/ or dot-agents/skills/; `find claude-setup -name taste.md` returns
nothing, while /diverge step 5, charters.md anti-convergence rule 2, and CLAUDE-OS rows
5/9 all reference docs/taste.md as if it were real. The creative half of the protocol
is specified and unshipped.

---

## 2. Existing assets (what to build on, honest state)

| Asset | State | Relevance |
|---|---|---|
| dot-claude/commands/diverge.md | VERIFIED live, operator-interactive only | The distribution-eliciting generator (Verbalized Sampling, arXiv:2510.01171). Needs an --auto mode to fire in autonomous runs. |
| docs/taste.md | VERIFIED missing (dangling reference from 3 places) | The curation memory. Must be created and seeded, not left to accrete from zero. |
| tools/slop_lint.py | VERIFIED live, exit-1 gate | The floor. Pattern to copy for a deliberation lint (same shape: scan artifact, exit 1 on missing section). |
| dot-claude/hooks/kernel-anchor.sh | VERIFIED live (RUN CONTRACT + calibrated claims injected every prompt) | The injection point for intent-class + diverge-mandatory lines. |
| dot-claude/hooks/stop-checklist.sh | VERIFIED broken (WSL path) | The natural audit point for run receipts and craft entries; must be rebuilt Windows-native first. |
| state/lessons.jsonl + state/claims.jsonl | VERIFIED live | The JSONL-ledger pattern; deliberation and craft ledgers copy it. |
| .github/workflows/claude-nightly.yml | STAGED (first run pending) | First autonomous artifact producer; its PR body is the first place a Deliberation section ships. |
| tools/digest/build_digest.py + cron | VERIFIED built, always-on blocked (AUTO-18) | The highest-frequency human-touching artifact; first place a signature craft element ships. |
| rules/calibrated-claims.md | VERIFIED live | The register the deliberation section must keep (dissent with evidence classes, not theater). |
| Memory cards: aesthetic-anchor, excavate-before-building, loop-until-intent-met | VERIFIED read | The operator's taste corpus seeds: named directions before code, avoid-lists, found-spec-is-input-not-template, intent-coverage over speed. |
| charters.md anti-convergence rules | VERIFIED live | Already mandates /diverge on design decisions and taste.md appends; unenforceable while taste.md is missing. |
| CLAUDE-OS §2b research base | VERIFIED in repo | Homogenization is measured and prompt-resistant; ensembles need information asymmetry; self-reflection is theater without external checks. |

Research added this run (2026-07 web sweep):

- Only hard role assignment produces real dissent. A 2026 study of multi-agent
  executive teams found devil's-advocate ASSIGNMENT reaches 99.2% disagreement vs
  48.3% baseline, while soft techniques (strong role framing 61.7%, explicit
  "please dissent" instructions 55.0%) are statistically indistinguishable from
  baseline. Soft prompts produce "nuanced agreement": lower stated conviction, same
  conclusion. ([OpenReview mxBmj5LYU2](https://openreview.net/forum?id=mxBmj5LYU2))
- The failure mode of hard assignment is inauthentic dissent (~4.9% of assigned
  advocates argue for options they privately rate lower), so the protocol must record
  the advocate's private ranking, not just its argued stance. (same source)
- Convergence in debate decomposes into conformity flips vs evidence flips; a
  deliberation record should distinguish them. ([arXiv 2606.00820](https://arxiv.org/pdf/2606.00820))
- Structured deliberation with typed epistemic acts (claim / challenge / concede /
  revise) outperforms free-form debate. ([arXiv 2603.11781](https://arxiv.org/pdf/2603.11781))
- Minority positions are sometimes the correct ones and majority voting needs an
  overturn condition. ([arXiv 2606.29270](https://arxiv.org/pdf/2606.29270))
- Verbalized Sampling holds up at ICML 2026: 1.6-2.1x diversity gain in creative
  tasks, stronger on more capable models; root cause named as typicality bias in
  preference data. ([arXiv 2510.01171](https://arxiv.org/abs/2510.01171),
  [ICML 2026 poster](https://icml.cc/virtual/2026/poster/60489))

Design consequence: dissent must be STRUCTURAL (an assigned role with its own evidence
scope), never REQUESTED ("consider disagreeing" is measured to do nothing). This is the
same lesson ADR-0005 already encodes for depth, now applied to disagreement.

---

## 3. Mechanisms (enforcement, not vibes)

### M1. Dissent Log protocol: every multi-agent run ships a Deliberation section

**What.** Any run with 2+ agents (or any /diverge invocation) writes dissent records to
`state/deliberations.jsonl` and renders a `## Deliberation` section into its
human-facing artifact (PR body, analysis doc, digest item, report). The section is the
operator-visible texture: what was considered, where agents disagreed, what was
overruled, and what would prove the overruled agent right.

**Schema** (one JSONL row per contested question):

```json
{
  "id": "DL-2026-07-25-01",
  "run_id": "nightly-2026-07-25",
  "question": "retry queue: DB table vs in-proc",
  "positions": [
    {"agent": "builder", "stance": "in-proc, simplest", "evidence": ["tools/eco/db.py:40"], "p_conventional": 0.7, "private_agreement": true},
    {"agent": "devils-advocate", "stance": "DB table; in-proc dies with the session (L005)", "evidence": ["state/lessons.jsonl#L005"], "p_conventional": 0.2, "private_agreement": true}
  ],
  "resolution": "adopted-dissent | overruled | merged | escalated-to-operator",
  "overruled": {"agent": "builder", "why": "ADR-0010 disk-is-memory dominates simplicity", "residual_risk": "schema churn"},
  "flip_type": "evidence | conformity | none",
  "revisit_if": "retry rows exceed 1k/day and polling cost shows in digest"
}
```

Non-negotiables baked into the schema, each tied to a research finding: the advocate is
an ASSIGNED role with a DISJOINT evidence scope (it must cite at least one artifact the
lead did not read: information asymmetry, the debate-martingale requirement);
`private_agreement` is recorded so assigned dissent that privately agrees says "tested,
held" instead of manufacturing fake conflict (the 4.9% inauthenticity finding);
`flip_type` distinguishes an evidence flip from a conformity flip; `revisit_if` is the
minority-overturn condition, and when it later fires it becomes a lessons.jsonl row and
a reputation event (M7).

**Rendered form** (what the operator reads, kept to 5-10 lines):

```markdown
## Deliberation
Considered: in-proc queue (p=.7), DB table (p=.2), file drop (p=.1).
Disagreed: builder wanted in-proc (simplest); devils-advocate cited L005
(sessions die, disk is memory) from evidence builder had not read.
Resolved: adopted the dissent. Overruled: builder, residual risk = schema churn.
Revisit if: retry rows >1k/day.
```

**Where it hooks.** (1) `.github/workflows/claude-nightly.yml` agent prompt: add "run
one devil's-advocate pass against your chosen item with a disjoint evidence scope
(read 2 files the plan does not cite); write the Deliberation section into
.github/NIGHTLY_PR_BODY.md and a row shaped like state/deliberations.schema.json"
(prompt edit, no new infrastructure). (2) hive-mind-workflows rule: worker return
schema gains `dissent` as a required field next to claim/evidence/confidence. (3) A
`tools/deliberation_lint.py` (clone of slop_lint's shape, ~40 lines): given an artifact
produced by a multi-agent run, exit 1 if no `## Deliberation` section; wired into the
same places slop_lint is. (4) Once stop-checklist is rebuilt Windows-native (TODO P0),
it checks: run claimed 2+ agents but deliberations.jsonl gained 0 rows => flag.

**Cost.** One extra agent pass per contested question (hundreds of tokens to low
thousands; the advocate reads 2 files, writes 5 lines). The lint is free. No new
model calls for single-agent mechanical runs (protocol does not apply to them).

**Next week the operator sees.** The first nightly PR whose body contains "we
disagreed, here is who lost and why, here is what would prove them right" instead of a
bare what/why. That sentence is literally the thing he asked for, verbatim shape.

### M2. Wow-gate: one named deliberate touch per human-touching artifact, logged

**What.** Before any human-touching artifact ships (digest, PR body, push text,
analysis doc, diagram, email/Jira draft), the producer names ONE deliberate touch above
functional, appends it to `state/craft.jsonl`, and the artifact carries it. Naming is
the gate (same move as calibrated claims: the sin is not lacking a touch, it is
shipping without SAYING so). Mechanical artifacts may log `"touch": "none"` but the
weekly digest reports the none-rate, so flatness becomes a visible metric instead of an
ambient disappointment.

**The touch menu** (bounded so this produces craft, not decoration; each item is
anchored to the operator's taste corpus, which bans decorative gradients, emojis,
adjective-piling, symmetric bullet walls):

1. the unasked number (a quantity nobody requested that reframes the item)
2. the miniature (a 5-line ascii/d2 sketch of blast radius or topology)
3. the kill line ("the one thing I would delete from this repo today")
4. the counterfactual ("if this is wrong, it is because X")
5. the callback (a concrete reference to an earlier lesson/run/decision, showing
   memory: "same shape as L006, different lane")
6. the road not taken (one line from the Deliberation section, M1 synergy)

Explicitly NOT touches: emojis, exclamation, adjectives, decorative formatting, extra
length. The touch is one line or one small block, always information-bearing.

**Schema.** `{"ts","artifact":"PR#7|digest-2026-07-25|push","kind":"pr|digest|push|doc","touch":"kill-line: retire tools/whatsapp, 0 refs in 30d","class":"unasked-number|miniature|kill-line|counterfactual|callback|road-not-taken|none"}`

**Where it hooks.** (1) Nightly workflow PR-body instruction gains: "include one touch
from the menu; name it in a `<!-- craft: ... -->` comment". (2) build_digest.py gains
one deterministic touch (see M6) plus a craft-ledger append. (3) The rebuilt
stop-checklist verifies: human-touching artifact produced this turn => craft.jsonl
gained a row. (4) `tools/deliberation_lint.py` doubles as craft lint (one file, two
checks: Deliberation section present when multi-agent; craft comment present when
human-touching).

**Cost.** One line of thought per artifact; near-zero tokens. The bounded menu is what
keeps cost flat: the producer picks from six moves, it does not brainstorm decoration.

**Next week the operator sees.** The 7:03 digest push ends with a kill line. The
nightly PR body has a 5-line blast-radius miniature. The push text contains the one
number that changed since yesterday. Every artifact has exactly one fingerprint, and
`grep '"none"' state/craft.jsonl | wc -l` is a number he can watch fall.

### M3. /diverge mandatory at run start for big-intent asks (with an --auto mode)

**What.** Two changes. First: /diverge gains an `--auto` mode for autonomous/long
runs, same steps 1-3 (name the default and forbid it; 5 candidates with
p_conventional, weird-first, 2 under 0.3; defixation on the 2 weirdest) but step 4
self-resolves: the run picks, MUST consult docs/taste.md before picking, records the
pick + rejected default + one-line reason into the Deliberation section (M1) and
appends to taste.md marked `picker: auto` (operator can veto later; auto rows carry
less weight in the corpus than operator rows). Second: for any run classified L/XL
(M5), a diverge pass on the run's central design question is MANDATORY at run start,
before implementation begins.

**Where it hooks.** (1) dot-claude/commands/diverge.md: add the --auto section
(~15 lines). (2) kernel-anchor.sh: the injected RUN CONTRACT line gains one sentence:
"L/XL intent => /diverge (auto mode if no operator) on the central design choice
BEFORE building; a big run that starts building without a candidate table is
non-compliant." (3) Workflow templates and the nightly prompt: phase 0 = diverge.
(4) Enforcement: the M5 run receipt has a `diverge: true|false` field; stop-checklist
flags L/XL receipts with false.

**Cost.** 400-1000 tokens per big run (one candidate table). Zero for S/M runs.

**Next week the operator sees.** Any broad ask begins with a visible 5-candidate table,
weird options first, before any file changes, and the eventual output names which
candidate won and why the default was rejected. Fast convergence on a broad ask
becomes structurally impossible: the run cannot skip the sampling step and stay
compliant.

### M4. taste.md: create it seeded, then run the growth loop

**What.** Create `docs/taste.md` NOW (it is a dangling reference in three live
documents, VERIFIED), seeded from the existing corpus rather than starting empty:

- From feedback_aesthetic-anchor: direction-first (named direction in words before
  code); named avoid-list is steering (ban Inter, purple gradients, glass, clone
  cards, emoji chrome); after approval, lock decisions into a binding doc.
- From feedback_excavate-before-building: a found spec is input, not a template
  (name-lifting = slop-merging); anchor every design vocabulary to something real
  (the resolved anchor: Hebrew manuscript rubrication, ink on paper, one red);
  defend every choice from evidence about HIM.
- From the Living Codex thread: OKLCH tokens, bento/editorial layouts, restrained
  motion, layered "living" surfaces, no emojis, no guilt mechanics.
- From this analysis: dissent visible in output; one deliberate touch, never
  decoration; the register of calibrated-claims is itself a taste position.

**Format.** Two sections. Top: "Axioms" (distilled, stable, ~10 lines). Below:
"Ledger", append-only rows `date | domain | context | pick | rejected default |
reason | picker: operator|auto`. /diverge appends to the ledger; the weekly
self-improve cron (AUTO-17) distills repeated ledger patterns into axioms and prunes
superseded rows (the medium loop from CLAUDE-OS §2d, applied to taste).

**Where it hooks.** (1) /diverge step 5 finally has a real target. (2) Charters
anti-convergence rule 2 becomes enforceable. (3) kernel-anchor injects one pointer
line when the prompt matches creative/design verbs: "taste corpus: docs/taste.md,
read before any aesthetic or naming choice." (4) The digest counts ledger appends per
week; zero appends over a week with L/XL runs = the loop is dead, surfaced as a flag.

**Cost.** 30 minutes to seed; appends are free; weekly distillation rides the
already-planned AUTO-17 cron.

**Next week the operator sees.** His picks stop evaporating. When he chooses candidate
4 on Tuesday, Thursday's run cites that row instead of re-asking or regressing to the
default. The system starts having HIS opinions, visibly, with provenance.

### M5. Run-size contract: intent-size classifier sets minimum deliberation budget

**What.** Classify every prompt into S/M/L/XL and attach enforceable minimums, turning
kernel-anchor's existing RUN CONTRACT prose into a measured contract:

| Class | Signal (v1 heuristic) | Minimums |
|---|---|---|
| S mechanical | short imperative, single file, "quick", "typo" | none (wow-gate still applies if artifact is human-touching) |
| M scoped | one feature/bug, bounded files | acceptance checklist + evidence (already required) |
| L broad | verbs: audit, redesign, rethink, "what is missing", "gap analysis", multi-file/repo scope, attached plan | 3+ agents with DISJOINT evidence scopes, /diverge at start (M3), 2+ deliberation rows (M1), no "done" before minimums met or an explicit budget-exhausted statement |
| XL frontier | ambiguous + cross-system + long horizon | L minimums + operator checkpoint at the fork + consider [1m] lead |

Every L/XL run writes a receipt row to `state/runs.jsonl`:
`{"run_id","class","agents_planned","agents_actual","diverge":bool,"deliberation_rows":n,"turns","ended":"minimums-met|budget-exhausted|operator-cut"}`.

**Where it hooks.** (1) v1 classifier: ~15 lines of bash/regex inside kernel-anchor.sh
(it already reads the prompt; on L/XL match it injects the class and its minimums as
additionalContext, so the run KNOWS its floor). (2) v2 home: the golden-tested router
(`intent_control_plane.harness.router`, already shimmed by prompt-router.sh) classifies
properly. (3) Audit: rebuilt stop-checklist compares receipt actuals vs class minimums;
a shortfall is a lessons.jsonl calibration-loss row (same currency as claim
downgrades, per calibrated-claims rule 5). (4) The digest surfaces last week's
receipts: "L-runs: 3, minimums met: 2, shortfall: 1 (run X, 1 agent on a broad ask)".

**Cost.** Classifier is free (regex v1). The real cost is the intended one: L runs
spend more tokens than they do today. That is the operator's explicit ask; the
contract makes the spend legible instead of accidental.

**Next week the operator sees.** A broad ask visibly fans out: the run states its
class and minimums up front ("L: 3 agents minimum, diverge first"), and if it ends
early it must say "budget exhausted, minimums unmet" instead of "done". The
off-by-a-mile feeling gets a number: the shortfall count in the digest.

### M6. Signature elements: design the wow once per artifact TYPE, not per instance

**What.** For recurring artifacts, per-instance creativity is the wrong price point;
a newspaper does not redesign its front page daily, it has a masthead. Give each
recurring artifact type ONE designed signature element, specified once, produced
deterministically or near-deterministically forever after:

- **Daily digest**: ends with the kill line (one candidate deletion/retirement with
  its evidence: "0 references in 30 days") plus the delta-of-the-day (the one number
  that moved most since yesterday, computed from yesterday's digest.json vs today's).
  Both computable in build_digest.py, no model call.
- **Nightly PR body**: the miniature (blast-radius ascii sketch: files touched ->
  what reads them, from the existing blast-radius grapher #16) plus the Deliberation
  section (M1) plus revisit-if.
- **Push text**: the one number that changed, never a generic "digest ready".
- **Analysis docs**: a Deliberation section on the doc's own design (self-applied M1)
  and an explicit what-would-change-my-mind line.
- **Review comments**: one "held finding from history" callback when the same defect
  class was seen before (reads lessons.jsonl).

**Where it hooks.** build_digest.py (kill line + delta: ~40 lines, deterministic);
claude-nightly.yml prompt (miniature + deliberation instructions); a short
`docs/specs/` spec fixing each signature so it is a contract, not a habit. The
wow-gate (M2) then has an easy default: recurring artifacts satisfy it by carrying
their signature, and only novel artifacts need a fresh touch from the menu.

**Cost.** One-time build (~2-3 h total); zero marginal tokens for the deterministic
ones. This is what makes "wow in EVERY small thing" affordable: amortized design.

**Next week the operator sees.** Every recurring artifact becomes recognizable, the
way a colleague's emails are recognizable. The digest stops being a counter dump; the
7:03 push says "proposals 12->9, one L-run shortfall, kill candidate: tools/whatsapp".

### M7. Dissent reputation: overruled minorities that prove right earn routing weight

**What.** Close the loop on M1 with ADR-0008 (reputation from external truth only).
When a deliberation row's `revisit_if` condition later FIRES (an external fact: the
bug appears where the advocate predicted, the retry volume crosses the line), that is
(a) a lessons.jsonl row and (b) a reputation event for the overruled agent/persona:
vindicated dissent. Personas whose dissents keep being vindicated get more weight in
the persona-review-economy router (spec 2026-07-23); personas whose dissents never
land get their advocate assignments rotated. This makes disagreement a career, not a
performance, and it is the anti-inauthenticity pressure the research says assigned
advocates need.

**Where it hooks.** deliberations.jsonl rows carry `revisit_if`; the weekly
self-improve cron greps open rows and checks trigger conditions (most are digest
metrics or repo facts it already reads); hits append to lessons.jsonl with
`vindicated: <agent>`; the reputation table (AUTO-20, needs ecosystem.db AUTO-06)
consumes them.

**Cost.** Rows are free now; the check rides the weekly cron. Full value waits on
AUTO-06/AUTO-20, which is fine: the LEDGER must start accumulating now so the router
has history when it arrives.

**Next week the operator sees.** Nothing yet from M7 itself (this is the slow loop),
except that Deliberation sections carry revisit-if lines that read like a colleague
saying "fine, but if X happens, I was right." STAGED by design.

---

## 4. What changes visibly next week (composite)

Monday 7:03 push, today: `Digest ready: 14 open, 3 lessons open.`
Monday 7:03 push, after M2+M6: `proposals 12->9 (delta-of-day); 1 L-run shortfall Fri;
kill candidate: tools/whatsapp (0 refs 30d).`

Nightly PR body, today: what/why, how to verify, proposal id.
Nightly PR body, after M1+M3+M6: candidate table (5, weird-first), Deliberation
(who disagreed, who was overruled, residual risk, revisit-if), blast-radius miniature,
craft comment naming the touch.

A broad ask ("rethink the review fabric"), today: fast plan, fast convergence,
"done" in one context.
After M3+M5: run states "class L: 3+ agents, diverge first"; candidate table before
any edit; 3 workers with disjoint evidence; 2+ dissent rows; receipt in runs.jsonl;
ending is either "minimums met" with the deliberation visible or an honest
"budget exhausted, unmet: X".

And the operator's Tuesday pick shows up in Thursday's reasoning, cited from
taste.md, which is the difference between a tool that asks again and a colleague
who remembers.

---

## 5. Build order (smallest-first, each lands alone)

1. **Seed docs/taste.md** (M4): fixes a VERIFIED dangling reference; 30 min; no code.
2. **Nightly prompt edit** (M1+M2+M6 v1): Deliberation section + advocate pass +
   craft comment + miniature in claude-nightly.yml. Prompt-only change; ships with
   the next scheduled run.
3. **kernel-anchor v3** (M3+M5 v1): intent-class regex + injected minimums + the
   diverge-mandatory sentence. ~25 lines of bash.
4. **/diverge --auto** (M3): ~15 lines added to the command doc.
5. **build_digest.py signatures** (M6): kill line + delta + craft append. ~40 lines,
   deterministic, testable.
6. **tools/deliberation_lint.py + Windows-native stop-checklist** (M1/M2/M5
   enforcement): the audit half; depends on the TODO P0 WSL-path purge.
7. **runs.jsonl receipts + digest surfacing** (M5): closes the run-size loop.
8. **Vindication check in weekly cron** (M7): after AUTO-17 exists.

Suggested proposals.jsonl rows: `creativity-M1-nightly-deliberation`,
`creativity-M4-taste-seed` (both claimable now, lane B).

---

## 6. Deliberation (this document, self-applied M1)

Considered for the core mechanism: (a) a "creativity skill" the model invokes
(p_conventional=.6, rejected: requested depth is theater, CLAUDE-OS §2b finding 2);
(b) higher sampling temperature / style prompts (p=.5, rejected: homogenization is
prompt-resistant, measured); (c) a second "creative reviewer" model rating outputs
(p=.3, rejected: personas rating personas violates ADR-0008, and same-context
ensembles share the error floor); (d) structural protocols + ledgers + gates, the
adopted design (p=.25). Overruled position worth recording: (c) is genuinely
tempting because it needs no schema work; its residual pull is real and it should be
revisited if the deliberation ledger fills with rows nobody reads. Revisit-if:
after 4 weeks, deliberations.jsonl has >50 rows and zero of them are cited in any
later run or lesson; that would mean texture without consumption, and a cheaper
mechanism should win.

Craft touch, named (M2 self-applied): the before/after push-text pair in §4
(class: unasked-number + callback), and this section (class: road-not-taken).

## Sources

- [Verbalized Sampling, arXiv:2510.01171](https://arxiv.org/abs/2510.01171) and
  [ICML 2026 poster](https://icml.cc/virtual/2026/poster/60489)
- [Inducing Disagreement in Multi-Agent LLM Executive Teams: Only the Devil's
  Advocate Works, OpenReview](https://openreview.net/forum?id=mxBmj5LYU2)
- [Not All Flips Are Conformity, arXiv:2606.00820](https://arxiv.org/pdf/2606.00820)
- [From Debate to Deliberation: Typed Epistemic Acts, arXiv:2603.11781](https://arxiv.org/pdf/2603.11781)
- [Minority Sentinel: When to Overturn Majority Voting, arXiv:2606.29270](https://arxiv.org/pdf/2606.29270)
- [Preserving Disagreement: Architectural Heterogeneity, arXiv:2604.26561](https://arxiv.org/pdf/2604.26561)
- In-repo: CLAUDE-OS.md §2b/§2d, dot-claude/commands/diverge.md, tools/slop_lint.py,
  rules/calibrated-claims.md, docs/charters.md, state/lessons.jsonl, memory cards
  (aesthetic-anchor, excavate-before-building, loop-until-intent-met).
