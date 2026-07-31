# The four-layer board, fitted to claude-setup

Status: DESIGN. Nothing here has been applied. Every write command is marked
UNEXECUTED WRITE. The operator decides what runs.
Date: 2026-07-31. Lane A (harness). Reconciles two specs already on disk.

---

## 0. Verified state, and what the brief got wrong

All reads below were run against the live API on 2026-07-31, read-only.

```bash
gh project view 3 --owner ShovalBenjer --format json                       # RAN
gh project field-list 3 --owner ShovalBenjer --format json                 # RAN
gh project item-list 3 --owner ShovalBenjer --format json --limit 60       # RAN
gh api graphql -f query='query{user(login:"ShovalBenjer"){projectV2(number:3){
  public views(first:20){totalCount nodes{name layout filter}}
  fields(first:30){nodes{... on ProjectV2Field{name dataType}
  ... on ProjectV2SingleSelectField{name dataType}}}}}}'                    # RAN
gh api repos/ShovalBenjer/claude-setup --jq '{visibility,private}'          # RAN
gh api repos/ShovalBenjer/claude-setup/issues/4/sub_issues --jq length      # RAN, returns 0
gh issue view 30 --repo ShovalBenjer/claude-setup                           # RAN, does not resolve
```

| Brief said | Measured 2026-07-31 | Consequence |
|---|---|---|
| project 3 is PRIVATE | `projectV2.public == true`. The repo is `private`, the project is not | Section 6 M-10. Unresolved exposure question, cheap to close |
| 31 items | 31 items, issues #4..#35 with no #30 | The numbering gap is not a missing item; #30 never existed |
| custom fields Priority, Ingestion, Estimate, Lane, Autonomy, Evidence state, Target date | all present, plus an eighth the brief omits: `Evidence` (TEXT) | `Evidence` is the field this design retires. Section 3.3 |
| option sets changed twice tonight | confirmed. `Lane` now reads `A harness / B resume / C learning / D content`, the ADR-0016 letters | the github-native spec's defect 1 is FIXED and its text is now stale |
| gate has 12 domains, several permanently N/A | 12 domains in `quality-contract.json`. Exactly three are N/A: `e2e`, `a11y_ux`, `perf`. There is no `visual` domain | the brief names a domain that does not exist |

Further measurements that change the design and appear in neither existing spec:

1. **`Estimate (min)` is NUMBER and empty on all 31 items.** The zion-board spec
   section 3 states a total of 4,610 minutes. No item carries a value, so that
   total cannot be read off the board and is not reproducible from it.
2. **`Status` is unset on all 31 items.** Not one is Todo. The stage axis the
   operator wants to layer onto is currently empty, which is the strongest single
   argument in this document for keeping LAYER 1 small.
3. **`Evidence state` is unset on all 31 board items**, while
   `state/github-backlog-2026-07-31.json` carries `evidence_state` on all 31 epics
   (23 `unmeasured`, 7 `measured`, 1 `asserted`). Source and projection disagree
   because the sync has not run, not because the schema is missing.
4. **`Evidence` (TEXT) is degenerate**: 23 items hold the byte-identical string
   `python tools/gate/gate.py run --project .`, 3 hold closure notes, 5 are empty.
5. **The backlog JSON already carries `lane`, `autonomy` and `evidence_state` per
   epic** (31 epics, 184 tasks, 5 prefixed `DONE`), and
   `tools/ghpub/publish_backlog.py` now has a `FIELD_MAP` owning exactly
   `priority -> Priority`, `session -> Ingestion`, `lane -> Lane`,
   `autonomy -> Autonomy`, `evidence_state -> Evidence state`. The github-native
   spec's finding 3, that nothing in the repository writes these values, is stale
   as of this session's concurrent work.
6. **Native sub-issues: zero in use.** `Parent issue` and `Sub-issues progress`
   exist and are empty on every item.
7. **One view exists**: `View 1`, `TABLE_LAYOUT`, filter `null`. The seven views in
   the zion-board spec and the five in the github-native spec are all unbuilt.
