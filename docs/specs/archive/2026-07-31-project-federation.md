# Per-repo project federation for the ShovalBenjer estate, and why it is not built

Status: parked. The document argues against its own proposal and concludes the federation is overhead; kept because the argument is the useful part.

Date: 2026-07-31. Companion to `docs/specs/archive/2026-07-31-github-native-project-surface.md`,
which this document extends rather than replaces. That document designed the schema
and views for Zion. This one answers the question it did not ask: whether Zion should
be one board or many.

Verdict up front: **one board. Per-repo projects are not justified, and the operator
has already run the experiment that shows why.**

Counts in this document are a snapshot taken at the start of this session: Zion
held 26 items and 20 fields. It ended the session at 31 items and 21 fields,
because a concurrent session appended five epics to
`state/github-backlog-2026-07-31.json` and published them while this work was in
flight. Every ratio quoted below (23 of 26 on `Evidence`, 26 of 26 on `Lane` and
`Autonomy`) is against the 26 that were measured, and the full pre-change dump is
at `state/backups/zion-project3-2026-07-31.json`. The concurrency is itself worth
recording: two writers were on this board within one hour and neither knew about
the other, which is the same failure shape as section 1.3 at a smaller scale.

---

## 1. The question, answered with evidence before any plumbing

The brief's own framing is the right one: GitHub Projects v2 holds items from many
repositories in a single project, so the honest first question is whether per-repo
projects buy anything that Zion plus a `Repository` slice does not.

Three measurements, all read-only, all run 2026-07-31.

### 1.1 The slice field already exists and is already populated

`gh project field-list 3 --owner ShovalBenjer --format json` returns
`PVTF_lAHOBTKVvM4At4WJzgkkYd4  ProjectV2Field  Repository`. It is stock, it is not
one of the seven customs, and every one of the 26 items carries it
(`Counter({'https://github.com/ShovalBenjer/claude-setup': 26})`). The per-repo
axis is not a thing to build. It is a thing already present and unused, because
the board currently holds exactly one repository.

### 1.2 A user-owned board already holds another owner's repository

This is the load-bearing measurement, because it settles capability rather than
policy. `gh project item-list 4 --owner ShovalBenjer` returns 29 items, and all 29
resolve to `https://github.com/solosolve-ai/solosolve-ai-phase1`. That project is
owned by the user account `ShovalBenjer`; the repository is owned by the
organisation `solosolve-ai`. So a user-level project already carries items across
an owner boundary in this estate today. Zion can hold `claude-setup`,
`oren-roast-hq`, `daily-deep-learning` and anything else the operator can read,
without a single new project.

### 1.3 The operator has already built a federation, and it drifted

`ShovalBenjer` project 4 (`solosolve-ai-project`) and `solosolve-ai` project 1 are
two boards over the **same single repository**. Measured diff by item title:

| | count |
|---|---|
| titles on both boards | 22 |
| titles only on project 4 | 7 |
| titles only on project 1 | 8 |
| `Status` on project 1 | 30 Done, 0 anything else |
| `Status` on project 4 | 25 Done, 4 Todo |

Two boards, one repository, no code syncing them, and they disagree about both
membership and completion. Nothing malicious happened. Nobody skipped a step. The
divergence is what two hand-maintained projections of one fact do on their own.
Project 4 also carries `Start Date`, `End Date` and `Dependecies`, copies of
project 1's fields including the misspelling, which is the same duplication one
layer down.

That is the whole federation argument, already run, already failed, on the
operator's own account. Proposing per-repo projects for the remaining repos is
proposing to reproduce it four more times.

### 1.4 There is no native cross-project roll-up, and what one would cost

For completeness, since the brief asks what would do the syncing if federation
were adopted. GraphQL has `addProjectV2ItemById` and
`updateProjectV2ItemFieldValue`; it has no mutation that subscribes one project to
another. A roll-up is therefore a program: a scheduled job holding a
`project`-scoped token, reading N boards, writing the union into Zion, resolving
field-schema differences between boards that were created at different times, and
deciding what happens when Zion and a leaf disagree. Section 1.3 is the measured
prior on that last question.

Cost, stated plainly: one more token with write scope, one more scheduled process,
one more reconciliation oracle that has to be maintained or it fails open, and a
second copy of every item. Benefit for a one-operator estate: a per-repo URL that
a `repo:` filter already produces.

---

## 2. What is built instead

