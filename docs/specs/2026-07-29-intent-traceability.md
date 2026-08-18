# Intent traceability: wiring, not building

Status: proposed. Wiring design, 2026-07-29. Partially built.

Corrected 2026-08-17 glue pass: header said "not built"; that is now false for
half the slice. Verified today: `tools/intent/capture_turn.py` exists (step 3
below is done), `state/prompt-tickets.jsonl` holds 1851 chained rows with
recent timestamps (the ledger is live-writing), and `UserPromptSubmit` is
registered in `dot-claude/settings.json` (step 5 done). Still not done: step 4,
`dot-claude/hooks/intent-capture.sh` is still the 45-byte dead-home stub named
in 4.1 break 1 (`cat` shows a single line pointing at
`/home/shovalbe/.codex/hooks/intent-capture.sh`, a home that does not exist on
this machine), so whatever writes the ledger today is not this hook; the real
wiring path is unverified and is itself the next slice, not this document's
claimed one.

Spec date 2026-07-29. Scope: turn operator prompts into tracked work items, and trace
every session and every turn.

> **CORRECTION, 2026-07-29, after the spec was written.** This document and its
> companion trace-model spec treat `~/.claude/projects/<slug>/<session>.jsonl` as a
> stable interface, and the trace-model spec calls it THE timeline. Claude Code's own
> documentation says the entry format is internal and changes between versions, so
> anything parsing it directly can break on any release. The documented stable routes
> are `/export` and `claude -p --resume <id> --output-format json`.
>
> What changes, and what does not:
> - Live capture takes `session_id`, `cwd` and the prompt from the **UserPromptSubmit
>   hook payload**, a documented hook input. No transcript is parsed on the hot path.
> - `promptId` and `message_uuid` become OPTIONAL metadata enrichment. Their absence
>   must not fail a capture, and no join may depend on them.
> - The section 4.3 backfill, which joins 587 corpus rows against transcript files, is
>   **at risk** and is not scheduled until it is re-based on a supported route.
> - Ticket identity is unaffected: it derives from `{session_id, text_sha,
>   occurrence_index}` and contains no vendor id, so it survives a format change.
>
> Recorded as `L-2026-07-29-e`. The schema was measured rather than read about, and
> present-and-consistent was mistaken for supported.

**Verdict.** The storage, the CLI, and the capture hook are already written on this
machine. The store they write to has never been created. This is a wiring job with four
small patches, not a build. Every artifact named below was opened and measured today;
counts on live-growing files carry their read time.

Terms used once and then reused. **Hook**: a script Claude Code runs at a named lifecycle
point, registered in `settings.json`. **Ledger**: an append-only text file that is the
system of record. **Event**: one recorded occurrence with a stable id. **Ticket**: a
projection over events, not a separate record. **Projection**: a view rebuilt by replaying
the ledger. **Tracer bullet**: one thin path through every layer, working end to end,
before any layer is widened.

---

## 1. What already exists

Excavation result. Read as: nothing in the "artifact" column needs to be written.

