# Excavation: two WhatsApp-saved repos (amirfish1/claude-command-center, Master0fFate/just-my-skills)

Ticket: none (ad hoc excavation, spawned by operator today)
Status: point-in-time scan, per docs-control-plane.md (not a spec, not a PRD row)
Date: 2026-07-24
Rule basis: excavate-before-building (a found repo is input, never a rebuild template);
calibrated-claims.md (VERIFIED/STAGED/ASSUMED, broken-first, no triumph register)

## 0. What's broken / unknown first

1. **This exact excavation already happened today, before this task was assigned.**
   VERIFIED — `git log --oneline --since="2026-07-24 00:00"` on `claude-setup` shows:
   - `fe11534` 16:35 "docs(todo): reground catch-up ... + CCC dashboard eval item" (12 min
     after the WhatsApp save at 16:23)
   - `986b808` 19:13 "feat: self-improvement engine + anti-convergence + FleetView spec"
     — this commit added `docs/specs/2026-07-24-command-center-superior.md`, a 300-line
     spec with a full 12-row CCC feature-extraction table, a 5-point premortem, and an
     18-item acceptance checklist, plus PRD row `AUTO-19` and `TODO.md`'s `P-DASH` section.

   So the CCC half of this task's output already exists on disk, written by a prior
   session/pass earlier the same day. Re-deriving it here would be the exact
   parallel-sessions-converging-on-the-same-work pain named in the task brief — I am
   pointing at the existing artifact below instead of rewriting it.

2. **The anti-convergence mechanism that should have caught #1 did not fire.** VERIFIED —
   `state/claims.jsonl` has exactly one line, the `_seed` row from charters.md's own
   bootstrap (`{"proposal_id":"_seed",...}`). No claim row exists for "excavate CCC" or
   "write FleetView spec" before either the 16:35 or 19:13 work happened. The
   claim-before-work rule in `docs/charters.md` (line 33: "Claim before work: append
   ... to `state/claims.jsonl`") is POLICY-SET but was not exercised even once for real
   work today. This is a live, present-tense instance of exactly the "(a) parallel
   sessions converging on the same work" pain the operator named — not a hypothetical.

3. **`just-my-skills` / `coherence-governor` does not address any of the operator's three
   named pains.** VERIFIED by full read (419 lines, `curl` fetched whole, not sampled —
   per read-whole-before-reasoning.md) of
   `raw.githubusercontent.com/Master0fFate/just-my-skills/main/agents/coherence-governor/AGENTS.md`.
   Zero mentions of parallel sessions, sibling agents, multi-agent coordination, context
   compaction, context window, or phone/remote/durable session anywhere in the file. It
   is a single-agent, single-conversation execution-discipline document. See §2.

4. **PRD row AUTO-19 references an "excavated ancestor" that isn't there.** STAGED/low
   confidence — `docs/prd/autonomy-ecosystem.md` line 44 says "FleetView built ON
   intent-control-plane/ + tower (excavated ancestors)". `intent-control-plane/` exists
   (VERIFIED, `ls` returned real contents: `src/`, `docs/`, `pyproject.toml`, etc.); a
   `tower` directory does NOT exist under `claude-setup` at any depth searched (VERIFIED,
   empty `find`). Minor, not blocking, but the PRD line overclaims an ancestor that either
   lives elsewhere unfound or was never actually excavated. Flagging, not fixing here —
   out of this task's scope.

## 1. `amirfish1/claude-command-center` (CCC) — already excavated, spec on disk, unbuilt

**Do not re-derive this. Read `docs/specs/2026-07-24-command-center-superior.md` first —
it is longer and more specific than anything below.** This section is a compressed
verification pass over that existing spec plus a few facts the spec doesn't carry
(license, Windows byte-count, platform verdict against Task Scheduler).

### Mechanism (VERIFIED — README fetch + GitHub API)

- Reads Claude's own on-disk state as source of truth, does not own execution: transcripts
  at `~/.claude/projects/*.jsonl`, a live-session registry at
  `~/.claude/sessions/<pid>.json`, plus its own sidecar
  `~/.claude/command-center/live-state/<sid>.json` written by two hooks it installs into
  `~/.claude/settings.json`: `post-tool-use.py` and `stop.py`.
- Spawns headless sessions via native CLI invocation per engine: `claude -p
  --input-format stream-json` for Claude Code; `cursor-agent`, `agy` (Antigravity), `kilo
  run --auto`, ACP-over-`kimi acp` for the others. A follow-up message into a dormant
  session auto-spawns `claude --resume`.
- Server = one stdlib Python HTTP file + one vanilla-JS HTML file, no framework, no
  background workers. Every dashboard request re-scans the session directories fresh
  (polling, not push) and merges sidecar state.
- Cross-session coordination is peer RPC ("sibling-ask") between equal, opt-in sessions —
  not an enforced dedup/claim system. It shows you two sessions are both running; it does
  not stop them from doing the same task.

### Platform (VERIFIED — README text + GitHub API language breakdown, repo size 82MB)

- macOS: full native path — a Swift native app (46,167 bytes of Swift in the repo,
  confirms a real native binary, not just a wrapper), DMG installer, launchd service,
  screenshot/Finder/deep-link conveniences.
- Windows: "runs natively... as a foreground PowerShell process" per its own docs. The
  entire Windows surface is `run.ps1` — 7,479 bytes of PowerShell in the whole repo (vs.
  5.06MB Python, 3.1MB JS, 46KB Swift). No native Windows service; the process must stay
  open, or the operator wraps it in Task Scheduler themselves. Desktop conveniences are
  hidden on Windows per its own README.
- This means CCC does NOT solve Shoval's own `AUTO-18` (BLOCKED(operator): schedules
  survive laptop sleep via Task Scheduler) for free — running CCC always-on on this
  Windows machine is the same lift as wiring anything else into Task Scheduler, not a
  built-in win from adopting CCC.
