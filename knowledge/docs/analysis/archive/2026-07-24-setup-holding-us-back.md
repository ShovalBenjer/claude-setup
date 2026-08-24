# Is the setup holding us back? Synthesis of 5 audit lanes, 2026-07-24

Point-in-time scan (docs-control-plane: `analysis/`). Synthesizes 5 adversarially
refuted audit lanes into one answer to the operator's direct question, prompted by
a screenshot of another Opus 5 user shipping a Call-of-Duty-Zombies clone in one
session via 13 named parallel teammate subagents plus a closed CDP verification
loop with an honest bug report.

Evidence classes per `rules/calibrated-claims.md`: VERIFIED = command + real output
(either pasted in a lane file, or re-run fresh in this synthesis pass, both marked).
STAGED = exists on disk, unproven live. ASSUMED = inferred, not directly tested.

Two of the five lane files this synthesis was told to read do not exist on disk.
That gap is real and is disclosed up front in section 3 and again in section 6,
not papered over.

---

## 1. VERDICT

Yes, the setup is holding him back, and it is not the model. Opus 5 is already
available and already the account's recommended lead (VERIFIED, re-checked fresh
this pass: `env | grep AGENT_TEAM` -> not set, `model` key in `~/.claude/settings.json`
-> `undefined`, meaning nothing even pins the session away from whatever the account
default already is). The single biggest cause is a **deployment and enablement gap**,
not a fleet-design gap or a verification-design gap: every mechanism the reference
run used has a fully-formed equivalent already written in this repo (23 named persona
files with correct frontmatter, a working native CDP driver, routing rules naming a
fleet skill), and none of it was ever copied, enabled, or pointed at what is real on
this machine. Three independent lanes converged on the identical root pattern without
copying from each other: real artifact in `claude-setup/`, nothing copied to where
Claude Code actually reads (`~/.claude/`), no working sync between the two, and in one
case (Agent Teams) not even a missing copy, just an unset environment variable next to
a research memo that explicitly recommended deferring it. Governance overhead is a
secondary, real cost (see the prompt-mining substitute in section 3) but it rides on
top of the same root cause: process gets written down at length while the five-minute
edits that would make it live never happen.

---

## 2. THE OBVIOUS MISTAKES, ranked by output-quality cost (most expensive first)

