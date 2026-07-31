# Trace model: worldlines, cones, and one canonical branch

Spec, 2026-07-29. Scope: the event model for "trace every session and every turn".
Companion to the ticket model. This document defines what an event is, what a
worldline is, what branches, what prunes, what makes a branch canonical, and which
file on this machine is the timeline.

Every claim below that names a count, a path, or a field was read from the file at
design time. Claims I did not verify are marked UNVERIFIED in place.

---

## 0. Verdict first

**Nothing here needs to be written. The trace already exists and is severed at every
boundary.**

Inside one session the causal graph is complete: `~/.claude/projects/<slug>/<sessionId>.jsonl`
carries `uuid`, `parentUuid`, `promptId`, `timestamp` at millisecond precision, `cwd`,
`gitBranch`, `version` on every row, plus `tool_use` block ids and `hookInfos` entries with
the hook command and its duration. Verified on `8d6f373f-1fb3-4765-8616-a252ae5cfb3f.jsonl`:
1687 rows, 289 user rows of which 289 carry `promptId`, 21 human main-thread turns, 251
`tool_use` blocks paired with 251 `tool_result` blocks, 20 `system` rows carrying `hookInfos`.

Outside that one file, the graph has no edges at all. `state/gate-runs.jsonl` (968 rows) has
no session and no id. `state/bus.jsonl` has `from_session: ""` on 19 of 19 rows.
`state/hook-fires.log` UserPromptSubmit lines carry a timestamp and nothing else. Git commits
name no session. `state/reviews/<sha>.json` is keyed by commit only.

So "were getting lost" is not a missing-capture problem. It is a missing-edge problem plus
an unlogged-pruning problem, and both have a written, tested, uncalled implementation sitting
on this disk.

**The single physical fact:** `C:/Users/shova/.intent` does not exist (verified: `ls` returns
No such file or directory). `intent_control_plane/schema.py:12` sets
`DEFAULT_BASE_DIR = Path.home() / ".intent"` and `base_paths()` at lines 16-30 defines
`ledger = base_dir / "ledger" / "events.jsonl"`. `ledger_append()` in `cli.py` writes it.
`capture()` inserts the matching `events` row with `raw_text_ref = "<ledger path>:<line_no>"`.
None of it has ever run outside tests, because the directory has never been created.

---

## 1. The physics, stated exactly, before any mapping

Four objects, no decoration:

1. **Event.** A point in spacetime. Not a thing, an occurrence: it has coordinates and no
   duration.
2. **Worldline.** The path a persistent object traces through spacetime. Parameterized by its
   own proper time, which is not the same as anyone else's coordinate time.
3. **Light cone.** The past cone of event `e`, written `J-(e)`, is the set of events from which
   a signal could have reached `e`. It is derived from the geometry: given coordinates and an
   invariant speed, cone membership is computed, not recorded.
4. **Causal structure is a partial order.** Two events outside each other's cones are spacelike
   separated. They have no causal relation, and their temporal order is frame-dependent: two
   observers legitimately disagree about which came first. There is no global "now".

The fiction adds three things physics does not have: exactly one canonical branch, a detector
that names divergences at the moment they happen, and an authority that removes branches.

Point 4 is the one that does real work here, and it is the one a naive event log gets wrong.

---

## 2. What is an EVENT here

**An event is the smallest occurrence that can be cited as a cause and addressed by a stable
id.** That test admits nine kinds today and excludes three that look tempting.

### Admitted (already observable on this machine)

| event_type | vendor id available today | source file | live today |
|---|---|---|---|
| `user_prompt` | `promptId` (UUID) | transcript `type=user` row | written, unwired (see 10.W3) |
| `assistant_final` | `uuid`, `requestId` | transcript `type=assistant` row | written, unwired |
| `tool_call` | `toolu_...` from the `tool_use` block `id` | transcript assistant content block | not captured |
| `tool_result` | same `toolu_...` | transcript user content block | not captured |
| `hook_fire` | `hookInfos[].command` + `toolUseID` | transcript `type=system` row, and `state/hook-fires.log` | log exists, carries no ids |
| `session_start` | `session_id` | `state/hook-fires.log` (210 lines) | live |
| `compaction` | none | `state/hook-fires.log` PreCompact (300 lines) + `state/compact-log.md` | live, no session id |
| `commit` | sha | git | not captured |
| `gate_run` | none (there is no id column) | `state/gate-runs.jsonl` (968 rows) | live, unjoinable |
| `review_verdict` | commit sha | `state/reviews/<sha>.json` (6 files) | live |
| `claim` | `C-0NN` | `state/claims-verify.jsonl` (26 rows) | live |
| `refutation` | `C-0NN` + ts | `state/refutations.jsonl` (287 rows) | live |
| `lesson` | `L001` / `L-2026-07-27-a` | `state/lessons.jsonl` (25 rows, two shapes) | live |
| `bus_message` | row `hash` (16 hex) | `state/bus.jsonl` (19 rows, 7 chained) | live |
| `subagent_spawn` | workflow / agent id | `projects/<slug>/<session>/subagents/workflows/wf_*/agent-*.jsonl` | not captured |