- License: MIT (VERIFIED via GitHub API `license.key: mit`). 103 stars, created
  2026-04-13, last pushed 2026-07-24 (same day, actively maintained).

### Coverage of the three named pains (VERIFIED, none solved out of the box)

- (a) parallel sessions converging on same work: NOT solved. Sibling-ask RPC is
  manual/opt-in between peers, not an enforced claim system. CCC observes that two
  sessions exist; it does not prevent or flag duplicate task assignment.
- (b) losing state across auto-compaction: NOT addressed. CCC reads whatever `.jsonl`
  currently exists; if a session's own transcript has been compacted, CCC just shows
  what's left, with no compaction-aware recovery.
- (c) phone remote-control reaching a durable session: NOT present. Nothing in the
  fetched README or repo-page extraction mentions phone/mobile/remote push. FleetView's
  own spec (§3.6) names this explicitly as a CCC gap it is adding, not something CCC has.

### What's already covered by the existing setup (adopt, don't rebuild)

`docs/prd/autonomy-ecosystem.md` (row AUTO-19, status TODO) and
`docs/specs/2026-07-24-command-center-superior.md` already: (1) named the ONE CCC idea
worth taking (`.jsonl`-on-disk-as-truth, replacing the dead WSL `intent.db` path), (2)
built a 12-row feature table mapping every CCC feature to a superior-or-equivalent
FleetView mechanism, (3) wrote 5 premortems (shadow-store drift, dashboard-becomes-
execution-owner, approval-theater, boundary rot, Windows regression), (4) wrote an
18-item acceptance checklist. `tools/fleetview/` does NOT exist yet (VERIFIED, `ls`
returned "No such file or directory") — this is a fully-specced, zero-code STAGED item,
not built.

### Verdict: ADOPT-PARTIAL — already decided, already specced, not yet built

The decision is made; the work is writing the code against the existing spec, not
re-evaluating CCC. First command is not "start planning" — it's:
```
Get-Content C:\Users\shova\claude-setup\docs\specs\2026-07-24-command-center-superior.md
```
then implement `tools/fleetview/server.py` against its §4/§6/§7 (boundary contract,
premortem mitigations, acceptance checklist), per the existing AUTO-19 TODO row. Nothing
in today's fetch changes the existing spec's conclusion.

