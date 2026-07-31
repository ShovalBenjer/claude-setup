# Architecture build plan v2, 2026-07-29 (supersedes v1 the same day)

v1 called itself "full scope" and "plan of record" after reading TODO.md and its
own session memory. The operator refused it. This version was written after the
sweep v1 skipped, and the sweep changed the plan's SHAPE, not just its contents.

## Coverage statement (v1 had none; that omission was the defect)

Swept for v2: bus log and inbox (20 rows), `selfimprove/scan.py`,
`refute.py run` (26 claims), `skills_sync check`, `pointers scan`,
`codemap check`, `gate status`, `git status`, TODO.md in full, all 31 lessons,
CLAUDE-OS.md sections 5 and 6, lane C and lane D working trees, live-vs-canonical
settings and rules.

NOT swept, still owed: the 15 ADRs and both PRDs read end to end (only the INDEX
headings and the supersession table were read), `work-docs/`, the
intent-control-plane subproject's own tests, open GitHub issues and PRs across
the 22 repos, and the 52 skills_sync drift items item-by-item (the count is
measured, the dispositions are not).

## What the sweep changed about the diagnosis

v1's frame was "here is the sequence of things to build." The measurements do
not support that frame as the primary one. Every number below is a maintenance
debt, not a missing capability:

- 19 messages addressed to this lane, unread since 2026-07-25, because the A2A
  inbox hook was present in canonical settings and ABSENT from live. Claim C-001
  had been refuting this the whole time and nobody read the refutation either.
- 3 of the top 4 proposals from the tool the project CLAUDE.md names for
  choosing work were phantom: it reported three live hooks as missing because
  `Path("/c/Users/...").exists()` is always False on Windows.
- 7 of 26 claims refuted, 4 of them only because a mutation lock file left by a
  dead process (pid 20320) had been blocking every mutation-backed verifier.
- 52 skills_sync drift items; 261 distinct absent paths in pointers scan.
- `/reground`, the command the operator typed, was absent from live and pointed
  at another machine's Linux path in canonical.

The competing frame v1 suppressed is therefore the correct primary one: this
system's throughput problem is that its own instruments were unread, unwired, or
wrong, and adding tickets on top of that made it worse. v2 leads with
reconciliation and puts new capability behind it.

## Fixed tonight, with the check that proves each

1. Response-channel slop gate. `completion_gate.py` now applies the repo's own
   dash rule to the assistant's response text, with fenced blocks, inline spans
   and URLs stripped first so quoting a command stays free. 27 tests (10 new),
   3 mutations applied by hand each turned the suite red, restore green.
   Deployed; canonical and live sha256 match; fires correctly on a live payload.
   Driver: 33 violations across 17 of 28 turns in this session (L-2026-07-29-g).
2. `scan.py` hook resolution. Added `resolve_hook_target`, widened
   `HOOK_SUFFIXES` to include `.py` (Python hooks were never checked at all),
   6 new tests asserting both directions. Ranked proposals went 14 to 11 and the
   three phantoms are gone.
3. A2A inbox rewired into live settings by copying canonical's own entry, so no
   path was hand-typed. `bus_wired.py` now exits 0: C-001 held.
4. Bus lane map. `downloads\daily-deep-learning` added (lane D had never been
   addressable and its own messages derived lane A), `DEFAULT_LANE` changed from
   the retired lane A to `?`, lane E named. The selftest CAUGHT this change and
   was updated to encode the new contract rather than weakened; 23/23 mutations
   still caught; chain verifies.
5. Stale mutation lock removed. Refutations went 7 to 3, then to 2 after
   accepting the config baseline for tonight's intentional settings changes.
6. `/reground` rewritten as the reconciliation sweep itself and deployed live;
   the dead path is described rather than quoted, so the fix does not register
   as the defect (L-2026-07-29-d).
7. Records corrected rather than quietly edited: model-selection.md now says the
   fable experiment ENDED EARLY with no verdict (operator set opus tonight,
   before the 08-05 falsifier); the effort contradiction is recorded IN the rule
   as an untested hypothesis instead of resolved by rewriting the losing side;
   CLAUDE-OS.md decision 1 closed; the retro's workflow section carries an
   explicit correction.
8. Workflow cost correction. The retro claimed workflow yield had never been
   measured. The bus holds two negative measurements: one workflow burned 2.66
   hours and 3.64M subagent tokens for nothing usable, and one fan-out exhausted
   a shared session budget and silently degraded everything after it.

Root test suite 179 passed. Ship gate PASS on the final tree.

## Phase 0, before any new capability (this is the change from v1)

- Disposition the 52 skills_sync drift items and the 261 absent paths: each is
  adopt, delete, or record-as-intentional. A count is not a decision.
- Read the 15 ADRs and 2 PRDs end to end and reconcile against TODO.md, which
  has grown 7 sections written by at least 3 sessions.
- Re-run refute weekly, not never. The 4 lock-blocked refutations sat unnoticed
  because nothing runs it on a schedule.
- Decide the mixed tree: 65 files are staged and several untracked trees from
  other sessions (case-ledger-post, prior-art-gate, syndication-engine,
  whatsapp-query, tools/intent) are deliberately NOT staged, because staging
  them pulls prior-art obligations for code this session did not write.

## Phase 1, oracle batch (unchanged from v1, still correct)

Each with selftest and mutation spec: advice-without-artifact in the Stop gate,
lane-enforcement check, waiver-falsifier execution, stack-lint domain,
selftest-ledger isolation. The response-channel gate shipped tonight is the
template: measure the defect, write the check, prove it can go red, deploy both
copies, verify sha match.

## Phase 2, capability (unchanged in content, moved behind Phase 0)

ecosystem.db (AUTO-06) then FleetView v0 over the sessions tap, in parallel with
the CCC adopt-versus-build evaluation. Discovery sweep rebuild. Groq and
Cerebras probes. gemini-review workflow consuming the stored secret. AUTO-18
scheduled tasks observed firing unattended.

## Standing risks the sweep surfaced and v2 does not resolve

- No retrieval layer over `state/`: 130M transcript tokens per week, ~20M in one
  session, ledgers read by tail and grep only.
- The statusline underneath FleetView has never been observed rendering in a
  real terminal, only against synthetic payloads.
- C-025 (pre-bus-wiring snapshot) stays refuted: the write it guarded has now
  happened, so the claim is obsolete rather than failing, and an obsolete claim
  that still reports red trains people to ignore the ledger.
- Lane C and lane D have no TODO.md at all, so their backlogs are not
  enumerable from disk the way lane B's is.

## Operator decision queue (consolidated, stale rows removed)

1. panel.py: lexical pass or retire to /code-review. Waiver expires 2026-08-12.
2. The mixed tree: what to commit, what to leave, or delegate the split.
3. voice-metrics: commit with the WhatsApp LID in keys, or keep live-only.
4. DECIDE row: which undeployed work-enforcement hooks to adopt.
5. API key rotation, unconfirmed since 2026-07-24 (CLAUDE-OS decision 2).
6. PR-fabric opt-in repo list (CLAUDE-OS decision 3).
7. WhatsApp copilot cadence (CLAUDE-OS decision 4).
8. CCC: adopt, fork, or build FleetView, after the evaluation.
9. case-ledgers custom domain, and the-bench v5 draft keep or revert.

Removed from v1's queue as no longer live: the fable/effort decision (you made
it tonight by switching to opus; the effort contradiction is now recorded as an
untested hypothesis rather than a pending choice).