| Capability needed | Artifact that already implements it | Measured state today | Missing wire |
|---|---|---|---|
| Per-turn store | `intent-control-plane/src/intent_control_plane/schema.py`, `SCHEMA_VERSION = 3`, 14 tables | `~/.intent` **does not exist** (`ls` fails). 0 rows ever written | `intent init` has never been run |
| Prompt capture | `dot-codex/hooks/intent-capture.sh`, 192 lines, dual mode prompt and stop | Never fires. Four independent breaks, section 4.1 | Registration plus interpreter path |
| Same hook, Claude side | `dot-claude/hooks/intent-capture.sh` | 45 bytes, whole content is the string `/home/shovalbe/.codex/hooks/intent-capture.sh`. A WSL symlink checked into git as plain text | Needs to become a real file |
| Hook registration | `~/.claude/settings.json`, 13 top-level keys | Hook events present: SessionStart, PreToolUse, PostToolUse, PreCompact, Stop, Notification. **No `UserPromptSubmit`** | One JSON block |
| Turn ledger | `cli.py::ledger_append` writing `~/.intent/ledger/events.jsonl` | Function exists, path defined at `schema.py:16`, file absent | Store creation |
| Ticket-shaped record | `intent_cards` table plus `cli.py::extract_intent` | Runs, produces goal, constraints, proof_required | No status, owner, or tag column |
| State machine | `cli.py::ILLEGAL_TRANSITIONS` plus `state_transitions` table | Blocks GENERATED to SHIPPED with exit 2 | No ticket lifecycle allow-list on top |
| Causal parent pointers | `graph_edges` table, `schema.py:155` | Declared. **Zero writers** across all 44 source modules | One insert |
| Vendor turn DAG | `~/.claude/projects/<slug>/<session>.jsonl` | 72 session transcripts across 7 project dirs, plus 745 nested subagent files, 817 total, 448 MB. `parentUuid` to `uuid` tree. On the one claude-setup transcript: 1779 rows, 279 main-thread human turns, **279 of 279 carry `promptId`** | Nothing reads it |
| Prompt corpus | `~/.claude/corpus-operator-inputs/corpus_inputs.json` | 587 rows, 586 unique `ts` (one same-second collision), 55 sessions. Zero callers anywhere | No id, no state, no backfill path |
| Tamper evidence | `tools/bus/bus.py`, `canonical()` plus `row_hash()` plus `row_altered()` | Working. `state/bus.jsonl` 21 rows, 9 chained (read 2026-07-29 03:5x) | Chain shape is scalar `prev`; causality is a partial order |
| Verification ledger | `state/gate-runs.jsonl` | 992 rows (read 2026-07-29). Carries `commit` and 16-hex `fingerprint` | No session, no prompt, no ticket column |
| Ticket list | `TODO.md` | 60 checkbox lines, tags SETUP-OS, AUTO-nn, RT-n | Tags appear in no ledger except `lessons.jsonl` |
| Retention control | `~/.claude/settings.json` | **`cleanupPeriodDays` is absent** from all 13 keys. Anthropic documents the default as 30 days | One key |

Two numbers I did not re-measure and am carrying from the survey packets: the 537
deduplicated standing rules in `memory.db`, and the ~242 broken citations inside
`distilled_raw.json`. Treat both as reported, not verified here.

---

## 2. The one-paragraph model

One append-only file is the truth: every prompt you type, every final answer, every
commit and gate run, lands there as a line with a stable id and a pointer to whatever
caused it. Nothing is ever edited or deleted in that file. Everything else, the ticket
list, the backlog, the dashboard, is a view computed by reading the file top to bottom,
so a view can be thrown away and rebuilt without losing anything. A ticket is therefore
not a thing you create; it is the name for one prompt plus everything that later cites
it. "Were getting lost" has a mechanical cause: the file that would hold all of this was
never created, so each session starts blind, and the only surviving prompt record is
being deleted on a rolling 30-day default nobody set.

---

## 3. Schema

### 3.1 Ledger line, `~/.intent/ledger/events.jsonl`

One JSON object per line. `EXISTS` means the key is already written by `cli.py::capture`
today. `NEW` means the first slice adds it.

```json
{
  "event_id":       "evt_20260729003541_68761a4a1c",   // EXISTS. cli.py stable_id(), uuid4-based
  "event_type":     "user_prompt",                      // EXISTS. free string today; 8 values named in the 2026-06-25 spec, 2 ever emitted
  "timestamp_utc":  "2026-07-29T03:55:12Z",             // EXISTS. util.py utc_now(), second precision
  "actor":          "shoval",                           // EXISTS
  "session_id":     "8d6f373f-1fb3-4765-8616-a252ae5cfb3f", // EXISTS. joins transcripts, skill-use.jsonl, hook-fires.log
  "repo_path":      "C:/Users/shova/claude-setup",      // EXISTS
  "branch":         "main",                             // EXISTS
  "bead_id":        "PT-4f2a9c1e77b0",                  // EXISTS as a column, repurposed: the ticket id, section 3.2
  "workflow_id":    null,                               // EXISTS
  "raw_text":       "<verbatim prompt, never truncated>", // EXISTS. lives only here, not in sqlite
  "redaction_state":"raw_local",                        // EXISTS
  "authority":      "raw_user_prompt",                  // EXISTS as a stored string, read by no ranking code
  "metadata": {                                         // key EXISTS, hardcoded {} in both writers
    "prompt_id":   "b31c0f4e-...",                      // NEW. vendor promptId from the transcript row
    "message_uuid":"9a77...",                           // NEW. transcript uuid, the join to the turn DAG
    "parents":     ["evt_...", "PT-..."],               // NEW. list, not scalar. causality is a partial order
    "text_sha":    "sha256 hex of raw_text",            // NEW. the content key
    "seq":         41,                                  // NEW. per-session monotonic counter
    "cwd":         "C:/Users/shova/claude-setup",       // NEW. observer coordinates, not subject
    "hash":        "16 hex"                             // NEW. bus.py row_hash() over the sorted keys minus hash
  }
}
```