### Derived (an event, but produced by reading other events, not by an instrument)

| event_type | how derived |
|---|---|
| `correction` | operator pushback on a prior turn. 258 of 814 items in `~/.claude/corpus-operator-inputs/distilled_raw.json` already carry `is_correction: true`. This is a labeled set that exists, not a classifier to build. |
| `prune` | see section 7 |
| `canonize` | see section 7 |

### Rejected as events

- **A ticket.** A ticket is a projection over events, not an occurrence. `TODO.md` lines are
  the current fold; they have no timestamp of their own that means anything.
- **A file read inside a tool call.** Below the addressable floor. `tool_call` is the floor.
- **A lesson or a verdict about the past.** These ARE events (they occurred, an actor made
  them), but their effect is on a projection. An event never changes another event. This is
  the immutability rule from section 9.

The 2026-06-25 spec at `work-docs/specs/2026-06-25-local-intent-control-plane.md:214` named 8
intended event types of which exactly 2 are emitted by live code. Shipping 15 at once repeats
that. Section 10 ranks them.

---

## 3. What is the WORLDLINE

**Not the session. The worldline is the repository working tree. The session is a proper-time
segment of an agent acting on it.**

The argument is not aesthetic. A worldline has to be the thing with continuous identity.
Sessions do not have that: `state/hook-fires.log` records 300 PreCompact fires and 210
SessionStart fires, and the same session id reappears after compaction (`31f7a525-...` appears
on four separate SessionStart lines on 2026-07-24 alone). Sessions die, restart, fork, and get
their memory replaced. The tree persists across all of it.

The tree also already has a coordinate: `gate-runs.jsonl.fingerprint`, a 16-hex tree
fingerprint from `tools/gate/gate.py:144 tree_fingerprint`. 968 rows of it. That is a sampled
path through configuration space. It is a worldline that has been getting recorded for four
days with nothing reading it as one.

**Corollary, and it explains a live bug.** `tools/bus/bus.py LANE_MAP` derives the lane from
`cwd`. The three sessions that built this harness all ran with `cwd = ~/Downloads/new-recruit`
and were therefore labeled lane C while modifying `claude-setup`, which is lane B. Deriving
lane from cwd labels the observer's coordinates. The object being moved is the repo. Lane
should be derived from `repo_path`, meaning the tree the event actually wrote to, not from
where the shell happened to be standing.

Practical definition used by the schema:

```
worldline_id = repo_path            # the object
segment_id   = session_id           # a proper-time segment of an agent on it
frame        = (cwd, gitBranch, version, actor)   # the observer's coordinates
```

`repo_path`, `branch`, `session_id` are all already columns on `events`. `cwd` and `version`
go in `metadata`.

---

## 4. What creates a BRANCH

A branch exists wherever one segment has more than one successor. Six sources, and they are
not the same kind of thing, which is the part the metaphor flattens:

| Source | What forks | Merges back? | Evidence today |
|---|---|---|---|
| **Subagent spawn** (`isSidechain: true`) | context only | yes, the agent's final text returns to the parent turn | 17,820 sidechain user rows measured across `~/.claude/projects/` |
| **Parallel sessions** | nothing (they share one tree) | no | 63 sessions with human turns; `session_guard.py` exists because this is normal here |
| **Compaction** | the agent's visible past | no, it replaces | 300 PreCompact fires; 12 `## compact` blocks in `state/compact-log.md` |
| **Git branch / worktree** | repo state | yes, git merge | git |
| **Interruption / retry** | the turn | no, one side is abandoned | `interruptedMessageId` key on user rows; 38 `queue-operation` rows in one transcript |
| **Queued prompt** (`promptSource: "queued"`) | turn ordering | joins the same line | transcript |