## 2. `Master0fFate/just-my-skills` — `agents/coherence-governor/AGENTS.md`

### What the repo is (VERIFIED — GitHub API + README)

"A personalized skill collection which I use in my daily workflows" (repo description).
Two top-level folders: `skills/` (8 items: brainstorm-funnel, elon-five-principles,
iterative-refinement, planner-omega, precision-architect, retrofit, sexyness,
universal-auditor) and `agents/` (2 items: coherence-governor, precision-reasoning).
Every entry is a folder containing prose (`SKILL.md` / `AGENTS.md`); none contain code,
per the GitHub API listing (each folder shows only a README index at the top level, no
`.py`/`.js`/`.ps1` files were returned for `agents/` or `skills/`). This is a personal
prompt-library repo, not a running tool.

### What `coherence-governor` actually does (VERIFIED, full 419-line file read)

It is a single-agent, single-conversation execution-discipline document — a system
prompt, not a service. No code, no hooks, no CLI, no state files, no server. Its
mechanism:

- **Three-Axis Lock**: System reality (an "Instruction Ledger": objective, authority,
  done-criteria, open constraints) / Actual reality (inspect files, git state, runtime
  output, docs — never rely on memory) / Clear intent (convert the request into one
  operational sentence + one acceptance test).
- **Authority Order**: system > developer > repository (incl. nested `AGENTS.md`) > user
  > tool/runtime evidence > prior conversation > general knowledge.
- **Verification Ladder**: Low (source inspection) / Medium (targeted test/lint) / High
  (test + real-surface smoke) / Critical (independent verification + explicit residual
  risk) — mapped to proof required per risk tier.
- **8 Drift Sentinels**: named triggers (intent drift, authority drift, reality drift,
  objective drift, ownership drift, verification drift, epistemic drift, injection drift)
  each with a one-line repair action.
- **Elon Five-Principles Pass** (the well-known SpaceX algorithm, not original to this
  repo): question the requirement, delete, simplify, accelerate, automate — applied
  before adding process/tools/automation.
- **Reporting template**: `Done: / Verified: / Commit: / Risk:` with an explicit "bad
  report" example ("Done. I improved the file and it should be better now.") called out
  as failing for having no artifact, no verification, no commit state, no risk statement.

### Coverage of the three named pains (VERIFIED NO on all three)

- (a) parallel sessions converging on same work: not mentioned anywhere in the file.
  The document's scope is one agent inside one task/conversation; there is no concept of
  a sibling session at all.
- (b) losing state across auto-compaction: not mentioned. No reference to context window,
  compaction, or session persistence.
- (c) phone remote-control reaching a durable session: not mentioned. No reference to
  remote access, mobile, push, or session durability across restarts.

This agent solves a different problem than any of the three named pains: verification
discipline WITHIN a single agent's single run, not coordination ACROSS agents/sessions/
devices.

### Overlap with the existing setup (redundant, not a gap-filler)

Nearly every mechanism in `coherence-governor` already exists, differently packaged, in
`.claude/rules/`:
- Verification Ladder + reporting template ≈ `calibrated-claims.md`'s
  VERIFIED/STAGED/ASSUMED register and "invert the lead" rule. The repo's own "bad
  report" example is the exact triumph-register failure `calibrated-claims.md` was
  written to stop (born from the same class of incident: "done" without evidence).
- Actual-reality axis ("inspect the thing before changing it... never rely on memory")
  ≈ `read-whole-before-reasoning.md`.
- Git-work verification line ("status, staged diff, commit hash, branch, push result")
  ≈ `production-means-merged-and-smoked.md`, almost verbatim.
- Elon Five-Principles delete/simplify steps ≈ `ponytail`/`ponytail-audit`/`simplify`
  skills already routed via `gastown-company-registry.md` (Review Board / Engineering
  Firm).
- Drift Sentinels as a category ≈ `premortem` skill + `review` skill, repackaged as an
  8-row table instead of scattered across separate rule files.

