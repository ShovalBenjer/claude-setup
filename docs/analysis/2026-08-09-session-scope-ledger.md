---
PRD: prd/2026-08-03-unified-architecture.md
Ticket: SETUP-OS
Status: active, point-in-time scope ledger for the 2026-08-07 to 2026-08-09 session
---

# Full scope, every prompt of this session accounted for

Written 2026-08-09 on request: "whats more left to do? write me full to list full scope,
iterate against all prompts." One row per instruction the operator gave, in the order he
gave them, with what landed and what did not. The point of the ordering is that it makes
an unanswered instruction visible instead of letting it dissolve into the next one.

Status vocabulary: DONE means the evidence is on disk and named. PARTIAL means some of the
instruction landed and the rest is itemised. OPEN means nothing landed. BLOCKED means it
waits on the operator.

## The prompts, in order

| # | Instruction | Status | What remains |
| --- | --- | --- | --- |
| 1 | BOOT UP | DONE | nothing |
| 2 | your changes violate the standards, why is it not enforced, who said to implement | DONE | the enforcement gap it exposed is row S3 below |
| 3 | keep the diff, consolidate the repo, review job cost | PARTIAL | S1, S2 |
| 4 | change settings so hooks are editable, I want autonomous | DONE | nothing |
| 5 | fix Skill(i-have-adhd) | DONE | the 13 sibling skills are row B1 |
| 6 | use all Claude features, agents at will, TODO is not updated | DONE | nothing |
| 7 | ensure the WSL move brought all the sessions | PARTIAL | S4, the Codex store |
| 8 | how do I trust the code, when is advisor called, are you orchestrating | DONE | nothing |
| 9 | connectors: which went unused, do the wiring | PARTIAL | S5, other lanes |
| 10 | git should not ask for approval | DONE | nothing |
| 11 | do not miss my last two prompts | DONE | nothing |
| 12 | subagents for waived domains, document Zion, autonomous workflows, connectors, what next | PARTIAL | **S6 is the one I under-served** |
| 13 | did you change git push | DONE | nothing |
| 14 | what now | DONE | nothing |
| 15 | approvals, and write the full scope | this document | S1 to S8 below |

Prompt 12 carried four instructions and I answered three. The one I did not is
"the autonomous workflows should be done", and it is the largest open item in this file.

## Approved and starting now

**A1. Drop `disable-model-invocation: true` from the 13 repo skill copies.** Approved
2026-08-09. That line is what made `/i-have-adhd` unusable, because a slash invocation
reaches a skill through the same Skill tool the flag disables. Deploying it instead would
have disabled 13 more. Closes the largest bucket of the `skills` waiver, which expires
2026-08-12.

**A2. Promote the harness resolver.** `new-recruit/tools/harness.py` resolves this
repository through `$CLAUDE_HARNESS`, then a `.harness-ref` file, then a vendored
fallback. It works, it was written to fix a defect a spec had named, and it lives in a
consumer rather than in the producer it consumes. Move it to `claude-setup/tools/harness/`,
name it once in `AGENTS.md`, give `daily-deep-learning` a `.harness-ref`, and re-pin
new-recruit's sha, which has drifted eight days (`9d94efb5` pinned against `98bb64da`).

**A3. The unblocked half of the directory decisions.** Archive `home-dotfiles` (2 commits
ever, all three of its live targets absent) and `startup-scripts` (2 commits, unchanged
since the 2026-05-09 export, zero references from Python). Merge `master-plans` into
`work-docs`, where 6 of its 8 files already sit byte-identical and its own purpose row says
superseded.

**A4. Fix `dot-claude/bin/self-improve.py:27`.** It inserts
`$HOME/projects/intent-control-plane/src` on `sys.path`, and `/home/shov/projects` does not
exist. A live broken consumer, findable now only because the `pointers` domain started
reading the live settings on 2026-08-08.

## Still open, not yet approved

**S1. The one-src consolidation.** Two Python worlds: `tools/` at 100 files with no
package, no lint and no types, and `intent-control-plane` at 90 files that is the only
packaged tree and the only place ruff and mypy run. The dependency runs from the unchecked
half into the checked one, through 25 `sys.path.insert` calls. Three directories are
contested and were deliberately left for the operator: `dot-agents`, `dot-codex`, and
whether the `intent-control-plane` boundary survives at all. Evidence in
`docs/analysis/2026-08-07-toplevel-dir-decisions.md`.