The sqlite mirror is `events(...)` with those same column names plus `raw_text_ref`,
which is `"<ledger path>:<offset>"`. Section 4.2 changes it from line number to byte
offset.

### 3.2 Ticket

A ticket is not a table. It is a `bead_id` plus the transition history already recorded
in `state_transitions`.

```json
{
  "ticket_id":  "PT-4f2a9c1e77b0",
  "derivation": "sha256(json({session_id, text_sha, occurrence_index}))[:12], prefixed PT-",
  "stored_in":  "events.bead_id, with a partial unique index where bead_id like 'PT-%'",
  "aliases":    ["AUTO-15", "RT-1"],
  "aliases_stored_in": "intent_cards.scope_json -> scope.beads (extract_intent already writes scope_json)",
  "state":      "CAPTURED",
  "state_stored_in": "state_transitions rows; current state is the newest row for subject_id",
  "states":     ["CAPTURED","TRIAGED","OPEN","IN_PROGRESS","BLOCKED_OPERATOR",
                 "CLOSED_VERIFIED","CLOSED_WONTDO","NOT_WORK","SUPERSEDED"],
  "evidence":   "evidence rows joined on intent_id; CLOSED_VERIFIED requires >=1 pass row with non-null command",
  "goal":       "intent_cards.goal (exists, first 120 chars of the prompt today)"
}
```

The id has no clock and no randomness in it, so replaying the ledger reproduces it. That
is deliberate: `memory_index.py::build()` drops and re-inserts `prompts`, reassigning
every `prompts.id` on each rebuild, which is why nothing downstream can cite a prompt.
It also sidesteps the one known same-second `ts` collision at `2026-07-25T08:36:55`.

---

## 4. The first slice

One vertical path: a prompt you type today becomes a row you can query tonight. Six
steps. Nothing else in the package is touched.

### 4.0 Remaining wires (added 2026-08-17 glue pass)

Three of the six steps below still need closing, verified against disk today:

