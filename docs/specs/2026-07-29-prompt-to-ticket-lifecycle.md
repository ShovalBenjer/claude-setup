---
PRD: prd/claude-os.md (L2 intent ledger), prd/autonomy-ecosystem.md (AUTO-06)
Ticket: PT-lifecycle (this spec), supersedes the "~/.intent never created" gap
Status: active
Authority: measured against the live machine on 2026-07-29. Every count below was
computed by parsing the file, not read from a doc. Unverified items are listed in
section 11.
---

# Implementation spec: prompt-to-ticket lifecycle

## 0. Verdict, and what this spec is allowed to build

The storage layer, the ticket-shaped record, the state-transition table, the
evidence table, the capture entrypoint and the hook script all already exist and
are tested. The reason prompts get lost is not missing code. It is three
disconnected wires and one absent directory:

1. `C:/Users/shova/.intent` does not exist. `ls` confirms. Every write path in
   `intent_control_plane` defaults to `Path.home()/".intent"`, so the ledger has
   never had a row.
2. `dot-claude/hooks/intent-capture.sh` is not a script. Its whole content is the
   text `/home/shovalbe/.codex/hooks/intent-capture.sh`, a git-checked-in Linux
   symlink stored as a plain file on Windows.
3. `~/.claude/settings.json` has no `UserPromptSubmit` event at all. Verified by
   dumping the live hooks map: SessionStart, PreToolUse x2, PostToolUse, PreCompact,
   Stop x3, Notification. Nothing on prompt submit.

A fourth break, not previously reported, was found while verifying the hook:

4. `dot-codex/hooks/intent-capture.sh` line 15 invokes `python3`. In this Git Bash
   `which python3` returns nothing; only `python` resolves, to
   `C:/Users/shova/AppData/Local/Programs/Python/Python311/python`. The hook could
   not have worked on this machine even with the other three fixed. It also sets
   `PYTHONPATH="$HOME/projects/intent-control-plane/src"`, a directory that does
   not exist here (the package lives at `claude-setup/intent-control-plane`), and
   `import intent_control_plane` from system python fails with `ModuleNotFoundError`.

So this spec is mostly a wiring spec. The inventory below states, per component,
whether the action is WIRE (it exists, connect it), PATCH (it exists, small
correctness fix) or WRITE (genuinely absent).

| Component | Exists today | Action |
|---|---|---|
| `events`, `intent_cards`, `evidence`, `state_transitions`, `hive_bindings` tables | yes, `schema.py` SCHEMA_VERSION 3, 14 tables | WIRE |
| `intent capture / extract / evidence attach / state transition / session brief / doctor` | yes, `intent.exe` runs, 426 tests green | WIRE |
| Allow-list lifecycle state machine with checkpoint-before-write | yes, `transitions.py::PASS_LIFECYCLE` and `advance_pass` | WIRE (copy the pattern for a second subject type) |
| Hash-chained append-only ledger with tamper detection | yes, `tools/bus/bus.py::canonical/row_hash/row_id/row_altered` | WIRE (import, do not reimplement) |
| Executable per-domain gate producing a machine record | yes, `tools/gate/gate.py run --json` writes `{"record":…,"results":…}` and exits 0/1/2 | WIRE |
| Prompt corpus, 587 rows, 55 sessions | yes, `~/.claude/corpus-operator-inputs/corpus_inputs.json` | WIRE |
| Stable ticket identity | no. `prompts.id` is reassigned on every `memory_index.py build`; `corpus_inputs.json` has no `id` key | WRITE (one pure function) |
| Ticket state vocabulary and guards | no | WRITE (one module) |
| `ledger_append` line-number ref under concurrency | broken by design, see section 6 | PATCH |
| WAL / busy_timeout on the shared sqlite path | absent from `schema.connect()` | PATCH |
| `UserPromptSubmit` registration | absent | WIRE |

Net new code: one module (`tickets.py`), one test file, two small tools, one hook
script. Everything else is configuration and three-line patches.

---

## 1. Ticket identity

### 1.1 The scheme

```
ticket_id = "PT-" + sha256(canonical).hexdigest()[:12]

canonical = json.dumps(
    {"session": session_id, "text_sha": text_sha, "occ": occurrence_index},
    sort_keys=True, separators=(",", ":"),
).encode("utf-8")

text_sha  = sha256(re.sub(r"\s+", " ", text.strip()).lower().encode("utf-8")).hexdigest()
occurrence_index = number of earlier rows in the SAME session with the SAME text_sha,
                   ordering by (ts, text_sha) so the sort is total
```

`PT` reads as prompt ticket. It does not collide with any tag already in use here:
`SETUP-OS #n`, `AUTO-nn`, `RT-n`, `C-0NN` (claims), `L001` / `L-2026-07-27-a`
(lessons), `evt_` / `intent_` / `ev_` / `st_` / `fb_` (intent-plane rows).

### 1.2 Why not the ids that already exist

- `intent_cards.intent_id` and `events.event_id` come from
  `util.stable_id()`, which is `prefix_<UTC timestamp>_<10 random hex>`. Clock and
  randomness based. A backfill re-run mints different ids for the same prompt, which
  is precisely the `memory_index.py` defect (`build()` does `DROP TABLE` then
  re-inserts, so `prompts.id` changes every rebuild). Those ids stay, as row
  identity. They are not the ticket name.
- `ts` alone cannot be the key: it is second-precision, timezone-naive, and it
  collides. `2026-07-25T08:36:55` carries two different prompts in session
  `31f7a525…`.

### 1.3 Measured properties (run on the real 587 rows, 2026-07-29)