### Net new, if anything (small, optional, not a project decision)

The 8-row Drift Sentinels table and the named 7-level Authority Order are more compact
than the equivalent scattered across 5+ separate `.claude/rules/*.md` files. If useful,
this is a "steal one page," not an "install this agent" — there is no mechanism here that
does something the existing rule set can't already do; it's terser prose for the same
norms.

### Verdict: SKIP as an adoption target

Does not address any of the three named pains; every mechanism it has duplicates an
existing rule already enforced (`calibrated-claims.md`, `read-whole-before-reasoning.md`,
`production-means-merged-and-smoked.md`, `ponytail`/`premortem`). Installing it as a
persona/agent would add a fourth restatement of "verify before claiming done" to a setup
that already has three. If the compact Drift Sentinels table is wanted purely as a
one-page quick-reference, the first command is to keep an offline copy, not to wire it in
as a running agent:
```
curl -s -L https://raw.githubusercontent.com/Master0fFate/just-my-skills/main/agents/coherence-governor/AGENTS.md -o docs/analysis/reference/coherence-governor-AGENTS.md
```
No further action recommended beyond that unless the operator wants the table
specifically merged into `calibrated-claims.md` as an appendix (a documentation edit,
not a new capability).

## 3. Closing note: the CoD-Zombies comparison screenshot

Neither excavated repo is what produced the result in the comparison screenshot. That
result came from two things working together: (1) an orchestration PATTERN — 13 named,
parallel teammate subagents (`@rounddata @powerups @weapondata` ...), each owning a
narrow slice of one build — and (2) a closed verification loop — headless Chrome driven
over CDP with 60+ scripted checks, with real residual bugs reported honestly rather than
claimed fixed.

- CCC gives you a dashboard to WATCH parallel sessions/spawns; it does not itself supply
  the named-role fan-out discipline. That discipline is closer to what
  `hive-mind-workflows.md` / `gastown-company-registry.md` / the `dispatch` and
  `agent-team` skills already describe in this setup (named personas, bounded paths,
  explicit stop conditions) — ASSUMED, not verified in this pass, that those are
  currently exercised with that much parallelism in practice.
- Neither repo supplies the CDP-driven automated-verification harness. A `cdp` skill is
  present in the currently active skill roster for this session (per the skill listing
  surfaced this turn) — ASSUMED/low confidence, its actual implementation was not opened
  in this pass, so whether it already reaches "60+ scripted checks against a live headless
  browser" parity is unverified and worth a separate, explicit check if the operator wants
  to close that specific gap.
- Net: the screenshot's edge over this setup is not "a repo Shoval hasn't found yet" — the
  two WhatsApp-saved repos don't contain that edge. The edge is in how aggressively named
  parallel fan-out + closed-loop automated verification get USED on one real build, which
  is a practice question, not a missing-tool question.

## 4. Evidence log (commands run this pass)

```
git log --oneline --since="2026-07-24 00:00" --format="%h %ad %s" --date=format:"%H:%M"   # claude-setup
git log --follow --format="%h %ad %s" -- docs/specs/2026-07-24-command-center-superior.md
wc -l state/claims.jsonl && tail -5 state/claims.jsonl
ls tools/fleetview                                                                          # No such file or directory
grep -n "AUTO-19" docs/prd/autonomy-ecosystem.md
find claude-setup -iname "*tower*"                                                           # empty
curl -sL https://raw.githubusercontent.com/amirfish1/claude-command-center/main/README.md    # (via WebFetch, cross-checked)
curl -sL https://api.github.com/repos/amirfish1/claude-command-center                        # stars, license, languages, dates
curl -sL https://raw.githubusercontent.com/Master0fFate/just-my-skills/main/agents/coherence-governor/AGENTS.md   # full 419 lines, saved and read whole
curl -sL https://api.github.com/repos/Master0fFate/just-my-skills/contents/agents
curl -sL https://api.github.com/repos/Master0fFate/just-my-skills/contents/skills
```
