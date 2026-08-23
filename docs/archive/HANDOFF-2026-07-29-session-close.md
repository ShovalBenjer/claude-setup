# Session handoff, 2026-07-29, lane B

Session e49f33b5, started 10:12 UTC on opus-5[1m], switched by the operator to
fable-5 at max effort near close. Claims: session-2026-07-29-intent-traceability-slice
and session-2026-07-29-resource-ledger, both claimed before starting.

## What is LIVE now, with the check that proves it

1. **Prompt capture.** Typing a prompt fires UserPromptSubmit, runs
   `tools/intent/capture_turn.py` under the icp venv, writes the full event,
   an intent card, and a CAPTURED transition into `~/.intent`, and appends a
   hash-chained row (no prompt text) to `state/prompt-tickets.jsonl`. Check:
   the section 4.2 acceptance query returns the prompt, its PT id, and a
   goal; `PT-5d13dbe16217` exists in both stores. In-harness fire lands with
   the operator's next typed prompt after registration.
2. **Resource ledger.** `tools/intent/resources.py` (content-addressed key,
   seen vs note, self-describing chain rows) plus `scan_resources.py`.
   Backfill: 494 files, 3855 sightings, 2712 distinct resources, 1.1s, chain
   verifies, re-run adds zero. Coverage now reads the honest number: 0.2%
   (5 noted of 2716), against the week's measured 12.7% anecdote.
3. **Follow-through Stop gate.** `completion_gate.py` gained the handback
   check: a turn ending in an offer to continue with no blocker, approval,
   or destructive action named gets one corrective turn. Loop guard is
   `stop_hook_active`; escape hatch is `NEEDS OPERATOR: <reason>`; every
   stop (including clean) logs to `state/handback-log.jsonl`. Real fires:
   2 blocks, 2 releases, 0 trapped sessions. 17 tests.
4. **Lessons became a reflex.** session-recall.sh now injects the six newest
   open lesson CLASSES at SessionStart (was zero references; 20 open).
5. **Rules.** `model-selection.md` rewritten both copies: the fable default
   is recorded as a one-week EXPERIMENT with a falsifier due 2026-08-05
   (handback rate, restarts, refusals, throttling vs the opus baseline),
   plus the routing table, fable handling, and workflow overrides.
   New `out-of-distribution.md` both copies: diverge-or-forbidden default,
   real-reference anchoring, named avoid-lists, direction-first visuals,
   idiolect as anchor, taste.md compounding, prior-art clamp.

## Infrastructure defects found by measurement and fixed

- Windows concurrent appends DESTROY rows (24 threads wrote 18 lines; CRT
  append is seek-then-write). Fixed with a shared `file_lock` in bus.py and
  icp `ledger_append`; bus docstring corrected; selftest now counts rows
  under concurrency; 23/23 mutations caught.
- `bus.py canonical()` would have hashed a ticket row over id/ts/prev only.
  Self-describing `chain_fields` (operator-picked via /diverge, recorded in
  docs/taste.md) landed; existing bus hashes unchanged (golden vector
  1def9c6c00638f23); adding `source` later cost zero migration, the first
  exercise of that property.
- Per-turn telemetry inside the gate fingerprint made every PASS
  self-invalidating (the Stop hook wrote while reporting green). Fixed at
  .gitignore; same reasoning as GATE_OUTPUTS.
- The icp CLI `state transition` trusts caller-supplied from-state and
  hardcodes allowed_by_contract=1; capture_turn writes transitions itself
  with read-then-check inside BEGIN IMMEDIATE.

## Decisions taken (grounds in parentheses)

- Capture reads the HOOK PAYLOAD, never transcripts (vendor docs: format
  internal, breaks on any release; L-2026-07-29-e; spec header corrected).
- Ticket id is content-derived {session, text_sha, occurrence}; survives
  replay and vendor changes.
- `review` domain waived to 2026-08-12: all 5 highs are regex hits on
  comments, docstrings, JSON prose; waiver reason embeds two AST commands
  that refute it if wrong (both return []). Third waiver for this class:
  L-2026-07-29-d; fix-or-retire is on TODO and needs operator approval.

## Session-measured findings a future session should not re-derive

- Bypass/auto mode question is CLOSED: permission blocks 77 to 5 after the
  07-26 flip; remaining 5 are deny-list credential reads; convergence is
  self-stopping, hence the Stop gate, not a mode.
- Handback pattern: ~31% of reacted-to answers (124/405 and 136/414 by two
  independent measurements); 66/420 pure restart turns; ~940 min/week idle.
- Compaction churn ended 2026-07-26 (250 PreCompact on 07-25, 0 on 07-28/29);
  suspect env vars are absent; cause of the fix not established.
- Migration is acquisition-complete, activation-half-done: 91/186 deployed;
  every missing body recoverable in-repo; dot-agents 0/231 (no ~/.agents).
- Personas: 23 exist, byte-identical repo/live, 0 fired in 927 transcripts;
  the only router emits prose labels, its hook undeployed. 0/23 declare an
  output artifact; 17 artifact types, 1 schema-enforced.
- Access: deny list guards verbs, not resources (cat secret BLOCKED, cp
  secret ALLOWED, curl exfil ALLOWED); lanes are prose, 0 enforcing lines;
  no actor field in any ledger. Committed settings say acceptEdits, live
  runs bypassPermissions.
- Resources handed over in the week: 110; 66.4% left no trace; now ledgered.
- Platform: we use ~6 of ~30 hook events; bus.py is the one component with
  no first-party equivalent (Mailbox is one-team-per-session, no replay);
  panel.py duplicates /code-review; escape-from-Claude-Code via Agent SDK is
  a category error (same harness, same hosting); unattended runs belong to
  Managed Agents scheduled deployments with a self-hosted sandbox.

## Open risks, ranked

1. Concurrent sessions write one tree: files landed at 16:03-16:04 from
   another session mid-gate; any verdict has a racing writer. The unit
   FAIL-then-PASS on tree 842125e6 came from workflow selftests appending
   scratch rows to the real gate ledger (TODO row filed).
2. panel.py third waiver; expires 2026-08-12.
3. RBAC axes team/resource/action/audit have no mechanism.
4. RT-1 calibration pairs still zero; confidence gate still inert.
5. voice-metrics preservation pending operator (WhatsApp LID in keys).

## Exact next actions

1. Copy the 14 hook bodies from dot-codex into dot-claude stubs, test each
   under Git Bash/Windows paths, deploy selectively per the DECIDE row.
2. Attach notes to the top-cited ledger resources (806 appear in more than
   one doc) starting with the 18-doc Azure project cluster.
3. Isolate selftest ledgers (gate, panel) from production state/.
4. Decide panel.py: lexical pass or retire for /code-review.
5. Commit decision on the mixed tree (see below), then the PR path per
   ADR-0012.

## The commit question, stated once

The dirty tree now interleaves at least three sessions (mine, the 07-27/29
spec sessions, and a live writer at 16:04). The gate's PASS covers the WHOLE
tree fingerprint; committing any subset creates a tree state that was never
gated, while committing everything bundles another session's in-flight files.
Neither is safely mine to pick. Ledger appends, docs, and rules in this
handoff are all on disk regardless.