```
ids minted: 587   unique: 587   COLLISIONS: 0
repeat (session, text) pairs needing occ>0: 0
```

The `occ` term is therefore inert on today's corpus but is required for live
capture, where `push` and `y` repeat inside one session. Timestamp is deliberately
absent from the key, which is what makes the id survive the local-vs-UTC and
second-vs-millisecond mismatch between the corpus (`2026-05-25T23:33:13`, naive
local) and the live transcript (`2026-07-29T00:31:50.586Z`).

Collision budget: 12 hex is 48 bits. At 10^4 tickets the birthday probability is
about 1.8e-7. Not zero, so it is enforced rather than assumed, see 1.5.

### 1.4 Where it is stored (zero DDL for the identity itself)

`events.bead_id`. That column exists, is plumbed end to end (`intent capture --bead`),
and is unused on this machine (`intent hive sync` reads `~/.hive/beads.db`, which
does not exist). A bead is an external work item id in this package's own
vocabulary, so this is the designed meaning, not an overload. `hive_bindings`
(`bead_id` primary key, `intent_id`, `context_pack_id`, `evidence_id`,
`workflow_id`) becomes the ticket-to-intent index, again as designed.

Join from ticket to everything else:

```sql
-- current state
select to_state from state_transitions
 where subject_id = :ticket order by created_at_utc desc, rowid desc limit 1;

-- verbatim prompt
select raw_text_ref, model_text, session_id, repo_path, branch, timestamp_utc
  from events where bead_id = :ticket;

-- evidence (two hops, because evidence keys on intent_id)
select ev.* from evidence ev
  join intent_cards ic on ic.intent_id = ev.intent_id
  join events e        on e.event_id   = ic.event_id
 where e.bead_id = :ticket;
```

### 1.5 Relation to the human tags (AUTO-11, RT-1, SETUP-OS #7)

Those stay, as **aliases**, not as primary keys. An alias is appended to
`intent_cards.scope_json -> scope.beads`, a list that `extract_intent` already
writes (`[event["bead_id"]] if event["bead_id"] else []`). After aliasing,
`scope.beads == ["PT-4f2a…","AUTO-11"]`.

Rules:
- One ticket may hold many aliases. One alias must resolve to exactly one ticket.
- `PT-` ids are never authored by a human. Aliases are only authored by a human.
- `TODO.md` renders the alias and links the `PT-` id. See section 5.

### 1.6 Relation to session ids

`events.session_id` is the raw Claude Code session UUID, already indexed
(`idx_events_session`). This is the join that does not exist anywhere today: it
reaches `~/.claude/projects/<slug>/<uuid>.jsonl` (the transcript with its
`parentUuid` turn DAG and `promptId`), `state/skill-use.jsonl`,
`state/hook-fires.log` SessionStart lines, and `corpus_inputs.json`. Store it
verbatim, never truncated. `state/skill-use.jsonl` currently mixes 8-char and
36-char session ids; the backfill and hook both write the full UUID and a
`--strict` check rejects anything that is not 36 chars or the literal
`unknown-session`.

### 1.7 Enforcement

Additive DDL, `SCHEMA_VERSION` 3 to 4:

```sql
create unique index if not exists idx_events_ticket
  on events(bead_id) where bead_id like 'PT-%';
```

A partial unique index, so hive bead ids (if `~/.hive/beads.db` ever appears) are
unaffected. Re-capturing the same prompt raises `IntegrityError`, which the capture
path converts into "ticket already exists, returning existing" (idempotent), and a
genuine 48-bit collision surfaces as a hard error naming both texts instead of
silently merging two prompts.

---

## 2. States and the evidence each transition requires

### 2.1 The vocabulary

Twelve states. Allow-list, in the style of `transitions.py::PASS_LIFECYCLE`, in a
new `tickets.py::TICKET_LIFECYCLE`. `ILLEGAL_TRANSITIONS` from `cli.py` still
applies on top: an edge must be both in the allow-list and absent from the
deny-list.

```python
GENESIS = "CAPTURED"

TICKET_LIFECYCLE = {
    "CAPTURED":          {"NOT_WORK", "AMENDS", "OPEN"},
    "NOT_WORK":          {"OPEN"},           # re-triage is legal, see 2.4
    "AMENDS":            {"OPEN"},
    "OPEN":              {"SPECIFIED", "CLOSED_SUPERSEDED", "CLOSED_WONTDO"},
    "SPECIFIED":         {"IN_PROGRESS", "CLOSED_SUPERSEDED", "CLOSED_WONTDO"},
    "IN_PROGRESS":       {"CLOSED_VERIFIED", "BLOCKED_OPERATOR",
                          "BLOCKED_EXTERNAL", "SPECIFIED"},
    "BLOCKED_OPERATOR":  {"IN_PROGRESS", "CLOSED_VERIFIED", "CLOSED_WONTDO"},
    "BLOCKED_EXTERNAL":  {"IN_PROGRESS", "CLOSED_VERIFIED", "CLOSED_WONTDO"},
    "CLOSED_VERIFIED":   {"REOPENED"},
    "CLOSED_SUPERSEDED": {"REOPENED"},
    "CLOSED_WONTDO":     {"REOPENED"},
    "REOPENED":          {"SPECIFIED", "IN_PROGRESS"},
}
```

`NOT_WORK` and `AMENDS` are the triage outcomes. They are states, not a filter.
That is the structural answer to "nothing gets lost": a prompt is never dropped, it
is classified, and the classification is a row you can query and reverse.