**1. Agent Teams, the exact mechanism the reference screenshot used, is compiled into
this binary and simply never turned on.**
Evidence: VERIFIED, `deployment-gap-audit` lane extracted the gate function directly
from the installed `claude.exe` (v2.1.219): `isAgentSwarmsEnabled` requires
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` (env var) or `--agent-teams` (CLI flag), AND a
remote feature gate `tengu_amber_flint`. Re-checked fresh this pass: `env | grep -i
AGENT_TEAM` -> no match, and grepping `~/claude-setup` finds the flag named only inside
a research memo copy-pasted into three separate archive locations, recommending
"worth deferring... experimental, behavior may change." Nobody ever flipped it.
Default teammate mode is `in-process` (not `tmux`/`iterm2`), so Windows was never the
blocker either.
Denies him: named, addressable, cross-communicating teammates (`SendMessage`,
per-teammate git worktree, idle/finished reporting) inside a single session, which is
structurally what produced the reference screenshot. Without it, "13 named parallel
teammates" cannot happen at all, at any prompt quality.
Fix: add `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` to the `env` block of
`~/.claude/settings.json`, restart the session, and attempt one real teammate spawn to
confirm the remote gate (`tengu_amber_flint`) does not also block it server-side (that
part is unverified, see section 6).

**2. 23 correctly-formed named persona subagent files exist and were never deployed to
where Claude Code reads them.**
Evidence: VERIFIED, `~/.claude/agents/` does not exist as a directory at all (`ls`
errors "No such file or directory", not "0 files"), re-confirmed fresh this pass.
`~/claude-setup/dot-claude/agents/` has 23 files, spot-checked with valid
`name:`/`tools:`/`model:` frontmatter (`mayor-opus.md`: `tools: Read, Grep, Glob, Task`,
`model: opus`; `qa-lab.md`: `tools: Read, Grep, Glob, Bash`, `model: sonnet`). Committed
in one commit (`8d2277b`, 2026-07-24, from a 12-day-old archive import) and undeployed
the entire ~3 hours since. This session's own spawned-subagent record shows
`"agentType":"Explore"`, a generic built-in type, not any Gastown persona, proving the
gap bites in practice, not just in theory.
Denies him: harness-enforced tool/model boundaries per persona (QA Lab literally cannot
reach outside `Read, Grep, Glob, Bash` when deployed; today that boundary is only
whatever a hand-typed prompt asks for and a compaction can drop), and persistent named
identity for a subagent across a run.
Fix: `mkdir -p ~/.claude/agents && cp -r ~/claude-setup/dot-claude/agents/. ~/.claude/agents/`.
Verify: `ls ~/.claude/agents | wc -l` -> 23, and the next Task-tool subagent spawn's
`agentType` should read as a named persona, not `Explore`.

**3. The registry and hive-mind routing rules are marked "Global rule. Applies to every
project and session" but are live in exactly one project.**
Evidence: VERIFIED, `~/.claude/rules/` contains exactly one file (`calibrated-claims.md`).
Neither `gastown-company-registry.md` nor `hive-mind-workflows.md` is present globally
or in either of the two other known projects (`oren-roast-hq`, `daily-deep-learning`);
the only live copy is under this one project's `.claude/rules/`, present by accident of
where this session happens to run, not by any deploy step.
Denies him: any session in any OTHER project gets zero persona/skill routing at all,
despite the header claiming universal scope. The "company" operating model exists in
exactly the one place it is being audited from.
Fix: `cp -rn ~/claude-setup/dot-claude/rules/. ~/.claude/rules/`. Verify: `ls
~/.claude/rules | wc -l` climbs from 1 toward 17, and re-run the routing hit-rate check
(below) from a session opened in a different project directory.

**4. Combined named-routing hit rate across the registry's 99 skill names and 19
persona names is 20-33%, and the persona half is flat zero.**
Evidence: VERIFIED via `comm -12` against the strict global baseline: 24/99 skill names
resolve live, 0/19 personas resolve live (because of #2). 75 skill names and all 19
persona names dispatch to nothing. Sample of misses that are not exotic corners:
`agent-team`, `qa`, `tdd`, `to-prd`, `to-issues`, `deploy-prod`.
Denies him: any "send this to Engineering Firm, owned skill tdd" instruction is a
coin-flip-or-worse on the skill side and a guaranteed miss on the persona side. A route
that fails silently looks like a decision was made when none was enforced.
Fix: downstream of #2 and #3, plus de-stubbing (#5). Re-run the same `comm`-based check
after both land as the acceptance test.

**5. 35 of 62 entries under `dot-claude/skills/` are dead one-line stub files pointing
at a WSL path, not real skill directories.**
Evidence: VERIFIED, `find ~/claude-setup/dot-claude/skills -maxdepth 1 -type f | wc -l`
-> 35 (`apify-mcp`, `cleanup-crew`, `code-simplifier`, `deep-research`, `ponytail`,
`red-team`, `watchdog`, `web-inspect`, and 27 more), each file's content is a bare WSL
filesystem path, not a directory with `SKILL.md`.
Denies him: even a perfect `cp -r` of `dot-claude/skills` into `~/.claude/skills` would
not raise the live count for these 35 names; the real directories live elsewhere
(`dot-agents/skills`, `dot-codex/skills`) and have to be resolved and substituted first.
Fix: for each stub, resolve the real directory under `dot-agents/skills` or
`dot-codex/skills`, replace the stub with a real copy, then deploy. Verify: `find
~/claude-setup/dot-claude/skills -maxdepth 1 -type f | wc -l` -> 0.

**6. The `agent-team` skill, which both the registry and `mayor-opus.md` name as the
owned invocation path for the fleet mechanism, does not exist anywhere on disk.**
Evidence: VERIFIED, checked `~/.claude/skills/` (30 entries), this project's
`.claude/skills/` (20-27 depending on lane), the current session's own available-skills
list, and both known `commands/` directories. No `agent-team` in any of them.
Denies him: even after fixes #1 and #2 land, there is no authored skill teaching Claude
how to actually invoke Agent Teams or the persona fleet as a workflow, only routing
documents that assume one exists.
Fix: author `dot-claude/skills/agent-team/SKILL.md` (a real project, not a one-liner:
it needs to teach when to spawn named teammates, how many, and a stop condition).
Verify: skill appears under `~/.claude/skills/agent-team/` and in a fresh session's
available-skills list.

**7. The CDP verification loop, the mechanism that made the reference run's bug report
credible, is dead in two different ways in two different files, while a real,
driveable Chrome instance sits unreferenced on a port neither file mentions.**
Evidence: VERIFIED, both `~/.claude/commands/cdp.md` and the project-local copy default
to `~/.codex/bin/obscura-cdp` on port 9222 (does not exist: `~/.codex/bin` errors "No
such file or directory") or an "edge" path on 9223 via `ip route` (a Linux command,
irrelevant on native Windows) launching `C:\Users\shoval.be\...` (a different machine's
username; this machine's user is `shova`). Meanwhile `curl
http://127.0.0.1:9224/json/version` returned a live, real Chrome 150 instance with a
working `webSocketDebuggerUrl`, unreferenced by either `cdp.md`. `~/.mcp.json` does not
exist; no project has an `mcpServers` entry.
Denies him: no working "build it, drive it, prove it honestly" loop, the exact
differentiator that made the reference run's report trustworthy instead of a claim.
Fix: rewrite both `cdp.md` files to target the live local port with no WSL/`ip route`
logic and no other machine's paths, and wire `new-recruit/cdp_driver.py` (already
written, 80 lines, pure Python + `websocket-client`, currently unreferenced by any
skill or command) as the actual driver. Verify: `uv run --with websocket-client python
cdp_driver.py tabs` returns a real tab list, not a connection error.