Three of these fork **repo state**, three fork **epistemic state**. Only the git one has a
merge operator that anyone trusts. A trace model that gives all six the same `branch` field
will produce a graph nobody can query, so the schema carries `branch_kind` alongside
`branch_id`.

The dangerous case is row 2. Two parallel sessions are, in the metaphor, two universes. In
this system they are two agents writing the same `state/*.jsonl` files and, once `~/.intent`
exists, the same `intent.db`. `schema.connect()` sets no WAL pragma, no `busy_timeout`, and no
`BEGIN IMMEDIATE` outside `transitions.py`. Branches here collide. See section 9, break 3.

---

## 5. The causal past of a turn, concretely, in files that exist

Take a human turn T with `promptId = ae60aad5-7fd7-4281-b234-c27bb447edbb`, `uuid =
374c96af-...`, `timestamp = 2026-07-27T16:16:38.560Z`, session `8d6f373f-...`, repo
`C:\Users\shova\claude-setup`, branch `main`. Verified row.

**Inside the session, `J-(T)` is complete and machine-readable today:**

- Walk `parentUuid` from `T.uuid` to the session root. That is the full ordered ancestry:
  every prior human turn, every assistant turn, every tool call, every hook fire, in one file.
- `type=system` rows on that path carry `hookAdditionalContext`, which is literally the text a
  hook injected into T's context. Those are causes the model actually saw.
- `hookInfos` on those rows names the command and `durationMs`. Verified sample:
  `[{"command":"python C:\\Users\\shova\\.claude\\hooks\\completion_gate.py","durationMs":187}, ...]`.
- Content blocks give `tool_use.id` paired 251/251 with `tool_result`.

**Outside the session, `J-(T)` has no recorded edges. Every join below is a guess:**

| Wanted edge | Available key on the turn side | Available key on the other side | Join |
|---|---|---|---|
| turn to the gate run it caused | `session_id`, `timestamp` | `ts`, `commit`, `fingerprint` | timestamp proximity |
| turn to the commit it produced | `session_id`, `gitBranch` | sha, author date | timestamp proximity |
| turn to the hook that fired on it | `promptId`, `uuid` | timestamp only | timestamp proximity, and 23 UserPromptSubmit lines total |
| turn to the bus message it caused | `session_id` | `from_session: ""` on 19/19 | impossible |
| turn to the review of its output | `session_id` | commit sha | two hops of proximity |
| turn to the ticket it belongs to | none | `TODO.md` text tag | none |
| turn to an earlier session's turn | none | none | none |
| turn to `~/.claude/history.jsonl` | `session_id`, timestamp | `sessionId`, epoch ms, no promptId | session plus proximity, never per-prompt |

That table is the deliverable of this section. **The cone is intact inside one transcript file
and severed at every boundary that file does not own.** The severance is one missing field in
seven places, not seven missing systems.

**The field that closes it: `promptId`.** Present on 289/289 user rows. A UUID. Stable across
the session. Not present in the hook payload (verified: `dot-codex/hooks/intent-capture.sh`
reads only `session_id`, `cwd`, `workspace`, `prompt` from the payload; whether Claude Code
sends `promptId` in the UserPromptSubmit payload is UNVERIFIED here), so a hook must resolve it
by reading the tail of `transcript_path`, which the payload does provide (visible in
`state/hook-fires.log` SessionStart lines).

**Ordering warning, which is the physics doing real work.** Three of this repo's own timestamp
writers are second-precision: `intent_control_plane/util.py:19 utc_now()` calls
`.replace(microsecond=0)`; `tools/bus/bus.py now_iso()` uses `timespec="seconds"`;
`gate-runs.jsonl` ts is second-precision. The vendor transcript is millisecond. And the
operator corpus already contains a proven same-second collision:
`2026-07-25T08:36:55` carries two different prompts in the same session. **Timestamps are
coordinates, not the order.** The order comes from parent pointers and from a monotonic
sequence number, never from `ts`.

---

## 6. Where the existing hash chain fits, and what it does not give

`tools/bus/bus.py` lines 120-175. Verified live: `python tools/bus/bus.py verify` reports
`19 row(s): 7 chained, 12 predate chaining`, `chain intact across every chained row`, exit 0.

```
CHAIN_FIELDS = ("id","ts","from_lane","origin_lane","from_session","to",
                "kind","subject","body","refs","prev")
canonical(rec) = json.dumps({k:rec[k] for k in CHAIN_FIELDS if k in rec},
                            sort_keys=True, separators=(",",":"), ensure_ascii=False)
row_hash(rec)  = sha256(canonical(rec)).hexdigest()[:16]
```