One board, Zion, project 3. Per-repository separation is a **view filter**, not a
project.

```bash
# Add any repo's issues to the same board. Works across owners, see 1.2.
gh project item-add 3 --owner ShovalBenjer \
  --url https://github.com/ShovalBenjer/oren-roast-hq/issues/1

# A per-repository view is a filter string, not a new project. The filter is
# API-settable via updateProjectV2View; the layout is too. See the companion
# spec section 3 for the mutation shape and for what stays UI-only.
#   filter: repo:ShovalBenjer/oren-roast-hq -status:Done
```

The backlog JSON already carries `repo` at the top level, so the publisher writes
one repository per source file and multiple source files project onto one board
with no schema change.

### 2.1 The condition that would reverse this verdict

Named so it is falsifiable rather than a preference. Build a per-repo project when
either becomes true:

1. **A collaborator gets access to one repository and not the estate.** A single
   board leaks item titles across every repo on it to anyone who can see the
   board. A repository-scoped project is the access boundary, and no filter is.
2. **A board must be world-readable while `claude-setup` stays private.** This is
   closer to live than it looks: `gh project list --owner ShovalBenjer` reports
   Zion as `"public": true` today. GitHub redacts private-repo items from viewers
   without access, so the 26 `claude-setup` items are not exposed, but the
   project title, README, field names and option labels are world-readable. If
   `daily-deep-learning` items are ever added to Zion, the board becomes a mixed
   public and private surface with one visibility setting governing both. The
   cheap fix is to set Zion private; the alternative is a second, deliberately
   public board for public repos only.

Neither condition holds for a one-operator estate today. The second is one
`item-add` away from holding.

---

## 3. Per-repository status, and what unblocks each

| Repo | Visibility | Issues | On a board | Action taken today |
|---|---|---|---|---|
| `ShovalBenjer/claude-setup` | private | enabled | Zion, 26 items | defects fixed, see section 4 |
| `ShovalBenjer/oren-roast-hq` | **private**, verified `gh repo view --json visibility` | enabled | no | eligible, nothing created; the operator decides whether it has work worth tracking |
| `ShovalBenjer/daily-deep-learning` | **public** | enabled | no | **design only. Nothing was created.** Adding its issues to Zion triggers condition 2 of section 2.1 and needs a visibility decision first |
| `~/Downloads/new-recruit` | no remote | n/a | impossible | design only, see below |

`new-recruit` has no remote (`git remote -v` returns empty) and has never been
pushed, so it has no repository to attach items to. What unblocks it, in order:

1. A credential sweep over **every commit in the tree**, not the working copy.
   `git log --all` history is what a push publishes, and a secret deleted in a
   later commit is still in the object it was added in.
2. A decision on the 17,292 files under its ignored `projects/` and `archive/`
   trees, which `~/.claude/rules/hidden-trees.md` records as invisible to a
   repo-root search. A push publishes what is tracked, so the sweep and the
   ignore rules have to be reconciled before anyone can claim the sweep covered
   the repository.
3. `gh repo create ShovalBenjer/new-recruit --private --source=. --push` only
   after 1 and 2. Private, because step 2 records that its contents are not
   known.

Until then it is not a projects problem, it is a credential-audit problem
wearing a projects hat.

---

## 4. The Zion defects, fixed, with what was destructive and what was not

### 4.1 A correction to the companion spec, measured rather than assumed

`docs/specs/archive/2026-07-31-github-native-project-surface.md` section 2.6 states that
single-select option renames are UI-only, that the `updateProjectV2Field` mutation
may clear values, and that its blast radius is unverified. It is now verified, and
the answer is that both halves are true depending on one input field.

Method: a disposable single-select field `ZZ probe` was created on Zion with
options `B harness` and `C resume`, set on one item, mutated, read back, and
deleted. Two runs:

| Mutation input | Option ids after | Item value after |
|---|---|---|
| `singleSelectOptions:[{name:"A harness",...}]`, no `id` | regenerated (`3a2f5fc8` became `f93e7b59`) | **cleared to null** |
| `singleSelectOptions:[{id:"f93e7b59",name:"Z renamed",...}]` | unchanged | **preserved** |

`ProjectV2SingleSelectFieldOptionInput` accepts `id`, `name`, `color`,
`description` (introspected). Passing the existing `id` renames in place and every
item keeps its value. Omitting `id` is a replace, and a replace is a delete plus a
create. So the option rename is scriptable and non-destructive, and the destructive
version is one omitted key away.