**8. The shared hardcoded CDP port (9224) races across the operator's own normal
parallel-session load, live, right now, independent of any file being stale.**
Evidence: VERIFIED, re-checked minutes apart: first check found the port live and
answering; a follow-up found `curl` refused 5/5 times while `netstat` showed 12
separate `chrome.exe` processes across 5+ distinct `--user-data-dir` values all
hardcoded to port 9224, only one of which can hold the OS-level bind at a time.
CLAUDE.md itself documents "6+ parallel Claude sessions are normal" for this operator;
that habit is what collides on this exact port.
Denies him: even after fix #7 lands, a single fixed port will keep intermittently
breaking under his own normal multi-session habit unless the port is allocated
per-session.
Fix: derive the port from `$CLAUDE_CODE_SESSION_ID` or scan for a free port in the
launcher, rather than hardcoding 9224 everywhere. This is a small project (touches the
launcher plus both `cdp.md` files), not a one-line edit.

**9. No script anywhere in the repo deploys `dot-claude/{agents,skills,rules}` into
`~/.claude/`; the only sync scripts found move state between two already-live
directories (`~/.claude` <-> `~/.codex`), and even those show no evidence of ever
having run.**
Evidence: VERIFIED, read `sync-setup.sh`, `sync-skills.sh`, `docs-sync.sh` whole; none
takes the git repo as a source or target argument. `~/.codex/skills` contains only a
`.system` subdirectory (zero populated symlinks, which is what a successful
`sync-skills.sh` run would produce); every entry in `~/.claude/skills/` is a real
directory, not a symlink. Script mtimes are all last-edit dates, and none of the 4 live
hooks call any of the three scripts.
Denies him: the operator's working assumption that a deploy mechanism exists and just
needs triggering is false; this is a missing script, not a broken one, and fixing #2/#3
manually today does not prevent the same drift from recurring on the next archive
import.
Fix: write `dot-claude/bin/deploy-setup.sh` that idempotently does #2, #3, and #5.
Verify: run it twice, confirm identical end state both times (true idempotency), then
either wire it into a hook or document it as a required first step of any session that
touches `claude-setup`.

**10. The claim-before-work anti-convergence mechanism exists in policy
(`docs/charters.md`, `state/claims.jsonl`) but had zero real usage on today's own CCC
excavation work, the exact parallel-sessions-converging pain it exists to catch.**
Evidence: VERIFIED, `state/claims.jsonl` has exactly one line, the `_seed` bootstrap
row. No claim row exists for the 16:35 or 19:13 commits that did the CCC excavation and
FleetView spec work, which happened without any claim being filed first.
Denies him: the one mechanism specifically built to stop redundant parallel work is
unproven-in-practice on the same day it should have fired for real.
Fix: add a claim-append step as the first action of any substantive session in this
repo; consider a `PreToolUse` hook nudge when editing `docs/prd` or `docs/specs`
without a matching claim row. This is a process change, not a file edit with a single
verification command.

---

## 3. WHAT HIS OWN PROMPTS PROVE