`BLOCKED_OPERATOR` and `BLOCKED_EXTERNAL` are kept separate because L012 was
specifically a pair of falsely-claimed operator blocks (AUTO-10 and AUTO-18 were
both marked BLOCKED(operator) and both turned out to be machine-resolvable). The
guard on `BLOCKED_OPERATOR` is deliberately the strictest in the table.

### 2.2 The guard table

The repo rule is that a state change needs an executable check, not an assertion.
Two mechanisms, and the distinction matters:

- A **guard** is a pure verifier over the store. It reads rows and checks files and
  PATH. It never executes arbitrary strings, because it runs inside a hook.
- An **evidence row** is the record of an execution that already happened
  (`intent evidence attach --command "<argv>" --status pass|fail|blocked`). The
  guard checks that such a row exists, is fresh, and carries a re-runnable command.
- `intent ticket verify --ticket PT-x --rerun` re-executes the recorded command
  and compares the exit code. This is what closes the assertion loophole: any
  `CLOSED_VERIFIED` ticket can be re-proved on demand. See 2.5.

| Edge | Guard (all of these are SQL plus stdlib, no subprocess) |
|---|---|
| none to `CAPTURED` | `raw_text_ref` resolves, and `sha256(normalize(line["raw_text"]))` equals the `text_sha` that derives this ticket's own id. Detects an edited or truncated ledger. |
| `CAPTURED` to `NOT_WORK` | `reason` carries a `rule_id` from the closed rule set in 3.2, and re-running `classify(raw_text)` reproduces exactly that `(class, rule_id)`. A human cannot hand-wave a prompt into NOT_WORK; only a named replayable rule can. |
| `CAPTURED` to `AMENDS` | `reason` names a parent `PT-`; that ticket exists in `events.bead_id`; parent `timestamp_utc` is strictly earlier; parent `session_id` equals this one's. Three SQL predicates. |
| `CAPTURED` to `OPEN` | an `intent_cards` row exists for this ticket's `event_id` and `goal != "No goal text captured"`. |
| `OPEN` to `SPECIFIED` | at least one `proof_required` entry carries a non-empty `command`, and `shutil.which(shlex.split(command)[0])` or `Path(argv0).exists()` is truthy. The command is validated as resolvable, not run. |
| `SPECIFIED` to `IN_PROGRESS` | written inside `BEGIN IMMEDIATE`, re-reading current state in-transaction; no other ticket is `IN_PROGRESS` under the same `session_id`+`repo_path` claim key. Loser gets `already claimed by <session>`. |
| any to `BLOCKED_EXTERNAL` | at least one `evidence` row with `status='blocked'`, non-null `command`, and a `summary` recording a non-zero exit. You must show the thing that failed. |
| any to `BLOCKED_OPERATOR` | everything `BLOCKED_EXTERNAL` requires, plus a non-null `artifact_ref` pointing at an existing file, plus `actor == 'shoval'`. The artifact is the probe output showing the blocker is not machine-resolvable. This is the anti-L012 guard. |
| any to `CLOSED_VERIFIED` | at least one `evidence` row with `status='pass'`, non-null `command`, and `created_at_utc >= ` the most recent `IN_PROGRESS` or `REOPENED` transition for this ticket. If `events.repo_path` is a git repo, additionally: a row in `state/gate-runs.jsonl` whose `commit` and `fingerprint` match the tree now, whose `partial` is false, and whose `verdict` is `PASS`. |
| any to `CLOSED_SUPERSEDED` | successor `PT-` exists, its `timestamp_utc` is later, and walking the successor chain terminates (cycle detection, hard error on a loop). |
| any to `CLOSED_WONTDO` | `actor == 'shoval'` and `len(reason) >= 20`. This is the only human-authority edge in the machine, and it is labelled as such in the code so it shows up in an audit of unproven closes. |
| any `CLOSED_*` to `REOPENED` | at least one `evidence` row with `status='fail'` and `created_at_utc` strictly greater than the close transition's `created_at_utc`. |

### 2.3 The freshness rule that makes this bite

`CLOSED_VERIFIED` requires evidence newer than the last `IN_PROGRESS`. That single
predicate is what stops the current failure mode where `TODO.md` line 41 says
"kernel-anchor hook: live+wired [x]" while the live `settings.json` does not
register it. Under this machine, that line could not have reached
`CLOSED_VERIFIED`, because there is no passing evidence row naming a command whose
re-run would show the hook registered.

### 2.4 Reversibility

Every triage outcome has an edge back to `OPEN`, and every close has an edge to
`REOPENED`. Nothing in the graph is a one-way drop. The transitions table is
append-only, so a re-triage adds a row rather than editing one, and the full
history of how a prompt was classified stays queryable.

### 2.5 The audit that keeps closes honest

```
intent ticket audit --rerun-closed [--since 30d] [--limit N]
```

Walks every `CLOSED_VERIFIED` ticket, re-runs the recorded `command` in
`events.repo_path`, and compares exit code to the recorded status. Any ticket whose
command no longer passes gets a new `evidence` row with `status='fail'`, which is
exactly the guard for `REOPENED`, so the audit can then legally reopen it. Run it
weekly from the existing self-improve cron slot. A close that cannot be re-run is
reported separately as `unreplayable`, which is a finding, not a pass.

---

## 3. Backfilling the 587 without inventing intent

### 3.1 The principle

Do not decide what "becomes a ticket". Mint an id for all 587 and record a
classification for each. A prompt that stays in `CAPTURED` forever is an honest,
queryable outcome. A prompt auto-declared conversational by a fuzzy heuristic is a
silent loss, and silent loss is the reported pain.

### 3.2 The classifier: closed, high precision, replayable