Second measured fact, recorded because it is a live foot-gun: `gh project
item-list` lowercases only the **first character** of a field name when it builds
the JSON key. `ZZ probe` came back as `zZ probe`, not `zz probe`. Any code that
compares against `name.lower()` reads `None` forever and re-writes an unchanged
value on every run. `tools/ghpub/publish_backlog.py::item_key` encodes this and
`tests/test_ghpub_backlog.py::test_item_key_lowercases_only_the_first_character`
pins it.

### 4.2 Defect 1, Lane. FIXED, non-destructive, zero values lost

```bash
# RAN. Non-destructive: every option id is passed through unchanged.
gh api graphql -f query='mutation{ updateProjectV2Field(input:{
  fieldId:"PVTSSF_lAHOBTKVvM4At4WJzhZTCtU",
  singleSelectOptions:[
    {id:"1da3f54a",name:"A harness",color:GREEN,description:"claude-setup harness (ADR-0016)"},
    {id:"2afacf53",name:"B resume",color:BLUE,description:"resume / hiring engine (ADR-0016)"},
    {id:"9e490094",name:"C learning",color:YELLOW,description:"learning, hasadna (ADR-0016)"},
    {id:"9d5f7a9e",name:"D content",color:PURPLE,description:"content and publishing (ADR-0016)"}]}){
  projectV2Field{ ... on ProjectV2SingleSelectField { options{id name} } } } }'
```

Before: all 26 items read `B harness`, a letter ADR-0016 retired on 2026-07-30 and
which under the current charter names the resume lane. After: all 26 read
`A harness`. Verified by re-reading `item-list`. The names in the mutation match
`tools/lib/lanes.py::LANE_NAMES`, which is the single source of truth for the
scheme.

### 4.3 Defect 2, Evidence. Field created, values written, old field NOT deleted

The old `Evidence` TEXT field held the byte-identical string
`python tools/gate/gate.py run --project .` on 23 of 26 items. A field whose modal
value covers 88% of its population is a constant.

```bash
# RAN. Additive, non-destructive.
gh project field-create 3 --owner ShovalBenjer --name "Evidence state" \
  --data-type SINGLE_SELECT \
  --single-select-options "unmeasured,asserted,measured,verified,refuted"
```

Values are now written by the publisher from the backlog JSON's `evidence_state`
key, which is **computed, not judged**: an epic with at least one `DONE` task is
`measured`, otherwise `unmeasured`. Today that is 3 measured and 23 unmeasured,
which is a distribution rather than a constant, and it is reproducible from the
source file.

**The old field was not deleted, and deleting it is destructive.** Its full
contents are dumped to `state/backups/zion-project3-2026-07-31.json` (20 fields,
26 items, every value). The operator runs this when satisfied:

```bash
# DESTRUCTIVE. Irreversible on GitHub's side. The dump above is the only copy.
gh project field-delete --id PVTF_lAHOBTKVvM4At4WJzhZTCtc   # Evidence (TEXT, PVTF not PVTSSF)
```

### 4.4 Defect 3, nothing wrote any field value. FIXED

See section 5.

### 4.5 A fourth defect the brief did not name

`Autonomy` reads `agent-ships-behind-gate` on 26 of 26 items. It is a constant by
the same test that condemned `Evidence`, and it is the field the companion spec
called "the highest-value field on the board". A field that has never taken a
second value has not yet demonstrated that it can. It is kept, because it is now
written from the JSON and can therefore be corrected in one commit, but it should
not be cited as evidence of anything until at least one epic carries a different
value.

---

## 5. The publisher change, which is the actual root cause fix

Both live defects existed for one reason: the projection was richer than its
source. Seven custom fields were hand-typed on GitHub, no code wrote them, and so
no regeneration could correct them. A field nothing writes can only rot.

`tools/ghpub/publish_backlog.py` gains a `--fields` mode.

- **`FIELD_MAP`** declares the five fields the JSON owns: `Priority`, `Ingestion`,
  `Lane`, `Autonomy`, `Evidence state`. Everything else, `Status` above all, is a
  reaction to work happening and stays hand-set on GitHub. One writer per field is
  the property that makes drift detectable rather than merely regrettable, and it
  is the seam that section 5 of the companion spec called a hope until something
  enforced it.
