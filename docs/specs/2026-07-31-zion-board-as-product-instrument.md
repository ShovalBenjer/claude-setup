---
PRD: prd/autonomy-ecosystem.md (AUTO-11 merge policy, AUTO-19 FleetView)
Ticket: ZION-BOARD (this spec)
Status: active
Authority: every count below was read from the live GitHub API on 2026-07-31, not from
a doc. Field and view names are the ones that exist; where a thing is proposed rather
than built, section 4 says so per row.
---

# Zion as a product instrument, not a task list

## 0. What was wrong with the 2026-07-30 publish

I shipped 27 issues titled `EPIC: ...` with their tasks as markdown checkboxes in the
body, and the project carrying only GitHub's 13 default fields. Three consequences, all
measurable:

- **Hierarchy lived in a string.** `EPIC:` is a title prefix. GitHub cannot group, filter,
  or roll up on a prefix, so the board could not answer "what is left in this epic".
- **166 tasks were invisible to the board.** Checkboxes are body text. They do not appear
  as items, cannot be assigned, cannot carry a status, and cannot be counted except by
  parsing markdown.
- **Priority did not exist as data.** It was rendered into the body by `build_body`, so
  sorting by priority meant reading 27 bodies.

## 1. What the solosolve board did instead, measured

`gh project view 1 --owner solosolve-ai` and `field-list`, read 2026-07-31:

| | solosolve project 1 | Zion before | Zion now |
|---|---|---|---|
| items | 30 | 27 | 27 |
| fields | 16 | 13 (all default) | 20 |
| custom fields | `Start_date`, `End Date`, `Dependecies` | none | 7, section 3 |
| title convention | plain imperative: "Set up multi-channel support" | `EPIC:` prefix | unchanged, see 2.1 |
| hierarchy | native `Parent issue` + `Sub-issues progress` | body checkboxes | native, materialized per 2.2 |
| status | Todo / In Progress / Review / Done | Todo / In Progress / Done | unchanged |

The instructive part is not the field count. It is that solosolve put **dates and
dependencies** on the board, which are the two things that let a board answer "what is
late" and "what unblocks what" without a human reading every card. It also used a
four-state `Status` including `Review`, which distinguishes work that is done from work
that is waiting on a human, and that distinction is the whole game for an agentic
backlog.

Its weakness, worth not copying: 30 items and every one of them `Done`, with no
priority, no estimate, and no evidence field. It records that work happened. It cannot
tell you whether the work was verified, what it cost, or what to do next.

## 2. Hierarchy

### 2.1 Keep the EPIC prefix, add the native parent link

The prefix stays because it survives export, search, and the JSON source, and because
renaming 27 issues would break `publish_backlog.py`'s title idempotency and create 27
duplicates. The prefix is now decoration on top of a real `Parent issue` relationship
rather than a substitute for one.

### 2.2 Materialize sub-issues at ingestion time, not at publish time

166 sub-issues created up front would make the board unreadable, which is the reason
the 2026-07-30 note gave for checkboxes in the first place. That note was right about
the symptom and wrong about the fix. The rule instead:

> A task becomes a native sub-issue when its epic enters its ingestion window.
> Until then it stays a checkbox in the body.

So the board holds roughly 25 epics plus the 10 to 20 sub-issues of whatever is actually
in flight. `Sub-issues progress` then shows real completion per epic, and closing a
sub-issue updates the parent's progress bar without anyone editing markdown.

## 3. Fields now on the board, and what each one buys

Created 2026-07-31, 165 writes across 27 items, zero failures.

| field | type | why it exists | what it unlocks |
|---|---|---|---|
| `Priority` | select P0-P3 | ordering that survives a context switch | the P0 view, section 4.1 |
| `Ingestion` | select S1-S6 | the unit that matters mid-move: S1 fits a 25-minute gap, S6 needs a clear day | section 4.2, the only view that gets used while moving apartment |
| `Estimate (min)` | number | 25 / 45 / 60 / 90 / 240 / 480 | sum and burn-down. Current total: **4,610 minutes, 76.8 hours** |
| `Lane` | select B/C/D/E | charters.md lane, so cross-lane work is visible as a violation | catches the most-logged lesson in `state/lessons.jsonl` |
| `Autonomy` | select | operator-only / agent-drafts / agent-ships-behind-gate | the agentic KPI in 5.3; nothing else in the repo records this |
| `Evidence` | text | the command or artifact that closes the row | makes "done" falsifiable at a glance |
| `Target date` | date | set on P0 only | the review waiver expires 2026-08-02 and the board now knows |