Disclosure first, per the calibrated-claims register: the task pointed at
`docs/analysis/2026-07-24-user-prompt-mining.md` and
`docs/analysis/2026-07-24-config-throttle-audit.md` as the source for this section.
**Neither file exists.** VERIFIED, re-checked twice this pass: `find
~/claude-setup/docs -iname "*2026-07-24*"` lists 7 analysis files and 2 spec files,
none named `user-prompt-mining` or `config-throttle-audit`; a repo-wide search for
`prompt-mining` or `config-throttle` in filenames returns nothing. Those two audit
lanes' output was never written to disk, or was written somewhere this search did not
reach. This section cannot honestly claim to summarize a lane that left no artifact.

What follows instead is real, dated, quoted friction pulled from
`~/.claude/projects/C--Users-shova/memory/feedback_*.md` (his own words, from actual
past sessions, with session ids), independently found this pass while confirming the
missing files. It is not the intended lane's output, but it is genuine and it
corroborates the same root cause named in section 1 from a different angle: even when
this setup does produce something, its default output is documents, not working
artifacts, which is exactly what the reference screenshot's edge (a shipped game, not
a report) throws into relief.

- 2026-07-21, on a personal build going generic instead of custom: **"the plan ui
  fails on the app i wanted... custom design with custom human choices and unique ui
  that feels custom and layered"** and **"You failed me that you didnt do it on your
  own."** Same night, on the rebuild attempt: **"Its a slop merging... Even the name
  living codex you took as is. Disappointed from lack of reasoning."**
  (`feedback_excavate-before-building.md`)

- 2026-07-23, on the core SDLC complaint: **"everytime i give you context plan and you
  dont match my intent in implementing and do small patches and report done fast
  instead of looping and taking your full time."**
  (`feedback_loop-until-intent-met.md`)

- On Gastown specifically defaulting to reports over shipped work: **"i dont want only
  reports i want code implementations changing refactoring like actual websearch
  gastown."**
  (`feedback_gastown-auto-actions.md`)

Read together with section 1's verdict: the infra gap (governance written, never
deployed) and this behavioral gap (small patch, early "done", report instead of
artifact) are the same failure mode at two different layers. A setup that writes 23
persona files and never copies them is doing, at the infrastructure layer, exactly what
the sessions above complain about at the output layer: producing the artifact of
diligence (a spec, a rule, a report) and stopping short of the work that would make it
real (a `cp`, a shipped feature, a driven browser).

---

## 4. FIX ORDER, cheapest and highest-impact first

**ONE EDIT / ONE COMMAND (minutes, do these today, in this order):**

1. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` added to the `env` block of
   `~/.claude/settings.json`. Verify: open a fresh session, `env | grep AGENT_TEAM`
   shows it set; attempt one real named-teammate spawn and confirm it does not silently
   no-op (this also tests the section-6 open question about the remote gate).
2. `mkdir -p ~/.claude/agents && cp -r ~/claude-setup/dot-claude/agents/. ~/.claude/agents/`.
   Verify: `ls ~/.claude/agents | wc -l` -> 23; next subagent spawn's `agentType`
   reads as a named persona.
3. `cp -rn ~/claude-setup/dot-claude/rules/. ~/.claude/rules/`. Verify: `ls
   ~/.claude/rules | wc -l` rises from 1; open a session in a different project and
   confirm the registry loads there too.
4. Add `"model": "opus"` to `~/.claude/settings.json`, or edit `model-selection.md` to
   state the true current source of the default (pick one, both are one edit). Verify:
   `node -e` read of the key shows the value you chose.

**SMALL PROJECTS (an afternoon each, need a plan not just a command):**

5. Rewrite both `cdp.md` files to target the live local Chrome, wire
   `new-recruit/cdp_driver.py` as the actual driver, and fix the per-session port
   collision (derive from `$CLAUDE_CODE_SESSION_ID` or scan for free). Verify: `uv run
   --with websocket-client python cdp_driver.py tabs` returns a real tab list under
   normal 3+ parallel session load, not a connection error.
6. De-stub the 35 dead WSL-path files in `dot-claude/skills` against their real
   siblings in `dot-agents/skills` / `dot-codex/skills`, then deploy the skills
   directory. Verify: re-run the `comm`-based hit-rate check from section 2.4, expect
   materially above 24%.
7. Author the missing `agent-team` skill so the registry's own routing reference
   resolves to something real. Verify: it appears in a fresh session's available-skills
   list.

**STANDING PROJECTS (process changes, no single verification command closes them):**

8. Write `dot-claude/bin/deploy-setup.sh` that idempotently performs steps 2, 3, and 6
   above, and wire it into a hook or a documented required first step, so this list
   does not need to be re-run by hand after the next archive import.
9. Make the claim-before-work step (`state/claims.jsonl`) an actual habit or a hook
   nudge, not policy prose, so the next same-day duplicate-work incident (section 2.10)
   does not repeat.
10. Given section 3's substitute evidence: for autonomous/nightly runs specifically,
    require an explicit acceptance checklist extracted from the plan up front, and
    block a "done" report that has no corresponding code/artifact diff. This is a
    behavioral enforcement change layered on existing rules (Forge Loop, calibrated
    claims), not a new file.

---

## 5. CHECKED AND DISMISSED

- Registry/hive-mind marked "Global rule" but live in one project: the file-scope facts
  hold; the "mistake" framing did not survive on its own (folded into section 2's item
  #3 instead, where it does hold as part of the routing gap).
- `mcpServers` unconfigured everywhere: config facts reproduce, but framed as an
  intentional documented policy with a working substitute already in place, not a
  mistake distinguishing this setup from the reference run.
- Target output file (this doc's slot) already existed before this pass: file-existence
  facts checked out but described no actionable mistake, and part of its own supporting
  evidence was wrong.
- "This exact CCC excavation was already done today" as a fresh finding: mostly true on
  the facts (two real commits exist) but the specific acceptance-checklist claim built
  on top of it did not hold.
- CCC's Windows support being foreground-PowerShell-only, framed as a gap in Shoval's
  setup: the technical facts hold, but it is a restatement of Shoval's own existing spec
  conclusion, not a new mistake.
- PRD row AUTO-19 referencing a nonexistent "tower" ancestor: did not reproduce; `find`
  for `tower` returns 3 real hits including a 506-line committed `tower.py`.
- Shared CDP port 9224 collision "right now, today": the specific repro cited did not
  reproduce on re-check (port answered live 5/5); a separate, later re-check did catch a
  real collision (kept as section 2 item #8), but the original claim's specific evidence
  was stale at the moment it was written.
- A working native CDP driver "wired into nothing": false: `cdp_driver.py` is imported
  and called for real actions by 2 files in `hiring_engine/`, 6 files total reference
  it.
- A `cdp` skill with real recent usage but unlocatable source: the usage facts hold
  (`skillUsage.cdp` shows a real 2026-07-20 use) but "unlocatable" was not a mistake in
  the setup, just a search that ran out of time; not enough to stand as a finding.

---

## 6. OPEN / UNKNOWN

- **The two named prompt-mining and config-throttle lane files do not exist anywhere in
  the repo.** VERIFIED absent by direct search; not established whether that work was
  ever actually run, or was run and its output lost/never saved, or was misnamed. This
  synthesis substituted real memory-file quotes for section 3, but that is not the same
  evidence base the task asked for, and the config-throttle angle (whatever it was
  meant to audit, likely model/rate-limit throttling behavior) has no substitute at all
  in this pass.
- Whether the remote feature gate `tengu_amber_flint` would actually allow Agent Teams
  to activate even after the env var is set. ASSUMED unclear; the lane that found the
  gate function did not test a live spawn end to end.
- Whether `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5` (the global cost-control setting)
  would silently override an explicit `model: opus` in a deployed persona's frontmatter.
  ASSUMED unclear, flagged but not tested by any lane.
- Whether deploying `dot-claude/{agents,rules}` globally would alter behavior in the
  other two known projects (`oren-roast-hq`, `daily-deep-learning`) in a way the
  operator would not want. Believed low-risk (additive per the Authorization rule) but
  not verified against either project's existing local rules for conflicts.
- Whether the `cdp` skill with real 2026-07-20 usage (per `skillUsage` in
  `~/.claude.json`) already reaches CDP-driven verification parity with the reference
  run's "60+ scripted checks." Its source file could not be located in the time budget
  of the lane that flagged it; unresolved, not just unmeasured.
- Whether any of the 3 other project-local `.playwright-mcp` output directories found
  under `new-recruit/projects/*` have a live, working `mcpServers` entry today, which
  would mean a working CDP path already exists somewhere in this account's history and
  only needs pointing at `new-recruit` rather than building fresh. Not opened in any
  lane.