8. Milestone spread: M1 13, M2 7, M3 5, M4 3, M5 3. All five have no due date.
9. `Target date` is DATE, not TEXT as the github-native spec states, and is set on
   3 items, all `2026-08-02`, matching the `review` waiver expiry in
   `quality-contract.json`.

---

## 1. LAYER 1, workflow stages

Proposed: Backlog, Spec/Context, Agent Plan, Implement, Eval/Verify, Deploy, Done.

**Mechanism: the stock `Status` single-select. No new field.** Rule 4 binds here:
`Status` exists and `Evidence state` exists, and the seven stages collide with both.

| Proposed stage | Disposition | Reason, with the file that decides it |
|---|---|---|
| Backlog | keep as `Todo` | stock value, no change |
| Spec/Context | **merge** into `Specced` | in this repo both produce one artifact class: a file under `docs/specs/` or `docs/prd/` plus a row in `state/claims.jsonl`. Splitting them creates a transition nothing observes |
| Agent Plan | **merge** into `Specced` | same artifact class. `state/plan-deviations.jsonl` (2 rows, both 2026-07-30, session c882fd81) shows the interesting event is a plan being REFUTED, not a plan existing, and that is an `Evidence state` transition, not a column |
| Implement | keep as `In Progress` | stock value |
| Eval/Verify | keep as `In Review` | ADR-0012 makes this a real state: branch, PR, two-model decorrelated review, class-based merge policy. Its absence makes review work read as In Progress |
| Deploy | **drop from Status, see LAYER 4** | no deploy event here is distinct from merge for the tracked tree. What deploy means in this repo is `dot-claude` reaching `~/.claude`, a property of the artifact rather than a stage of the ticket |
| Done | keep | stock value |

**Final option set, five values: `Todo`, `Specced`, `In Progress`, `In Review`, `Done`.**

Question it answers: where is this item in the ADR-0012 shipping path.

Writer: **the operator, by hand on GitHub.** Status is a reaction to work
happening, so it stays out of `publish_backlog.py`'s `FIELD_MAP`, and that
exclusion is already stated in the comment above that table. The backlog JSON must
never gain a `status` key.

Non-duplication with `Evidence state`, stated explicitly: Status says where the
work is, `Evidence state` says how strong the proof is. The product of the two is
the only reason to have either. `Status:Done` with `Evidence state:asserted` is the
failure the whole harness exists to catch.

```bash
# UNEXECUTED WRITE. gh cannot add a single-select option; this is the GraphQL form.
# WARNING: updateProjectV2Field replaces the option list wholesale. Omitting an
# existing option may clear it from every item holding it. Status is unset on all
# 31 items today, so blast radius is currently ZERO. That makes now the cheapest
# moment in this project's life to run it. Field id comes from the RAN field-list.
gh api graphql -f query='mutation{ updateProjectV2Field(input:{
  fieldId:"<STATUS_FIELD_ID>",
  singleSelectOptions:[
    {name:"Todo",color:GRAY,description:"published, not started"},
    {name:"Specced",color:BLUE,description:"spec file and claims.jsonl row exist"},
    {name:"In Progress",color:YELLOW,description:"branch open"},
    {name:"In Review",color:PURPLE,description:"PR open, ADR-0012 gate running"},
    {name:"Done",color:GREEN,description:"merged"}]}){ projectV2Field{ __typename } } }'
```

---

## 2. LAYER 2, work taxonomy and intent

Proposed swimlanes: Feature, Bug Fix, Refactor/Perf, Architecture Spike, Tech Debt,
Auto-Fix Ops.

**GitHub has no swimlanes, and the design depends on saying so plainly.** What
exists: board layout groups cards into columns by exactly one single-select column
field; table layout groups rows by one field; `slice by` is a left-hand panel that
filters rather than a second axis. There is no row-band mechanism. A taxonomy
therefore either competes with Status for the single column slot, or it is a filter.

Second constraint, measured: `Priority`, `Ingestion`, `Lane`, `Autonomy`,
`Evidence state` and now `Status` all want that slot. A seventh single-select does
not add an axis, it adds a filter.