`tickets.classify(text) -> (class, rule_id) | (None, None)`. Ordered, first match
wins, deterministic, no LLM. Only two rules auto-classify. Everything else returns
`(None, None)` and the ticket stays `CAPTURED`.

- **R1 `control`**: `re.fullmatch(r"/[a-z][a-z0-9-]*\s*", text.strip())`. A bare
  slash command is harness control, not work.
- **R2 `ack`**: `normalize(text)` is an exact member of a closed allowlist
  (`y`, `yes`, `yeah`, `ok`, `go`, `go on`, `continue`, `next`, `push`, `commit`,
  `commit push`, `ey`, `do it`, `proceed`, `done`, `stop`, `n`, `no`, `wait`,
  `again`, `sure`, `fine`, `thanks`, and so on). Exact membership, never a length
  threshold. Length alone would invent intent by omission.

Measured yield on the real corpus (2026-07-29):

```
R1 control (bare slash): 14   /btw /clear /compact /deep-research /effort /exit
                              /fast /login /model /new /rate-limit-options
                              /remote-control /resume /workflows
R2 ack   (allowlist):    10   commit push, do it, done, ey, go, push, y, yeah,
                              yes, yes go
TIER0 all: 587   TIER1 auto NOT_WORK: 24   remaining CAPTURED: 563
```

The conservatism is visible and intended. Of the 52 records at or under 15
characters, 23 are auto-classified and **29 stay CAPTURED**, including
`whats left?`, `push. merge`, `UI improvments?`, `carry on`, `per job role.`,
`Y GO`, `end session`, `.`. `Y GO` is uppercase and therefore not an exact
allowlist member after normalization; leaving it CAPTURED is the correct failure
direction.

Note a discrepancy worth recording: the corpus survey reported 17 bare slash
commands including `/compact` twice. Measured here with a full-string regex the
count is 14 records with 14 distinct texts. `merge_inputs.py` deduplicates by
lowercased whitespace-collapsed sha256, so a duplicate `/compact` cannot survive in
this file. The survey figure is likely pre-dedup. Use 14.

### 3.3 The correction hint, used as a hint only

`distilled_raw.json` holds 814 items, 258 flagged `is_correction`, across 205
distinct timestamps. Joining those timestamps to the current corpus:

```
corr ts present in corpus: 162
corpus prompts reachable through that join: 163
```

Those 163 get a **proposed** `AMENDS` transition, written to a review queue, not
applied. Applying requires the guard in 2.2 to resolve a parent `PT-` in the same
session and strictly earlier. Where no parent resolves, the ticket stays `CAPTURED`
and the hint is discarded. The `is_correction` flag was produced by an agent pass
over chunk files that no longer match the corpus (the manifest describes 691
prompts and 5,350,807 chars; the corpus is 587 prompts and 160,007 chars, because a
later `COMPACTION` filter removed assistant-authored summaries that were 97.1% of
the corpus by character count). It is therefore evidence of an opinion, not
evidence of intent, and it must never become a ticket's own goal text.
`room_assignments` (585 uncontrolled free-text labels) is not imported at all.

### 3.4 The triage queue and its ordering

563 tickets in `CAPTURED` is a backlog, and an unordered backlog is the same as
lost. Order it by a computed recoverability score, highest first:

| Signal | Measured | Weight |
|---|---|---|
| The session's transcript still exists in `~/.claude/projects/` | 29 of 55 sessions; **338 prompts recoverable, 249 in vanished sessions** | +3 |
| `src == 'session'` (came from a transcript, has surrounding turns) | 267 of 587 | +1 |
| `chars` above the median (112) | by construction ~294 | +1 |
| A `distilled_raw` item exists at that `ts` | 404 of 537 unique item timestamps match | +1 |
| Any `files_touched` path from that item still exists on disk | not measured, see 11 | +1 |

The 249 prompts whose session transcript is gone score at most 3 and sort last.
State this plainly in the runbook: **some of those will never be triageable, and
`CAPTURED` is their permanent, recorded, correct end state.** That is not a
failure of the system; a prompt whose entire context was deleted by
`cleanupPeriodDays` cannot honestly be turned into a work item.

Budget: `intent ticket triage --limit 10` per session, surfaced by the SessionStart
brief. At 10 per session the recoverable 338 clear in about 34 sessions.

### 3.5 The backfill command

```
python tools/tickets/backfill_corpus.py \
  --source "C:/Users/shova/.claude/corpus-operator-inputs/corpus_inputs.json" \
  --base-dir "C:/Users/shova/.intent" \
  [--also-history]  [--dry-run]
```

Per row it calls `intent_control_plane.cli.capture` in-process with
`event_type="user_prompt"`, `authority="raw_user_prompt"`, `actor="shoval"`,
`session=<row.session>`, `repo=<row.cwd>`, `branch=None`,
`bead=<computed PT- id>`, `text=<row.text verbatim>`, then `extract_intent`, then
one `CAPTURED` transition, then R1/R2 classification.

Properties:
- **Idempotent.** Re-running produces the same ids; the partial unique index turns
  the second insert into a no-op. Safe to abort and resume.
- **Row-at-a-time transactions**, not one large one, so a live session's prompt can
  interleave (see section 6).
- `--also-history` extends the same treatment to `~/.claude/history.jsonl`, which
  holds 787 rows of which **214 are newer than the corpus maximum**
  (`2026-07-26T22:28:48`). The corpus is three days and 214 prompts stale. Fields
  map as: `sessionId` to session, `project` to repo, `timestamp` (epoch ms) to ts,
  `display` to text. `pastedContents` is currently discarded by `merge_inputs.py`
  and should be preserved into `events.metadata_json`.