**What it gives, and it is worth keeping verbatim:**

- Content commitment per row. `row_altered()` is checked on the **read** path, not only in
  `verify`, so a tampered row is marked at the moment it is handed to a reader.
- Sequence integrity within one file: `prev` names the previous row's id, so insertion,
  deletion, and reorder inside the chained region are all detected.
- Forward compatibility: absent keys are omitted rather than defaulted, so adding a field
  later cannot silently rehash rows that predate it. This is the property that lets the new
  ledger add `parents` without touching `bus.jsonl`.
- `row_id()` returns the **stored** hash for a chained row, so a tampered row keeps its
  address and a cursor set before the tamper still resolves.

**Does it give the ordering guarantee a canonical timeline needs? No, in four specific ways:**

1. **Coverage.** 12 of 19 rows carry no hash. `verify` says so itself: "those rows carry no
   hash, so nothing can be said about whether they were altered."
2. **No tip anchor.** The module docstring states it: truncation of the newest rows is
   undetectable, because nothing outside the file records where the tip should be. A canonical
   timeline must know where its head is. A chain alone cannot tell you.
3. **No authentication.** All lanes run as the same OS user. Anything that can edit the log can
   recompute the chain over its edit. Tamper evident, not tamper proof, and it authenticates
   nobody. A canonical timeline decides what counts, which is an authorization question the
   chain does not touch.
4. **A chain is a total order. Causality is a partial order.** This is the deep one. Forcing
   concurrent lanes into a single chain manufactures an ordering that does not exist, and the
   order it manufactures is arrival-at-the-file order, which is the observer's frame, not the
   causal one. Two spacelike-separated lane events get an authoritative-looking `prev`
   relationship they do not have.

**Verdict.** Keep the mechanism, change the shape. Copy `canonical()` and `row_hash()`
unmodified into the new ledger (same 16-hex width, same sorted-keys rule, same omit-absent-keys
rule) and replace the single-valued `prev` with a list-valued `parents`. That turns the chain
into a Merkle DAG, which is what git already is for the repo worldline. `state/bus.jsonl` stays
exactly as it is: a lane-to-lane message channel with 19 rows, and it becomes a **producer** of
`bus_message` events into the ledger. It does not become the timeline. Conflating "I told you
X" with "X happened" is how a comms log turns into an unqueryable fact log.

---

## 7. What makes a branch canonical, and what prunes

### Canonical is a computable predicate, not a decree

There is no TVA here. The operator is both the branching agent and the authority, so
canonicity cannot be assigned from outside. It has to be a rule applied to recorded evidence,
and the rule has to be contestable.

An event `e` is canonical iff all three hold:

1. Either `e` produced no repo state, or the terminal tree of `e`'s branch is an ancestor of
   the current `HEAD`. Test: `git merge-base --is-ancestor <sha> HEAD`.
2. `e` is not the target of a `supersedes` edge.
3. `e` is not the target of a `pruned_by` edge.

**The gap, stated rather than papered over.** Condition 1 is decidable only for committed work.
Verified: the entire RT section of `TODO.md` is uncommitted (`git show HEAD:TODO.md | grep -c
RT-1` returns 0, `git log -S "RT-1 Log" -- TODO.md` returns empty). For uncommitted work the
predicate has no witness, and the honest answer is `canonical: null`, never `false`. A trace
model that reports `false` where it means "undecidable" is the same defect as a confidence
score pinned at 0.9.

### Pruning must be an appended event, never an unlink

Five things prune this system today. Exactly one leaves a record.

| Pruner | What it removes | Logged? |
|---|---|---|
| `cleanupPeriodDays` default (Anthropic docs say 30 days; the key is **not set** in `~/.claude/settings.json`, verified against its 13 top-level keys) | whole transcripts, the richest causal graph on the machine | no, and it is external |
| Compaction | the agent's view of its own past, 300 fires | partially: `state/compact-log.md` records git status and last 3 commits, not the summary and not the session id |
| `chunk.py` | `for f in os.listdir(OUT): os.remove(...)` deletes every chunk before writing | no |
| `tools/selfimprove/scan.py` | `write_text` overwrites `proposals.jsonl` wholesale, so a proposal id has no history | no |
| `git branch -d` | a branch head | yes, reflog |