- **`resolve_option`** maps a JSON value to exactly one board option: exact name,
  then leading token (`S2` finds `S2 45min`, `A` finds `A harness`), then
  case-insensitive prefix. Ambiguity returns nothing rather than guessing. The
  retired `B harness` fails to resolve instead of landing on `B resume`, which is
  a different lane, and there is a test for exactly that.
- **`plan_field_writes`** is pure. It takes epics, fields and items and returns one
  row per pair with an action of `set`, `skip`, `no-field`, `no-item` or
  `unresolved`. Nothing is dropped silently. All the decision logic is here, so the
  oracle needs no network and no token.
- **Idempotence** is a `skip` when the board already holds the resolved value.
  Measured on the live board across 130 planned rows (26 epics times 5 owned
  fields): the first `--execute` reported `set=26, skip=104`, and the second
  reported `skip=130` with no writes at all. The 104 skips on the first run are
  `Priority`, `Ingestion`, `Autonomy` and the already-corrected `Lane`, which the
  planner recognised as matching and left alone.
- **Dry run stays the default** and now prints the plan instead of refusing to run,
  because the plan is built from reads and showing it costs nothing.

Backlog schema additions, all three per epic: `lane`, `autonomy`, `evidence_state`.
`autonomy` was **imported from the operator's existing hand-set values on Zion**
rather than regenerated, so the migration preserves judgement instead of
overwriting it with a default.

```bash
# Plan only, writes nothing.
python tools/ghpub/publish_backlog.py --source state/github-backlog-2026-07-31.json --fields

# Write. Re-running is a no-op.
python tools/ghpub/publish_backlog.py --source state/github-backlog-2026-07-31.json --fields --execute
```

Tests: `tests/test_ghpub_backlog.py` gains 14 cases covering resolution, the
retired-letter failure, ambiguity, idempotence, missing field, missing item,
absent keys, the `Status` exclusion, the gh key casing, and a case that reads the
live backlog file and asserts every epic's `lane` and `evidence_state` resolve
against the real option sets.

### 5.1 What is still not enforced

The companion spec's condition (c) is not met. Nothing in `tools/gate/` fails when
a JSON-owned field's value on GitHub differs from the JSON. `--fields` does now
exit 1 when the board cannot be made to match the source (a field the board lacks,
a value no option can represent, a failed write), and 0 otherwise, so it is wirable;
nothing is wired to it. Making that a gate domain means a
domain that needs a network and a token, which `CLAUDE.md` records as the class of
check that fails open and reports nothing. The honest position is that this is a
detector the operator runs, not an oracle the gate runs, until somebody decides
how a network-dependent domain should behave when offline.

---

## 6. The strongest argument that this federation is overhead

It is not that the board is wrong. It is that the board is a coordination
instrument in a system with nothing to coordinate.

One operator. One reader. Every field on Zion is written by the person who reads
it, so the board conveys no information that was not already in the head of the
only person looking at it. `TODO.md` is already the single ticket list.
`tools/selfimprove/scan.py` already ranks what to pick next. The eight ledgers
under `state/` already hold every fact a KPI could want, and they are local,
diffable, and readable by an oracle that exits non-zero. GitHub Projects is none
of those things.

The measurements in this document are the case for the prosecution, not against
it. `Lane` was wrong for a day and nobody noticed. `Evidence` degenerated to one
string across 23 items and nobody noticed. `Autonomy` has one value across 26
items and the companion spec called it the most valuable field on the board.
Project 4 and project 1 disagree about whether four items are done and nobody
noticed. Four defects, all of the same shape: a hand-maintained surface that
nobody reads because everybody already knows what it says.

The response in this document is a publisher that regenerates five of those
fields. That fixes the rot mechanism and it does not answer the prior question,
which is whether a surface that rots unobserved was worth having. If the answer is
no, the correct action is not this publisher. It is `gh project close 3` and
`gh project close 4`, keeping `TODO.md` and the ledgers, and spending the same
effort on K11 through K14 in the companion spec section 4, which are four real
measurements currently blocked on missing instrumentation rather than on a missing
board.

The narrow counter, and it is narrow: the estate is about to stop being one repo.
`oren-roast-hq` is private with issues on and no board, `new-recruit` is 17,292
untracked files awaiting a credential audit, and `daily-deep-learning` is public.
The moment a second repository has live work, "what is in flight" stops being
answerable by reading one `TODO.md`, and a `Repository` slice over one board is the
cheapest instrument that answers it. That is a reason to keep **one** board with
the slice field it already has. It has never been a reason to build four.