`corpus_inputs.json` is never rewritten. `memory_index.py`, `chunk.py` and
`merge_inputs.py` are not touched by this spec. `chunk.py` in particular must not
be re-run: it deletes `chunks/` before writing, and `chunks/` is the only surviving
copy of the pre-filter text that the 814 distilled items were derived from.

---

## 4. Live capture: one prompt, one ticket, automatically

### 4.1 Hook and registration

Event: `UserPromptSubmit`. Script: `dot-claude/hooks/intent-capture.sh`, replacing
the dangling symlink with a real file, content adapted from the working
`dot-codex/hooks/intent-capture.sh` with the four fixes from section 0.

Registration goes in **both** files, because they have diverged:

- Live `C:/Users/shova/.claude/settings.json`: add the `UserPromptSubmit` event.
- Canonical `claude-setup/dot-claude/settings.json`: it already has a
  `UserPromptSubmit` entry pointing at `tools/bus/bus.py inbox`. Add intent-capture
  as a **second hook in the same event array**, do not replace the bus one. Both
  should fire.

Command form, matching the shape the live file already uses for SessionStart and
PostToolUse:

```json
{ "type": "command",
  "command": "C:\\Program Files\\Git\\bin\\bash.exe",
  "args": ["-lc", "$CLAUDE_OS_DIR/dot-claude/hooks/intent-capture.sh prompt"] }
```

Inside the script, do not use `python3` and do not set `PYTHONPATH`. Call the venv
interpreter by absolute path:

```
PY="C:/Users/shova/claude-setup/intent-control-plane/.venv/Scripts/python.exe"
```

`capture()` calls `initialize()`, which creates `~/.intent` and applies the schema,
so the directory bootstraps itself on the first prompt. Run
`intent --base-dir C:/Users/shova/.intent init` once anyway, then
`intent doctor` (6 checks, verified passing against a temp base-dir) as the
acceptance check.

### 4.2 What one prompt writes

Five records, one line of stdout:

1. `~/.intent/ledger/events.jsonl`: one JSON line with the verbatim `raw_text`,
   plus a new `ticket_id` key (see 6.1).
2. `intent.db events`: one row, `bead_id = PT-<hex>`, `authority='raw_user_prompt'`,
   `session_id` = full 36-char UUID from the hook payload, `repo_path` = cwd,
   `branch` from `git branch --show-current`, `raw_text_ref` as content ref.
3. `intent.db intent_cards`: one row via `extract_intent` (goal truncated to 120
   chars, first `do not|don't|never|must not` window as a `must` constraint, proof
   type inferred from four substring tests).
4. `intent.db state_transitions`: one row, `subject_id = PT-<hex>`, `from_state=''`,
   `to_state='CAPTURED'`, `actor='shoval'`.
5. `claude-setup/state/prompt-tickets.jsonl`: one hash-chained line, see 4.3.

Stdout is the existing `hookSpecificOutput.additionalContext` block, with the
ticket id added as the first line so the assistant sees the id it must close:

```
INTENT CONTROL PLANE:
- ticket: `PT-4f2a91c0d3e7`   state: CAPTURED
- captured_event: `evt_…`   intent: `intent_…`   context_pack: `cp_…`
- constraints: …
- proof_required: test, log_or_trace
- recalled context (top ranked prior events): …
Before claiming completion, attach evidence with `intent evidence attach` or clearly state the blocker.
```

Failure behavior stays fail-open (print a warning into context, exit 0). A hook
that blocks the operator's prompt is worse than a missed row. But the warning text
must change from the current generic string to name the ticket id that was lost, so
a gap is visible rather than silent.

### 4.3 The chained mirror in git, and why it is not duplication

`~/.intent/ledger/events.jsonl` is append-only by convention only. Unlike
`state/bus.jsonl` it is not hash-chained, it is outside the repo, and it is not
committed. Given that Claude Code's own transcript store is subject to a
30-day `cleanupPeriodDays` default (not set in `settings.json`, so the documented
default applies), a store that lives only in `%USERPROFILE%` is a store that can
vanish without a trace.

`state/prompt-tickets.jsonl` therefore carries the spine, and **no prompt text**:

```json
{"id":"PT-4f2a91c0d3e7","ts":"2026-07-29T03:41:02+03:00","session":"8d6f373f-…",
 "repo":"C:\\Users\\shova\\claude-setup","branch":"main","text_sha":"9a1c…",
 "state":"CAPTURED","aliases":[],"prev":"<prev row hash>","hash":"<16 hex>"}
```

No text means no secrets and no PII enter git, which satisfies the global rules.
The chain is produced by importing `tools/bus/bus.py`'s `canonical`, `row_hash`,
`row_id` and `row_altered`, with `CHAIN_FIELDS` extended for this file. Do not
reimplement them; that module documents its guarantees (tamper evident, not tamper
proof; authenticates nobody; truncation of the newest rows is undetectable) and
those caveats carry over unchanged.

Recovery property: if `~/.intent` is lost, `state/prompt-tickets.jsonl` still names
every ticket, its session, its state and its text hash, so the loss is *detectable
and enumerable* rather than silent. Text can then be re-derived from
`~/.claude/history.jsonl` for any prompt whose `text_sha` still matches.

### 4.4 The Stop side

The hook's `stop` mode already captures `assistant_final` with
`authority='assistant_summary'`. Keep it. Add one thing, in the existing Stop slot
alongside `completion_gate.py`: if any ticket for this `session_id` is in
`OPEN`, `SPECIFIED` or `IN_PROGRESS`, print them. Do **not** auto-close anything.
An automatic close from a Stop hook would be an assertion, which is the thing this
spec exists to prevent.