Rule: **a prune is an appended `prune` event naming `target_event_id`, `reason`, `actor`. The
target is never removed.** This is where the fiction is actively wrong and the wrongness is
already costing him: in the fiction the authority deletes the branch, and on this machine the
default retention policy is doing exactly that, silently, to the only complete record of his
turns.

The single highest-value action in this whole design is a config key, not code: set
`cleanupPeriodDays` in `~/.claude/settings.json`. It is currently absent.

### Divergence should be named when it happens, not reconstructed

This is the one thing the fiction contributes that a plain trace model misses. A nexus event is
detected at the moment of divergence, not inferred later. That maps onto something already
labeled here: `distilled_raw.json` carries `is_correction: true` on 258 of 814 items. The
external literature agrees on the operational definition (observable developer correction or
pushback in the log) and reports precision 0.93 over 16,118 validated episodes
(arXiv 2605.29442, per the prior-art survey; I did not fetch the paper). So a `correction`
event with a `supersedes` edge has 258 labeled positives on this disk before anything is
written.

---

## 8. Authority order becomes a sort key

`CLAUDE-OS.md:67` states the order as prose: `raw prompt > spec > verified evidence > repo
state > summary > vector similarity`. Verified: `authority` is written into the `events` column
and read by nothing. `rank_by_relevance_and_recency` in `text_index.py` sorts on
`relevance * recency` only.

Make it an integer so it can be an `ORDER BY`:

```
AUTHORITY_RANK = {
  "raw_user_prompt":   0,
  "spec":              1,
  "verified_evidence": 2,
  "repo_state":        3,
  "summary":           4,
  "vector_similarity": 5,
}   # lower wins; sort lexicographically on (authority_rank, -(relevance*recency))
```

**Why this is the mechanism behind "were getting lost", stated as a claim with its evidence.**
Compaction output is `summary`, rank 4. After 300 PreCompact fires, the agent's working view is
rank-4 text, while the rank-0 text that caused the work sits 525 MB away in a transcript file
nothing reads. Ranking retrieval by similarity alone lets a summary of a prompt outrank the
prompt. Making `authority` the primary sort key forbids that by construction, and it is a
comparison function plus a dict, not a system.

This is also the light cone doing real work: retrieval that pulls an event from **outside**
`J-(current turn)` is acausal by definition. It may still be useful, but it must be labeled
`outside_cone: true` so the model knows it received a resemblance, not a cause.

---

## 9. Where the metaphor breaks, explicitly

A metaphor that survives contact everywhere is decoration. Seven places this one fails, and
each failure changes a design decision.

**Break 1. There is no `c`, so the cone cannot be computed.** In relativity, cone membership
falls out of the geometry given an invariant speed. Here the operator is a superluminal
channel: he reads lane C output on one screen and types it into lane B on another, with no
recorded trace. Any event can influence any later event. **Consequence: cone membership must be
RECORDED as an edge, never inferred from timestamps and repo distance.** This kills the
tempting design where you reconstruct causality from proximity, which is exactly what section 5
shows the system is reduced to today.

**Break 2. Timestamps do not define the order.** Physics has continuous proper time. This
system has three second-precision writers, one millisecond writer, multiple clocks, and a
proven same-second collision in the operator corpus. **Consequence: `seq` and `parents` are the
order; `timestamp_utc` is a coordinate and is never the sort key.**

**Break 3. Branches are not independent universes. They collide.** Two parallel sessions write
the same `state/*.jsonl` and the same `intent.db`. There is no analogue in physics for two
worldlines assigning to the same variable. **Consequence: the branch model must carry a write
scope, and the store needs WAL plus `busy_timeout` before per-turn hooks start writing from
several sessions. `schema.connect()` has neither today.**

**Break 4. Worldlines do not merge; these do, constantly.** Two objects can collide, but their
worldlines stay two. Here a subagent's result merges into the parent turn, a compaction summary
merges N turns into one text, and git merges two histories into one commit. **Consequence:
`merged_from` is a first-class edge type and `parents` is a list, not a scalar. A chain cannot
express this, which is break 4's version of section 6's point 4.**

**Break 5. There is no TVA and there should not be one.** No external authority exists to
declare a branch sacred. Many-worlds does not have a preferred branch either; the Born rule
gives weights, not canonicity. **Consequence: "canonical" is an explicit, contestable
projection computed by the rule in section 7, recomputable from the ledger, and it returns
`null` when undecidable. It is never a stored truth that someone asserted.**

