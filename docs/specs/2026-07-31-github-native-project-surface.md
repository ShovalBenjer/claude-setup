# GitHub-native project surface for ShovalBenjer/claude-setup and Zion (project 3)

Status: DESIGN. Nothing in this document has been applied. Every write command
below is marked UNEXECUTED. The operator decides.

Author persona: product, planning agentic-product metrics for July 2026.
Date: 2026-07-31. Verified against live GitHub state on that date.

---

## 0. The brief's starting state was stale. Corrected measurements first

The task packet described Zion as having 13 stock fields and 21+ items. That is
not what is on the server today. Read-only verification, run 2026-07-31:

```bash
gh project field-list 3 --owner ShovalBenjer --format json   # RAN
gh project item-list  3 --owner ShovalBenjer --format json --limit 60   # RAN
```

| Claim in brief | Measured 2026-07-31 | Delta |
|---|---|---|
| 13 fields, all stock | 20 fields | 7 custom fields already exist |
| 21+ items | 26 items | all 26 are open issues |
| Status single-select Todo/In Progress/Done | same | but see below |

The seven custom fields that already exist on Zion: `Priority` (P0..P3),
`Ingestion` (S1 25min .. S6 full-day), `Estimate (min)` (TEXT), `Lane`
(single-select), `Autonomy` (single-select), `Evidence` (TEXT), `Target date`
(TEXT).

Three defects in that existing schema, all measured, all of which change the
design:

1. **`Lane` carries the retired letters.** Its options are `B harness`,
   `C resume`, `D learning`, `E content`. ADR-0016 renumbered the lanes on
   2026-07-30 to A/B/C/D (`docs/charters.md:1`). All 26 items are tagged
   `B harness`, which under the current charter means the resume lane. The
   field is actively wrong, not merely stale.
2. **`Evidence` carries no information.** 23 of 26 items hold the byte-identical
   string `python tools/gate/gate.py run --project .`. The remaining 3 hold
   closure notes. A field whose modal value is 88% of the population is a
   constant, and a constant is not a measurement.
3. **Nothing in the repository writes any of these values.**
   `tools/ghpub/publish_backlog.py` creates labels, milestones and issues, and
   calls `gh project item-add`. It never calls `gh project item-edit` or
   `updateProjectV2ItemFieldValue`. Grep across `tools/` and `dot-claude/` for
   either returns zero files. The seven custom fields are hand-maintained and
   cannot be regenerated. The backlog JSON has no `lane`, `autonomy`,
   `evidence` or `target_date` key per epic, so the projector could not write
   them even if it tried.

Also corrected from the brief: `gh api repos/ShovalBenjer/claude-setup/issues/4/sub_issues`
returns `[]`. Native sub-issues are available but are **not in use** on this
repo, so "sub-issues work already" describes a capability, not a practice. The
`Sub-issues progress` field is therefore empty on every item.

The org path is open, though: `gh api orgs/solosolve-ai/issue-types` returns
`Task`, `Bug`, `Feature`. The operator does have somewhere to put native issue
types. It is the wrong somewhere, because the code lives under the user account.

---

## 1. What the GitHub API can and cannot do in 2026, measured

This section exists because the published guidance is wrong in both directions.