**Mechanism: labels, which this repo already writes, plus one cardinality rule. No
new field.**

Measured label population across the 31 items, from the RAN `item-list`: `epic` 31,
`measured` 15, `instrument` 14, `absorption` 3, `drift` 2, `blocked-operator` 2,
`native-surface` 2, `design` 2, `licensing` 1, `prose-gate` 1, plus `P0..P3`
mirrored onto labels. Three items carry only `epic` and a priority label.

The six generic types map onto this repo's real vocabulary as follows, and the
mapping is not one to one because two of the six do not occur here:

| Generic type | This repo | Evidence |
|---|---|---|
| Auto-Fix Ops | `type:instrument` | 14 of 31 items already carry `instrument`. This is the dominant type, and it is what auto-fix ops means in a repo whose product is oracles |
| Bug Fix | `type:defect` | the defects here are oracle defects: L-2026-07-29-d (panel matched a comment as code), L-2026-07-30-c (a flaky test inside the oracle suite). Both are bugs in the instrument |
| Tech Debt | `type:drift` | drift is the measured form of debt here: repo-versus-live (`skills_sync check`), dead pointers (`pointers.py scan`), retired lane letters surviving in a field |
| Architecture Spike | `type:design` | charters rule 2 requires `/diverge` on these, and L-2026-07-27-b records it fired zero times. The label is what a hook would key on |
| Feature | `type:capability` | rare here. The board's honest reading is that this repo ships instruments, not features |
| Refactor/Perf | **dropped as a type** | `perf` is a permanently N/A gate domain: no budget is declared for this repo. A perf lane whose oracle is N/A can never be verified. Refactors land as `type:drift` or `type:instrument` |

Rule: **exactly one `type:*` label per epic**, sourced from a new `work_type` key
in the backlog JSON and emitted through the label path that already exists in
`publish_backlog.py`. The topic labels (`absorption`, `native-surface`,
`licensing`, `prose-gate`, `measured`) stay as free tags with no cardinality rule.

Question it answers: what KIND of work is this, so that twenty instrument epics and
zero capability epics is a readable fact rather than a feeling.

Writer: **`state/github-backlog-2026-07-31.json` through `publish_backlog.py`.**
Single writer, because labels already sit on the JSON-owned side of the seam.

What is lost by choosing labels over a field, stated honestly: a board cannot be
columned by label, and grouping a table by label is not verified here. The
verification is one read-only call and should run before anyone relies on it:

```bash
# UNEXECUTED, read-only when run. Does LABELS appear as a usable group-by field.
gh api graphql -f query='query{ user(login:"ShovalBenjer"){ projectV2(number:3){
  views(first:5){ nodes{ name groupByFields(first:5){ nodes{
    ... on ProjectV2FieldCommon{ name dataType } } } } } } } }'
```

If group-by-label is unsupported AND the operator wants columns by type, the
fallback is a `Work type` single-select carrying the same six options, written from
the same JSON key. Do not build both.

---

## 3. LAYER 3, agent role and autonomy

Proposed: Primary Agent, Evaluator/Judge Agent, Human-in-the-Loop Gate. This layer
is largely built already, and one third of it is unbuildable.

### 3.1 Human-in-the-Loop Gate: this is `Autonomy`. Do not duplicate it