**Break 6. Pruning as deletion is the failure, not the feature.** The fiction's authority
deletes branches. On this machine the unlogged pruner is the 30-day retention default and three
scripts that overwrite their own history. **Consequence: prune is an append, and the target
survives.**

**Break 7. Compaction is amnesia, not time travel, and correction is reinterpretation, not
retrocausality.** Nothing here rewrites the past. Compaction changes what the agent can see;
the transcript is untouched. A refutation changes how a past claim is read; the claim event is
untouched. **Consequence, and it is the load-bearing invariant: events are immutable, and
everything that "changes the past" is a new event plus a projection change.** Physics agrees:
the past light cone of an event does not change.

Two smaller ones, named so they are not mistaken for insight: physics is roughly
time-reversible and this log is not (you cannot run a deployment backwards), and the
relativity-of-simultaneity point is true here for a mundane reason, clock skew and second
precision, not a deep one. Do not oversell either.

---

## 10. The event schema

One JSON object per line in the ledger. Fields marked EXISTS are already columns on
`events` in `intent_control_plane/schema.py` and need no DDL change.

```jsonc
{
  // identity and order
  "event_id":        "evt_20260729031500_9f3c1a2b7d",  // EXISTS. stable_id("evt"), util.py:22.
                                                       //   Second-granularity prefix + 10 hex.
                                                       //   NOT sortable below one second.
  "seq":             41287,                            // NEW in line. Ledger line number.
                                                       //   ledger_append() already computes this
                                                       //   as line_no; today it is only embedded
                                                       //   in raw_text_ref. This is the order key.
  "hash":            "3f8a1c0d9e7b4a26",               // NEW. sha256(canonical(rec))[:16],
                                                       //   bus.py:137 rule, copied unmodified.
  "parents":         ["evt_...", "evt_..."],           // NEW. Recorded causal past. A list,
                                                       //   because branches merge (break 4).
                                                       //   Also written to graph_edges as caused_by.
  "prev":            "evt_...",                        // NEW. Predecessor on THIS branch only.
                                                       //   Sequence integrity, not causality.

  // worldline and frame
  "worldline_id":    "C:/Users/shova/claude-setup",    // = repo_path. The object. See section 3.
  "repo_path":       "C:/Users/shova/claude-setup",    // EXISTS
  "session_id":      "8d6f373f-1fb3-4765-8616-a252ae5cfb3f", // EXISTS. A segment, not a worldline.
  "branch":          "main",                           // EXISTS. Git branch.
  "branch_id":       "br_8d6f373f",                    // NEW. Trace branch (section 4).
  "branch_kind":     "session",                        // NEW. session|subagent|compaction|git|
                                                       //   interruption|queue
  "actor":           "shoval",                         // EXISTS. shoval|claude|hook:<name>|
                                                       //   tool:<name>|git|gate|codex
  "timestamp_utc":   "2026-07-29T03:15:00Z",           // EXISTS. Coordinate. NOT the order key.

  // content and provenance
  "event_type":      "user_prompt",                    // EXISTS. Enum in section 2.
  "authority":       "raw_user_prompt",                // EXISTS. Enum + rank in section 8.
  "raw_text_ref":    "C:/Users/shova/.intent/ledger/events.jsonl:41287",  // EXISTS
  "model_text":      "Deep research them",             // EXISTS. Redacted copy.
  "redaction_state": "raw_local",                      // EXISTS. raw_local|redacted_for_model
  "source": {                                          // NEW. Idempotency key for mirroring.
    "system": "claude_code_transcript",                //   claude_code_transcript|history_jsonl|
                                                       //   corpus_operator_inputs|git|gate|bus|
                                                       //   review|claims|lessons
    "id":     "ae60aad5-7fd7-4281-b234-c27bb447edbb",  //   promptId | uuid | toolu_* | sha |
                                                       //   bus row hash | C-0NN | L-id
    "file":   "C:/Users/shova/.claude/projects/C--Users-shova-claude-setup/8d6f373f-....jsonl",
    "line":   412
  },

  // ticket and workflow linkage
  "bead_id":         "RT-1",                           // EXISTS, currently never written.
                                                       //   The SETUP-OS / AUTO-nn / RT-n tag.
  "workflow_id":     null,                             // EXISTS
  "intent_id":       null,                             // EXISTS on intent_cards, mirrored here

  // projection, written by a LATER event, never by the producer
  "canonical":       null,                             // NEW. true|false|null. null = undecidable
                                                       //   (uncommitted work, section 7).
  "outside_cone":    false,                            // NEW. Set on retrieved context that is
                                                       //   not in this turn's recorded past.

  "metadata": {                                        // EXISTS as metadata_json, currently
                                                       //   hardcoded to "{}" in capture().
    "cwd": "C:\\Users\\shova\\claude-setup",
    "cli_version": "2.1.220",
    "parent_uuid": "e093dd35-396d-4cf2-b4ff-6e686605b320",
    "prompt_id": "ae60aad5-7fd7-4281-b234-c27bb447edbb",
    "tool_use_id": null,
    "claimed_confidence": null,                        // RT-1 pair, on event_type=claim
    "action": null,                                    // RT-1 pair
    "compaction_trigger": null,                        // auto|manual, hook already logs it
    "fingerprint": null                                // gate tree fingerprint
  }
}
```