**Finding: `createProjectV2View` and `updateProjectV2View` DO exist in the live
GraphQL schema.** Community discussions
(https://github.com/orgs/community/discussions/150130, opened 2025-01-28, still
unanswered as of 2026-05-01; and
https://github.com/orgs/community/discussions/153532, dormant since 2025-05-10)
state that no view mutations exist and that this blocks project-as-code. GitHub's
own API page
(https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
documents item and field mutations only. Live introspection contradicts both:

```bash
# RAN, read-only introspection
gh api graphql -f query='query{ __type(name:"Mutation"){ fields{ name } } }' \
  --jq '.data.__type.fields[].name' | grep -i projectv2
```

returns, among others, `createProjectV2View`, `updateProjectV2View`,
`deleteProjectV2View`. So the mutations are real and undocumented.

**Counter-finding, and it is the binding one: the mutation cannot set group-by
or slice-by.**

```bash
# RAN
gh api graphql -f query='query{ __type(name:"ProjectV2ViewConfigurationInput"){ inputFields{ name } } }'
```

returns exactly one input field: `visibleFieldIds`. The readable
`ProjectV2View` type exposes `groupByFields`, `verticalGroupByFields`,
`sortByFields` and `filter`, but of those only `filter` appears on
`UpdateProjectV2ViewInput` (`viewId`, `name`, `layout`, `filter`,
`configuration`).

Net capability, verified rather than assumed:

| Operation | API | gh CLI | Verdict |
|---|---|---|---|
| Create a field | `createProjectV2Field` | `gh project field-create` | scriptable |
| Set an item's field value | `updateProjectV2ItemFieldValue` | `gh project item-edit` | scriptable |
| Create a view | `createProjectV2View` (undocumented) | absent | scriptable, unsupported |
| Set a view's layout | `updateProjectV2View.layout` | absent | scriptable |
| Set a view's filter | `updateProjectV2View.filter` | absent | scriptable |
| Set a view's group-by | none | absent | **UI only** |
| Set a view's slice-by | none | absent | **UI only** |
| Set visible columns | `configuration.visibleFieldIds` | absent | scriptable |

`gh project view` displays a *project*, not a view object. `gh project --help`
(RAN, gh 2.92.0) lists 19 subcommands with no view-create, view-edit or
view-delete, matching https://cli.github.com/manual/gh_project.

Layouts confirmed present in 2026: `BOARD_LAYOUT`, `TABLE_LAYOUT`,
`ROADMAP_LAYOUT`, read from the live `ProjectV2ViewLayout` enum and matching
https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/changing-the-layout-of-a-view.
Roadmap positions items by date **or iteration** field
(https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/customizing-the-roadmap-layout).
Iteration fields exist with `@current`/`@previous`/`@next` filters
(https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-iteration-fields);
the live `ProjectV2CustomFieldType` enum confirms `ITERATION` and
`MULTI_SELECT`, neither of which `gh project field-create` can create (it offers
`TEXT|SINGLE_SELECT|DATE|NUMBER` only).

**Consequence for the design: every view below is half-scriptable.** Layout,
name, filter and visible columns can be set from a script. Group-by and slice-by
are manual UI steps and must be written down as such, because a "provisioned"
board that silently lacks its grouping is the drift class this repo already
logs.

---

## 2. Field schema

### 2.1 The three fields inherited from orgs/solosolve-ai project 1

Verified with `gh project field-list 1 --owner solosolve-ai --format json` (RAN).
His three customs are `Start_date` (TEXT), `End Date` (TEXT), `Dependecies`
(TEXT, his spelling), plus a Status option set of Todo / In Progress / Review /
Done.

| His field | Verdict | Reason |
|---|---|---|
| `Start_date` | **REJECT** | A start date on a one-operator repo is a plan, and plans here are not measured. Nothing on disk records when work on an epic began. The field would be filled by recall, which is the failure class `state/lessons.jsonl` already logs. It is also TEXT, so it cannot drive a roadmap. |
| `End Date` | **REJECT as a second field, KEEP the concept** | Zion already has `Target date`. Two date fields on a repo whose 26 items have zero populated dates is not a schedule, it is two empty columns. Fold into a single retyped `Target date`. |
| `Dependecies` | **REJECT** | Free-text dependencies are unqueryable and unenforceable, and the misspelling is a live demonstration of that: nothing can validate a string field. GitHub already models this natively twice over, via the `Parent issue` field and sub-issues, and neither is in use here yet. Adopting a text field before adopting the native mechanism buys a worse version of something already paid for. |
| Status options incl. **`Review`** | **KEEP** | This is the one thing worth copying. Zion's Status is Todo / In Progress / Done. ADR-0012 says autonomy ships only via the PR gate, so a review state is a real state in this repo's own model, and its absence means work under review reads as "In Progress" and is invisible. Cost: one more column value to keep honest. |

Copying one of three. The reason is not that his schema is bad. It is that his
three fields describe a schedule, and this repository does not have one; it has
a verification pipeline.

### 2.2 Disposition of the seven custom fields Zion already has

| Field | Verdict | Cost of keeping | Reason |
|---|---|---|---|
| `Priority` (SINGLE_SELECT P0..P3) | **KEEP unchanged** | one triage decision per new epic | Populated on all 26 items (3 P0, 8 P1, 11 P2, 4 P3) and written from the backlog JSON's `priority` key, so it is reproducible. |
| `Ingestion` (SINGLE_SELECT S1..S6) | **KEEP unchanged** | one sizing decision per epic | The operator's own session-shape vocabulary, sourced from the backlog JSON's `session` key. It is the effort field, which is why no separate Effort/Size field is proposed. |
| `Estimate (min)` (TEXT) | **DELETE** | zero, it is derived | It duplicates `Ingestion` (S2 and "45 min" are the same fact) and it is TEXT, so it will not sum in a group header, which is the only thing a numeric estimate is good for. Two encodings of one quantity drift apart. |
| `Lane` (SINGLE_SELECT) | **KEEP, RETYPE OPTIONS** | one edit now, then free | Options must become `A harness`, `B resume`, `C learning`, `D content` per ADR-0016. Today every item claims a lane the charter no longer defines. |
| `Autonomy` (SINGLE_SELECT operator-only / agent-drafts / agent-ships-behind-gate) | **KEEP unchanged** | one judgement per epic | The highest-value field on the board and the one with no analogue in the operator's prior project. It is the machine-readable form of ADR-0012 and it is what makes a "what may an agent take unattended" query possible at all. |
| `Evidence` (TEXT) | **REPLACE** | see next table | 23 of 26 values identical. Retype as an enum. |
| `Target date` (TEXT) | **RETYPE to DATE** | one migration | ROADMAP layout requires a real DATE or ITERATION field. As TEXT it cannot drive the one view that would justify it. |

### 2.3 Fields proposed for addition

| Field | Type | Options | Cost stated plainly | Why it earns its place |
|---|---|---|---|---|
| `Evidence state` | SINGLE_SELECT | `unmeasured`, `asserted`, `measured`, `verified`, `refuted` | One honest self-assessment per item, and the field is worthless the moment it is filled optimistically. Mitigation is that `refuted` is reachable from `state/refutations.jsonl`, which has recorded 90 REFUTED and 9 BROKEN verdicts against 344 HELD, so the value has an external check. | This is the field this repository would actually use, and the one the current `Evidence` TEXT field failed to be. It makes the central question of the whole harness ("which of these claims has an oracle behind it") answerable by a filter instead of by reading 26 issue bodies. |
| `Blocked by operator` | SINGLE_SELECT | `no`, `decision`, `spend`, `credential`, `review`, `taste` | One field to set and, more importantly, one to *clear*. A stale `decision` value is worse than an empty field because it parks work invisibly. | Best-evidenced addition on this list. `state/handback-log.jsonl` records 832 entries, 160 of them `block`, of which 177 `loop_guard` and 134 `completion_without_evidence`. The work-cadence rule names operator-only decisions as one of two legitimate stop reasons. There is currently no way to ask "what is waiting on me" without reading the log. |

### 2.4 Fields explicitly rejected

| Candidate | Verdict | Reason |
|---|---|---|
| `Risk` | **REJECT** | No ledger on disk produces a risk score. It would be filled by feel, and this repo already ran that experiment: the `Evidence` TEXT field is what a vibe field looks like 26 items later. Revisit only if something computes it. |
| `Effort` / `Size` | **REJECT** | `Ingestion` is already the effort field in the operator's own vocabulary. A second one splits the signal. |
| `Start_date` | **REJECT** | See 2.1. |
| `Dependencies` | **REJECT** | See 2.1. Use sub-issues and `Parent issue`. |
| Native issue **types** | **REJECT for now, with a named condition** | `gh api repos/ShovalBenjer/claude-setup/issues/4 --jq .type` returns null (RAN) and `gh api orgs/ShovalBenjer/issue-types` 404s because ShovalBenjer is a user account (stated in brief, consistent with the 404). The operator's org `solosolve-ai` does have types (`Task`, `Bug`, `Feature`, verified RAN). Adopting them requires moving `claude-setup` under `solosolve-ai`, which is a repository transfer with URL, fork, and star consequences. That is an operator-only decision, and the `epic` label plus sub-issues covers the same ground today at zero cost. |

### 2.5 Final schema, 8 custom fields

`Priority`, `Ingestion`, `Lane` (retyped), `Autonomy`, `Evidence state` (new,
replaces `Evidence`), `Blocked by operator` (new), `Target date` (retyped to
DATE), plus stock `Status` gaining a `Review` option. Net change: +1 field
against today's 7, with three retypes and one deletion.

### 2.6 Commands. ALL UNEXECUTED WRITES

Nothing below has been run. Field ids are read fresh because they differ per
project.

```bash
# ---- RAN (read-only), gives the ids the writes below need ----
gh project field-list 3 --owner ShovalBenjer --format json \
  | python -c "import sys,json;[print(f['id'],f['type'],f['name']) for f in json.load(sys.stdin)['fields']]"

# ---- UNEXECUTED WRITE: two new fields ----
gh project field-create 3 --owner ShovalBenjer \
  --name "Evidence state" --data-type SINGLE_SELECT \
  --single-select-options "unmeasured,asserted,measured,verified,refuted"

gh project field-create 3 --owner ShovalBenjer \
  --name "Blocked by operator" --data-type SINGLE_SELECT \
  --single-select-options "no,decision,spend,credential,review,taste"

# ---- UNEXECUTED WRITE: Target date must be a real DATE for the roadmap view ----
# gh has no field-retype. Create, migrate values by hand or by script, then delete.
gh project field-create 3 --owner ShovalBenjer \
  --name "Target" --data-type DATE
# then, per item, and only after the operator has decided the dates:
# gh project item-edit --id <ITEM_ID> --field-id <TARGET_FIELD_ID> \
#     --project-id PVT_kwHOBTKVvM4At4WJ --date 2026-08-15
gh project field-delete --id <OLD_TARGET_DATE_FIELD_ID>   # only after migration

# ---- UNEXECUTED WRITE: delete the duplicated estimate ----
gh project field-delete --id <ESTIMATE_MIN_FIELD_ID>

# ---- UNEXECUTED WRITE: retype Lane to the ADR-0016 letters ----
# Single-select OPTIONS cannot be renamed by gh. Rename via the web UI
# (Project settings > Lane > edit each option label), which PRESERVES item
# values, or recreate the field, which LOSES them. Prefer the UI rename:
#   B harness -> A harness   C resume -> B resume
#   D learning -> C learning E content -> D content
# Recreation fallback, destructive:
# gh project field-create 3 --owner ShovalBenjer --name "Lane v2" \
#   --data-type SINGLE_SELECT \
#   --single-select-options "A harness,B resume,C learning,D content"

# ---- UNEXECUTED WRITE: add the Review status option ----
# Not expressible in gh; single-select options are add-only via the UI, or:
# gh api graphql -f query='mutation{ updateProjectV2Field(input:{
#   fieldId:"PVTSSF_lAHOBTKVvM4At4WJzgkkYdo",
#   singleSelectOptions:[
#     {name:"Todo",color:GRAY,description:""},
#     {name:"In Progress",color:YELLOW,description:""},
#     {name:"Review",color:PURPLE,description:""},
#     {name:"Done",color:GREEN,description:""}]}){ projectV2Field{ __typename } } }'
# WARNING, unverified: updateProjectV2Field replaces the option list wholesale.
# Omitting an existing option may clear it from every item. Verify on a COPY
# first: gh project copy 3 --source-owner ShovalBenjer --target-owner ShovalBenjer --title "Zion scratch"
```

The `Status` mutation above is the one command in this document whose blast
radius is not established. It is written down so the operator can see the shape,
and it is marked as requiring a copy-first trial.

---

## 3. Views

Five views. For each: the question, the layout, the API-settable part, and the
UI-only part. All are UNEXECUTED.

Project id, read live (RAN):
`gh api graphql -f query='query{user(login:"ShovalBenjer"){projectV2(number:3){id}}}'`
returns `PVT_kwHOBTKVvM4At4WJ`. Today the project has exactly one view,
`View 1`, `TABLE_LAYOUT`, filter `null`.

### V1. "Waiting on Shoval"

Question: what cannot move without an operator decision, and which kind of
decision is it.

- Layout: `TABLE_LAYOUT`
- Filter (API-settable): `-field:"Blocked by operator" no -status:Done`
- Group by (UI only): `Blocked by operator`
- Sort: `Priority` ascending
- Why it earns a slot: the work-cadence rule permits exactly two stopping
  reasons, and one of them is an operator-only decision. 160 measured `block`
  events in `state/handback-log.jsonl` and no current way to see them as a queue.

### V2. "Evidence versus assertion"

Question: how much of the board is claimed rather than checked.

- Layout: `BOARD_LAYOUT`
- Column field (UI only): `Evidence state`
- Filter (API-settable): `-status:Done`
- Why it earns a slot: this is the repository's own thesis rendered as a board.
  A column of 26 cards under `asserted` and none under `verified` is a finding,
  not a decoration. Note that GitHub's board layout groups by a **column field**,
  not by a separate group-by axis
  (https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/customizing-the-board-layout).

### V3. "In flight per lane"

Question: is this session doing another lane's work.

- Layout: `TABLE_LAYOUT`
- Filter (API-settable): `status:"In Progress",Review`
- Group by (UI only): `Lane`
- Slice by (UI only): `Autonomy`
- Why it earns a slot: cross-lane work is the most frequently logged entry in
  `state/lessons.jsonl` per `CLAUDE.md`. Measured today, all 26 items sit in one
  lane value, so this view's first honest reading will be that the `Lane` field
  is not being used, which is itself the answer.

### V4. "Roadmap to M5"

Question: what is scheduled, and what has no date at all.

- Layout: `ROADMAP_LAYOUT`
- Date field (UI only, roadmap config): `Target` (the retyped DATE field)
- Filter (API-settable): `-status:Done`
- Group by (UI only): `Milestone`
- **Blocked today, and say so.** The five milestones exist (`M1 Instruments
  trustworthy` .. `M5 Autonomy and CI`, verified RAN via
  `gh api repos/ShovalBenjer/claude-setup/milestones?state=all`) but every one
  has `due_on: null`, and `Target date` is TEXT and empty. A roadmap over a
  field with no values renders an empty timeline. This view is contingent on
  section 2.6's retype **and** on the operator actually setting dates. It is
  listed because it is the only justification for keeping a date field at all;
  if the operator will not set dates, delete `Target date` and drop this view.

### V5. "Agent-shippable queue"

Question: what may an agent pick up unattended right now.

- Layout: `TABLE_LAYOUT`
- Filter (API-settable):
  `field:"Autonomy" "agent-ships-behind-gate" field:"Blocked by operator" no -status:Done`
- Sort: `Priority` ascending, then `Ingestion` ascending
- Why it earns a slot: this is the one view an agent reads rather than the
  operator. It is the machine-readable answer to "what is next" and it replaces
  the current practice of ranking with `tools/selfimprove/scan.py` against a
  board that has no autonomy signal in it.

### 3.1 Commands. ALL UNEXECUTED WRITES

```bash
# ---- RAN (read-only): current views ----
gh api graphql -f query='query{ user(login:"ShovalBenjer"){ projectV2(number:3){
  id views(first:20){ totalCount nodes{ id name layout filter } } } } }'

# ---- UNEXECUTED WRITE: create V1. Repeat per view, changing name and layout ----
gh api graphql -f query='mutation{
  createProjectV2View(input:{
    projectId:"PVT_kwHOBTKVvM4At4WJ",
    name:"Waiting on Shoval",
    layout:TABLE_LAYOUT
  }){ projectV2View{ id name layout } } }'

# ---- UNEXECUTED WRITE: set the filter on the view id returned above ----
gh api graphql -f query='mutation{
  updateProjectV2View(input:{
    viewId:"<VIEW_ID>",
    filter:"-field:\"Blocked by operator\" no -status:Done"
  }){ projectV2View{ id filter } } }'

# ---- UNEXECUTED WRITE: V2, V3, V5 identical shape ----
#   V2 name "Evidence versus assertion" layout BOARD_LAYOUT   filter -status:Done
#   V3 name "In flight per lane"        layout TABLE_LAYOUT   filter status:"In Progress",Review
#   V4 name "Roadmap to M5"             layout ROADMAP_LAYOUT filter -status:Done
#   V5 name "Agent-shippable queue"     layout TABLE_LAYOUT   filter <see V5 above>

# ---- NOT SCRIPTABLE AT ALL. Do these five things in the web UI ----
#   V1 group by  Blocked by operator
#   V2 column field  Evidence state
#   V3 group by  Lane ; slice by  Autonomy
#   V4 roadmap date field  Target ; group by  Milestone
#   V5 sort  Priority then Ingestion
```

Both `createProjectV2View` and `updateProjectV2View` are undocumented. Treat
them as they deserve: run one, read the view back with the RAN query above, and
only then run the other four.

---

## 4. Agentic product KPIs, July 2026

### 4.1 What the outside literature supports, and what it does not

Grounding first, because the wrong instinct here is to invent metric names.

- DORA's 2025 report (https://dora.dev/dora-report-2025/, PDF at
  https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf,
  ~5,000 respondents) frames AI as an amplifier of existing strengths and
  weaknesses rather than a uniform gain, and pairs throughput with **delivery
  instability** rather than reporting throughput alone. The instability pairing
  is the transferable idea: a KPI that counts output without a matching
  correctness or rework counter is a vanity metric by DORA's own framing.
- METR's RCT (https://arxiv.org/abs/2507.09089, blog
  https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) is
  the single most load-bearing citation for this repo. 16 developers, 246 tasks:
  allowing AI **increased** completion time by 19%, while the same developers
  predicted a 24% speedup beforehand and still estimated a 20% speedup
  afterwards. Self-report was wrong in sign. METR's own 2026 update
  (https://metr.org/blog/2026-02-24-uplift-update/) says its follow-on data is
  biased and that the 19% figure should not be treated as a standing claim. Both
  halves matter: the measurement is dated, and the lesson that self-report is
  not evidence is not.
- On benchmark validity, the 2026 position paper
  https://arxiv.org/abs/2606.17799 argues a coding agent is a system harness
  ("a composite of models, harnesses, contexts, environments, and feedback
  signals") and that model-shaped benchmarks measure the wrong unit. That is a
  direct argument for measuring **this** harness on **its own** ledgers rather
  than importing SWE-bench-shaped scores. See also
  https://arxiv.org/abs/2606.28430, "Coding Agents Deliver What You Check, Not
  What You Requested", which is the oracle-gaming risk every KPI below inherits.
- DX Core 4 (https://getdx.com/dx-core-4/) and DX's AI measurement framework
  (https://getdx.com/research/measuring-ai-code-assistants-and-agents/) are the
  nearest published specs for measuring agents. Their Speed dimension is PRs per
  engineer and lead time, which does not transfer: this repo has one operator
  and no customers.
- Two things I looked for and did **not** find a primary source for:
  a standardised definition of "agent rework rate", and a standardised
  "human intervention rate" threshold. Vendor blogs use both terms without a
  spec. Per prior-art-gate, the two KPIs below that resemble them are coined
  here and are labelled as coined, not cited.

### 4.2 KPI table

All figures computed 2026-07-31 from the live ledgers. Every ledger read is a
plain file read, so all of these were RAN.

| # | KPI | Question it answers | File and field | Value today | Computable today |
|---|---|---|---|---|---|
| K1 | Clean-tree gate pass rate | Does the contract pass when the tree is not dirty | `state/gate-runs.jsonl`: `verdict` where `dirty == false` | **0.286** (638 PASS of 2232 clean runs) | **YES** |
| K2 | Blocking-domain concentration | Which domain costs the most, so effort has a target | `state/gate-runs.jsonl`: `blocking[]` | e2e 572, codemap 502, prior_art 492, house_rule 314 | **YES** |
| K3 | Refutation rate | How often a written claim dies when its own falsifier runs | `state/refutations.jsonl`: `verdict` | **20.3%** (90 REFUTED + 9 BROKEN of 443) | **YES** |
| K4 | Broken-falsifier rate | How often the checker itself is the thing that failed | `state/refutations.jsonl`: `verdict == "BROKEN"` | **2.0%** (9 of 443) | **YES** |
| K5 | Handback block rate | How often the completion gate stops a claimed finish | `state/handback-log.jsonl`: `action` | **19.2%** (160 block of 832) | **YES** |
| K6 | Unevidenced-completion rate | How often the agent says done with no evidence attached | `state/handback-log.jsonl`: `reason == "completion_without_evidence"` | **134 events**, 16.1% of all handbacks | **YES** |
| K7 | Loop-guard rate | How often the agent is spinning rather than progressing | `state/handback-log.jsonl`: `reason == "loop_guard"` | **177 events**, 21.3% | **YES** |
| K8 | Open-lesson backlog | Are measured failures being closed or accumulating | `state/lessons.jsonl`: `status` | **29 open, 9 closed** (24% closure) | **YES** |
| K9 | Lane-claim coverage | Is the charter lane actually being claimed before work | `state/claims.jsonl`: `lane`, vs sessions in `state/handback-log.jsonl`: `session` | 11 claims total against hundreds of sessions | **YES**, and the answer is that the practice is not happening |
| K10 | Backlog task completion | Is the published backlog moving | `state/github-backlog-2026-07-31.json`: `epics[].tasks[]` prefixed `DONE` | **2.5%** (4 of 161) | **YES** |
| K11 | Skill-use outcome rate | Which skills produce a result versus get invoked and abandoned | `state/skill-use.jsonl`: `outcome` | **BLOCKED.** `outcome` is `null` on all 44 rows. The field exists and is never written. | **NO** |
| K12 | Ticket-to-completion conversion | What fraction of captured intent ever ships | `state/prompt-tickets.jsonl`: `state` | **BLOCKED.** All 176 rows are `CAPTURED`. The state machine has one state, so there is no transition to measure. | **NO** |
| K13 | Reliability curve, confidence versus outcome | Is the CLAUDE-OS.md autonomy threshold of >=0.90 protective or inert | requires `{claimed_confidence, action, verified_outcome}` | **BLOCKED**, TODO.md RT-1. No ledger carries `claimed_confidence`. | **NO** |
| K14 | Human approve/reject ratio | Is operator review a real gate or a rubber stamp | requires a decision ledger | **BLOCKED**, TODO.md RT-2. `state/` holds machine verdicts and no human approve-or-reject event. A ratio that has never seen a rejection is itself the finding. | **NO** |
| K15 | Board evidence honesty | Does the `Evidence state` field agree with the ledgers | Zion `Evidence state` field, cross-checked against `state/refutations.jsonl`: `claim` | **BLOCKED on section 2**, the field does not exist yet | **NO, by design** |

Ten of fifteen are computable today from files already on disk. That is the
argument for this KPI set over any imported framework: it needs no new
instrumentation for two thirds of its content.

### 4.3 The three KPIs deliberately not proposed

- **Lines or commits produced by agent.** DORA 2025's amplifier framing and the
  METR result both say volume is uninformative about outcome. Also unmeasurable
  here without attribution the repo does not record.
- **Time saved.** METR measured this directly and found the sign was wrong, with
  developers still misestimating after the fact. Any self-reported figure this
  repo produced would be the same artifact.
- **Gate pass rate on all runs, dirty included.** 3736 July runs at 0.31 PASS
  looks like a metric and is not one: 1516 of those runs were against dirty
  trees, and `CLAUDE.md` already records that the `review` domain matches by
  commit sha rather than by tree. K1 restricts to clean trees for that reason.

### 4.4 What to instrument next, in cost order

K11 is cheapest: one field already exists and is never written. K12 needs a
state machine on prompt-tickets. K13 and K14 are TODO.md RT-1 and RT-2 and are
the two that would make the autonomy claims in ADR-0012 falsifiable. None of
them are a GitHub Projects problem, which is a point in favour of section 5's
verdict.

---

## 5. How information is stored

`tools/ghpub/publish_backlog.py` (203 lines, RAN: read in full) already answers
this, and its module docstring states the position outright: "the JSON is the
source of truth and GitHub is the projection". Idempotency is by title, not id,
and the header explains that choice: renaming an epic in the JSON deliberately
creates a new issue rather than mutating an existing one.

### Option A. GitHub issues as the source of truth

- Shape: edit in the web UI, and the repo reads GitHub when it needs the list.
- Gain: no drift by construction, because there is only one copy. Sub-issues,
  types, cross-references and notifications all work natively.
- **Failure mode: the backlog becomes unreadable offline and unverifiable by the
  gate.** Every oracle in this repo is a local process that exits zero or
  non-zero. A gate domain that has to call the GitHub API to know what the work
  is now depends on network, on a `project`-scoped token, and on rate limits,
  and it fails open when any of those is missing. `CLAUDE.md` already records
  that a check which cannot run reports nothing. This option converts the
  backlog into exactly that class of check.

### Option B. state/github-backlog-*.json as source, GitHub as projection (today)

- Shape: what exists now. Two dated snapshots on disk,
  `state/github-backlog-2026-07-30.json` (21 epics) and
  `-2026-07-31.json` (26 epics, RAN: the diff is 5 appended epics).
- Gain: diffable, re-runnable, reviewable in a PR, and gate-readable without a
  network call. The dry-run default means a mistake is visible before it lands.
- **Failure mode, and it is not hypothetical, it is measured.** The projection is
  already richer than its source. Zion carries `Lane`, `Autonomy`, `Evidence`
  and `Target date` values that appear in **no** key of the backlog JSON, and no
  code in `tools/` or `dot-claude/` calls `item-edit` or
  `updateProjectV2ItemFieldValue`. So a full re-projection cannot reconstruct
  the board. The half that was typed by hand is unbacked, and the operator has
  no way to tell which half is which. The second failure mode is the dated
  filenames: two files with no pointer to which is current means "the source of
  truth" is ambiguous the moment there are two of them.

### Option C. Hybrid, with a stated seam

- Shape: JSON owns everything the JSON can produce (title, body, labels,
  milestone, priority, ingestion, lane). GitHub owns everything that is a
  *reaction to work happening* (Status, Evidence state, Blocked by operator,
  sub-issue links). The seam is written into the publisher and enforced.
- Gain: each field has exactly one writer, which is the only property that makes
  drift detectable rather than merely regrettable.
- **Failure mode: the seam is a convention until something checks it.** A hybrid
  with an unchecked seam is Option B with extra steps and a better story. It
  needs (a) `lane` and `autonomy` keys added to the backlog JSON schema, (b)
  `publish_backlog.py` extended to set those two project fields via
  `item-edit`, and (c) a gate check that fails when a JSON-owned field's value
  on GitHub differs from the JSON. Without (c) it is not a design, it is a hope.

### Recommendation

Option C, contingent on (c) existing. Absent (c), stay on Option B and **stop
hand-editing project fields**, because the current state is Option B with an
undocumented manual annex, which has the drift surface of a hybrid and none of
the checks. The cheapest honest move today is to delete `Evidence` and
`Target date` from Zion rather than add more fields to a board nothing
reconciles.

---

## 6. The strongest argument against this entire document

A one-operator repository does not have a coordination problem, and a project
board is a coordination instrument.

Concretely: 26 items, one human, and every field on the board is written by the
same person who reads it. There is no assignment to negotiate, no handoff to
track, no stakeholder to inform, no standup to feed. `TODO.md` is already the
single ticket list, `tools/selfimprove/scan.py` already ranks what to pick up,
and the eight ledgers under `state/` already hold every fact a KPI could want.
The board adds a second place where each of those facts lives, and the
measurement in section 0 shows what that costs: the `Lane` field has been wrong
since ADR-0016 landed on 2026-07-30, and the `Evidence` field degenerated to a
constant across 23 of 26 items. Both defects survived because nobody reads a
board they wrote themselves, and nothing checks it. This document's response to
a schema that rotted is a larger schema, plus five views, plus a manual UI step
per view that no script can verify.

Against that, the honest counter is narrow and it is not about project
management. It is that `Autonomy` and `Blocked by operator` encode two facts
that exist nowhere else on disk, and the second is the only machine-readable
answer to "what is waiting on the operator" in a system that logged 160 blocked
handbacks in one week. If the operator wants only the defensible subset: keep
those two fields, keep views V1 and V5, delete `Evidence`, `Estimate (min)` and
`Target date`, and skip the roadmap entirely. That is a four-field board with
two views, and it is the version that would survive its own gate.

---

## 7. Command inventory, execution status

| Command | Status |
|---|---|
| `gh project view 3 --owner ShovalBenjer` | RAN |
| `gh project field-list 3 --owner ShovalBenjer --format json` | RAN |
| `gh project item-list 3 --owner ShovalBenjer --format json --limit 60` | RAN |
| `gh project view 1 --owner solosolve-ai` | RAN |
| `gh project field-list 1 --owner solosolve-ai --format json` | RAN |
| `gh project --help`, `gh project field-create --help` | RAN |
| `gh api graphql` Mutation/type/enum introspection (4 queries) | RAN |
| `gh api graphql` project id and views read | RAN |
| `gh issue list --repo ShovalBenjer/claude-setup --state all` | RAN |
| `gh api repos/ShovalBenjer/claude-setup/milestones?state=all` | RAN |
| `gh api repos/ShovalBenjer/claude-setup/issues/4 --jq .type` | RAN, returns null |
| `gh api repos/ShovalBenjer/claude-setup/issues/4/sub_issues` | RAN, returns 0 |
| `gh api orgs/solosolve-ai/issue-types` | RAN, returns Task/Bug/Feature |
| `gh project field-create` (2 new fields) | **UNEXECUTED WRITE** |
| `gh project field-delete` (2 fields) | **UNEXECUTED WRITE** |
| `gh project item-edit` (date migration) | **UNEXECUTED WRITE** |
| `updateProjectV2Field` (Status options) | **UNEXECUTED WRITE, blast radius unverified** |
| `createProjectV2View` x5 | **UNEXECUTED WRITE, undocumented mutation** |
| `updateProjectV2View` x5 | **UNEXECUTED WRITE, undocumented mutation** |
| all group-by / slice-by / roadmap-date configuration | **NOT SCRIPTABLE, UI only** |