Deliberately **not** added: story points (an estimate in minutes is already a guess, a
second unit is a guess about a guess), a Risk field (the lesson id in `Evidence` carries
it), and an Iteration field (ingestion size is the honest unit while the calendar is
unstable).

## 4. Views

Views are per-user on GitHub and cannot be created by CLI, so these are the definitions
to build once in the UI. Each states its question, because a view whose question nobody
can name is a view nobody opens.

1. **Now** — question: what do I do next? Filter `Priority:P0,P1` and `Status:Todo`,
   group by `Ingestion`, sort by `Target date`. Board layout.
2. **Fits the gap** — question: I have 25 minutes, what fits? Filter
   `Ingestion:"S1 25min","S2 45min"`, group by `Priority`. Table. This is the view for
   the current apartment move and it should be the default.
3. **Lane B integrity** — question: are the instruments trustworthy? Filter
   `Milestone:"M1 Instruments trustworthy"`, group by `Status`. Roadmap layout with
   `Target date`.
4. **Waiting on a human** — question: what is blocked on me specifically? Filter
   `Autonomy:operator-only`. This is the queue an agent cannot drain, and it should stay
   short; if it grows, the harness is asking for permission too often.
5. **Unverified done** — question: what claims to be finished with no proof? Filter
   `Status:Done` and `Evidence` is empty. Should always be empty. When it is not, that is
   the calibrated-claims rule failing in public.
6. **Cost** — question: where is the time going? Group by `Milestone`, sum
   `Estimate (min)`. Insights chart, stacked column.
7. **Agent-shippable** — question: what could run without me tonight? Filter
   `Autonomy:agent-ships-behind-gate` and `Priority:P1,P2` and `Estimate (min) < 90`.
   This is the input queue for the nightly autonomy pilot (AUTO-07/09).

## 5. KPIs for an agentic backlog, July 2026

Each KPI names the field it reads and the way it can be wrong. A metric with no stated
failure mode becomes a target and stops measuring.

### 5.1 Verified-done ratio
`count(Status:Done AND Evidence non-empty) / count(Status:Done)`. Target 1.0.
**Fails when** `Evidence` is filled with prose instead of a command. Mitigation: the
field's value must start with `python `, `git `, or `closed: DONE ` and cite an artifact.

### 5.2 Ingestion accuracy
`actual minutes / Estimate (min)`, per closed epic. Not a productivity number, a
**planning-calibration** number: if S2 items routinely take 3 hours, the ingestion sizes
are lying and the mid-move plan is worthless. **Fails when** nobody records actual time;
the honest version is to sample five closures rather than instrument everything.

### 5.3 Autonomy mix
Share of closed work by `Autonomy`. The interesting series is
`agent-ships-behind-gate / total` over weeks. This is the only number in the repo that
would show whether the autonomy programme is working. **Fails when** trivial work is
labelled agent-shippable to move the number; mitigation is that it is only claimable
with a gate run recorded in `state/gate-runs.jsonl` for that tree.

### 5.4 Operator-block latency
Median age of items in view 4. The measured cost of the old short-cycle pattern was 66
operator turns and ~940 minutes of waiting in one week; this is the standing version of
that measurement. **Fails when** items are closed rather than unblocked.

### 5.5 Waiver half-life
Days between a waiver being recorded in `quality-contract.json` and being cleared, versus
being renewed. The review waiver was renewed three times on a reason nobody executed
(L-2026-07-31-a). A renewal count is the leading indicator of an oracle nobody trusts.

### 5.6 Lesson recurrence
Count of `state/lessons.jsonl` classes that fire a second time after being written.
Currently at least three have (the absence-claim class fired three times in one session).
This is the harness's own regression rate and it is not on any board yet.