### Edge types for `graph_edges`

`graph_edges(edge_id, source_id, target_id, edge_type, created_at_utc)` is declared in
`schema.py:155` and has **zero writers** (verified: grep across all 44 src modules and the test
suite returns only the DDL and one test that lists the table name). It is free.

| edge_type | source | target | meaning |
|---|---|---|---|
| `caused_by` | event | event | target is in source's recorded past cone |
| `responds_to` | assistant_final | user_prompt | the reply to a turn |
| `invoked_by` | tool_call | assistant_final | which turn issued the call |
| `spawned` | subagent branch root | parent turn | fork |
| `merged_from` | parent turn | subagent result, or compaction summary, or git merge | join |
| `supersedes` | correction | the turn it corrects | the nexus edge |
| `evidences` | gate_run / review_verdict / refutation | claim | closes the RT-1 triple |
| `pruned_by` | event | prune event | removed from canonical, still present |
| `mirrors` | ledger event | vendor source id | idempotent backfill |

### What this buys, immediately and by joins rather than new tables

- **RT-1** (`TODO.md:29`, currently open): `claimed_confidence` and `action` live in
  `metadata` on a `claim` event; `verified_outcome` is the status of whatever is joined by an
  `evidences` edge. The reliability curve becomes a query. `eval_results.details_json` already
  accepts arbitrary JSON, so the computed rows persist with no DDL change.
- **RT-2** (decision ledger + rejection rate): a human approve or reject is an event with
  `actor: "shoval"` and `event_type: "review_verdict"`. Rejection rate is a count over the
  ledger. A ratio that has never seen a rejection is still the finding.
- **"Which prompt caused this TODO line"**: `bead_id` on the prompt event, which is the first
  time any tag has existed outside `TODO.md` prose.

---

## 11. Which existing file becomes the timeline

**`C:/Users/shova/.intent/ledger/events.jsonl`.**

It is defined at `intent_control_plane/schema.py:16-30`, written by `ledger_append()` in
`cli.py`, indexed by the `events` table via `raw_text_ref = "<path>:<line_no>"`, and it has
zero rows because the directory has never been created. The writer exists, the reader exists,
the CLI exists, and 426 tests pass over it. **Do not write a ledger. Run `intent init`.**

Four tiers, and being explicit about which is which is what keeps this honest:

| Tier | Path | Role | Owned by | Mutable |
|---|---|---|---|---|
| 0 | `~/.claude/projects/<slug>/<sessionId>.jsonl` | the actual worldline, 807 files, 525 MB | vendor | no, but **deleted on a 30-day default** |
| 1 | `~/.intent/ledger/events.jsonl` | **the timeline**, append-only, hash-DAG | us | append only |
| 2 | `~/.intent/intent.db` (`events`, `graph_edges`, `intent_cards`, `evidence`) | index and projections | us | rebuildable |
| 3 | `state/bus.jsonl` | lane comms, unchanged, 19 rows | us | append only, chained |

Two properties this arrangement must hold, both of which are design commitments and not
observations:

1. **The ledger is a projection, not the only copy.** Every row must be reconstructible from
   tier 0 plus `state/`. That makes losing `~/.intent/` recoverable, and it makes backfilling
   the 587 corpus prompts an ordinary operation rather than a one-shot migration. The `source`
   field plus the `mirrors` edge is what makes re-running the mirror idempotent.
