# Ponytail audit: what two months of prompts actually contain

Measured 2026-08-01. Scope of this document is the prompt-archaeology half of the
directive: recover every operator prompt since the work started, and decide from
the record what was asked and never landed. It deliberately does NOT re-derive
the `.md` consolidation and directory-organisation findings, which three other
documents already cover from measurement:
`docs/analysis/archive/2026-08-01-fog-of-war.md` (document-to-path existence, tool
wiring), `docs/analysis/archive/2026-08-01-pocock-skills-teardown.md` (skill context
cost), and the `FOG` section of `TODO.md` (CI, mutation control, Zion). Producing
a fourth document that disagrees with those three about counts would be worse
than producing none.

## 1. The two-month record exists, and it is not in Claude

The directive asked to visit every prompt "since we started (2 months ago)".
Claude's own transcript store cannot answer that. Measured:

| Store | Oldest | Files |
|---|---|---|
| `~/.claude/projects` plus `/mnt/c/Users/shova/.claude/projects` | 2026-07-08 | 1,069 |
| `/mnt/c/Users/shova/.codex/archived_sessions` | **2026-05-08** | 25 |

**Retention is not the cause and this was worth checking before concluding
anything.** `cleanupPeriodDays` is `3650` in both `settings.json` files, so
nothing was auto-deleted. The Claude record starts on 2026-07-08 because that is
when Claude Code started being used here. The two months before that are Codex
sessions on the Windows side, and no session, ledger, or document in this
repository has ever read them.

That is the largest single blind spot the audit found. It is not a missing
feature; it is a store nobody looked in, which is the `hidden-trees` rule class
arriving through a different door: not gitignored, just outside every path any
tool searches.

## 2. Corpus: 2,806 prompts, 30 active days, two record shapes

Unified from both stores. The two shapes are not interchangeable and merging
their extraction is how this measurement fails silently:

```
Claude:  {"type":"user","message":{"content":...},"timestamp":...}
Codex:   {"type":"event_msg","payload":{"type":"user_message","message":...}}
```

Running the Claude predicate over a Codex rollout yields zero rows and reads as
"the files are empty", which is exactly how 25 sessions stay invisible.

- 2,806 prompts raw, 2026-05-08 to 2026-08-01, 30 distinct days
- 244 Codex, 2,562 Claude
- 2,197 after removing 789 harness-injected turns (system reminders, command
  wrappers, task notifications, bash echoes)
- 36,815 records skipped as empty content, which is the normal ratio for
  transcript JSONL

Coverage boundary: every `*.jsonl` under both stores parsed without a file-level
error. Prompts under 12 or over 400 characters were excluded from clustering
only, not from the corpus.

## 3. The dominant signal is interruption, not a forgotten request

The most repeated string in the corpus is not a request at all:

| String | Count | Span |
|---|---|---|
| `[Request interrupted by user]` | **217** | 11 days, 2026-07-15 to 2026-08-01 |
| `Stop hook feedback: Evidence check ...` | 47 | 8 days, 2026-07-24 to 2026-07-31 |
| pasted image headers | 57 | 6 days |

217 interruptions over 11 working days is roughly 20 per day. The
`work-cadence` rule already records the opposite failure, an agent stopping too
early, at 66 operator turns and 940 minutes over one week. Both numbers describe
the same broken loop from the two ends: the agent stops when it should run, and
runs when it should stop. Only one of the two currently has a rule written for
it.

The 47 `Evidence check` stop-hook fires over 8 days are the same class as the
interrupts, mechanised: a hook that keeps firing is a class that keeps
recurring, and its fire count is the cheapest available regression signal on
agent behaviour. Nothing currently reads it.

## 4. What I measured and then threw away, because it was not sound

A first pass classified prompts into complaint classes ("you did not do it",
"you lied", "wrong direction") by regular expression, and produced confident
counts: 280, 40, 356, 200, 495. **Those numbers are not in this document because
spot-checking the samples showed the patterns matching incidental words inside
pasted context packs**, so a 3,000-word context block scored as five complaints.
The counts are unrecoverable without a real classifier and are recorded here as
discarded rather than deleted, because L-2026-07-31-c is a reviewer whose own
numbers went unchecked.

What survives is only exact-string counting, which cannot make that error.

## 5. The failure record is unreadable by its own reader

`state/lessons.jsonl` is the repository's answer to "which failures did we make
and did we handle them". Measured directly:

- 42 rows
- **10 distinct key shapes**
- the largest shape (`date, enforcement, id, incident, lesson, status`) covers 17
  rows; the next covers 10; six shapes have 1 or 2 rows each
- **24 of 42 rows lack `lesson` or `enforcement`**, both of which
  `tools/digest/build_digest.py:89` reads unguarded, so the digest build dies
  with `KeyError`. First offender is `L-2026-07-27-a`.

AUTO-16 exists to surface open lessons in every digest. It surfaces none, and
has surfaced none since roughly the day a writer changed shape. The failure
record has a failure of exactly the class it exists to record, which is why it
did not record it.

`tools/workspace/log_session_lesson.py`, one of the writers, is an orphan
one-shot script that nothing invokes (see the fog-of-war document's tool wiring
section). A writer nobody owns produced a shape nobody enforced, and the reader
broke silently.

## 6. Two clauses of the directive that could not be answered here

**`ledger.csv` is not in this repository.** The only one on the machine is
`/home/shov/work/repos/new-recruit/ledger.csv`, 9 rows, a share-triage table
(`date_shared, canonical, kind, license, gate_absorb, status, ...`) whose oldest
row is 2025-12-14. It belongs to the resume lane, not the harness lane, and
absorbing it into this repo would be cross-lane work needing its own claim.

**The WhatsApp "reminder to myself" export does not exist as a file.** No
`_chat.txt`, `*chat*.txt` or `.chat_txt` anywhere under the home directory. What
exists is `~/.claude/skills/whatsapp-query`, which decrypts the live WhatsApp
Desktop store at
`/mnt/c/Users/shova/AppData/Local/Packages/5319275A.WhatsAppDesktop_cv1g1gvanyjgm/LocalState`.
That is the path to the corpus, and running it is a separate task with its own
PII handling, not something to fold into a sweep.

## 7. Edits this implies, ordered, none applied here

Written as a list rather than applied, because a one-shot fork half-applying a
sweep across the live tree with no gate run is worse than a written finding.

1. **Add the Codex store to whatever reads history.** `session_recall`,
   `reground`, and any future memory or RAG layer currently see 24 days of a
   record that is 85 days long. One path constant.
2. **Schema the lessons ledger before guarding its reader.** A `.get()` default
   at `build_digest.py:89` makes the digest print blanks and stay green, which is
   the same silence in a new costume. The declaration belongs in
   `state/schemas/lessons.json` with a validator wired as a gate domain, which
   is the Grain DDL pattern the other fork independently arrived at.
3. **Give `state/hook-fires.log` a reader.** 47 `Evidence check` fires over 8
   days is a measured behavioural regression signal that nothing consumes. A
   weekly count per hook, per day, is a two-line query and the closest thing this
   harness has to an outcome metric.
4. **Write the interruption side of the cadence rule.** `work-cadence.md`
   documents stopping too early with numbers. Stopping too late, at 217
   interrupts over 11 days, has no rule and no threshold.
5. **Decide who owns `tools/workspace/log_session_lesson.py`.** Either wire it
   as the single writer for the ledger, or move it out of `tools/` with the other
   finished errands.
