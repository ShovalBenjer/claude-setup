---
PRD: prd/claude-os.md
Ticket: SETUP-OS
Status: active, full-estate audit ordered by the operator on 2026-08-11
---

# Estate audit 2026-08-11: what the ledgers say when nobody is converging

Ordered by the operator, upset, in these words: a full iteration of all specs, plans,
prompts, and partial or reported-complete implementation, with an explicit ban on the
"12/12" convergence numbers. Every number below names the command or file that produced
it. Where a subagent measured, the section says so. Evidence classes per
calibrated-claims: VERIFIED means the output is pasted or on disk, MEASURED-BY-AGENT
means a read-only subagent's pasted output, ASSUMED is marked where it occurs.

## 1. The one item only the operator can close, restated first

The ElevenLabs key in `e695af5` has ESCALATED: `git branch -r --contains e695af5` now
lists `gh/main`, and `git merge-base --is-ancestor e695af5 gh/main` confirms it
(VERIFIED, run 2026-08-11). The incident doc (2026-08-10) said "a branch that is on
GitHub"; the carrying branch has since been merged, so the value is in the default
branch history. Rotate the key. Nothing in this audit matters more. L-2026-08-11-b.

## 2. The wiring layer, measured dead or alive

| mechanism | promised | measured 2026-08-11 | state |
| --- | --- | --- | --- |
| Gastown crons | 8 durable jobs, weekly re-bootstrap (memory file) | `CronList`: no scheduled jobs; newest file in /mnt/c/Users/shova/gastown/reports/ is 2026-06-03 | dead 69 days, VERIFIED |
| agent feed (Discussion #43) | post every 30 min via systemd timer | `journalctl`: exit 2 every tick since the unit passed `--sink discussion` to a publish.py that only knew `--issue`; last real post 2026-08-06T15:03Z | dead 5 days, REPAIRED this session |
| verbatim prompt capture | every operator prompt stored | TODO.md FOG row: text path dead since the WSL move; hashes only in prompt-tickets.jsonl; the recovery sits in PR #60, DRAFT, `mergeable: CONFLICTING`, all 7 checks SKIPPED | dead, fix rotting in a draft |
| settings.json hooks | 14 entries, 7 events | all 14 target paths exist, 0 dead (agent 4, `test -e` each) | alive |
| gate + oracles | run per session | state/gate-runs.jsonl 9329 rows; selftests wired in CI | alive |
| company personas | 19 personas route work | state/agent-spawns.jsonl: 10 rows ever, first 2026-08-08; router named the wrong persona in 5 of 6 named rows | barely born |
| external judges | codex-call after checks, Gemini judge, dispatch | skill-use.jsonl 61 rows: codex-call 1, dispatch 0, gemini 0, eval-runner 0; ~/.claude/cache/a2a/audit.jsonl never created | approx. unused |

The pattern is exact: everything that fires from an event (hooks, gate) is alive;
everything that requires an agent or a human to voluntarily re-arm it (crons, feed
config, judges, personas) died quietly. publish.py's own docstring predicted this:
"this repository's lessons ledger is a list of voluntary steps that stopped happening."

## 3. Specs and plans against the disk (agent 1, read-only)

Across docs/prd/ (5) and docs/specs/ (21): **BUILT 2, PARTIAL 11, PAPER 13.** Half the
planning corpus has no implementation artifact at all. Sharpest rows:

- `specs/2026-07-24-command-center-superior.md` (FleetView): 12-row feature table,
  5 premortems, 18-item acceptance checklist. `tools/fleetview/` does not exist.
  TODO's own ABSORB-05 row has said "SPECCED, ZERO CODE" for 18+ days.
- `specs/2026-07-23-persona-review-economy.md` carries `Status: active`; its
  reputation.db exists nowhere in the repo. A header that lies is worse than PAPER.
- `specs/2026-07-29-intent-traceability.md` says "Not built" while its capture path
  half-runs and its text half is the dead prompt capture above: the status is wrong in
  BOTH directions at once.

TODO.md: 145 open rows by fresh grep (`grep -c "^\s*- \[ \]"`), while the file's own
text claims 96 (2026-08-05) then 133 (2026-08-08). The boot hook injects 6 rows, so
139 open items are invisible at session start. Nothing ratchets the count; every
self-report is stale by the time it is read.

## 4. Local vs remote, clone vs clone

VERIFIED directly this session:

- Primary: /home/shov/work/repos/claude-setup (via the /home/shov/claude-setup
  symlink), branch was lane-a/na-domains-and-run-duration, dirty state ledgers, 1
  behind gh/main.
- Second clone: /mnt/c/Users/shova/claude-setup on branch `chore/delete-dolt`,
  mid-deletion of intent-control-plane files, different HEAD (f5d697e). No lane
  branch of the WSL clone knows this work.
- The live skills tree depends on the second clone: `~/.claude/skills/learn-on-demand`
  and `prove-implementation` are symlinks into /mnt/c/Users/shova/claude-setup
  (agent 4). Deleting the "stale" Windows clone would break two live skills.
- Open PRs on claude-setup: 6 (numbers 42, 47, 52, 53, 60, 61), five of them DRAFT,
  oldest from 2026-08-05. The two spot-checked (42, 60) are both
  `mergeable: CONFLICTING` with checks SKIPPED. The delegation plan already flagged
  rebasing them as work that waits on "do we still want this".
- Memory is fragmented across 7 stores under ~/.claude/projects/*/memory; boot recall
  in /home/shov sessions reads the pre-move Windows-path store, which still promised
  the dead Gastown crons and the pre-move new-recruit path (both corrected this
  session).
- Skill trees: live 78 dirs + 2 symlinks, dot-claude 76, dot-agents 70;
  skills_sync DRIFT 16 (4 committed-not-deployed, 8 deployed-not-committed, 4
  diverged); 39 of 100 registry-owned skills have no live dir, 31 of those exist only
  in dot-agents, which no sync tool reads; 17 live skills are in no registry.
  55 of the live dirs share mtime 2026-08-06, one bulk-sync event, so mtime cannot
  date authorship (S8 stays open for the operator's memory).

MEASURED-BY-AGENT (agent 2), sibling repos:

| repo | branch | ahead/behind | dirty | last commit | verdict |
| --- | --- | --- | --- | --- | --- |
| new-recruit | master | 3 unpushed / 0 behind | 85 files | 2026-08-10 harness re-pin | implementation trails its plans by hours to days; alive |
| daily-deep-learning | types/callsite-delta-oracle | 0 / 0 | 0 | 2026-08-10 review fix | clean and synced; PRs #4 open, #5 draft |
| claude-memes-skills | main | 0 / 16 behind | build artifact only | 2026-05-09 | abandoned locally since May; remote moved without it |

The hiring engine's real state, from its own ledger.sqlite: discovery is alive (114
jobs routed through arm A as of 2026-08-11 07:02, all 7 arms routing), and the apply
layer has produced nothing since 2026-07-23 because **the operator withdrew approval
for all 7 arms on 2026-07-27** ("He stated he does not approve the resumes; the ledger
said otherwise") and never restored it. Two arms ever sent real applications (A: Cato,
G: Glow, both human_reject). "Way back in my projects" is, on this surface, half a
system fault and half an approval the operator has not re-granted.

The Windows clone, precisely: 104 behind / 3 ahead of origin/main; its 3 commits
(2026-08-01, otel propagation plus gate fixes) are reachable from no branch anywhere;
the 45 unstaged deletions are a legitimate dedup of intent-control-plane/src into a
committed src/ tree, half-finished for 10 days. **17 untracked files there exist
nowhere else at all**, including PROJECTS-MANIFEST.md and 15 other reference notes
under docs/analysis/reference/, one `git clean -fd` away from gone. An incidental
find also surfaced a second new-recruit mirror at /mnt/c/Users/shova/new-recruit,
unaudited.

## 5. "Prompts I gave were totally ignored", measured precisely

Three independent measurements, and they disagree in an informative way:

1. In-turn: agent 3 sampled 25 operator-typed prompts (2026-07-30 to 2026-08-06)
   matching the operator's named topics (deepseek, gemini, free tier, github repos,
   compare, train). All 25 show concrete same-session action; 0 were no-trace. The
   sample is keyword-biased toward visible activity and covers 25 of 55 matching
   human prompts, said plainly.
2. Across sessions: the claims ledger records the drops the operator felt. Row 25
   (2026-08-07) scoped "comparing against the WhatsApp GitHub repos which may never
   have been compared"; row 28 (2026-08-10) scoped the prime-agent and self-hosted
   model analysis. Both produced nothing, and row 29 is the ledger's own UNDELIVERED
   confession: "Twice scoped, twice dropped, neither drop noted."
3. Structurally: the same 3,200-char instruction entered two different sessions 12
   seconds apart and each lane acted independently, unaware of the other (agent 3).
   Work happens, split across lanes the operator is not simultaneously watching, and
   nothing reconciles the halves.

So the honest verdict is not "ignored in the turn". It is: acted on in the moment,
dropped across time, because no executor persists intent between sessions (S6, the
under-served instruction, still open) and the capture layer that would even remember
the words is dead (PR #60). The operator's experience is the correct reading of a
system whose plans outlive its follow-through.

## 6. What this session repaired, with evidence

- **The twice-dropped repo comparison ran.** New skill `repo-compare`
  (dot-claude/skills/repo-compare, byte-identical live copy, sha1 b87f39ee, owner
  Evidence Clerk in both registry copies). First run:
  `docs/analysis/2026-08-11-repo-compare.md`, 8 repos, 4 ADOPTs with named trial
  gates, 8 chained rows in resource-ledger (`resources.py verify`: chain intact,
  3877 rows).
- **The agent feed is repaired.** publish.py learned `--sink discussion` with the
  same cannot-post-by-accident properties, target resolved from the new
  state/agent-feed.json; unit copies re-synced; selftest 9 ok including two new
  checks; dry run rendered 7 fresh items. The next 30-minute timer tick posts to
  Discussion #43 again. VERIFIED: selftest exit 0, dry-run output.
- **Memory corrected in place**: Gastown memory now carries its measured death date;
  new-recruit memory carries the repo's real location.
- **TODO.md FOG secret row** now states the gh/main escalation.
- **Lessons L-2026-08-11-a and -b** filed for the two new failure classes.

## 7. Root cause, one paragraph

The estate optimizes for provable honesty at rest (ledgers, oracles, falsifiers) and
has no organ for liveness. A cron expires, a unit flag drifts, a memory goes stale, a
PR conflicts: each is silent, and the reporting layer keeps producing confident
documents on top. The specs count (13 of 26 PAPER) is not laziness, it is a system
that rewards writing a checkable plan more than it rewards checking yesterday's. Every
mechanism that died, died at a voluntary step. The fix that matters is the one the
scope ledger already named as under-served: S6, a loop that notices and acts without a
turn happening, with the boundary rule already written for it.

## 8. Decisions that are the operator's, each with a recommendation

1. **Rotate the ElevenLabs key.** Recommended now; section 1. No git operation
   substitutes.
2. **The 6 open PRs.** Recommendation: merge or kill by number this week; 42 and 60
   need conflict resolution first, which the loop may do on its own branches if you
   say which survive. A draft queue this old is where repairs go to die (the prompt
   capture fix is in it).
3. **Agent communication on GitHub.** The feed to Discussion #43 resumes on its own
   now that the code matches the unit. PR comments and new discussion posts by agents
   remain forbidden by the-loop-may-act, your rule of 2026-08-10. If today's
   complaint ("no communication of agents in github discussions nor comments on prs")
   means you want that widened, say which surfaces: the rule file names the exact
   lines, and drafts can flow the day you do.
4. **The DeepSeek pivot.** The mechanism exists without new code
   (ANTHROPIC_BASE_URL retargeting; glm-harness ships DeepSeek profiles, repo-compare
   run 1 ADOPT). Recommendation: approve a zero-spend trial against their mock
   endpoint first; any funded endpoint or training experiment is money and stays
   yours. The prime-agent analysis (dropped row 28) restarts on top of this.
5. **Re-arm crons, or not.** The 8 Gastown jobs and any CronCreate revival spend
   subscription quota unattended. Recommendation: revive at most the daily PR check
   and the Monday repo sweep (now `/repo-compare`), leave the rest dead until S6
   exists properly.
6. **The second clone.** chore/delete-dolt work exists only there, and two live
   skills symlink into it. Recommendation: land or discard that branch consciously,
   then repoint the two symlinks at the WSL tree; do not delete the clone before.

## 9. What this audit did not cover

Falsifier command clauses in old claims rows were not re-run (file-existence only,
agent 1). 18 of 26 spec files were verdicted from headers plus targeted greps, not
full-text reads. The kith and gws surfaces were not audited. The 191 unexamined
saved repos remain unexamined. The Codex session store (S4) stays unmigrated. No
part of this audit ran on the Windows clone beyond git reads.