2. **It lives outside the repo on purpose.** The causal graph crosses repos: lane C is
   `~/Downloads/new-recruit`, lane B is `claude-setup`. A repo-local ledger cannot hold a
   cross-repo edge, which would re-fragment exactly what this is joining. The cost is that
   `~/.intent/` is not git-tracked, which property 1 is the mitigation for.

---

## 12. Wiring order, ranked. Nothing here is new construction

Each item names the file and the change. Effort is my estimate and is UNVERIFIED until run.

| # | Action | File | Why first |
|---|---|---|---|
| W1 | Set `cleanupPeriodDays` | `~/.claude/settings.json` | The unlogged pruner is deleting tier 0. One key. Verified absent from the file's 13 keys. |
| W2 | `intent init` | creates `~/.intent/` | Every write path defaults there and it does not exist. Zero code. |
| W3 | Replace the dangling symlink with a real script and fix its PYTHONPATH | `dot-claude/hooks/intent-capture.sh` is a text file containing `/home/shovalbe/.codex/hooks/intent-capture.sh`; the real 192-line script is at `dot-codex/hooks/intent-capture.sh` and sets `PYTHONPATH="$HOME/projects/intent-control-plane/src"`, a path that does not exist (the package is at `claude-setup/intent-control-plane`) | Capture is 100% written and 0% reachable |
| W4 | Add a `UserPromptSubmit` hook event | `~/.claude/settings.json` (verified: 6 events registered, none of them UserPromptSubmit) | Without it W3 never fires |
| W5 | Add `--metadata` to `capture` and stop hardcoding `"{}"` | `cli.py` `capture()` insert tuple and `build_parser()` (verified: capture takes event-type, session, repo, branch, bead, workflow, actor, authority, text, and nothing else) | This is the field that carries `source`, `parents`, `seq`, `hash`. Smallest change, largest effect. |
| W6 | Add `intent link --source --target --type` | `cli.py`, by analogy with `attach_evidence` | `graph_edges` has zero writers. Edges are the whole point. |
| W7 | Make `authority` a sort key | new `AUTHORITY_RANK` + `rank_by_relevance_and_recency` in `text_index.py` | Stops a compaction summary outranking the prompt it summarizes |
| W8 | Write `session_id` and the leaf uuid on UserPromptSubmit and PreCompact lines | `state/hook-fires.log` writer | 23 UserPromptSubmit lines carry a timestamp and nothing else |
| W9 | Add `run_id` and `session_id` to gate rows | `tools/gate/gate.py` | 968 rows currently name no cause |
| W10 | Pass `session_id` through to `--from-session` | `tools/bus/bus.py` (lines 30-33 document why it is empty: `CLAUDE_SESSION_ID` is not in the hook env; the hook payload does carry `session_id`) | `from_session` empty on 19/19 |
| W11 | WAL + `busy_timeout` before per-turn writes go multi-session | `schema.connect()` | Break 3. Untested contention path. |
| W12 | Backfill the 587 corpus prompts | loop over `capture()` in-process | `capture` takes one `--text`; there is no bulk import. Corpus rows have `session` but no `promptId`, so `source.id = sha256(text)[:16]` since `ts` is not unique. |

Ordering note on W12: 133 of 537 distilled item timestamps and 109 of 168 rule `evidence_ts`
values point at prompts the compaction filter removed from the corpus. Those backfilled rows
cite an authority-0 source that no longer exists. They must be captured with
`authority: "summary"` (rank 4) and a `source` that resolves to nothing, not as raw prompts.
Recording a dangling citation honestly is the whole point of the authority column.

---

## 13. What I did not verify

- Whether the Claude Code UserPromptSubmit hook payload includes `promptId`. The hook currently
  reads only `session_id`, `cwd`, `workspace`, `prompt`. The transcript-tail fallback is the
  design assumption.
- The 30-day `cleanupPeriodDays` default value. The key's **absence** from
  `~/.claude/settings.json` is verified; the documented default is carried from the prior-art
  survey and I did not fetch the doc.
- The 17,820 sidechain row count and the 807-file / 525 MB totals, carried from the prior-art
  survey. I measured only the `claude-setup` project directory (1 file, 1687 rows, 21 human
  turns).
- arXiv 2605.29442's precision figure and the `is_correction` count of 258/814, both carried
  from the surveys.
- Whether `intent init` succeeds against a real `~/.intent` on this machine. I read the code
  path; the survey reports a successful run against a temp base-dir, which is not the same
  thing as running against `Path.home()`.
- Effort estimates in section 12. Every one is a guess until the change is made.