`Autonomy` (`operator-only` / `agent-drafts` / `agent-ships-behind-gate`) is the
machine-readable form of ADR-0012, is populated on all 31 items (30
agent-ships-behind-gate, 1 operator-only, item #32), and is written from the JSON
by `FIELD_MAP`. Keep unchanged. A separate HITL field would be a second encoding of
one fact, which is the mistake `Estimate (min)` already makes against `Ingestion`.

### 3.2 Primary Agent: DROPPED

There is no agent identity to record. Stock `Assignees` is empty on all 31 items,
no bot account exists, and every issue was created by the same token. A field whose
value is constant across the population is not a measurement, which is precisely
what happened to `Evidence` at 23 of 31 identical. Revisit when a distinct machine
account opens PRs.

### 3.3 Evaluator/Judge: retarget the existing `Evidence` TEXT field

The evaluator here is not an agent, it is a named oracle: `gate.py`, `panel.py`,
`refute.py`, `skilleval/run.py`, `mutate.py`. The question worth a field is which
oracle closes this item, and a field already sits empty of information waiting for
it.

Retarget `Evidence` from the command that closes the row, which collapsed to one
constant, to **the specific falsifier**, sourced from a new `oracle` key in the
backlog JSON. A value is valid only when it names something other than
`gate.py run`, because the gate is the floor under every item and therefore carries
no information about any one of them.

Question it answers: what, specifically, would prove this item wrong.

Writer: **the backlog JSON through `FIELD_MAP`.** This moves `Evidence` off the
hand-maintained annex, which is what let it rot.

If the operator will not populate `oracle` for 31 epics, delete the field instead.
An empty field beats a constant one, because a constant reads as coverage.

```bash
# UNEXECUTED WRITE. Only if the retarget is rejected.
gh project field-delete --id <EVIDENCE_TEXT_FIELD_ID>
```

### 3.4 The one field genuinely missing: `Blocked by operator`

Carried over from the github-native spec section 2.3, still correct.
`state/handback-log.jsonl` holds 832 entries with 160 `block` actions, and the
work-cadence rule permits exactly two stopping reasons, one of which is an
operator-only decision. Nothing on the board answers what is waiting on the
operator. `Autonomy` does not: it states standing policy, not a live block, and
item #32 is `operator-only` as a property rather than as a current stop.

Options: `no`, `decision`, `spend`, `credential`, `review`, `taste`.
Writer: **the operator, by hand.** It is a reaction to work happening.
Cost, stated plainly: a stale `decision` value parks work invisibly, which is worse
than an empty field. The mitigation is view V2, whose whole job is to be short.

```bash
# UNEXECUTED WRITE
gh project field-create 3 --owner ShovalBenjer \
  --name "Blocked by operator" --data-type SINGLE_SELECT \
  --single-select-options "no,decision,spend,credential,review,taste"
```

---

## 4. LAYER 4, environment and infrastructure

Proposed: Local Sandbox, Ephemeral Preview Env, Staging, Canary, Production.

**Rejected as written, and replaced with an axis that is real here.**

The evidence is in `quality-contract.json` itself. `e2e` is N/A because
claude-setup serves no application of its own and every `.html` in the tree is a
static export rather than a route. `a11y_ux` is N/A because it reads the e2e report
that therefore does not exist. `perf` is N/A because no budget is declared. Three
of twelve domains are N/A for one root cause, and that root cause is exactly the
absence of a deployed environment. A five-stage deploy pipeline over this repo
would read `Local Sandbox` on all 31 items forever: a constant, which is the
`Evidence` failure for a third time.

### 4.1 What IS a promotion pipeline in this repo

There is one, and it is not about servers. `CLAUDE.md` states it: the `dot-*` trees
are payload, and editing a file under `dot-claude/` changes nothing about a running
session until it is deployed, while the live tree can also drift ahead of the repo.
So an artifact does move through stages here, and each stage has an existing oracle:

| Stage | What it means | Existing oracle |
|---|---|---|
| `n/a` | docs or analysis work with no deployable artifact | none needed |
| `local` | edited in the working tree | `git status` |
| `merged` | on `main` through a PR | ADR-0012, `gh pr view` |
| `live` | deployed into `~/.claude` | `python tools/audit/skills_sync.py check`, which measures drift in BOTH directions |
| `enforced` | a gate domain or CI step fails when it regresses | `quality-contract.json` domains, `.github/workflows/ship-gate.yml`, and the `pipeline` domain that greps the workflow for a literal `gate.py run` |

That ladder is ADR-0005 rendered as a column: prose stops at `merged`, a hook
reaches `live`, and only a check that can fail is `enforced`. An epic that stops at
`merged` produced a request rather than a control, and the board would show it.

### 4.2 Verdict: the right axis, and NOT created yet

Rule 3 blocks it. `local` and `merged` could be derived from the linked PR, `live`
needs a `skills_sync` read, `enforced` needs a `quality-contract.json` read. No
single writer exists for that combination, and a hand-set `Promotion` field would
rot exactly as `Lane` did between ADR-0016 on 2026-07-30 and its correction
tonight.

**Condition for creating it, stated as a gate:** a script under `tools/ghpub/` that
computes the value from `skills_sync check` output plus the domain table and writes
it through `item-edit`, with its own selftest, and a `mutate.py` control proving
that selftest can go red. Until that exists, do not create the field. That is the
same standard every other oracle in this repo had to meet.

### 4.3 Where the operator's LAYER 4 IS correct: the other lanes

Local, Preview, Staging, Canary, Production is a category error for lane A and a
fair model for lanes B, C and D:

- Lane C owns the daily-deep-learning PWA, which is served and really deploys.
- Lane D publishes the case-ledger post to a public site.
- Lane B ships new-recruit artifacts as HTML an employer loads.

`docs/specs/2026-07-31-project-federation.md` is where a multi-repo board is
designed. **Scope LAYER 4 to that spec, and keep Zion's environment axis at the
four-rung promotion ladder above.** Do not put a canary column on a board whose
repository serves nothing.

---

## 5. Views

Views are per-user and mostly UI-configured. `createProjectV2View` and
`updateProjectV2View` exist in the live schema but are undocumented, and
`ProjectV2ViewConfigurationInput` exposes only `visibleFieldIds`, so group-by and
slice-by cannot be scripted. That finding is quoted from the github-native spec
section 1 and was not re-verified in this session; treat it as second-hand.

Four views. Each names its question. Anything without a question is cut.

| # | Name | Question | Layout | Filter (scriptable) | Column or group (UI only) |
|---|---|---|---|---|---|
| V1 | Fits the gap | I have 25 minutes, what fits | TABLE | `ingestion:"S1 25min","S2 45min" -status:Done` | group by `Priority` |
| V2 | Waiting on Shoval | what cannot move without me, and which kind of decision | TABLE | `-field:"Blocked by operator" no -status:Done` | group by `Blocked by operator` |
| V3 | Claim versus proof | how much of this board is asserted rather than checked | BOARD | `-status:Done` | column field `Evidence state` |
| V4 | Agent-shippable queue | what may an agent take unattended tonight | TABLE | `autonomy:"agent-ships-behind-gate" -field:"Blocked by operator" -status:Done` | sort `Priority` then `Ingestion` |

V1 is the default and it is the constraint from the brief: mid-move, `Ingestion` is
the axis in use. Nothing in this design touches `Ingestion`, and both new axes (the
Status option set and `Blocked by operator`) are absent from V1, so it stays a
two-column read.

Cut from the zion-board spec's seven: **Now**, subsumed by V1 with a priority sort.
**Lane B integrity**, whose filter names a retired lane letter and which would group
31 items into one band. **Unverified done**, which is a KPI rather than a view
(`Status:Done AND Evidence state in {asserted, unmeasured}`, target zero).
**Cost**, because `Estimate (min)` is empty on all 31 items and the chart renders
nothing today.

Cut from the github-native spec's five: **Roadmap to M5**. All five milestones have
`due_on: null` and only 3 items carry a `Target date`, all the same waiver date. A
roadmap over three identical dates is a vertical line.

---

## 6. Migration for the 31 existing items

Items are issues #4 through #35, with no #30.

| ID | Change | Mechanical or human |
|---|---|---|
| M-1 | `Evidence state` written from the JSON on all 31 (23 unmeasured, 7 measured, 1 asserted). The board is empty and the source is complete | **mechanical**, one run of the existing `FIELD_MAP` sync |
| M-2 | `Status` set on all 31, currently unset everywhere. No file on disk records which epic is in flight, so it cannot be derived | **human**, 31 writes. Cheapest honest default is `Todo` on all, then move the two or three actually in flight |
| M-3 | Status option set extended from three values to five, adding `Specced` and `In Review` | **mechanical**, one GraphQL mutation, section 1. Zero blast radius while every item is unset |
| M-4 | `Estimate (min)` populated from the JSON `estimate` string: 25 min, 45 min, 60 min, 90 min, half day, full day map to 25/45/60/90/240/480. Current spread is S5 8, S4 8, S3 6, S2 4, S6 4, S1 1 | **mechanical**, needs either a `minutes` key on the JSON or a parse in the publisher. See section 7 for the ruling on whether to keep the field |
| M-5 | Exactly one `type:*` label per epic. 28 items map defensibly from their existing topic labels (`instrument` 14 to `type:instrument`, `drift` 2 to `type:drift`, `design` 2 to `type:design`, `absorption` 3 by hand since absorption is a topic and not a type) | **human for 3**: #7 Phase D reclamation, #21 GitHub repo standards maintained by an agent, #22 Autonomy ecosystem backlog. These carry only `epic` plus a priority label and have no type signal at all |
| M-6 | `Evidence` TEXT: clear the 23 identical `gate.py run` values, move the 3 closure notes to issue comments where they belong, then either repopulate from a JSON `oracle` key or delete the field | **human decision** first, then mechanical |
| M-7 | `Blocked by operator` set to `no` on 30 items, and to `decision` on #32, whose `Autonomy` is already `operator-only` | **mechanical for the default**, human for the exceptions. Note #11 (licensing and privacy blockers) and #17 (design foundations, taste) are the likely second and third exceptions and need an operator call |
| M-8 | `Target date`: keep the 3 waiver-dated items at 2026-08-02, leave the other 28 empty | **no change**. Do not invent dates to fill a column |
| M-9 | Sub-issues: none exist today. Materialize a task as a native sub-issue only when its epic enters its ingestion window (zion-board spec 2.2). 184 tasks, 5 already prefixed `DONE` | **no bulk migration**. This is the one point both existing specs agree on and neither has executed |
| M-10 | Project visibility is `public` while the repo is `private`. Whether item titles are exposed to anonymous viewers is UNVERIFIED here | **human**, one decision. The check is to open the project URL logged out. Titles such as "EPIC: Licensing and privacy blockers on going public" are the ones to look at first |

No item needs a title change and none is deleted, so `publish_backlog.py`'s
title-based idempotency is undisturbed by every row above.

---

## 7. Reconciliation of the two specs already on disk

### From `docs/specs/2026-07-31-zion-board-as-product-instrument.md` (APPLIED)

Survives: the storage order (JSON is source, GitHub is projection, evidence points
into an append-only ledger); the ingestion-window rule for materializing
sub-issues; the requirement that every view names its question, which this document
inherits; and KPIs 5.1 through 5.6, all of which read fields this design keeps.

Now wrong in it:

- Section 3 gives `Lane` options as B/C/D/E. They are A/B/C/D as of tonight.
- Section 3 claims 4,610 estimate minutes, 76.8 hours. `Estimate (min)` is empty on
  all 31 board items, so that figure is not on the board and cannot be read from it.
- Section 3 describes `Evidence` as the command that makes done falsifiable at a
  glance. Measured: 23 of 31 values identical. The field did not do that.
- Section 4 view 3 is titled "Lane B integrity" against milestone M1. Under
  ADR-0016 the harness lane is A.
- Every count in it is against 27 items. There are 31.

### From `docs/specs/2026-07-31-github-native-project-surface.md` (UNEXECUTED)

Survives: the API capability table, where view mutations exist but cannot set
group-by; the rejection of `Start_date` and `Dependecies`; the `Review` status
option, adopted here as `In Review`; `Blocked by operator` with its handback-log
evidence; the KPI table K1 through K15; the Option C hybrid with a stated seam,
which the concurrent `FIELD_MAP` work has now begun building; and its section 6
self-criticism, which is the strongest argument either document contains.

Now wrong in it:

- Section 0 defect 1: `Lane` no longer carries the retired letters.
- Section 0 defect 3: the repo does now write project fields. `FIELD_MAP` in
  `tools/ghpub/publish_backlog.py` owns five of them.
- Section 2.2 calls `Estimate (min)` TEXT. Live `dataType` is `NUMBER`.
- Section 2.2 calls `Target date` TEXT and prescribes a create-migrate-delete
  retype for the roadmap. Live `dataType` is `DATE`. That procedure is unnecessary
  work against the current schema.
- Section 2.3 proposes `Evidence state` as a new field. It exists.
- Every count in it is against 26 items. There are 31.

### Where the two disagree, and the ruling

`Estimate (min)`: the zion spec keeps it for burn-down, the github-native spec
deletes it as a duplicate of `Ingestion`. **Ruling: keep the field, populate it,
and never sum it as a schedule.** Its one defensible use is KPI 5.2, ingestion
accuracy, which needs a number to compare an actual against. Empty across 31 items
it is neither thing, so M-4 or deletion, not the present middle state.

`Target date` and the roadmap: **ruling, no roadmap view.** Three identical dates
and five milestones with no due date.

---

## 8. Deliberately not proposed

- **A `Promotion` or environment field**, despite section 4 arguing it is the right
  axis for this repo. No single writer exists yet. The condition is in 4.2.
- **A `Work type` single-select.** Labels already carry the taxonomy and already
  have one writer. Fallback condition in section 2.
- **A `Primary Agent` field.** There is no agent identity to put in it.
- **Sprints or an `Iteration` field.** Mid-move the calendar is not stable, and
  `Ingestion` is the honest unit. `gh project field-create` cannot create ITERATION.
- **Native issue types.** They need the repo moved under an organisation, which is
  a transfer with URL and fork consequences and is an operator-only call. The
  `type:*` labels cover the same ground at zero cost.
- **A `Risk` field.** Nothing on disk computes risk, so it would be filled by feel,
  and `Evidence` already ran that experiment to its conclusion.
- **Story points.** An estimate in minutes is one guess; a second unit is a guess
  about a guess.
- **Bulk materialization of all 184 tasks as sub-issues.** It would make the board
  unreadable, which is why checkboxes were chosen in the first place.
- **Any KPI counting lines, commits, or time saved.** METR's RCT measured
  self-reported time saved and found the sign was wrong.
- **Renaming any of the 31 issues.** Title is the idempotency key in
  `publish_backlog.py`, so a rename creates a duplicate rather than an edit.

---

## 9. Command inventory, execution status

| Command | Status |
|---|---|
| `gh project view / field-list / item-list 3 --owner ShovalBenjer` | RAN, read-only |
| `gh api graphql` project fields, data types, views, public flag | RAN, read-only |
| `gh api repos/ShovalBenjer/claude-setup` visibility | RAN, read-only |
| `gh api repos/ShovalBenjer/claude-setup/issues/4/sub_issues` | RAN, returns 0 |
| `gh issue view 30` | RAN, does not resolve, no such issue |
| local reads of `quality-contract.json`, `docs/QUALITY-CONTRACT.md`, `docs/charters.md`, ADR-0005/0012/0016, `state/lessons.jsonl`, `state/plan-deviations.jsonl`, `state/github-backlog-2026-07-31.json`, `tools/ghpub/publish_backlog.py` FIELD_MAP | RAN, read-only |
| `updateProjectV2Field` Status options, section 1 | **UNEXECUTED WRITE** |
| `gh project field-create "Blocked by operator"`, section 3.4 | **UNEXECUTED WRITE** |
| `gh project field-delete <Evidence>`, section 3.3, conditional | **UNEXECUTED WRITE** |
| `publish_backlog.py` field sync for `Evidence state`, M-1 | **UNEXECUTED WRITE** |
| `gh project item-edit` for Status, Estimate, Blocked by operator (M-2, M-4, M-7) | **UNEXECUTED WRITE** |
| group-by introspection query, section 2 | **UNEXECUTED**, read-only when run |
| `createProjectV2View` and `updateProjectV2View`, four views | **UNEXECUTED WRITE**, undocumented mutations |
| all group-by, column-field and slice-by configuration | **NOT SCRIPTABLE, UI only** |