### 4.5 Turn granularity, deliberately deferred

`event_type` is a free-form string. The 2026-06-25 spec names eight intended values
(`user_prompt`, `assistant_final`, `tool_output`, `diff`, `test_result`,
`deploy_result`, `decision`, `correction`); only two are ever emitted. This spec
emits those same two and no more. Full turn-level tracing already exists in
`~/.claude/projects/<slug>/<uuid>.jsonl`, which is a `parentUuid` to `uuid` DAG
carrying `promptId`, `requestId`, per-message `usage`, and tool results. Do not
re-emit it. Join to it by `session_id`, and if per-turn export is wanted later, the
supported route is Claude Code's own OpenTelemetry emitter
(`CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_LOGS_EXPORTER=console`, and
`OTEL_LOG_USER_PROMPTS=1` if prompt text is wanted, since content is off by
default). That is a separate decision with a privacy dimension and is out of scope
here.

---

## 5. TODO.md

### 5.1 Decision

TODO.md **stays as the one human-facing list** and gains a generated block. It is
not replaced by the ticket store, because a store plus a hand list is two TODOs and
breaks `CLAUDE-OS.md:148-149` ("Docs control plane applies to every repo incl. this
one: prd/ spec/ adr/ analysis/, ONE TODO, ONE INDEX"). It is also not fully
generated tomorrow, because its hand-written bodies carry real content that exists
nowhere else (the AUTO-10 and AUTO-18 L012 corrections, the AUTO-01/02 closing
evidence, the COMPACTION CHURN analysis). Regenerating tomorrow would destroy them,
which is the exact excavation failure this spec is written to avoid.

### 5.2 Phase 1, tomorrow

Add two markers to TODO.md and one tool:

```markdown
<!-- tickets:begin  generated by tools/tickets/render_todo.py, do not hand-edit -->
## Inbox: prompt tickets without a TODO alias
- [ ] PT-4f2a91c0d3e7 `OPEN` 2026-07-27 (8d6f373f) wire the UserPromptSubmit hook so prompts stop getting lost
<!-- tickets:end -->
```

Only tickets in `OPEN`, `SPECIFIED`, `IN_PROGRESS` or `BLOCKED_*` that carry **no
alias** are rendered. Everything already tracked by hand keeps its hand-written
body. Nothing outside the markers is ever touched.

### 5.3 The drift oracle

`python tools/tickets/render_todo.py --check` exits non-zero when:

1. A hand-written TODO line carries a tag (`AUTO-nn`, `RT-n`, `SETUP-OS #n`) that
   resolves to no ticket alias.
2. A ticket carries an alias whose TODO line is missing.
3. A ticket is `CLOSED_VERIFIED` but its TODO line is `[ ]`, or a TODO line is
   `[x]` while the ticket is not in a `CLOSED_*` state.
4. The `tickets:begin/end` block is stale relative to the store.

Case 3 is where the authority order from `CLAUDE-OS.md:67` finally does something.
That line ("raw prompt > spec > verified evidence > repo state > summary > vector
similarity") is currently a string in a column that no ranking code reads.
`render_todo.py --check` resolves the conflict by that order: a TODO checkbox is a
**summary**, and a summary never overrides **verified evidence**. So a `[x]` with
no passing evidence row is reported as an unproven claim and the ticket state wins.
That is one concrete enforcement of the authority order, in one tool, not a
general ranking engine.

Wire `--check` into the existing gate as a `docs` domain check, so drift blocks a
ship-gate pass rather than being a report nobody reads.

### 5.4 Phase 2, explicitly not tomorrow

Only after the store has run for a few weeks and `--check` is clean: migrate the
hand-written bodies into `intent_cards.goal` plus a notes artifact, make TODO.md
fully generated, and delete the hand-written sections. Gate phase 2 on
"`render_todo.py --check` has exited 0 on every commit for 14 days". Do not start it
before that. `docs/INDEX.md` gains exactly one line pointing at this spec.

---

## 6. What breaks when two sessions create tickets at once

Multiple concurrent sessions are normal here (`session_guard.py` exists for that
reason), and every one of the following is a real defect in the code as it stands
today, not a hypothetical.

### 6.1 `ledger_append` has a time-of-check-to-time-of-use race, and it is the worst one

```python
def ledger_append(base_dir, event):
    line_no = 1
    if ledger.exists():
        with ledger.open("r") as handle:
            line_no = sum(1 for _ in handle) + 1     # count
    with ledger.open("a") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")   # then append
    return f"{ledger}:{line_no}"
```

Two hooks firing in the same moment both count N lines and both return `:N+1`. One
of the two `events.raw_text_ref` values then points at the wrong line, and the
`CAPTURED` guard in 2.2 (ledger sha must match the ticket's `text_sha`) fails on a
prompt that was captured perfectly well. It is also O(file) per turn: counting the
whole ledger on every prompt makes the 587-row backfill quadratic.

**Fix: stop depending on line numbers.** Write `ticket_id` into the JSON line and
make the ref content-addressed:

```python
event["ticket_id"] = ticket_id
with ledger.open("a", encoding="utf-8") as handle:      # O_APPEND, no read
    handle.write(json.dumps(event, sort_keys=True) + "\n")
return f"{ledger}#{ticket_id}"
```

Lookup becomes a scan for the matching `ticket_id`, ordering stops mattering, the
per-turn cost drops to a single append, and the backfill goes linear. Existing rows
keep the `path:lineno` form; the resolver accepts both.

### 6.2 `database is locked`, silently swallowed

`schema.connect()` sets only `row_factory`. No `journal_mode=WAL`, no
`busy_timeout`. SQLite's default busy timeout is 0, so a second writer raises
`OperationalError` immediately. The hook wraps its whole body in
`except Exception: print(warning); exit 0`. Net effect: **two sessions prompting in
the same second, and one prompt is silently not captured.** That is the original
complaint reintroduced by the fix for it.

Fix, two lines, in `initialize()` and `connect()`:

```python
conn.execute("pragma journal_mode=WAL")     # once, in initialize()
conn.execute("pragma busy_timeout=5000")    # every connect()
```

WAL matches this workload (many `session brief` and `context-pack` reads, one
writer at a time). Note the interaction with `_ClosingConnection.__exit__`, which
closes the handle on every `with` block: WAL files are per-database and survive
that, so no change is needed there.

### 6.3 Ticket id collision under concurrency is a feature, but the insert is not

Because the id is content-derived, two sessions capturing the same text in the same
session at the same occurrence index produce the *same* id. That is correct and
idempotent. But `events.event_id` is time-plus-random, so both inserts succeed and
you get two events claiming one ticket. The partial unique index from 1.7 turns the
second into an `IntegrityError`; `capture` catches it and returns the existing
event. Add a regression test for exactly this.

### 6.4 Claim contention on `IN_PROGRESS`

Two sessions claiming one ticket. Handle it the way `transitions.advance_pass`
already does: take a bare `connect()`, `BEGIN IMMEDIATE`, re-read current state
inside the transaction (checkpoint-before), write only if still legal, commit. The
loser gets `SystemExit("PT-… already IN_PROGRESS, claimed by session <uuid> at
<ts>")`. `transitions.py` is the only module in the package that already takes a
bare connection for `BEGIN IMMEDIATE`; copy that idiom rather than inventing one.

### 6.5 The chained mirror forks under concurrent append

`bus.py cmd_send` reads `rows[-1]` to compute `prev`, then appends. Same race as
6.1, and worse: two concurrent appends both set `prev` to the same row, producing a
fork that `bus.py verify` reports as a broken chain. This has never fired because
`bus.jsonl` has 19 rows and one writer. A per-turn writer with two sessions will
fire it.

Fix: **one mutex, not two.** Write the `state/prompt-tickets.jsonl` line inside the
same `BEGIN IMMEDIATE` transaction that inserts the event. SQLite is then the lock
for both the database and the file. Do not add a second lock file; two locks taken
in different orders by different code paths is how deadlocks get introduced.

Also fix `bus.py cmd_send` the same way if the bus is ever wired to
`UserPromptSubmit` (the canonical `settings.json` already points it there, and lane
B's cursor `state/bus-cursors/B.txt` still reads `0` with 17 unread, so it has
never actually been delivered).

### 6.6 Backfill against a live session

Row-at-a-time transactions, so live prompts interleave rather than waiting behind a
587-row transaction. Idempotent by content id, so an abort mid-run is resumable.
Still, run the first backfill with no other session open, and check `intent doctor`
plus `python tools/bus/bus.py verify` afterwards.

### 6.7 What is deliberately not fixed

`state/hook-fires.log` is appended to by every lane with no lock. Short-line
`O_APPEND` writes are effectively atomic at these sizes and the file is diagnostic,
not authoritative. Leave it. Its real defects (UserPromptSubmit lines carry a
timestamp and nothing else; `session-recall.sh` truncates the SessionStart payload
at 100 chars, severing `transcript_path` mid-string) are separate tickets.

---

## 7. Premortem

1. **The hook fires, the guard rejects, and the operator's prompt is blocked.**
   Mitigation: the hook is fail-open by construction (exit 0, warning into context).
   No guard runs on the capture path; the only guard at capture time is the ledger
   sha check, which runs *after* the write. Acceptance test: kill `intent.db`
   mid-session and confirm the next prompt still submits.
2. **563 tickets sit in CAPTURED forever and the ticket store becomes the new
   place things get lost.** Mitigation: the SessionStart brief surfaces the top 10
   by recoverability score, and `render_todo.py --check` fails if the CAPTURED
   count grows for 7 consecutive days without a triage transition. The metric that
   matters is triage throughput, not backlog size.
3. **`CLOSED_VERIFIED` gets rubber-stamped by attaching a trivial passing
   command.** This is RT-2's rubber-stamping concern applied here. Mitigation:
   `intent ticket audit --rerun-closed` re-runs the recorded commands weekly and
   reports `unreplayable` separately from `pass`; and the daily digest prints the
   ratio of closes whose command is one of `true`, `echo`, `exit 0`, or a no-op.
   A close-rate that has never seen a reopen is itself the finding.
4. **Two ledgers drift: `~/.intent/intent.db` says OPEN, `state/prompt-tickets.jsonl`
   says CLOSED_VERIFIED.** Mitigation: they are written in one transaction (6.5),
   and `intent ticket reconcile` compares them row by row and exits non-zero on any
   divergence. Wire it into the same gate `docs` domain as `render_todo.py --check`.
5. **The backfill invents intent.** Mitigation is structural, not procedural: the
   backfill has no path to `OPEN`. It can only write `CAPTURED` and, via the two
   closed rules, `NOT_WORK`. `CAPTURED` to `OPEN` requires an intent card with a
   real goal, which requires a human or a session to look at the prompt. The
   `is_correction` hints are written to a review queue and are never applied
   automatically.

---

## 8. Acceptance table

Every row is an observable check. No row is satisfied by an artifact existing.

| # | Criterion | Executable check | Pass condition |
|---|---|---|---|
| A1 | The store exists | `intent --base-dir C:/Users/shova/.intent doctor` | `status: pass`, 6/6 checks |
| A2 | Ids are stable across a rebuild | `backfill_corpus.py --dry-run` twice, diff the id lists | byte-identical, 587 ids, 0 collisions |
| A3 | All 587 are captured | `select count(*) from events where bead_id like 'PT-%'` | 587 |
| A4 | Triage is conservative | `select to_state, count(*) from state_transitions group by 1` | `NOT_WORK` = 24, `CAPTURED` = 587 |
| A5 | The ledger is tamper-evident | edit one char in `state/prompt-tickets.jsonl`, run `intent ticket reconcile` | non-zero exit, names the altered row |
| A6 | A live prompt makes a ticket | submit any prompt, then `intent list events --limit 1` | `bead_id` starts `PT-`, `session_id` is 36 chars |
| A7 | An illegal close is refused | `intent ticket advance --ticket PT-x --to CLOSED_VERIFIED` with no evidence | exit 2, message names the missing guard |
| A8 | A legal close is accepted | attach a passing evidence row with a real command, then advance | exit 0, transition row written |
| A9 | A close can be re-proved | `intent ticket verify --ticket PT-x --rerun` | exit code matches recorded status |
| A10 | Concurrency does not lose a prompt | two shells, 50 captures each, simultaneously | 100 distinct tickets, 0 exceptions, `bus.py verify`-style chain check intact |
| A11 | TODO drift is caught | flip one TODO checkbox to `[x]` by hand | `render_todo.py --check` exits non-zero citing "summary over verified evidence" |
| A12 | A prompt traces to its work | pick a `CLOSED_VERIFIED` ticket, run `intent ticket show PT-x` | prints verbatim prompt, session id, commit, gate verdict, evidence command |

A12 is the whole point. It is the query that is impossible today: the survey worked
two real TODO lines (`RT-1` and `AUTO-06`) back toward their originating prompts and
in both cases every step was a heuristic and no step was a recorded reference.

---

## 9. Implementation order for day one

Each step is independently useful and independently revertible. Stop after any step
and the system is still coherent.

1. **Patch `schema.py`** (WAL, busy_timeout, `SCHEMA_VERSION` 3 to 4, partial unique
   index) and **`cli.py::ledger_append`** (content ref). Run the 426-test suite.
   Nothing else changes yet. (~30 min)
2. **Write `tickets.py`** (`ticket_id`, `normalize`, `classify`, `TICKET_LIFECYCLE`,
   `current_state`, `advance`, the guard functions) plus `tests/test_tickets.py`.
   Pure logic, property-testable: id stability under reordering, allow-list totality,
   guard rejection on every illegal edge. (~3 h)
3. **Add the `intent ticket` subcommand group** (`advance`, `show`, `list`, `triage`,
   `verify`, `audit`, `reconcile`) to `build_parser`, delegating to
   `record_transition` for the write. (~1 h)
4. **Run `intent init` and the backfill** with no other session open. Verify A1 to
   A5. This is the point at which nothing is lost any more, and it is reachable in
   one morning. (~1 h)
5. **Write the real `dot-claude/hooks/intent-capture.sh`**, register
   `UserPromptSubmit` in both settings files, restart the session, verify A6. (~1 h)
6. **`tools/tickets/render_todo.py`**, add the markers to TODO.md, wire `--check`
   into the gate `docs` domain, verify A11. (~2 h)
7. Later, not day one: `audit --rerun-closed` in the weekly cron, and the RT-1
   calibration pairs, which now have a natural home
   (`{claimed_confidence, action, verified_outcome}` per `CLOSED_VERIFIED`
   transition, stored in `eval_results.details_json` under
   `eval_type="calibration"`, which accepts arbitrary JSON with no DDL change).

---

## 10. What this spec deliberately does not do

- It does not touch `memory_index.py`, `chunk.py`, `merge_inputs.py`,
  `corpus_inputs.json`, `distilled_raw.json` or `memory.db`. The FTS5 multi-word
  AND defect in `_fts_query()` is real and separate.
- It does not build turn-level tracing. That data already exists in
  `~/.claude/projects/*/*.jsonl` as a `parentUuid` DAG with `promptId`.
- It does not adopt OpenTelemetry GenAI conventions. Every `gen_ai.*` attribute is
  Development status, and the standard has no attribute for a human prompt as an
  entity, no permission-decision vocabulary, and no ticket or work-item concept.
  The pieces that are stable (W3C Trace Context, OTel `session.*`) are not what is
  missing here.
- It does not create a second TODO, a second index, or a web dashboard.
- It does not import `room_assignments` (585 uncontrolled labels) or
  `files_touched` (436 paths with mixed separators for the same file) as controlled
  vocabulary.

---

## 11. Unverified, and what would settle it

- **`files_touched` survival rate** (the +1 recoverability signal in 3.4) was not
  measured. Settle with a stat loop over the 343 items that carry the field.
- **`cleanupPeriodDays`** is unset in `settings.json`; the 30-day default is from
  Anthropic's documentation, and the observed transcript floor is consistent with it
  but does not prove deletion. Settle by setting the key explicitly to a chosen
  value and watching the floor.
- **The 426-test suite was reported green by the icp survey, not re-run here.**
  Re-run before step 1 so the WAL patch has a clean baseline.
- **Windows `O_APPEND` atomicity** for the ledger line is assumed, not tested. The
  design does not rely on it (SQLite is the mutex, 6.5), but A10 is the test that
  would expose it if the assumption leaked in.
- **`intent hive sync` and `~/.hive/beads.db`**: this spec claims `bead_id` is free
  on this machine because that database does not exist. If it ever appears, the
  partial unique index confines the collision, but the alias model would need a
  second look.