1. **Fix the live hook.** `dot-claude/hooks/intent-capture.sh` still points at
   `/home/shovalbe/.codex/hooks/intent-capture.sh`, a home directory absent on
   this machine (this is `tools/audit/pointers.py`'s dead-home class).
   Falsifiable: `cat dot-claude/hooks/intent-capture.sh` shows the step-4 body
   in this file, not a one-line path, and `tools/audit/pointers.py scan`
   reports zero dead-home hits for this file.
2. **Identify the actual ledger writer.** `state/prompt-tickets.jsonl` is
   live-writing (1851 rows, most recent 2026-08-17) through some path other
   than the broken hook above. Falsifiable: one comment in this file or a new
   analysis names the real writer with a `grep`/`git log -p` citation, so the
   next reader is not misled by the "not built" verdict this file carried
   until this pass.
3. **Run the step-6 acceptance query for real.** The SQL join against
   `~/.intent/intent.db` in step 6 has not been shown to return a row.
   Falsifiable: paste the query's real output (bead_id, session_id, goal) for
   one live prompt, not a description of what it should return.

### 4.1 The four breaks the slice has to clear

All four verified today. Any one of them alone kills capture.

1. `dot-claude/hooks/intent-capture.sh` is 45 bytes of dangling symlink text.
2. `~/.claude/settings.json` has no `UserPromptSubmit` event at all.
3. `dot-codex/hooks/intent-capture.sh:15` sets `PYTHONPATH="$HOME/projects/intent-control-plane/src"`. That directory does not exist; the package is at `claude-setup/intent-control-plane`.
4. The same line invokes `python3`. `which python3` returns nothing on this machine. The hook could not have worked even if registered and even if the symlink were real.

### 4.2 Steps

**Step 1. Create the store.** Run once:

```
C:/Users/shova/claude-setup/intent-control-plane/.venv/Scripts/python.exe -m intent_control_plane.cli init
```

Acceptance: `~/.intent/intent.db` exists and `intent doctor` reports 6 of 6 checks pass.

**Step 2. Three patches inside `intent-control-plane/src/intent_control_plane/`.** These
are the only source edits in the slice.

| File and symbol | Current line | Change |
|---|---|---|
| `schema.py:60-63` `connect()` | `sqlite3.connect(...)`, then `row_factory` only | Add `pragma journal_mode=WAL` and `pragma busy_timeout=5000`. SQLite's default busy timeout is 0, so a second concurrent writer raises immediately and the hook's `except Exception` swallows it. Two sessions prompting in the same second lose one prompt silently, which is the original complaint reintroduced by the fix for it |
| `cli.py:60-68` `ledger_append()` | counts every line, then appends, returns `:N+1` | Return a byte offset from `handle.tell()` after the write. Fixes a lost-update race (two hooks both compute `N+1`) and an O(file) cost per turn that would make a 587-row backfill quadratic |
| `cli.py:113` and `cli.py` capture insert | ledger dict has `"metadata": {}`, sqlite insert passes the literal `"{}"` | Accept a `--metadata` JSON string, add it to `build_parser()` at `cli.py:1062-1072` where `capture` currently has 9 flags and none for metadata. **This one literal is what blocks every NEW field in section 3.1** |

**Step 3. One new file, `C:/Users/shova/claude-setup/tools/intent/capture_turn.py`.**
Reads the hook JSON payload on stdin, calls `capture` then `extract_intent` in process,
computes `PT-<12hex>`, writes one `state_transitions` row at `CAPTURED`, and appends one
chained line to `state/prompt-tickets.jsonl` carrying id, ts, session, repo, branch,
`text_sha`, state, `prev`, `hash`, and **no prompt text**, so nothing sensitive enters
git while a `~/.intent` loss stays detectable. It imports `canonical`, `row_hash`,
`row_id`, `row_altered` from `tools/bus/bus.py` rather than reimplementing them. Both
writes happen inside one `BEGIN IMMEDIATE` transaction, copying `transitions.py`, which
is the only module in the package already taking a bare connection for that. One mutex,
not two.

**Step 4. One new hook, `C:/Users/shova/.claude/hooks/intent-capture.sh`,** a real file,
roughly six lines, calling the venv interpreter by absolute path. No `python3`, no
`PYTHONPATH`:

```sh
#!/usr/bin/env bash
set -euo pipefail
[ -n "${CLAUDE_LOOP_MODE:-}" ] && { echo '{}'; exit 0; }
exec "C:/Users/shova/claude-setup/intent-control-plane/.venv/Scripts/python.exe" \
     "C:/Users/shova/claude-setup/tools/intent/capture_turn.py" "${1:-prompt}"
```

**Step 5. Register it.** Add to `~/.claude/settings.json`, matching the shape the six
live hook events already use:

```json
"UserPromptSubmit": [
  { "hooks": [ { "type": "command",
                 "command": "C:\\Program Files\\Git\\bin\\bash.exe",
                 "args": ["/c/Users/shova/.claude/hooks/intent-capture.sh"],
                 "timeout": 10 } ] }
]
```

Mirror it in `dot-claude/settings.json` as a **second** entry in the existing
`UserPromptSubmit` array. Do not displace `bus.py inbox`.

**Step 6. Acceptance, one query.** Type any prompt, then run:

```sql
select e.bead_id, e.session_id, e.timestamp_utc, substr(e.model_text,1,60), i.goal
from events e left join intent_cards i on i.event_id = e.event_id
order by e.timestamp_utc desc limit 5;
```

The slice is working when that returns your prompt, its `PT-` id, and a goal, and when
`state/prompt-tickets.jsonl` holds a matching chained line for the same id. Until that
output is observed, treat every step above as written and unproven.

### 4.3 Backfill, after step 6 and not before

Mint an id for all 587 corpus rows. Do not decide what "becomes a ticket": record a
classification instead, because triage is a state, not a filter. Only two closed
non-LLM rules auto-classify to `NOT_WORK`: bare slash commands, and exact membership in
an acknowledgement allowlist. The survey measured the yield at 14 and 10, so 24 leave
and 563 stay `CAPTURED`. There is deliberately no code path to `OPEN`, because that edge
requires an intent card, which requires a human to look.

---

## 5. Decision rules

Four modes. Trigger is when to reach for it, test is the question that decides, counter
case is the failure this mode cannot see. **Conformal** here means a prediction method
that converts a raw score into a set with a stated error rate, which requires stored
score-and-outcome pairs.

| Mode | Trigger | Test | Counter-case |
|---|---|---|---|
| **Deterministic** | You can write the pass condition before seeing any output | Is there a fixed predicate over files or SQL that returns true or false? If yes, code it. Default to this | The 13 dangling 45-byte hooks in `dot-claude/hooks/` passed every deterministic check on this machine, because no check named the category "file is a symlink stub". Patterns are blind to categories nobody wrote down |
| **Agentic** | The failure category has not been named yet, so no predicate can exist | Is the job discovery rather than enforcement? If yes, use an agent, and require its output to land as a frozen deterministic check | Correlated proposer and verifier failure. This repo hit it and fixed it on 2026-07-27 by blinding the judge in `SKILL.md`. An agent reviewing its own artifact reports health it cannot see |
| **Conformal** | A continuous score is already being stored next to its verified outcome | Do `{score, outcome}` pairs exist on disk? If no, this mode is unavailable, full stop | **Unavailable today.** The `CLAUDE-OS.md:45` gate at 0.90 autonomous has zero stored pairs anywhere in `state/`, so its reliability curve is not computable and the threshold is inert rather than protective. `TODO.md` RT-1 has to land first |
| **Speculative** | Verification is much cheaper than generation | Is the verifier independent of the proposer, and does it run on every proposal rather than a sample? | The corpus backfill is the live example: the survey reports roughly 242 broken citations inside `distilled_raw.json` (item timestamps and rule `evidence_ts` values pointing at prompts that no longer exist). Every one is catchable by a dict lookup at write time. A cheap proposer without a mandatory verifier produces exactly this |

Rule of assignment for this spec: steps 1 through 6 of the first slice are all
deterministic. Classification of the 563 `CAPTURED` prompts is where agentic starts, and
its output must be written back as a state, not as prose.

---

## 6. What this does NOT solve

- **Vanished sessions.** The survey reports 338 of 587 corpus prompts sit in sessions whose transcript still exists and 249 do not. The 249 can be given an id and a hash, and nothing more. That is a recorded outcome, not a recovery.
- **Retention.** Nothing here stops the rolling deletion. `cleanupPeriodDays` is absent from `~/.claude/settings.json`, and the documented default is 30 days. The slice does not set it. See open question 1.
- **Tool-call granularity.** Day one records `user_prompt` and `assistant_final` only. `event_type` is a free string with no enum. Tool calls, hook fires, and subagent spawns stay uncaptured.
- **Authority ordering.** `authority` remains a stored string. `CLAUDE-OS.md:67` ranks raw prompt above summary, and no code sorts on it. Until a retrieval path uses it as a primary key, a rank-4 compaction summary can still outrank the rank-0 prompt it summarizes.
- **Causal edges across boundaries.** `graph_edges` gains its first writer for prompt-to-event only. Commit to prompt, gate run to prompt, and lesson to prompt still resolve to timestamp proximity, which is a guess.
- **Concurrency at scale.** WAL plus a 5 second busy timeout is a fix for two writers. It is untested at the parallel-session count that is normal here, and Windows append atomicity was not verified.
- **`TODO.md`.** It stays a hand-written file. Nothing here generates it, and nothing here reconciles its 60 checkbox lines against the store.
- **Vocabulary.** The 585 free-text `room_assignments` labels, including the unmerged `ui` and `ui-ux` pair, are not normalized by anything in this slice.
- **Closing.** No path auto-closes a ticket. A Stop-hook close would be an assertion, not evidence.

---

## 7. Open questions

1. **Retention.** Set `cleanupPeriodDays` to a large value and keep trusting the vendor store, or copy the 72 session transcripts out to a directory you own on a schedule? The first is one key and keeps a vendor dependency; the second is 448 MB today and grows.
2. **Prompt text in git.** The proposed `state/prompt-tickets.jsonl` carries hashes and no text, so `~/.intent` stays the only place your words live and a loss there is unrecoverable but detectable. The alternative puts verbatim prompts in a git-tracked file. Which failure do you prefer?
3. **Ticket id authority.** Content-addressed `PT-<12hex>`, which survives rebuilds and works for the 587 historical prompts that have no vendor id, or the vendor `promptId`, which is present on 279 of 279 recent turns and joins the transcript DAG for free but does not exist before 2026-07-08?
4. **The 563.** Leave them at `CAPTURED` indefinitely and let the backlog surface them as you happen to need them, or spend one agentic pass to propose a state for each, with every proposal requiring your confirmation before it is written?
5. **Blast radius.** Wire `UserPromptSubmit` for `claude-setup` only first, or for all 7 project directories at once? The second gives real data faster and puts an untested hook in front of every prompt you type, including in `new-recruit`.
