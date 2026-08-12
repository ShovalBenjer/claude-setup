---
PRD: prd/claude-os.md
Ticket: SETUP-OS
Status: active, point-in-time measurement of the three-tree skills question
---

# The third skill tree is not dead weight, and one of the "genuine forks" is not a fork

Measured 2026-08-10, while executing the approved `dot-codex` split. The split went ahead
in a narrower form than the recommendation it came from, because the measurement
contradicted the recommendation.

## What the recommendation said, and why it was wrong

`docs/analysis/2026-08-07-toplevel-dir-decisions.md:204` recommends archiving
`dot-codex/skills` entire: "33 dead pointers plus 28 directories deploying to an empty
target". The first half is right. The second half would have deleted the only committed
copy of a skill that is live right now.

## The 33 are genuinely dead and are gone

Each was one line whose whole body is a path under `/home/shovalbe/.claude/skills/`, a
home directory that does not exist on this machine. `git rm`, recoverable from history,
named in the commit.

## The 28 directories are not dead, and 13 of them ARE the live tree

Comparing `dot-codex/skills/<name>/SKILL.md` against `~/.claude/skills/<name>/SKILL.md`
by sha1, 13 are byte-identical: `code-simplifier`, `feature-investor`, `kill-stale`,
`ops-status`, `ponytail`, `ponytail-audit`, `ponytail-help`, `ponytail-review`,
`shoval-voice-draft`, `triage-tests`, `watchdog`, `web-inspect`, `workspace-brain`.

Twelve of those are also identical in `dot-claude/skills`, so they are simply three
copies of one file and cost nothing but disk. The thirteenth is the finding.

## `shoval-voice-draft` is not a genuine fork

| tree | bytes | sha1 |
| --- | --- | --- |
| `dot-claude/skills` | 27401 | 42d86679 |
| `dot-codex/skills` | 10935 | **a4df916f** |
| live `~/.claude/skills` | 10935 | **a4df916f** |

The skills waiver has carried this as one of three "genuine forks" where "whichever side
someone reads is a coin flip". It is not a coin flip. The live file is committed, exactly,
in the tree the oracle does not read. `tools/audit/skills_sync.py` compares `dot-claude`
against live and nothing else, so a third tree holding the answer reads as drift.

That does not settle which version SHOULD be live: `dot-claude`'s is 2.5 times longer and
may well be the intended replacement. What it settles is that nothing is lost, and the
question is a promotion decision rather than a recovery problem.

## What survives as real drift

- `youtube-distill`: two versions, `dot-claude` 12545b and live 8205b, no third copy.
- `grill-me`: `dot-claude` and `dot-agents` agree at 635b, live differs at 1261b. Direction
  is known here and contradicts size: commit `3df7704` rewrote the repo copy into a terse
  brief, so the SMALLER repo file is the newer one and live holds the older protocol.
- `case-ledger-post`: appeared 2026-08-10 12:13 in the live tree during a session that did
  not write it. Two clones share one `~/.claude` here. Needs a human who knows what changed.

## What this changes about the three-tree question

The honest framing is no longer "which tree do we keep". It is "the oracle reads one of
three trees and reports the other two as drift". Fifteen of the sixteen drift items are
downstream of that, not of anything anyone did wrong. Extending `skills_sync.py` to read
all three would shrink the number without a single file moving, and would stop the waiver
from restating a measurement problem as a backlog.

That extension is not done here. It changes what an oracle asserts, and the waiver expires
2026-08-12 regardless, so it is a decision rather than a cleanup.
