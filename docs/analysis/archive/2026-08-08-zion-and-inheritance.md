---
PRD: prd/2026-08-03-unified-architecture.md (acceptance row U5)
Ticket: ZION-BOARD (docs/specs/archive/2026-07-31-zion-board-as-product-instrument.md), reconciled by
docs/specs/2026-07-31-kanban-four-layer-model.md
Status: point-in-time analysis, read-only
---

# Zion today, and what other repos actually inherit from claude-setup

Read-only pass. No issue, discussion, or project item was created, closed, commented on, or
edited to produce this. All reads ran 2026-08-08 against the live GitHub API and against the
`claude-setup`, `new-recruit`, and `daily-deep-learning` clones on this machine
(`/home/shov/work/repos/*`, the main clones, not a worktree). Every number below names the
command that produced it. VERIFIED means the command and output are shown or were shown in
this session; STAGED means the artifact exists but was not exercised; ASSUMED is not used
anywhere in this document without being labeled.

## The one-line answer to the operator's real question, up front

Two different inheritance mechanisms exist, they behave oppositely, and neither is written
down where a new project would find it. Config (rules, hooks, skills) inherits implicitly and
unpinned, every session, with no version recorded. Tools (the gate, the review panel) inherit
explicitly by cross-repo invocation, resolved three different ways in three places, and the
one place that pins a version has let the pin drift for eight days. Section 2 is the evidence
for this claim; section 4 is what closes the gap.

## 1. Zion's board, measured today, against the recorded numbers

Command: `gh issue list -R ShovalBenjer/claude-setup --state all --limit 500 --json
number,title,state,closedAt,createdAt` plus `gh project item-list 3 --owner ShovalBenjer
--format json --limit 200`, both re-run together as one atomic snapshot at
**2026-08-08T07:55:38Z** after an earlier pull inside this same session had already gone stale
(see the note below the table; that staleness is itself evidence, not noise).

| | Recorded 2026-08-03 (PRD U5 row, unified-architecture.md:565) | Measured 2026-08-08T07:55:38Z |
|---|---|---|
| epics (issues titled `EPIC:`) | 31 | **33** |
| epics closed | 0 | **0** |
| checklist items done | 5 | **8** |
| checklist items total | 184 | **196** |