## 6. How information is stored, and why in that order

```
state/github-backlog-YYYY-MM-DD.json     source of truth, versioned, diffable
        |  tools/ghpub/publish_backlog.py --update
        v
GitHub issues + milestones + labels      the projection humans and agents read
        |  gh project item-edit
        v
Zion ProjectV2 fields                    the queryable layer: views, grouping, insights
        ^
state/gate-runs.jsonl, lessons.jsonl     evidence, append-only, referenced by Evidence
```

Three rules that keep this from rotting:

- **The JSON is edited, never the issue body.** The footer of every generated body says
  so, and as of 2026-07-31 it finally names the file it actually came from; it used to
  hardcode the 2026-07-30 name on every publish, which is the drift class the sentence
  itself warns about.
- **Field values are written from the JSON, not typed.** `zion_fields.py` is the writer.
  A hand-set field is drift with no diff.
- **Evidence points into an append-only ledger**, never into prose. A gate run has a tree
  hash; a sentence does not.

## 7. Applying the research-synthesis standard to this repo's own .md files

`docs/prompt-research-effiefecnt-.md-files-gemini-code-1785450497712.md` is written for
synthesising ~50 sources into one survey. Its four processing directives generalise to
document consolidation, and its schema does not. Adopt the directives, adapt the schema.

**Measured need.** `~/Downloads/new-recruit` holds **5,720** `.md` files. The duplication
is structural, not incidental:

| pattern | evidence |
|---|---|
| skills trees copied between `.claude/` and `.agents/` | `vercel-react-best-practices/rules` 68 files in each; `remotion-best-practices/rules` 37 in each |
| one project checked out as four git worktrees | `ORM-AGENT`, `-widgora-indicators-wt`, `-widgora-gates-wt`, `-ci-review-wt`, 48 docs each |
| dated research snapshots that supersede each other | `docs/research/` 4 files, 1,197 lines |

Note the hidden-trees rule applies: `projects/` and `archive/` are gitignored there, so a
repo-root ripgrep returns zero hits across most of that corpus. Any dedup sweep must use
`--no-ignore` or name the path, and must say which it used.

**The three failure modes the operator named, and the constraint each implies.**

1. *Token and length bottleneck.* A 13-section publication-quality output in one pass hits
   the output cap and truncates the tail. Constraint: **one pass produces one section**,
   with the inventory produced first and the synthesis written against it. Never ask for
   the whole survey in a single generation.
2. *Over-modular structural bloat.* Separate sections for Best Practices, Common Mistakes,
   Disagreements, Gaps, Takeaways and Insights make the model restate the same finding
   four or five times. Constraint: **one finding lives in exactly one section**, and every
   other section cross-references it. This document is the test of that rule; the thesis
   review written earlier in this session failed it, measurably: finding `G2` appears 12
   times in 13,180 words, `G4` eight times, with three verbatim repeated sentence openings.
3. *No processing constraints.* Constraint: state conflict-resolution and source-indexing
   policy up front. For a dedup sweep that means: when two copies of a file differ, the
   newer mtime does not win automatically; the one with more unique content wins and the
   diff is recorded, because a worktree copy can be behind on formatting and ahead on
   substance.

**Sequence, one ingestion each.** Inventory before synthesis, always.

1. Hash every `.md` and group by content hash (`--no-ignore`). Byte-identical copies are
   deletable without reading. Expect the skills trees to collapse here.
2. Near-duplicate pass on the remainder: shingle similarity, report pairs above 0.8 with
   their unique spans. These need a human call, so they go to view 4.
3. Per project, write one consolidated doc using the standard's directives and a schema
   fitted to the project, not the survey schema. Keep the source files until the
   consolidated doc is verified to contain every unique span; the acceptance test is that
   every span flagged unique in step 2 appears in the output.
4. Only then delete, and record what was deleted in the append-only ledger.

The acceptance criterion for the whole sweep is not a file count. It is: **no unique span
lost**, demonstrated by the step-3 check, with the count reported both ways.