**S2. The review job cost knob.** Raised from 10 turns to 40 after establishing it bills
the subscription rather than a metered key. Nothing further is owed unless it hits the new
cap.

**S3. Nothing enforces the coding-style standard on `tools/`.** The `types` domain runs
ruff and mypy only after `cd intent-control-plane`, so repo-wide it checks syntax alone.
Separately, no rule in the house selection catches a prose comment, so rule 3 of the style
standard, the one most often broken, has no oracle anywhere. Extending the scope surfaces
a real backlog: 59 ruff errors in `tools/gate/gate.py` alone before this session touched
it, so it ships with a waiver carrying a number and a burn-down.

**S4. The Codex session store was not migrated.** `/mnt/c/Users/shova/.codex`, 95 jsonl.
Left out on purpose: its record shape is `event_msg` with a `user_message` payload rather
than Claude's `message.content`, so it needs its own reader and not a copy. Named because
the instruction said "all the sessions".

**S5. Connector lists for the other three lanes.** `disabledMcpServers` is per project and
only `claude-setup` has a non-empty list. `new-recruit` and `daily-deep-learning` inherit
every medical connector for no reason. Recommendations exist in
`docs/analysis/2026-08-08-connector-catalogue-reasoning.md` and were deliberately not
applied, because a working environment belongs to whoever works in that lane.

**S6. The autonomous workflows, which is the instruction I under-served.** The operator
said twice that he should not have to prompt for this. What exists today is reactive: hooks
fire on events, the gate runs when something asks it to, and agents spawn when a session
spawns them. What does not exist is a loop that notices and acts without a turn happening.
The pieces are on disk and unassembled: `state/` carries fourteen ledgers, `tools/telemetry`
publishes a cross-repo feed to issue #38, `tools/selfimprove/scan.py` ranks what to pick up
next, and `CronCreate` plus the `schedule` skill can run a cloud agent on a cron. Nothing
joins them. The honest scoping question, which is the operator's, is whether an autonomous
loop should propose or act: a loop that opens PRs nobody reads is the agent feed's failure
repeated, and the feed's own open question is still "watch whether anything ever ACTS on an
issue #38 item".

**S7. The board itself.** 33 epics, 0 closed, 8 of 196 checklist items, net debt up 9 in
five days. `Status`, layer one of the four-layer taxonomy, is unset on all 33 items and has
been for at least eight days because the design routes it to a human hand edit. Drafted and
deliberately unposted text sits in `docs/analysis/2026-08-08-zion-and-inheritance.md`,
including a reply on Discussion #43 about the feed's publish gap.

**S8. Live `~/.claude/skills` went from 40 to 79 in two days and nothing can date or
attribute it.** All three repo tree counts reproduce within one, so the change is isolated
to the one tree not under version control. `state/snapshots` holds a single manifest from
2026-07-25 and does not span the gap. This is not a measurement problem; it needs the
operator's memory of what he installed on 2026-08-06.

## Blocked on the operator

**B1. Nothing.** The `disable-model-invocation` decision was the only deadline-carrying
block and it was approved on 2026-08-09.

**B2. The three contested directories in S1.** No deadline.

**B3. Whether S6 proposes or acts.** No deadline, but it gates the largest remaining item.

## Two candidate inputs the operator supplied without an instruction attached

An O'Reilly course description on durable workflow harnesses and parallel deep-research
harnesses: checkpointing that survives interruption, approval gates that keep a human in
the loop without breaking determinism, an orchestrator with worker agents over a shared
evidence pool, and a consolidation pipeline turning episodic traces into durable semantic
knowledge. It arrived beside the S6 instruction and reads as the shape he wants, so it is
recorded here rather than acted on, since a course description is not a specification.

Connector authentication moved during the session: O'Reilly connected, while Ashby and CB
Insights failed to authorise. This changes nothing in S5's recommendations, all of which
were marked ASSUMED on auth cost precisely because this is volatile.