VERIFIED against the final snapshot: `gh issue list` returns 37 total issues, 33 titled
`EPIC:`, 0 closed. `gh project item-list` returns 36 Zion project items: the 33 epics plus 3
non-epic issues (#1, #57, #58). Checklist counts are a regex count of `- [ ]` and `- [x]`
(case-insensitive, 188 and 8) across the 33 epic bodies, and a second count restricted to
lines matching `- [x] DONE` returns the identical 8, so the regex total and the DONE-prefix
convention the source-of-truth JSON uses (`docs/specs/2026-07-31-kanban-four-layer-model.md`
section 0 item 5) agree; they are not two different countings of the same fact by accident.

**The board changed while this analysis was running, and the change itself is a finding.** An
earlier pull in this same session, minutes before the snapshot above, read 34 total issues and
33 Zion items with 0 non-epic items. Between that pull and 07:55:38Z, three issues were filed
(#56, #57, #58, all `createdAt` 2026-08-08T07:45-07:47Z) and two of them (#57, #58) plus one
older issue (#1) were added to the Zion project, live, mid-session. None of the three added
items is titled `EPIC:`; the project that this whole document otherwise describes as
untouched for eight days had three writes land in it in the ten minutes this report was being
assembled. That does not change the epic/closed/checklist numbers above (the additions carry
no checklist and are not epics), but it means "the board is idle" is a statement about the 31
epics specifically, not about all write activity on project 3, and a reader should not
extrapolate "nobody touches this board" from these numbers.

**The two epics added between the PRD snapshot and today are dated**: issues #49 and #50
(`EPIC: Bind the instruments that already run to a ratchet`, `EPIC: The falsifier layer, and
the five claims it now refutes`) both `createdAt` 2026-08-06T13:52 (`gh api graphql`
`content.createdAt`, VERIFIED). Every other epic's `updatedAt` clusters at 2026-07-30T23:5x
through 2026-07-31T00:00 (VERIFIED, same query). So across the five days between the PRD's
snapshot and this one: 2 epics were added, 12 checklist boxes were added to the 33 epics
(mostly by those two epics arriving with their own task lists), and 3 boxes were checked. Net
checklist debt grew by 9 in the window. Zero epics closed in either snapshot. "Throughput
zero" from the PRD still holds as a fair characterization of the 33 epics; it is not literally
frozen, but the work added in five days outpaced the work finished by 4 to 1.

**Zero of the 33 epics carry a comment written by a human responding to the work.** `gh issue
list --json number,title,comments`: 15 comments total across the 37 issues, all on 3 issues,
and those 3 are not epics: #38 (13 comments, the agent feed, section 2), #13 and #6 (1 each,
unrelated to Zion epic content). No epic has ever been discussed.

### The four-layer taxonomy, field by field, all 33 items

Command: `gh project item-list 3 --owner ShovalBenjer --format json --limit 200`, cross-checked
against `gh project field-list 3 --owner ShovalBenjer --format json` and one `gh api graphql`
`fieldValueByName` sweep for `Status`. VERIFIED.

| field | layer | filled / 33 |
|---|---|---|
| Status (workflow stage) | 1 | **0 / 33** |
| Milestone | (cross-cutting) | 33 / 33, five values in use |
| Priority, Ingestion, Lane, Autonomy, Labels | 2 and 3 | 33 / 33 each |
| Evidence state | 2 (evidence strength) | 33 / 33 (23 unmeasured, 8 measured, 1 asserted, 1 refuted) |
| Estimate (min) | 2 | 26 / 33 |
| Evidence (text) | 2 | 26 / 33 |
| Target date | (P0 only, by design) | 3 / 33 |
| Environment | 4 | **no such field exists on the board** |

Two things read as gaps and are not, and one thing reads as small and is the real finding:

- **Layer 4 (environment) has no field by design, not by omission.** The repo's own
  reconciliation spec (`docs/specs/2026-07-31-kanban-four-layer-model.md` section 4.2/8) argues
  this repo has no deployed environment or promotion pipeline for Zion to track and explicitly
  lists "a Promotion or environment field" under "deliberately not proposed." Reporting its
  absence as an oversight would be wrong; it is a recorded decision.
- **Evidence state and Estimate were empty on all 31 items as of 2026-07-31** (same spec,
  section 0, item 1 and 3, its own measured findings that day) **and are now filled on 26-33 of
  33.** `tools/ghpub/publish_backlog.py`'s field sync ran at some point between 07-31 and today
  and did its job. This is real, if quiet, progress on the plumbing.
- **Status is unset on all 33 items, and it was already unset on all 31 items on 2026-07-31**
  (same spec, section 0, item 2, and section 1: "Status stays out of `publish_backlog.py`'s
  `FIELD_MAP`... Writer: the operator, by hand on GitHub"). This is a field the design
  deliberately routes to a human and the human has not touched it in at least eight days across
  33 items. That is the sharpest single fact in this section: the one field whose entire job is
  to answer "where is this in the ADR-0012 shipping path" has never been set, by design, and the
  design has been live long enough that "nobody has gotten to it yet" is no longer the likely
  explanation.

Sub-issue materialization (spec section 2.2, "a task becomes a native sub-issue when its epic
enters its ingestion window"): swept all 37 open issues in the repo via
`subIssues(first:1){totalCount}` and `parent{number}`. **0 sub-issues, 0 parent links,
anywhere in the repo.** VERIFIED, not a single-issue sample. The 196 checklist items remain
body markdown text, invisible to the board's own grouping and rollup, exactly the problem the
spec was written to fix and the fix was never applied.

### The Zion telemetry channel is the same story: built, ran, went quiet

Issue #38 ("Agent feed: derived cross-repo telemetry") and its successor Discussion #43 are a
machine-written feed, not human discussion: `tools/telemetry/publish.py` posts derived rows
from `state/gate-runs.jsonl`, `refutations.jsonl`, `lessons.jsonl`, `claims.jsonl`, and
`bus.jsonl`. Issue #38's own body states it was moved to a discussion "after 12 comments and
146 item lines in 19 hours and received zero reactions and zero replies." The discussion's own
body sets a recheck date: 2026-08-19, "if this discussion also goes unread, the answer is to
post less, not more."

Last post to the discussion: 2026-08-06T15:03:32Z (`gh api graphql` `discussion(number:43)`,
VERIFIED). Checked whether the feed is silent because there is nothing to report, or because
nobody ran it: `state/gate-runs.jsonl` has 12 rows for `claude-setup`, 15 for
`daily-deep-learning`, and 2 for `new-recruit` with timestamps after 2026-08-06T15:03:32
(python filter over the ledger, VERIFIED). The feed is not caught up with an idle system; the
underlying ledgers kept moving and the publisher was not re-run for two days. That is a
different defect than "nobody reads it," and it is the honest read of the discussion's own
recheck condition, six days before it fires.

## 2. What actually inherits from claude-setup, and by what mechanism

Two mechanisms, verified against `~/work/repos/new-recruit` and `~/work/repos/daily-deep-learning`
(both live clones with `origin` remotes on `ShovalBenjer/new-recruit` and
`ShovalBenjer/daily-deep-learning`). A third project the task named,
`daily-deep-learning-daemon`, does not exist as a separate repository:
`~/work/repos/daily-deep-learning/daemon` is a folder inside `daily-deep-learning`, with its own
log at `state/_daemon.log`. That is the monorepo-with-folders shape `repo-topology.md`
prescribes, holding correctly here; naming it as a fourth project overstates the count.

### 2a. Rules, hooks, skills: inherited implicitly, every process, unpinned

`~/.claude` is one live tree shared by every Claude Code process on the machine regardless of
which repository's directory it is launched from. This is not a copy step per project; it is a
property of how the tool loads config. A session opened in `daily-deep-learning` and a session
opened in `claude-setup` read the identical `~/.claude/rules/*.md`, `~/.claude/hooks/*`, and
`~/.claude/skills/*` at that moment. `dot-claude/` in this repo is the payload that gets synced
into that live tree (ADR-0001); the sync is a push from claude-setup, not a pull by the
consumer, and nothing records which sync a given session in another repo was running under.

One partial exception, found and worth flagging precisely rather than generalizing from: `git
ls-files .claude/rules` in `new-recruit` shows 13 rule files committed inside that repo's own
tree, separate from the shared live `~/.claude/rules` (23 files today, `ls ~/.claude/rules |
wc -l`). Spot-checked 2 of the 13 (`repo-topology.md`, `calibrated-claims.md`) byte-for-byte
against the live copy: identical, both last touched 2026-07-24 per `git log -1 -- <path>`. The
other 11 were not diffed and are not claimed identical. What is measured without qualification,
by filename set difference (`comm -23` between the two directory listings): 10 live rule
filenames have no counterpart in this mirror at all, meaning any rule added or renamed
in claude-setup since this snapshot was made will not appear here even though the file exists
and is git-tracked, giving a false impression of completeness to anyone who reads the repo copy
instead of the live tree. `daily-deep-learning/.claude` is empty; it carries no such mirror at
all.

### 2b. Harness tools (gate.py, panel.py, e2e/flow.py): inherited explicitly, and resolved three different ways

`quality-contract.json` in both consumer repos names claude-setup's tools directly, and neither
repo carries its own `tools/gate/gate.py`. Confirmed: `find ~/work/repos/daily-deep-learning
~/work/repos/new-recruit -iname gate.py` returns nothing in either tree.

The ledger this produces is centralized, by source, not by convention: `gate.py`'s `LEDGER`
constant is `state/gate-runs.jsonl`, and `setup_root()` (`tools/gate/gate.py:406-407`) resolves
to the directory two levels above wherever `gate.py` itself physically lives, never the
`--project` path being gated. So a gate run invoked from `new-recruit` or
`daily-deep-learning`, if it calls claude-setup's `gate.py`, writes its row into claude-setup's
own `state/gate-runs.jsonl`, not into a ledger inside the gated repo. `python3 -c` count over
that file, VERIFIED: 8,571 total rows, 311 for `claude-setup`, 110 for `new-recruit`, 69 for
`daily-deep-learning`, plus several hundred `tmp*` rows from selftest fixtures. Both consumer
repos are actively gating today: last recorded run for `new-recruit` 2026-08-08T00:14:54 PASS,
for `daily-deep-learning` 2026-08-08T10:46:18 PASS.

How each repo names the path to that shared `gate.py` differs, and this is the actual finding:

- **`daily-deep-learning`**: `${CLAUDE_SETUP:-$HOME/claude-setup}/tools/e2e/flow.py` and
  `.../tools/review/panel.py`, an environment-variable-with-fallback pattern. No pin to a
  commit.
- **`new-recruit`**: `python tools/harness.py exec review/panel.py run --project .`, a resolver
  script the repo carries itself (`new-recruit/tools/harness.py`, written 2026-07-31,
  docstring self-cites `docs/specs/2026-07-26-repo-target-architecture.md:56` as the design that
  named the defect it fixes). It reads `$CLAUDE_HARNESS`, then a `.harness-ref` file at the repo
  root naming a search-ordered list of candidate paths and a pinned commit sha, then raises
  rather than silently falling through on an unresolved override. `new-recruit/.harness-ref`
  pins `sha = 9d94efb5...`. `python tools/harness.py check` (VERIFIED, run 2026-08-08): resolves
  the path correctly, then reports the pin has drifted: `9d94efb5 pinned, 98bb64da on disk`.
  Eight days, the file's own comment ("Expect drift to be the normal state... re-pin
  deliberately") predicted exactly this and it has not been re-pinned.
- **The specific `$CLAUDE_HARNESS` / `.harness-ref` resolver pattern does not exist in
  claude-setup at all.** `grep -rn "CLAUDE_HARNESS" tools/ AGENTS.md`: zero hits, VERIFIED.
  Nothing in this repo offers or documents it; it lives only inside `new-recruit`. The
  `CLAUDE_SETUP` name itself is not unprecedented here, though, and this is worth being exact
  about rather than claiming a clean absence: `tools/wsl/bootstrap.sh:158` reads
  `REPO="${CLAUDE_SETUP:-$HOME/claude-setup}"`, the identical fallback idiom
  `daily-deep-learning`'s contract uses, but that script bootstraps a WSL machine's copy of
  this repo, not a consuming project's tool calls, so it is precedent for the idiom, not
  documentation of a cross-repo contract. Separately, `tools/gate/enforce_selftest.py` uses a
  different variable, `CLAUDE_SETUP_ROOT`, to sandbox `gate.py` inside its own selftest, an
  unrelated internal use of a similar name. And `docs/prior-art/tools-telemetry.json` and
  `docs/specs/2026-07-29-prompt-to-ticket-lifecycle.md` both document `$CLAUDE_OS_DIR`, the
  variable the telemetry and intent-capture hooks use to find this repo's `state/` from
  another repo's working directory, which is the same shared-ledger problem as section 2b's
  gate finding, already named and already fixed for that one subsystem. So the honest claim is
  narrower than "claude-setup documents nothing here": it documents `$CLAUDE_OS_DIR` for
  telemetry, has informal precedent for the `$CLAUDE_SETUP` idiom in its own bootstrap script,
  and has no cross-repo contract for tool invocation at all. A new-project author would not
  find any of this by reading `AGENTS.md`, which is the gap that matters.

`new-recruit/docs/specs/2026-07-26-repo-target-architecture.md` already made this exact
argument, in a sibling repo, on 2026-07-26: it names the absolute-path defect, proposes the
`$CLAUDE_HARNESS` / `.harness-ref` / vendored-fallback resolution order as `[INFERENCE]`
because "no such mechanism exists in the tree today," and `tools/harness.py` is that proposal
built, five days later. It is real, it works, and it is the best answer on the table today. It
is also filed under a consumer's own `docs/specs/`, not under claude-setup's, so claude-setup's
own docs never learned it has a canonical answer to "how does a new project find me."

## 3. Is any of this written down where a person would find it

No, for the mechanism; partially, for the naming.

- `docs/adr/0001-claude-setup-as-canonical-os-repo.md` states the sync direction (repo pushes to
  `~/.claude`) and names it as the inheritance path for config. It does not mention tools,
  ledgers, or how a consuming repo should reference `gate.py`.
- Nothing in `claude-setup/AGENTS.md`, `CLAUDE-OS.md`, or `docs/dir-purpose.txt` tells a new
  project author that `quality-contract.json` domains can call out to
  `claude-setup/tools/*`, what the resolution order should be, or that a resolver already
  exists in `new-recruit`. `grep -rli "bootstrap\|onboard\|new project\|inherit" docs/
  AGENTS.md` (VERIFIED, run in full over `docs/`, not a truncated sample) returns 51 files, so
  the words are not absent from the repo; what is absent is a how-to. Spot-checked the
  candidates most likely to be one: `docs/adr/0001-...` (read in full, states the config sync
  direction only, no tool-invocation guidance, quoted above); `docs/charters.md` and
  `docs/taste.md`, whose hits are `grep -n "inherit"`-VERIFIED to be unrelated passing usage
  (a lane-naming provenance note, a design-taste note); `docs/dir-purpose.txt` and
  `docs/CODEBASE-MAP.md`, which have zero `inherit` hits despite matching the broader
  four-term search on other words. None of the 51 files was read end to end for this claim; the
  claim is scoped to "no bootstrap how-to found among the likely candidates," not "no file in
  the 51 could possibly contain one."
- The one document that names the defect precisely and proposes the fix
  (`new-recruit/docs/specs/2026-07-26-repo-target-architecture.md`) lives in the wrong repo
  under this codebase's own `docs-control-plane.md` rule: it is an architectural decision about
  claude-setup's own boundary, and it is filed as a spec inside a consumer of that boundary. A
  reader of claude-setup's `docs/` tree would never find it.
- If a new project were started tomorrow, the actual path to inherit the setup is: copy
  another project's `quality-contract.json` as a template, guess or ask which absolute-path
  convention is current, and discover `~/.claude` config by having a session running and
  noticing the rules apply. No file says any of that in one place.

## 4. The smallest change that would make this repeatable

Do not design a new mechanism; one already works. Promote it.

1. Move (or copy, with the original left as a pointer) `new-recruit/tools/harness.py` into
   `claude-setup/tools/harness/` as the canonical resolver, so the producer repo ships its own
   consumption story instead of a consumer having invented and kept it. **If the moved file
   exceeds 300 lines, `docs/prior-art/harness.json` is owed under this repo's own gate rule**
   (`docs/dir-purpose.txt` / AGENTS.md "a new Python component over 300 lines owes
   `docs/prior-art/<name>.json`") -- flagging this now so it is not a surprise mid-change.
2. Name it once, in `AGENTS.md`, in a short section a new-project author would actually read:
   "a consuming project's `quality-contract.json` calls claude-setup tools through
   `tools/harness/harness.py exec <tool> ...`, resolved via `$CLAUDE_HARNESS`, then
   `.harness-ref`, then a vendored fallback; run `harness.py check` in the gate to catch pin
   drift before it silently runs a stale harness."
3. Give `daily-deep-learning` a `.harness-ref` and switch its `${CLAUDE_SETUP:-$HOME/claude-setup}`
   commands to the same `exec` form `new-recruit` uses, so there is one convention instead of
   two live ones.
4. Re-pin `new-recruit/.harness-ref` from `9d94efb5` to the current `98bb64da` deliberately,
   after reading what changed between them, per the file's own instruction, rather than leaving
   a drifted pin that nobody is acting on.
5. Separately, and smaller: `docs/adr/0001-claude-setup-as-canonical-os-repo.md`'s consequence
   list should gain one line naming the tool-inheritance path alongside the config-sync path it
   already states, since the two behave oppositely (one implicit and unpinned, one explicit and
   pinnable) and an ADR that documents only one of them is documenting half the boundary.

None of the above was implemented in this pass; this is the analysis and the recommendation,
not the change.

## Draft text, not posted

Per the task's hard rule, nothing was posted, commented, or edited on GitHub. The two blocks
below are drafts only, for the operator to approve or edit before anything goes out.

**Draft, a discussion comment on #43** (would explain the two-day gap found in section 1, since
the discussion's own recheck condition fires 2026-08-19 and this evidence bears on it directly):

> The feed went quiet 2026-08-06T15:03 not because the ledgers stopped, gate runs for
> claude-setup, new-recruit, and daily-deep-learning all continued through today, 29 rows total
> since the last post. The publisher itself was not re-run. Worth distinguishing before the
> 2026-08-19 recheck: this is "nobody ran it," not "nobody reads it."

**Draft, a one-line addition to `AGENTS.md`** (the smallest documentation change from section
4, item 2, offered here as exact proposed text rather than only description):

> ## Consuming this harness from another repository
> A project outside this repo calls its tools (`gate.py`, `panel.py`, `flow.py`) through
> `tools/harness/harness.py exec <relpath> ...`, resolved via `$CLAUDE_HARNESS`, then a
> `.harness-ref` file at that project's root, then a vendored fallback. See
> `new-recruit/tools/harness.py`'s own docstring for the full resolution order and rationale
> until this section is promoted into a canonical copy here.
