# TODO: Claude OS

One TODO, grouped by layer, ticket-tagged (SETUP-OS + AUTO). Status mirrors
docs/prd/claude-os.md and docs/prd/autonomy-ecosystem.md. Fresh session? Read
docs/SESSION-BOOT.md first.

Read `docs/PLAN-SPINE.md` before picking up cross-surface work: it is the one
page connecting PRD to spec to current/next slice to ticket to % built, for
harness-gate, autonomy/AUTO, dashboard/DASH, voice/VOICE,
interpretability/Modal, persona-economy, intent-lifecycle, slm-swarm, and
kanban. Written 2026-08-17 glue pass, after a sweep found 26 planning docs
split BUILT 2 / PARTIAL 11 / PAPER 13 and no single spine.

## INV: unfinished-work inventory (docs/analysis/2026-08-15-unfinished-work-inventory.md)

- [ ] INV-1 Execute the phased waterfall in
  `docs/analysis/2026-08-15-unfinished-work-inventory.md` (Phase 0 operator decisions
  first; Phase 2 quick hygiene is agent-doable).

## FOG: what a file-by-file sweep found that no status marker reported (2026-08-01)

- [ ] **A secret reached a pushed commit and only the operator can finish removing it.**
  `docs/analysis/2026-08-10-inbox-secret-exposure.md` records what leaked, why deleting the
  file from HEAD does not remove it from the history that was already pushed, and the
  rotation plus history-rewrite that does. No commit can close this row; it is here because
  an analysis nothing links to is an analysis nobody reads, which is how the finding would
  be lost a second time.

Every row here was produced by opening the file or calling the API, not by reading a
PASS. Ordered by how badly the recorded status disagreed with the disk.

- [x] **CLOSED 2026-08-12: the operator rotated the ElevenLabs key** ("the elevenlabs
  key - replaced drop that issue", his words, recorded in this session's claim row).
  The exposed value in `e695af5`/`gh/main` history is now dead credential; no history
  rewrite needed. Evidence class: operator assertion, not independently verified
  against the ElevenLabs dashboard. Original row kept below for the record.
  2026-08-10.
  `docs/inbox-from-new-recruit/` is an untracked drop of another repository's tree, 74
  files, placed here for reading by something that was not the session that committed it.
  A `git add -A` swept it into `e695af5`, 83 files where the real diff was one Rust file,
  and the push went out before the gate ran.
  `docs/inbox-from-new-recruit/.claude/bin/elevenlabs-mcp-launcher.sh:9` assigns an
  ElevenLabs key. The tree is now untracked and gitignored, which removes it from HEAD and
  **does not remove it from `e695af5`**, which is on GitHub. A commit that deletes a file
  is not a redaction. **Rotate the key.** That works whatever git does next; a history
  rewrite plus force push does not, if anything already fetched the branch, and force push
  is denied to the assistant on purpose. Full write-up, including the ordering defect that
  let a push precede its gate:
  `docs/analysis/2026-08-10-inbox-secret-exposure.md`.
  **Escalated, measured 2026-08-11: `git branch -r --contains e695af5` now lists `gh/main`,
  so the value is in the default branch's history, not just a lane branch. The carrying
  branch was merged after the write-up was written. Rotation is now the only sane close;
  see L-2026-08-11-b.**

- [ ] **Read `docs/analysis/2026-08-12-plain-handoff.md` first: the plain-language
  entry point the operator asked for.** Written 2026-08-12 on his instruction ("write
  me full file of what you did what issues you did whats left to do ... note that
  everything you did here i dont understand"). One self-contained file: what both
  days did, every issue including the assistant's own, the full paper-vs-built
  inventory, and the seven items only he can move. Passes the explain-simply checker
  (`plain.py check`, exit 0) and slop_lint. Supersedes nothing; it points at the
  audit and the plan rather than replacing them.

- [ ] **The open-model and scheduling plan waits on five operator blocks (A to E).**
  Written 2026-08-12 on instruction ("tell me the plan how we do it ... oracle/aws free
  tiers first" and "regarding local and remote crons, tell me the full suggestion").
  `docs/specs/2026-08-12-open-model-and-scheduling-plan.md`: DeepSeek-V4-Flash-0731 as
  the API workhorse lane, Qwen3.6-35B-A3B on an OCI A1 box as the self-host lane,
  AgentWorld correctly reclassified as the training simulator, no monthly GPU
  subscription (on-demand bursts instead), and the 8 dead Gastown crons dispositioned
  revive-3 / fold-3 / retire-2 across systemd and cloud routines. Time-sensitive:
  OCI terminates over-limit Always Free A1 instances on or after 2026-08-18.

- [ ] **The 2026-08-11 estate audit is the current state of everything; read it before
  trusting any older status row.** Ordered by the operator, upset, banning convergence
  numbers. `docs/analysis/2026-08-11-estate-audit.md`: specs BUILT 2 / PARTIAL 11 /
  PAPER 13; Gastown crons dead since 2026-06-03; agent feed dead 5 days on a `--sink`
  flag mismatch, repaired and posting again; all 7 hiring arms unapproved since
  2026-07-27 by the operator's own withdrawal; external judges near-unused (codex-call
  1 of 61 skill-use rows); the twice-dropped repo comparison now lives as the
  `repo-compare` skill with its first run in `docs/analysis/2026-08-11-repo-compare.md`.
  Six operator decisions wait at its section 8.

One index over all of it, milestone-ordered and reconciled against the Zion board, the 6
unmerged PRs and the specs: [docs/analysis/2026-08-11-milestone-task-plan.md](analysis/2026-08-11-milestone-task-plan.md)
(supersedes the 2026-08-10 version).
It carries the nine operator decisions that block agent work and a PR triage with merge
order. Deliberately NOT added as a `- [ ]` row: the boot surface holds six and displacing
one of them to make room for a pointer is the wrong trade.

- [ ] **90 of 96 open TODO items are invisible at session boot, and this row exists to say so.**
  Measured 2026-08-05. `~/.claude/hooks/session-recall.sh:112` selects
  `l.strip().startswith("- [ ]")` and slices `[:6]`. TODO.md carries **96** matching rows,
  so **six reach a new session and ninety do not.** The cap is deliberate and correct
  ("a wall of history is the same as no history"); what is not correct is that nothing
  orders the file, so which six survive is an accident of line number. Two of the six
  were findings refuted on 2026-08-04 and had been injected into every session since.
  **The fix is ordering, not raising the cap**: the first six rows under FOG are the
  boot surface and must be the six things a fresh session most needs, re-picked whenever
  one closes. A second, cheaper fix: recall could prefer rows carrying a marker such as
  `[boot]`, which is a four-character change to the hook's predicate.
  **Also measured: rows written as `- **` instead of `- [ ]` are invisible entirely.**
  Ten rows added during the 2026-08-03/04 session had that defect and are corrected below.
  **Re-measured 2026-08-08: the count is now 133 open rows, not 96, and the row directly
  below this one had sat on the boot surface for two days after it was done.** Both
  numbers in this row's own title were stale, which is the failure it describes eating
  itself. The five rows under it are now re-picked by usefulness rather than by line
  number, and closing one means promoting the next, not leaving the hole.

- [ ] **The loop may ACT, and the five open items now have named owners.** Operator
  decision 2026-08-10, one word: "act". The boundary it does NOT carry is written beside
  it in `~/.claude/rules/the-loop-may-act.md`, because a one-word answer to a binary
  question is a decision without a scope, and the last time a general instruction was
  read as standing authority a PR got merged on green CI. The loop may gate, regenerate,
  fix red checks, push its own branch, open a PR, append ledgers, write analysis. It may
  not merge, deploy, post outward, silently change the live tree, delete what it did not
  create, or spend money. Who works what, in what order, and which items collide:
  `docs/specs/2026-08-10-open-scope-delegation-plan.md`. Item 3, the four DIRTY PRs, is
  deliberately last and needs a call on whether those drafts survive at all.

- [ ] **Verbatim prompt capture has been dead since the WSL move, and the hook that does
  it swallows the failure on purpose.** Measured 2026-08-10. Two capture paths exist and
  only one works. `state/prompt-tickets.jsonl` holds 494 rows and is healthy, but it
  stores hashes and no text by design. The path that holds the actual words, the
  intent-control-plane enrichment into `~/.intent/intent.db`, is specced, built,
  unit-tested AND wired in the live `settings.json`, yet writes nothing on this machine:
  the hook runs plain `python3`, which cannot import `intent_control_plane`, and
  `tools/intent/capture_turn.py` catches everything so a broken hook never blocks a
  prompt. It worked before the move. `/mnt/c/Users/shova/.intent/intent.db` holds 235
  verbatim prompts, last written 2026-07-31, and nothing since. Anthropic's own
  transcripts (1218 files, 831 MB, unbroken) are the reason this was invisible: the
  prompts ARE stored, just not by anything this repo can query. `ecosystem.db` and
  `corpus.db` are both confirmed absent. GraphRAG is neither built nor planned; the
  planned retrieval is flat FTS5 plus brute-force cosine, status OPEN.

- [ ] **The skills oracle reads one of three trees and reports the other two as drift.**
  Measured 2026-08-10 in `docs/analysis/2026-08-10-three-skill-trees-measured.md`, while
  executing the approved `dot-codex` split. `skills_sync.py` compares `dot-claude/skills`
  against the live tree and nothing else. Comparing by sha1 instead: 13 of the 28
  `dot-codex/skills` directories are byte-identical to live, and `shoval-voice-draft`
  matches live EXACTLY while `dot-claude` carries a different 27401-byte version. The
  waiver has been calling that a genuine fork where whichever side you read is a coin
  flip; it is not, the live file is committed in the tree the oracle does not read.
  Fifteen of the sixteen drift items are downstream of the oracle's scope rather than of
  anything anyone did wrong. Extending it to read all three would shrink the number with
  no file moving, and that is a decision about what an oracle asserts, not a cleanup.
  The split itself went ahead narrower than recommended: the 33 dead one-line pointers
  are gone, the 28 directories stay, because archiving them would have deleted the only
  committed copy of a live skill.

- [ ] **Live `~/.claude/skills` went from 40 to 79 in two days and nothing can date or
  attribute it.** Measured 2026-08-08 by `ls -1d ~/.claude/skills/*/ | wc -l` against the
  40 recorded on 2026-08-05 in row B below. All three repo tree counts reproduce within
  one, so the change is isolated to the one tree that is not under version control.
  `state/snapshots` holds a single manifest from 2026-07-25 and does not span the gap.
  A deploy of roughly 30 skills is the standing hypothesis, from mtimes at 15:12, 17:02
  and 17:38 on 2026-08-06, but no script in the repo copies the tree that would explain
  the 8 skills whose only repo copy is under `dot-agents`. **This is the loudest
  unexplained number in the repository and it governs every skills count below it.**

- [ ] **Three top-level directories are waiting on an operator call, and the report for
  them exists.** `docs/analysis/2026-08-07-toplevel-dir-decisions.md`, measured at
  f88d3a3. `dot-agents`: no live `~/.agents` anywhere and 6 commits ever, but 8 skills in
  `~/.claude` have their only repo copy there and no script in the repo deploys it.
  `dot-codex`: the Codex host is live and its `skills/` directory exists and is empty,
  which reads identically as "deploy never ran" and "payload abandoned", and archiving
  takes out the only copy of 10 differing bodies. `intent-control-plane` versus `tools`:
  keeping the boundary preserves ruff and mypy over 116 files with 4 commits ever while
  leaving 138 files with 56 commits unchecked, and the boundary is nominal anyway since
  all 6 external consumers reach the package through `sys.path.insert` rather than the
  wheel it declares. The clear calls in the same report (archive `home-dotfiles` and
  `startup-scripts`, merge `master-plans` into `work-docs`) are not blocked on anything.

- [ ] **The full open scope, one row per instruction, is in
  `docs/analysis/2026-08-09-session-scope-ledger.md`.** Written 2026-08-09 on request. It
  accounts for every prompt of the 2026-08-07 to 2026-08-09 session in the order given, so
  an unanswered instruction stays visible instead of dissolving into the next one. The
  finding that matters: **one instruction was under-served**, "the autonomous workflows
  should be done", said twice, and the pieces for it are all on disk and unassembled.
  `state/` carries fourteen ledgers, `tools/telemetry` publishes a cross-repo feed to issue
  #38, `tools/selfimprove/scan.py` ranks what to pick up next, and cron scheduling exists.
  Nothing joins them. The scoping question is the operator's and gates the item: whether an
  autonomous loop should PROPOSE or ACT. A loop that opens PRs nobody reads repeats the
  agent feed's own open question, which is still "watch whether anything ever ACTS on an
  issue #38 item".

- [ ] **The connector catalogue was reasoned over and the answer for this repo is zero.**
  `docs/analysis/archive/2026-08-08-connector-catalogue-reasoning.md`, 2026-08-08. claude-setup
  verifies its own hooks, oracles and gate and has no external data domain, so no connector
  earns a place here. Recommended elsewhere, one each and all ASSUMED on auth cost: Google
  Calendar for new-recruit, Cloudflare and Coursera for daily-deep-learning, Canva for lane
  D. **It corrected this session's own earlier claim:** the connector-usage analysis called
  the `Indeed` board "plausibly on-topic" for new-recruit without having read that project's
  PRD, which locks a hard constraint of keyless public ATS JSON, no browser, no login, no
  ban surface. So `Dice`, `ZipRecruiter` and that one are do-not-add rather than candidates.
  A note on the linter found while writing this row: `slop_lint.py` flags a line that BEGINS
  with the word Indeed as a ritual opener, which is correct for the adverb and wrong for the
  job board of that name. Rewrapping the line fixes it and the check was left alone, but a
  proper noun colliding with a banned phrase is worth knowing before it bites a real doc.
  Gmail stays off
  despite being topically plausible: zero calls in 1183 sessions against full-mailbox OAuth
  scope is a real PII exposure, and it is flagged as an open decision rather than a default.
  Zapier is not a force multiplier here: lane D's own `syndication-engine` already does the
  cross-posting job in a gate-covered way a zap is not.

- [ ] **Zion has 31 epics and the board is not the thing other projects inherit.**
  `docs/analysis/archive/2026-08-08-zion-and-inheritance.md`, 2026-08-08. Documents what actually
  crosses from claude-setup to the other repos and by what mechanism, which turns out to be
  `tools/harness/harness.py exec <relpath>` resolved through `$CLAUDE_HARNESS`, then a
  `.harness-ref` file at the consuming project's root, then a vendored fallback. That
  resolution order is currently documented only in `new-recruit/tools/harness.py`'s own
  docstring, which means the inheritance path for a NEW project lives in a downstream copy
  rather than in the upstream it inherits from. The report carries drafted board text that
  is deliberately unposted: posting to a shared board is outward-facing and needs a
  per-action approval.

- [ ] **The `perf` N/A said no number existed anywhere, and one had been written six days
  after it.** Re-checked 2026-08-08 in `docs/analysis/2026-08-08-na-domains-rechecked.md`.
  The `unit` domain's `_timeout_note` sets 900s with an explicit falsifier at 600s, and
  `state/gate-runs.jsonl` carried no duration field across 8571 rows, so that falsifier
  had never been evaluable. Runs now record `duration_seconds` and `domain_seconds`.
  **The open half is the operator's:** whether `perf` becomes a real domain measuring the
  gate's own wall clock and hook latency, or stays N/A with corrected wording. The same
  report keeps `e2e` and `a11y_ux` at N/A and gives the reason, which is that the e2e
  instrument is not idle at all: it drives daily-deep-learning's real served app and finds
  real WCAG failures there. Also found and unwired: `intent-control-plane/repo_health.py`
  enforces file, function and class LOC budgets and is referenced by no script, no gate
  domain and no CI job.

- [ ] **Nine connected connectors have never been called once, and two other lanes
  inherit all of them.** Measured 2026-08-08 in
  `docs/analysis/archive/2026-08-08-connector-usage.md` by counting assistant `tool_use`
  blocks across 1183 transcripts, which only became possible once the session store
  was migrated the same day. Never called: Semrush, SNOMED CT, ICD-10 Codes, Clinical
  Trials, Gmail, Medidata, Mobbin, Indeed, Zapier. `claude-setup`'s
  `disabledMcpServers` is wired from 3 to 10. **The open half is cross-lane and stays a
  proposal:** `new-recruit` and `daily-deep-learning` both have an EMPTY disable list,
  so they inherit every medical connector for no reason, and new-recruit is the one
  project where Indeed is plausibly on topic. Whoever owns those lanes decides.
  Do not add connectors from the ~850 directory before this pruning lands: nine
  unused ones already make the hit rate worse than the list length suggests.

- [ ] **`skills_sync.py` has no mutation spec, and now it has a guard worth breaking.**
  Opened 2026-08-10. `tools/audit/mutations/` holds 14 specs and none of them is skills.
  The tool has a selftest, CI runs it, and nothing has ever proven that selftest can go
  red, which is the exact condition `mutate.py` exists to detect and which codemap was in
  until 2026-07-27. The host-shape guard landed the same day with three layers rather than
  four: check, selftest case, pytest, no mutation. First mutations to write are the two
  that matter, the guard keying on the directory again and `is_deployed_home` returning a
  constant, both of which were run by hand against the new tests and both of which the
  tests caught.
- [ ] **`dot-claude/bin/self-improve.py:27` is a live broken consumer.** It inserts
  `$HOME/projects/intent-control-plane/src` on `sys.path` before importing
  `intent_control_plane.harness`, and `/home/shov/projects` does not exist. Its sibling
  `tools/bus/backfill_session_telemetry.py` uses a repo-relative path and resolves. Same
  class as the PostToolUse hook fixed on 2026-08-08: wired, absent, silent. Now findable,
  since the `pointers` domain reads the live settings from that date.

- [ ] **Nothing enforces the coding-style standard on `tools/`, which is most of the
  repo's code.** Measured 2026-08-07. The `types` domain is
  `compileall -q ... . && cd intent-control-plane && uv run ruff check . && uv run mypy`,
  so repo-wide it checks syntax only and ruff plus mypy see one subdirectory.
  `./intent-control-plane/pyproject.toml` is the only pyproject in the tree. Separately,
  no rule in the house selection `PERF,C4,SIM,PIE,ERA,D` catches a prose comment, so rule
  3 of `intent-control-plane/docs/specs/2026-07-12-coding-style-standard.md`, comments
  near-zero and the one most often broken, has no oracle anywhere. Extending the scope
  will surface a backlog: 59 errors in `tools/gate/gate.py` alone before this session
  touched it, so it ships with a waiver carrying a real number and a burn-down.

- [x] **CI has been red on every run and nothing says so.** `gh run list` returns four Ship gate runs, all `failure`, none referenced in any ledger, doc, or issue. The `gate` job's cause is one missing dependency: it runs `pip install "uv==0.9.4"` and never installs pytest, so the contract's `unit` domain reports `No module named pytest` and the gate reports `unit FAIL`. That reads like a test regression and is not one. FIXED in this pass by adding pytest to that step; UNVERIFIED until a run goes green, because a local gate PASS is not evidence about the runner. Zion #20's first item, "observe one real CI run", is not undone. It happened four times and nobody looked
  **CLOSED 2026-08-04 by re-measurement, and it was closed by drift, not by anyone reading it.** `gh run list` now shows Ship gate **success on `main` 2026-08-03**. What fails is two lane branches: `lane-a/config-incident-and-oracle-repair` (08-03) and `lane-a/panel-comment-strip` (08-04 12:52, Ship gate + Claude Code Review, still open). The pytest fix landed. **The successor row is the branch, not the workflow.**
- [x] **The mutation control is red on `bus.py` and the two survivors are both the lock.** `mutate.py --spec all` reports 12 of 13 specs at 0 survived and `spec bus: 23 of 23 applied, 21 caught, 2 survived`. The survivors are `append_row stops taking the lock` and `the lock is released before the write instead of after`. So the file's own selftest cannot tell a locked append from an unlocked one, on the one ledger the repo treats as tamper-evident and reads with `bus.py verify`. There is no `tests/test_bus*.py` at all
  **CLOSED 2026-08-04.** `python tools/audit/mutate.py --spec bus` now reports **23 of 23 applied, 23 caught, 0 survived**. Both lock survivors are gone. Consequence recorded in `docs/adr/0021-rust-for-hot-paths-python-for-oracles.md`: the ADR named `bus.py` as its first rewrite candidate on the strength of these two survivors, so **that rewrite's evidence is now historical**.
- [x] **and the obvious fix for it would be a test that cannot fail here.** `append_row`'s docstring states the lock exists because overlapping writes "on Windows destroy whole rows rather than tearing them". On Linux `O_APPEND` makes a small append atomic, so a concurrency test written on this machine stays green with the lock deleted. Writing one would be L-2026-07-31-e (scope drifting to whatever goes green) sitting on top of L-2026-07-31-g (a host-shaped oracle answering the wrong question on the other host). CLOSED 2026-08-01 by the structural option, not the Windows leg: `bus.py selftest` now parses its own `__file__` with `ast` and asserts every write in `append_row` is lexically inside the `with file_lock(...)` block. Reading `__file__` is what makes it work under mutation, since `mutate.py` runs a mutated COPY and the parse therefore sees the mutant. Evidence, from the control rather than from this row: `spec bus: 23 of 23 applied, 23 caught, 0 survived`, previously 21 caught / 2 survived. `tests/test_bus_lock.py` pins the same property in pytest with a fourth case asserting the structural check itself can go red, since a helper that silently stops matching would make the other three pass on any input. WHAT THIS STILL DOES NOT DO: it cannot prove the lock excludes a concurrent writer, which no test on Linux can. A Windows CI leg remains the only way to test the behaviour rather than the structure
- [x] **A. `skills_sync.py check` exists, CI runs only its selftest, and the check exits 0 while reporting drift.**
  Measured 2026-08-05. `.github/workflows/ship-gate.yml:239` runs `skills_sync.py selftest`
  and never `skills_sync.py check`. Run by hand, `check` prints **`DRIFT: 55 item(s) need a
  decision`** and **exits 0**, so wiring it in as-is would produce a green job reporting 55
  problems. The working pattern is one line away: the `rules` domain, added 2026-08-04,
  binds `python tools/audit/rules_sync.py check` and the gate prints `rules clean: 22
  rule(s), repo and live identical`. **Acceptance: `check` exits non-zero on drift, a
  `skills` domain in `quality-contract.json` runs it, and the gate goes red at 55 and green
  only at 0.** Same treatment for `tools/audit/pointers.py scan`. **Do this alone and first:
  until it exists, B and C produce numbers nothing enforces.**
  **CLOSED 2026-08-07 by re-measurement, and every clause of it was already stale when a
  session read it at boot.** `check` exits **1**, not 0 (`skills_sync.py:341` is
  `return 1 if bad else 0`, and the earlier reading of 0 came from piping it through
  `tail`, whose exit code it then read). A `skills` domain exists in
  `quality-contract.json` and a `pointers` domain beside it. `ship-gate.yml:260` runs
  `skills_sync.py check` with `continue-on-error` tied to the skills waiver, and
  `pointers.py scan` at :264 with no such line. The drift count is **29**, not 55.
  This row survived at the top of the boot surface for two days after it was done, which
  is the row above it (90 of 96 invisible) doing damage from the other direction: the six
  that reach a session are picked by line number, so a closed row keeps its place.
- [ ] **A2. The successor: a waiver expires but nothing checked whether it was still true.**
  Measured 2026-08-07 and half fixed the same day. The `skills` waiver ended with its own
  falsifier in prose, "expect `DRIFT: 51`, and if it prints a different number this waiver
  is stale". A gate run printed that sentence as the domain's evidence, reported WAIVED,
  and returned `VERDICT: PASS`; the checker printed `DRIFT: 29`. **Fixed:** a waiver may
  carry `confirm`, the gate runs the waived domain's command anyway and fails the domain
  if the string is gone (`confirm_waiver` in `tools/gate/gate.py`, 9 tests, 4 mutations,
  8 of 8 caught). **Still open, and it is the operator's:** 13 of the 17 repo-vs-live
  skill differences are the single line `disable-model-invocation: true`, added to the
  repo copies by `3df7704` and never deployed, so live currently auto-invokes 13 skills
  the repo says it should not. Deploying that is a live-tree behaviour change. The waiver
  expires **2026-08-12** and was deliberately not extended.
  **One correction inside this row, kept because it is the more useful half.** `grill-me`
  was written up as possible content loss, live holding 626 bytes the repo does not. The
  diff says the reverse: `3df7704` rewrote the repo copy on 2026-08-03 into a terse
  four-line brief and live still carries the older structured protocol, so the repo is
  ahead and live is stale. The byte count said which file was bigger and was read as
  saying which was current.
- [ ] **B. Three skill trees hold 45 FORKS, not 45 copies.**
  Measured 2026-08-05 by hashing every skill directory: **118 distinct names across
  `dot-agents/skills` (70), `dot-claude/skills` (74), `dot-codex/skills` (61) and live
  `~/.claude/skills` (40). 67 names appear in more than one tree: 22 byte-identical, 45
  DIVERGED.** `deep-research`, `dispatch`, `azure-runtime`, `openai-agents` and `premortem`
  are each three different files; `commit-push-pr` exists in all four. **78 skills sit in a
  repo tree and are not live; zero live skills are missing from the repo**, so live is a
  clean subset and the redundancy is entirely upstream. `dot-claude/` is canonical **by
  evidence, not preference**, because it is the only tree with a live counterpart.
  **Acceptance: one tree, and each of the 45 forks carries a recorded decision (merged,
  superseded, or archived with a reason). Picking by timestamp is not a decision** and
  destroys whatever the divergence was for.
  **Re-measured 2026-08-08 over the same four trees: the row holds and understates.**
  121 distinct names (was 118), 84 shared (was 67), 30 identical and **52 DIVERGED**
  (was 22 and 45). Restricted to real bodies present in two or more trees: 82 names, 30
  identical, 52 diverged; repo-only, 50 names, 17 identical, 33 diverged. Live is 79
  directories, not 40, and that change is the unexplained row near the top of this file.
  **One correction to the shape of the problem, not its size:** 33 of the counted forks
  in `dot-codex/skills` are one-line files naming `/home/shovalbe/`, a home directory
  that does not exist on this machine. Those are a wiring defect, not divergent content,
  and merging them merges nothing. The real fork count is smaller than 52 and the dead
  pointers are a separate, cheaper job.
- [ ] **48 definition-of-done rows exist and zero tools read them.** Measured 2026-08-04:
  `grep -rl "definition of done\|DoD" tools/` returns nothing, against 48 rows in
  `docs/prd/2026-08-03-unified-architecture.md` and
  `docs/specs/2026-08-03-detail-passes-teleology-and-creativity.md`. **Classify the 48
  before building a checker**, because some are prose and some measure things that do not
  exist yet, so the count of mechanically checkable rows is unknown and is below 48. A
  `dod.py` that reports mostly "not checkable" is another instrument that runs and says
  little.
- [ ] **`docs-control-plane` rule 1 is enforced for one field of three.** `strand.py` checks
  `Status:` and reachability. It does not check the `PRD:` / `Ticket:` header the rule
  names first: **6 of 19 specs carry one**. Rule 3 says superseded specs move to
  `docs/specs/archive/`, and **that directory does not exist**, so the rule is
  unenforceable by construction. Both are extensions to a tool that already parses every
  spec.
- [ ] **new-recruit declares a 10-domain contract and has no run ledger.** `.alint.yml`,
  `quality-contract.json`, two workflows and the full docs taxonomy (prd 3, specs 26,
  analysis 10, adr 2) are all present; `state/` holds three entries and no `gate-runs`.
  That is consistent with never having run and is NOT proof, since its contract differs
  from this repo's. **One command settles it: `gate.py run --project ../new-recruit`.**
- [ ] **C. Prior-art pass before writing a fourth unused-code checker.**
  This repo already has three hand-rolled partial ones: `pointers.py` (dead paths),
  `skills_sync.py` (repo versus live drift), `strand.py` (unreferenced documents). The
  operator named **knip**, which is the mature tool for "declared and never used" and is
  JS/TS-oriented, so it may not fit a Python and markdown estate. **Acceptance: a
  `docs/prior-art/` record comparing knip, vulture, deptry and dead against what the three
  local tools already do, with a named verdict per candidate, per ADR-0019 (adopt on
  recorded evidence).** Do not extend the local three before that record exists.
- [ ] **D. Generalise the one mechanism here that does not rot.**
  `docs/prior-art/` records carry `recheck_after` and `codemap.py prior-art` fails when one
  expires. **That is the only category in this repo with an expiry, and the only one that
  has not silently accumulated.** Everything that has (23 of 29 hooks wired nowhere, 78
  unlive skills, 6 standards bound to nothing, `atlas.py` built and wired to nothing until
  2026-08-05) shares one property: arrival created no obligation. **Acceptance: an adopted
  artifact declares who binds it and when that binding is rechecked; unbound past its date
  is a gate failure.** This is a design claim and has had no prior-art pass; run one before
  building. It is the structural answer to "how does this become mature and handled", and it
  is fourth because A, B and C are measurements it would otherwise sit on top of.
- [ ] **Two analysis documents are stranded, and both have live work behind them.**
  `docs/analysis/archive/2026-07-24-creativity-wow-gap.md` (457 lines) names the creativity and
  deliberation-texture gap and is the direct ancestor of the measured-`p_conventional`
  design in `docs/specs/2026-08-03-detail-passes-teleology-and-creativity.md` §4; nothing
  linked them until now. `docs/analysis/archive/2026-07-24-research-wiring-audit.md` designed
  `tools/selfimprove/research_sweep.py`, which is **still unbuilt** and is imbalance #8 in
  `docs/SYSTEM-MAP.md`. Found by `strand.py` on 2026-08-05, **after** fixing the bug that
  had made R2 vacuous. A hand pass on 2026-08-04 named seven stranded documents; five of
  those became referenced because this session wrote about them, and these two are what
  remains. **Do the work or supersede them; do not exempt them, because the exemption file
  is for evidence held and not maintained, and these are designs waiting on a build.**
- [ ] **Six standards were imported from other repos and are bound to nothing here.**
  Measured 2026-08-05: `docs/standards/nr-adr-0001-unified-platform-standard.md`,
  `docs/standards/nr-repo-standards-2026-07-09.md`,
  `docs/standards/nr-harness-structure-standard-2026-07-09.md`,
  `docs/standards/nr-code-quality-standard-2026-07.md`,
  `docs/standards/nr-prd-2026-07-10-platform-standard.md`,
  `docs/standards/ddl-engineering-standards-2026-07-26.md`. Each was
  referenced by **zero** files outside its own directory, and **17 of the 18 imported files
  were untracked**, so no oracle could see them at all. Fixed in this pass: tracked, moved
  from `docs/analysis/` (which the taxonomy defines as point-in-time scans) into
  `docs/standards/`, given declared statuses, and `docs/standards/` is now governed by
  `strand.py`. **What is still open is the binding itself.** `nr-harness-structure-standard`
  and `docs/standards/agentic-repo-standard.md` are two structure standards that have never
  been reconciled, and `nr-repo-standards` declares five per-project dimensions that no gate
  domain reads. Reconcile or supersede; do not leave two.
- [ ] **A branch has been failing Ship gate since 2026-08-04 12:52 and nobody has read it.**
  `lane-a/panel-comment-strip`: Ship gate FAILED, Claude Code Review FAILED, Gemini diff
  review passed. Almost certainly the other clone's session. This is the successor to the
  closed "CI red on every run" row, and it is the same shape as the lesson that produced
  that row: **a failing signal that exists and that nobody reads.** Not lane A's to fix
  blind; it needs whoever owns that branch.
- [ ] **Zion #20 says gemini-review.yml "has still never been written".** It is on disk at `.github/workflows/gemini-review.yml`, 4868 bytes, and the gate's `pipeline` domain names it among the workflows invoking `gate.py run`. Correct the issue item; do not delete it, because whether the workflow RUNS is a separate question from whether it exists
- [ ] **Zion #27 item 1 is done and unchecked.** `tools/slop_lint.py` already emits hyphen density and sentence standard deviation. What is genuinely undone is item 2: the output says `no band fitted`, so it measures and never judges. The correction to the epic is that this is now a threshold-fitting task, not a porting task
- [ ] **Zion board throughput is zero.** 31 open epics, 0 closed, 184 checklist items with 5 checked (2%). The checklists are real and specific, so this is unstarted work rather than scaffold. Worth deciding whether an epic-only board with no task issues is the surface that gets used, since nothing has ever moved on it
- [ ] **The scaffold is in the hooks tree, not the tools tree.** Measured: 1 orphan of 91 files under `tools/` (only `tools/refute/checks/portable_claims.py` is named nowhere outside its own directory). Against that, 23 of 29 `dot-claude/hooks` entries are wired nowhere in the live settings, and 12 of those are one-line pointers into `/home/shovalbe/`, a home that does not exist. If the question is what fraction is garbage, the answer differs by tree by two orders of magnitude, and the instruments are the healthy part
- [ ] **AGENTS.md was wrong about its own skills tree** and is corrected in this pass: it claimed about a dozen skill stubs, and there are 0 across 73 entries

- [ ] **`dot-claude/settings.json` describes a different machine, and no oracle checks it.**
  Measured 2026-08-06 while wiring a hook: the tracked payload carries **10 hooks, 10 of
  10 with Windows paths** (`C:\Users\shova\claude-setup\...`); the live
  `~/.claude/settings.json` carries **13 hooks, 0 with a Windows path**. The payload still
  wires `safety_gate.py`, the Python gate that `hookgate` replaced, and is missing
  `prior_art_gate.py`, `skill-usage-log.sh` and `route.py` entirely. So the committed copy
  of the harness contract is a snapshot of a host this repo no longer runs on. I nearly
  made it worse by mirroring one live Linux path into it, which would have produced a file
  correct on neither host; reverted. **`rules_sync.py` guards rules drift and
  `skills_sync.py` guards skills drift; settings has neither**, which is why this went
  unnoticed while both of those were being repaired in the same week. The fix is a third
  oracle in the same shape, and it must compare hook SETS and script basenames rather than
  paths, because the two hosts legitimately disagree about paths and only about paths.

## TELEMETRY: publish.py hardening (from Kilo review of PR #62, deferred 2026-08-12)

Operator decision 2026-08-12 (this session, verbatim intent): telemetry should be
OpenTelemetry, speced as part of the communication / A2A layer, not grown as ad-hoc
guards on publish.py. So the two rows below are stopgaps on the existing publisher;
the real work item is the spec that folds tools/telemetry into an OTel-shaped A2A
channel (spans/events over the bus and agent feed, not bespoke JSONL plus GraphQL).
That spec is a claimed lane-A session of its own under docs/specs/.

- [ ] Spec: OpenTelemetry-based telemetry as part of A2A communication; decide what
  replaces collect.py/publish.py and what maps onto bus.py. Blocks the rows below
  from growing further.
- [ ] `post_discussion()` returns `r2.returncode` without checking the second GraphQL
  call's stdout; a data-level error with exit 0 advances the cursor and drops the batch
  silently. Guard like the first call. (kilo WARNING, PR #62 thread)
- [ ] `int(cfg["discussion"])` accepts 0 and negatives; fail fast on `number < 1`.
  (kilo SUGGESTION, PR #62 thread)

## REGISTRY: census re-verification (from Kilo review of PR #64, 2026-08-12)

- [ ] The 2026-08-12 registry rewire's census (39 ghosts removed, 19 skills assigned)
  is claimed in prose only. Add a check that re-parses gastown-company-registry.md
  with hooks/route.py parse_registry and diffs against ~/.claude/skills, so a future
  rewire ships with its measurement instead of a sentence about one.

## SETUP-OS: oracle repair (opened 2026-07-31, docs/archive/HANDOFF-2026-07-31-review-oracle-repair.md)
- [x] review domain: sql-concat required a verb and a concatenation and never required SQL, so English prose ("Delete ~380 lines ... + their selftest") was a HIGH; and added_lines reported lines this branch added and then deleted. Both fixed in tools/review/panel.py, 20 pinned cases, mutate --spec panel 10/10 caught, panel 5 high -> 0 high. Waiver replaced (2026-08-12 -> 2026-08-02) recording the old reason as wrong rather than deleting it (closed 2026-07-31). **THE "0 high" HALF OF THIS ROW IS FALSIFIED, 2026-08-01.** The waiver it wrote carried its own falsifier, the falsifier was run, and `panel.py run --project .` returns CHANGES-REQUESTED with 3 high. Two are real (vendored innerHTML in dot-claude/skills/brainstorming/scripts/helper.js:57,59) and one is the comment-matching mechanism this row claimed was eliminated, still live in a different check. The two fixes landed; the generalisation did not, and the row said otherwise. Waiver text corrected in quality-contract.json rather than the number being chased
- [ ] slop_lint measures the ruled form, not the property (L-2026-07-31-b). It passes prose that reads as machine written: zero em dashes but 2.8% hyphen compounds and sentence stdev 14.8. Port a density + variance check from ~/.claude/skills/voice-metrics/voice_score.py into tools/slop_lint.py, thresholds FITTED against the operator's corpus, not guessed. Until then a clean slop_lint is not evidence
- [ ] review domain goes PASS only against a committed tree, so the waiver cannot be deleted until this branch is committed. Decide: commit chore/delete-dolt, or let the 2026-08-02 expiry force it
- [ ] panel.py architecture, deferred not done: run_local sees one diff line with no file context, which is why comment and docstring matches were plausible as a theory for three renewals. drop_stale_lines closes the reported cases; a token-aware pass (skip comment and string tokens per language) is the general fix and is an oracle edit needing its own approval. **NOW HAS A NAMED INSTANCE, 2026-08-01:** `py-shell-true` fires on tools/map/codemap.py:66, whose matched line begins with `#` and quotes `subprocess.run("git " + args, shell=True)` inside a comment explaining why that form is NOT used. So the theory that was wrong for sql-concat is correct here, in a different check, and the deferred token-aware pass is the fix for it. Regression oracle to write first: the same string as a comment is CLEAN and as code is a HIT, in one file
- [ ] `~/.config/kitty/kitty.conf` is untracked and lives outside the repo. `git log --grep=kitty` returns zero across all history, so a week of terminal work (Nerd Font map, Hebrew RTL decision, the 0.48 surface block, the lane watermarks) survives only as one file on one disk plus two `.bak` copies. Decide whether it becomes payload the way `dot-claude/` is. NOT done in this pass on purpose: the three existing `dot-*` trees each have a sync checker (`skills_sync.py`), and adding a fourth snapshot with no drift oracle is the failure this repo logs, not a fix for it. `tools/wsl/make_lane_logos.py` regenerates the PNGs, so those are already reproducible from the repo
- [ ] audit the 1,260 lines drop_stale_lines now removes (75,932 -> 74,672 reviewed). Every one should be a line the tree does not contain at the claimed position; nobody has checked them individually

## AUTO: Autonomy Ecosystem (prd/autonomy-ecosystem.md, spec 2026-07-24)
- [x] ADR-0010..0015 + PRD + spec + charters + SESSION-BOOT + lessons ledger (AUTO-03/08/13/16 seed), 2026-07-24
- [x] AUTO-01/02 hook fire-proof, CLOSED 2026-07-24 22:44. `state/hook-fires.log`: 7 harness-written SessionStart lines (real session ids incl. `8abb324e-…`) + 11 PreCompact lines + 12 `## compact` snapshots in `state/compact-log.md`. L011 interpreter/path bug fixed and now proven in-harness, not by pipe test
- [x] COMPACTION CHURN measured resolved 2026-07-29: PreCompact per day 47, 250, 2, 1, 0, 0 across 07-24 to 07-29; per-session 15.6 on 07-25 down to 0.0 on 07-28/29. Both suspect env vars (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `CLAUDE_CODE_DISABLE_1M_CONTEXT`) are ABSENT from live settings; sessions run on 1M context. `trigger=` now logged (289 lines). Caveat: the churn ended 2026-07-26 with no config change recorded, so the cause of the fix is not established; reopen if per-session climbs above 1
- [ ] DECIDE (counts re-measured 2026-07-29): live `~/.claude/settings.json` has 7 hook events (UserPromptSubmit added 2026-07-29 for intent capture; PostToolUse is live-only, absent from canonical). The work enforcement layer is still undeployed: PreToolUse protect-infra/rtk-bash-guard, Stop stop-checklist/verification-before-completion/contract-proof-stop, PostToolUse skill-usage-logger. Adopt selectively; these are the checks that would have caught L003/L009 mechanically. Note rtk binary is missing on Windows, so rtk-bash-guard cannot deploy as-is
- [x] Nightly autonomy pilot workflow on claude-setup (AUTO-07), first scheduled run pending
- [ ] ecosystem.db bootstrap from intent-control-plane schema + tools/eco/db.py (AUTO-06) ← unblocks work-claims (AUTO-04) + FleetView (AUTO-19)
- [x] AUTO-05 CLOSED 2026-07-29: Lane A RETIRED by operator decision (never used once between ADR-0013 and retirement). Intake/routing folded into Lane B as plumbing (docs/charters.md); UserPromptSubmit capture already ledgers intent. Any future RC/phone intake surface is a B feature, not a session lane
- [ ] Merge-policy labels + auto-merge for auto:low (AUTO-11)
- [ ] Scale nightly to tier-1 repos after 7 clean days (AUTO-09)
- [ ] Social: excavate social-media-agent.bundle → draft-first pipeline (AUTO-12/13/14)
- [ ] Research stage in weekly self-improve cron (AUTO-17)
- [x] CHAN-01 CLOSED 2026-07-30: ADR-0018 two-tier inter-agent channel (`text` / `dense-text` / `kv`, no silent downgrade, `kv` only on open-weight legs) + `tools/channel/roundtrip.py` round-trip fidelity oracle. Evidence: `selftest` exit 0 (identity 1.0 PASS, half-truncation FAIL, unreachable peer FAIL, absent-answer probe rejected); `run --channel truncate` exits 1 at fidelity 0.6667. Grounded in arXiv 2606.19857 (SJTU et al., 2026-06-18) and 2607.26773 (2026-07-29)
- [ ] CHAN-02: dispatch envelope gains `channel` + per-peer capability declaration; router must ERROR on `kv` to an API-only peer rather than fall back to text. Seam is the `dispatch` skill's `~/.claude/cache/a2a/audit.jsonl`
- [ ] CHAN-03: decide the dense-payload encoding for `state/bus.jsonl` BEFORE the first dense row is appended; the ledger is hash-chained so this is a chain-integrity decision. Same ticket exempts dense payloads from `tools/slop_lint.py` by envelope field, never by heuristic
- [ ] CHAN-04: first measured live leg. `dense-text` cross-vendor needs no new infra; `kv` needs two open-weight endpoints (Qwen via NVIDIA NIM) plus a projector. Record the compressor-reader PAIR with every verdict, since 2606.19857 measured retention varying strongly by pair
- [ ] CHAN-05: wire `roundtrip.py selftest` into ship-gate.yml as a named step, and add it to the mutation spec, so the oracle is covered the way the other oracles are
- [x] CHAN-06 RESOLVED 2026-07-30: Kilo trigger provisioning is UI-only, and that does NOT cap autonomy. Measured: `kilo --version` 7.3.12, and `kilo help` grepped for trigger/webhook/cloud/inbound/schedule/cron matches exactly one line, `--cloud-fork` (fetch a session FROM cloud). No create-trigger verb exists in the CLI and the docs confirm UI-only for both webhook and scheduled triggers. BUT a trigger is durable and reusable: one UI provisioning step, then unlimited inbound POSTs with no reconfiguration. So the manual step is one-time provisioning, not per-run. Earlier claim in this session that the manual step 'caps how autonomous any of this gets' was WRONG and is retracted
- [ ] CHAN-07: the inbound payload reaches the agent through a prompt template (`{{bodyJson}}`, `{{body}}`, `{{headers}}`, `{{query}}`, `{{path}}`, `{{method}}`, `{{timestamp}}`). That template IS the ADR-0018 envelope seam: channel + peer-capability fields ride in the JSON body and render into the prompt. Design CHAN-02 against `{{bodyJson}}` rather than inventing a second transport
- [ ] CHAN-08: two execution modes, and they are not interchangeable. KiloClaw mode delivers the rendered prompt to the LOCAL instance; Cloud Agent mode starts a repository session IN the cloud. Only the cloud mode survives a policy that forbids the local agent (Yarin's Tabula constraint, 2026-07-30). Pick per leg and record which
- [ ] CHAN-09: scheduled triggers are 5-field cron with a selectable timezone (UTC default, DST handled) and a hard 10-minute minimum interval; anything more frequent is rejected. Check AUTO-18's daily-digest and weekly self-improve schedules against that floor before moving either onto Kilo
- [ ] Reputation routing once runs-table volume (AUTO-20)
- [x] AUTO-10 UNBLOCKED 2026-07-24 (was falsely BLOCKED(operator), L012): key was already in a local .env; `gh secret list -R ShovalBenjer/claude-setup` now shows `GEMINI_API_KEY 2026-07-24T20:17:02Z`. Value piped via stdin, never echoed. REMAINING: `.github/workflows/gemini-review.yml` was written 2026-07-31 and consumes the secret, diff-only, advisory. It has NEVER RUN, so two-model review is still not measured; a workflow on disk is the same class of claim the secret was. Closes when a real PR shows a Gemini annotation. The actor itself IS reachable: a live diff-only call on 2026-07-31 returned two correct CWE-anchored findings (probe used a synthetic diff, no repo content sent)
- [ ] AUTO-15: split resume rails into verifiable rows (job-scan cron, review wf on hiring repo, lane-C tables)
- [ ] AUTO-18 NOT BLOCKED (was falsely BLOCKED(operator), L012): this shell runs as Administrator and S4U logon registers a passwordless always-on task. VERIFIED probe: `Register-ScheduledTask -Principal (New-ScheduledTaskPrincipal -LogonType S4U -RunLevel Highest) -Settings (New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable)` succeeded, read back `LogonType=S4U RunLevel=Highest WakeToRun=True`, probe removed. REMAINING: register the real tasks (daily digest 07:03, weekly self-improve) and observe one unattended fire

## 2026-07-29 session outcomes (lane B)

- [x] Intent capture slice LIVE: UserPromptSubmit hook, `tools/intent/capture_turn.py`, writes `~/.intent` (event + intent card + CAPTURED transition) plus chained `state/prompt-tickets.jsonl` (content-covered hash, no prompt text in git). Acceptance query returns ticket id + goal. Corpus backfill NOT scheduled: transcript format is vendor-internal (L-2026-07-29-e)
- [x] Resource ledger LIVE: `tools/intent/resources.py` + scanner. Backfill wrote 3855 sightings across 2712 resources from 494 files in 1.1s. TRUE coverage baseline 0.2% (5 noted of 2716); only a human-attached note moves it, the scanner mints sightings only
- [x] Autonomy Stop gate LIVE: completion_gate.py now blocks a turn that ends by handing the decision back with no blocker named (measured cause: ~31% of reacted-to answers; 940 min/week idle). Loop-safe via stop_hook_active; every stop logged to state/handback-log.jsonl (gitignored; a per-turn write inside the fingerprint made every gate PASS self-invalidating)
- [ ] panel.py prose-vs-code defect: THIRD waiver for the same false-positive class recorded 2026-07-29 (L-2026-07-29-d; current waiver expires 2026-08-12). Decide: lexical pass so comments/strings/JSON stop matching, or retire panel.py for first-party /code-review. Oracle edit, operator approval required
- [ ] gate selftest ledger pollution: workflow-spawned selftests wrote 5 scratch-repo rows into the real state/gate-runs.jsonl mid-run and produced FAIL-then-PASS on one tree fingerprint (13:51 vs 13:55). Selftests must write to an isolated ledger, same class as the handback-log fix
- [ ] Migration activation backlog: 91/186 dot-claude units deployed (48.9%); 14 hook bodies still 44-61 byte pointers with recoverable bodies in dot-codex/; 24 skill stubs likewise; dot-agents has no deploy target (~/.agents absent, 0/231 live). Bodies verified recoverable in-repo, zero bytes lost
- [ ] voice-metrics preservation NEEDS OPERATOR: only live-only skill not committed; profiles.json carries no message text but keys include a WhatsApp LID (linkable id) + 9.3MB lexicons

## RT: Research transfer (docs/analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md)

External research on compile-once architectures, commissioned 2026-07-27, landed
five findings on this harness. Ranked by ratio of value to effort.

- [ ] RT-1 Log `{claimed_confidence, action, verified_outcome}` so the CLAUDE-OS.md:45 gate (>=0.90 autonomous) can be calibrated at all. Today the reliability curve is not computable, and the literature says self-reported confidence sits at 80-100 regardless of accuracy, which would make that threshold inert rather than protective. Measure before tuning
- [ ] RT-2 Decision ledger + rejection rate on the daily digest. Three ADRs (0005/0012/0014) rest on human approval; `state/` records 753 gate runs and machine refutations but no human approve-or-reject, so rubber-stamping is undetectable. A ratio that has never seen a rejection IS the finding
- [ ] RT-3 Print the joint claim under `gate.py run`'s VERDICT: which domains were N/A and why, and what a PASS does not assert. Per-domain boundaries are documented; the composite one is not. Strings already exist in quality-contract.json
- [ ] RT-4 Fixture provenance for `tools/skilleval` + one independent audit of the existing 5 before writing the next 42. Self-annotated labels are the BIRD defect (52.8% annotation errors there); expanding coverage without auditing labels scales the defect
- [ ] RT-5 First metamorphic relation (start with codemap: renaming one directory must change exactly one row). The repo has mutation testing, which asks "can this check fail", and nothing that asks "is the output invariant under a transformation that must not change it". `grep -ril metamorphic tools/` returns zero implementations

## EXT: external landscape gaps (docs/analysis/2026-08-17-external-landscape-comparison.md)

Operator-ordered comparison against 7 talks, CommandCodeAI, deepseek-harness, and
cordiverse/paper (2026-08-17). Seven adopt-ranked gaps; the cross-source signal is
"the rule exists as prose while the oracle does not". Top three as tickets:

- [x] EXT-1 Append-only-write oracle for `state/*.jsonl`: `tools/audit/append_only.py` (static scan for truncating writers + git-history line-count check), `selftest` green, `check` clean against this repo. Gate-wired 2026-08-19: `check`+`selftest` now chained into quality-contract.json's `unit` domain cmd, so a truncating writer fails `gate.py run`, not just a manual invocation. Before this it existed and passed but nothing enforced it, per a fresh audit finding.
- [x] EXT-2 Risk-classified pre-action guard: `dot-claude/hooks/pretooluse-risk-guard.py`, payload-only (not wired into settings.json), `selftest` green
- [x] EXT-3 Skill-routing accuracy as a measured number: `tools/audit/routing_accuracy.py report`, reads `state/agent-spawns.jsonl` (router_named vs subagent_type) + `state/routing.jsonl` (activation volume); measured live 2026-08-17: 1/6 (17%) overall spawn agreement, 31/37 spawns with no router_named on record. Gate-wired 2026-08-19: `selftest`+`report` now chained into quality-contract.json's `unit` domain cmd (selftest gates, report is informational since the metric has no pass/fail threshold by design). Same "existed, passed, nothing ran it" gap as EXT-1.

- [ ] EXT-4 block/buzz follow-ups (docs/analysis/2026-08-17-repo-compare-block-buzz.md): WATCH rows for the ACP agent/tool protocol split and Nostr-signed per-agent audit events; re-check when a multi-agent server host or multi-principal threat model lands here

- [ ] DASH-1 Session dashboard, Tauri + React (docs/specs/2026-08-17-session-dashboard-direction.md): direction locked by operator 2026-08-17; build starts in its own worktree/PR, buzz clone as design anchor, ledger-read-only

- [ ] DASH-1 slice 1, program design (docs/specs/2026-08-17-session-dashboard-program-design.md): Rust ledger types (tolerant, skip-and-count on malformed/unknown-schema rows, empirically grounded against a key-set scan of all six ledgers), Tauri IPC contract, React component tree, five-slice plan. Row 7 of docs/prd/session-dashboard.md closes on PR review, not on this file existing. CORRECTIVE NOTE 2026-08-19: a fresh audit found 39 dashboard/ files merged with no such review artifact and no CI coverage; row 7 stays open, see docs/prd/session-dashboard.md's corrective note. Gate coverage (cargo test --workspace, npm run build) added 2026-08-19 so future dashboard commits are checked even though this one landed unchecked.

- [x] GATE-COV-1 Fail-closed coverage declaration (operator-approved 2026-08-19, prompted by external review Agentica independently converging on the DASH-1 finding and naming the general fix): `tools/audit/coverage_map.py` + `docs/coverage-map.txt` + `quality-contract.json`'s new `coverage_map` domain. Every top-level tracked directory now needs a `covered-by:<domain>` or `exempt` row or the gate FAILs; unlisted is blocked, not silently ungoverned (the inverse default from `docs/prior-art/out-of-scope.txt`, on purpose). First real run found a SECOND live instance of the DASH-1 class: `nexus-engine-rs` (a second Rust crate, 8 `#[test]` functions, its own README documenting `cargo test`, zero gate coverage), recorded as an admitted exemption naming the gap rather than silently passed. `nexus-engine-rs` gate wiring itself is a follow-up, out of scope for this ticket.

- [x] GPU-C Open-model plan block C answered in practice (operator, 2026-08-17): Modal API key provisioned (~/.env plus ~/.modal.toml, profile shovalbenjer, auth verified via `uvx modal app list`; one prior app glimmer-lab deployed 2026-08-13). GPU bursts for the training-interpretability lane (SAE/crosscoder/KAN on small models, LoRA when the trajectory corpus is ready) run on Modal per burst; the spec's RunPod/Vast rows stand as fallback pricing, no monthly subscription, which was the spec's own recommendation
- [ ] BILL-1 GitHub Actions billing wall (found 2026-08-17 post-merge of PR #74): hosted-runner jobs on every PR fail in seconds with "recent account payments have failed or your spending limit needs to be increased"; self-hosted jobs (gate, falsifiability) unaffected. Operator-only: Settings, Billing and plans. Blocks browser-instrument-selftest and supply-chain on PRs 75/76/78/79/80 and therefore blocks the standing auto-merge condition
- [x] EXT-6 Connector-use ledger BUILT and wired live (2026-08-17): state/connector-use.jsonl fed by dot-claude/hooks/connector-usage-log.sh (PostToolUse matcher mcp__.*, deployed to live settings.json same turn, selftested with a synthetic payload). Registry gained rows for ElevenLabs, Zapier, AWS and the measured-usage clause. Census same date: ~24 servers surfaced, 10 routed, 11 ruled irrelevant, 2 ever actually called (claude-in-chrome, ElevenLabs); the ledger turns that from a one-off count into a running number
- [ ] VOICE-1 Unified voice channel for the workstation (operator, 2026-08-17): replace the type-into-a-.txt loop with STT in and TTS out. Verified state from the interview-prep session, same date: TTS works today via Windows System.Speech (Zira, powershell say.sh); the voice-explainer/ElevenLabs path is DEAD (script missing, Seekapa-era key); STT is unwired because Win+H refuses Hebrew and cannot type into WSL terminals; the working stopgap is dictate-into-native-window then file-read via /mnt/c. Engine choice is an OPEN OPERATOR BLOCK per accepting-architectures: ElevenLabs Scribe realtime (~$0.39/audio hour, priced 2026-08-17) vs local Whisper (deferred once already) vs upgraded file-watch with auto-transcription. Constraint: do not touch the interview session's working loop before 2026-08-17 11:00. Update same date: their pipeline plan is on disk (~/docs/interviews/_pipeline/, plan.md holds the ElevenLabs opt-in operator block; reference that block, do not fork the decision), the operator endorsed Wispr Flow as preferred STT (pending confirmed install), and the channel-routing question is answered by the new rule dot-claude/rules/output-channel-routing.md. TTS engine update 2026-08-17 ~16:17: the ElevenLabs claude.ai MCP connector came online and a full loop was VERIFIED live (creative_generate_speech eleven_v3, voice Eric, mixed Hebrew+English, mp3 via ffplay through WSLg audio, 11.4s for ~142 credits about $0.05); the dead local generate-voice.py path is superseded by the connector, no local key needed, System.Speech stays the zero-cost fallback, and per-line pricing means briefings yes, long transcripts no

- [ ] EXT-5 everything-claude-code watch items (docs/analysis/2026-08-17-repo-compare-everything-claude-code.md): the deterministic delivery-gate Stop-hook pattern (write the gap vs our completion_gate before adopting), the consolidated hook-dispatcher pattern (relevant to the unwired-hooks debt), and git-remote-hash project scoping as a manually-gated tool. Their instincts auto-rule-writer is IGNORE by decision, it contradicts accepting-architectures and calibrated-claims

## ABSORB: external resources evaluated but never absorbed

Operator directive 2026-07-29: every external resource we look at must end in
absorbed (idea taken into our code), adopted (dependency added), or used as-is.
"Evaluated and shelved" is not an outcome, and 0 features may be neglected.
Audit of every external resource this repo has evaluated is below. Nothing here
deletes an existing row; these are the rows that were silently dropped.

- [x] ABSORB-01 and ABSORB-09 CLOSED 2026-08-10, as one schema change, one backfill and
  one oracle edit, which is what the ABSORB-09 row asked for. `verdict_class` (7 values)
  sits BESIDE the free-text `verdict`, which is unchanged, and `absorption_status`
  (absorbed / adopted / used-as-is / rejected-with-reason / unreviewed) plus `absorbed`
  are required on every record. `codemap.py prior-art` fails a record missing either
  field, fails a value outside either vocabulary, and fails a status that claims a
  decision with nothing named beside it, which is the free-text defect wearing an enum.
  It extends the oracle that already runs rather than adding a domain, per the 4.2 warning.
  **The measured answer to ABSORB-06 is 1 of 41.** Exactly one record, `tools-trycmd`,
  names what it took and where it landed; the other 40 are `unreviewed`. That is not a
  backfill placeholder, it is the rate, and it was unknown rather than zero until now.
  `unreviewed` is bounded by each record's own `recheck_after` rather than by a new
  calendar, so the first forced decision is 2026-09-07 and every record is decided inside
  three months. The count prints on the PASS path, because a number that only appears when
  something breaks goes back to unknown the moment it is fixed.
  Evidence: `codemap.py prior-art` exit 1 before with 82 findings and exit 0 after;
  `codemap.py selftest` 20 cases; `mutate.py --spec codemap` 17 of 17 applied, 17 caught,
  0 survived, with 4 new mutations; `tests/test_prior_art_absorption.py` 17 tests; the
  corpus test proven red by deleting one field from `tools-bus.json`.
  **One correction to my own work, kept because the mechanism found it:** two selftest
  cases asserted only a message COUNT, and the missing-field branch and the invalid-value
  branch are adjacent, so a None value falls through from one to the other and still
  produces exactly one message. Both passed with the check they were written for deleted.
  Mutation testing named it and they now assert the wording each branch owns.
  Backfill is a committed script, `tools/audit/absorption_backfill.py`, named in the
  oracle's own failure message, because three open PRs each land a record that will need
  it. Its `verdict_class` table is explicit data rather than keyword derivation: four of
  the 41 verdicts are whole sentences and a substring rule that groups them correctly
  today groups the next one wrongly and silently.
  STILL OPEN, and it is the real work: 40 absorption reviews. This change makes them
  representable and dated. It does not do them.
- [ ] ABSORB-01 ORIGINAL ROW, kept for the reasoning: the prior-art record schema cannot express absorption. All 27 records carry the same 14 fields (`verdict`, `why`, `strongest_counterargument`, `migration_loc`, `our_loc`, `recheck_after`, ...) and not one of them names what was taken from the alternative. So absorption is unrepresentable, therefore unchecked, therefore never happens. Add `absorbed` (what we took and the file it landed in) and `absorption_status` (absorbed / adopted / used-as-is / rejected-with-reason), backfill all 27 records, and have `codemap.py prior-art` fail on a record whose status is unset. Extends an oracle that already runs rather than adding a thirteenth domain (see the 4.2 warning in docs/reflections/2026-07-29-what-is-going-wrong.md)
- [x] ABSORB-02a Dolt-as-database CLOSED, rejected with reasons (operator, 2026-08-17): Python access needs a standing dolt sql-server (violates no-unowned-server; the beads "Embedded Dolt" workaround is Go-only), and Dolt's content-addressed binary chunk store would replace today's PR-reviewable JSONL diffs with opaque blobs. Git-tracked JSONL already absorbs diff/history/blame. Full comparison in the 2026-08-17 DB-substrate research (session b771656c); the point-in-time reconstruction remainder stays open as ABSORB-02 below
- [ ] ABSORB-02 DoltHub option (c), the deferred half. Three of Dolt's five features (diff, history, blame) were genuinely absorbed on 2026-07-25: `state/*.jsonl` is append-only in git, so `git show <rev>:state/x.jsonl` answers "what did this say on the 25th". The unabsorbed piece is point-in-time reconstruction for the ledgers that are gitignored and therefore have NO history at all, named in docs/analysis/2026-07-25-our-own-dolt.md section 4(c) as roughly 150 lines and deferred "only when a concrete need appears". It was never ticketed anywhere, which is how it got neglected. The concrete need now exists: `hiring_engine/ledger.sqlite` holds 272 jobs, 4 applications and 21 approvals with zero history (docs/analysis/2026-07-29-local-dependency-audit.md section 4). Lane B (resume) owns that ledger, so this is a lane-A proposal row, not lane-A work
- [ ] ABSORB-03 albert (Sdraugel/albert), two mechanisms. Code reuse is blocked by PolyForm Noncommercial 1.0.0, so these get rebuilt, not copied: (a) git-worktree isolation per concurrent producer, which structurally kills the one-tree race that is open risk 1 and that fired again during this session's own verification run; (b) producers-never-grade-themselves enforced by role rather than asserted in prose, starting with the prior-art records, which are currently written and self-graded by their own author. Verdict and license reasoning in docs/analysis/archive/2026-07-29-albert-prior-art-verdict.md
- [x] ABSORB-04 just-my-skills coherence-governor, "steal one page". Recommended 2026-07-24 with the exact curl to run; the curl was never run and `docs/analysis/reference/` did not exist. DONE 2026-07-29: 419 lines saved to docs/analysis/reference/coherence-governor-AGENTS.md. The two pages worth taking are the 8-row Drift Sentinels table (line 262) and the 7-level Authority Order (line 43), both more compact than the equivalent scattered across five `.claude/rules/*.md` files. Merging either into calibrated-claims.md is a separate decision, not done here
- [ ] ABSORB-05 CCC (amirfish1/claude-command-center) is NOT a new row on purpose: AUTO-19 above already owns it and the operator said not to duplicate or delete tasks. Recording the absorption status against it instead. Verdict was ADOPT-PARTIAL on 2026-07-24 with one idea named worth taking (jsonl-on-disk as truth, replacing the dead WSL intent.db path); `docs/specs/2026-07-24-command-center-superior.md` carries a 12-row feature table, 5 premortems and an 18-item acceptance checklist; `tools/fleetview/` still does not exist. Status: SPECCED, ZERO CODE, 5 days
- [ ] ABSORB-07 The saved-link corpus, which is the real unabsorbed pile and dwarfs the four repos audited above. `wa-export-archive/SENSITIVE-self-chat/_chat.txt` holds 8546 lines over roughly 14 months: 984 URL occurrences, 806 unique, 80 unique github.com repos, 12 arxiv papers, 14 learn.microsoft.com pages, 166 youtube. Save rate rose five to ten times in July 2026, so recency signals current intent. Named by docs/archive/HANDOFF-FROM-LEARNING-2026-07-27.md section 3.6 on 2026-07-27 as "better curated than the learning platform's 11 world-scan sources because it is filtered by his actual attention. It is unwired." Two days later it was still unwired. Links and dates extracted 2026-07-29 to `C:\Users\shova\wa-export-archive\self-chat-links-2026-07-29.csv` (no message text copied, source is marked SENSITIVE and stays local). External brief ready at docs/archive/2026-07-29-external-absorption-brief.md; run it in Claude Desktop with the CSV attached, then file the returned table against this section
- [ ] ABSORB-08 vulture ADOPTED 2026-07-29, the first genuine third-party tool in this repo's quality loop, run via `uvx vulture` so it adds no install footprint. Result: 0 findings at >=80% confidence, 70 at >=60%, and the distribution is the finding. 57 of 70 are in `intent-control-plane/src/intent_control_plane/` (memory.py 6, durable.py 6, roster_evolution.py 5, provenance.py 5, reliability_policy.py 4), which is the operator's own observation that parts of the code cannot possibly be connected, now measured. NOT YET DONE: (a) whole-module connectivity, which vulture does not measure, since it finds unused symbols and not modules no one imports; (b) triage of the 70 into genuinely-dead versus CLI-dispatched false positives; (c) wiring `uvx vulture` into the gate as a check rather than a one-off. Websearch 2026-07-29 says the current standard pairing is ruff for fast local unused-import checks plus vulture for cross-module scanning, with `albertas/deadcode` as the more configurable alternative presented at EuroPython 2024
- [ ] GATE-LOOP-01 `codemap` and `review` cannot both be green at the same time, and the reason is structural rather than a stale artifact. codemap records a file COUNT per directory and counts `state/reviews`, while the review domain requires `state/reviews/<HEAD sha>.json` to name HEAD exactly (gate.py review_artifact). So: leave the panel artifact uncommitted and codemap fails by one file; commit it and HEAD moves, so the artifact names the parent and review fails. Observed both ways on 2026-08-06 across four commits. gate.py already has `GATE_OUTPUTS = ('state/gate-runs.jsonl', 'state/reviews/')` for its own dirty calculation, so the concept exists and codemap.py simply does not share it. Fix is one of: have codemap exclude gate outputs the same way, or key the review artifact by tree fingerprint (`${FP}`, which review_artifact already supports) instead of commit sha. This is the general form of the fingerprint self-invalidation already known from the Stop hook
- [ ] HOOKGATE-01 The compiled force-push rule disagrees with the live one, and the disagreement relaxes a guard, so it is an operator decision rather than a regen. `tests/test_hookgate.py::test_rules_rs_matches_safety_gate` has been failing since at least 2026-08-05 (the mtime on ~/.claude/hooks/safety_gate.py) and blocks the gate's `unit` domain. The delta is one rule: committed `tools/hookgate/src/rules.rs` blocks `--force(-with-lease)?|-f`, while the live safety_gate.py blocks `--force(?!-with-lease)` and permits `--force-with-lease` with the reason that it refuses if the remote moved since your last fetch. Running `python tools/hookgate/regen_rules.py` closes the test in one command and, in the same command, relaxes what the compiled binary blocks. Done deliberately by whoever edited the live file, or not at all. Found and reverted 2026-08-06 during unrelated work
- [ ] HOOKPATH-01 A UserPromptSubmit hook FAILS CLOSED on a missing file and blocks the operator's prompt outright. Hit 2026-08-07: `python3: can't open file '/home/shov/claude-setup/tools/intent/route.py'`. Cause is not a bad path. `/home/shov/claude-setup` is a symlink to the main checkout, `route.py` exists ONLY on branch lane-a/boundary-contract-bans, and the main checkout had since been switched to lane-a/waived-domains-are-not-unmeasured, so another session changing branches deleted a live hook from disk. The live settings.json borrows three hooks out of a mutable working tree, which means any branch switch in any session can disable or block them. Fixed for route.py by deploying it to ~/.claude/hooks/route.py (404 lines, stdlib only, no repo-root derivation) and repointing settings.json; settings backed up first. NOT done for the other two, deliberately: capture_turn.py derives REPO_ROOT from Path(__file__).parents[2] and imports tickets from the repo, so deploying it to ~/.claude/hooks would resolve REPO_ROOT to /home/shov and write tickets to the wrong place. Those two need a real deploy step that carries their dependencies, or a wrapper that fails OPEN. A guard that blocks the operator when its own file is missing is worse than no guard
- [ ] METRIC-01 Six externally-sourced metrics we are missing, all computable from artifacts already on disk, in docs/analysis/archive/2026-08-06-persona-metrics-external-sweep.md. Cheapest first: M1 review-finding precision (state/reviews/*.json holds every panel finding and nothing has ever labelled one true or spurious; CR-Bench arXiv:2603.11078 measured that resolution rate alone rewards over-flagging), M3 request-to-outcome transitions (see INTENT-01), M5 per-task token and tool-call logging, which Anthropic measured as explaining roughly 80% of performance variance on BrowseComp and which we log nowhere
- [ ] METRIC-02 Before reporting ANY score this harness computes about itself, check it against what a trivial policy would score. arXiv:2607.28685 re-ran four agent-safety benchmarks under their own scorers and found an always-positive policy hits F1 0.690 on R-Judge, beating 5 of 21 models that actually discriminate, and that three benchmarks rank the same 18 models in three different orders. tools/audit/mutate.py is already this instinct one level down. Nothing in the gate currently reports a trivial-baseline comparison alongside a pass rate
- [ ] METRIC-03 Connector description scan for tool-poisoning shape, the one defensive check from the sweep computable here today. Malicious instructions hidden in an MCP tool description are invisible in the client UI and fully visible to the model (Invariant Labs 2025-04-01; the published example reads a local config and exfiltrates it through an innocuous argument). Mechanism is sourced, the check is a proposal, and it belongs with pointers.py rather than as a new gate domain
- [ ] INTENT-01 467 prompt tickets exist and every one is state CAPTURED. `tools/intent/tickets.py` defines the whole lifecycle (CAPTURED -> TRIAGED / NOT_WORK / SUPERSEDED and onward) with an allow-list of legal edges, and not one transition has ever been written, which is the mechanism behind the operator's 2026-08-06 complaint that his request 'got lost as always in the session'. The ledger records that a request arrived and never records whether anything happened to it. Nothing needs building: the state machine is already there and nothing calls it. Wire a transition at the two points that already know (a claim row being written, and the completion gate at Stop)
- [ ] INTENT-02 `tools/intent/resolve.py` now rejoins a ticket to the sentence that produced it, by recomputing text_sha over session transcripts, so 'dig it up later' works without storing prompt text twice and without touching capture_turn.py's hashes-only stance. Resolve rate is 226 of 467 today. The unresolved 241 are a floor not a measure: rotated transcripts, per-host project slugs, and any prompt that reached the model differently from how it was captured. Worth measuring which of the three dominates before assuming the join is lossy
- [ ] PILE-04 Two of the three payload trees have NO destination on this machine. `~/.claude` exists with 40 entries; `~/.codex` and `~/.agents` do not exist at all, verified 2026-08-06. So dot-codex (333 files, 2.2M) and dot-agents (218 files, 3.8M) are payloads for runtimes that are not installed, and 27 of the 29 forked skills involve one of those two trees. The operator chose one-tree-plus-per-runtime-deploy, which is right, and the measurement says the deploy has exactly one live target today. Recommendation: dot-claude becomes the canonical tree, dot-codex and dot-agents are demoted to archive rather than deleted (they are the only copy of several skills), and the deploy learns the other two destinations when those runtimes are actually installed
- [ ] PILE-05 `review` and `codex-call` are NOT forks, they are name collisions, and merging them would destroy a skill. dot-agents/review is automated checks (bundle size, vulnerabilities, licences, baseline screenshots, layer detection) plus a SOTA principles reference; dot-claude/review is a PR precheck with a CI fleet flow and two execution paths. Same for codex-call: dot-agents is a Codex orchestrator with four invocation patterns, dot-claude is external review judges with the Gemini Free Tier boundary. They need renaming, not a survivor. Between them they are 683 of the 1063 semantically divergent lines across all 29 forks
- [ ] PILE-06 Search-replace corruption in dot-agents, and a contamination this session caused and then fixed. dot-agents/skills/codex-call/SKILL.md:60 reads 'When to use Codex vs Codex vs subagent', which is a global Claude->Codex replace collapsing a comparison into nonsense. 28 dot-agents files reference `~/.Codex` with a capital C, a path that does not exist in any casing. 4 of the 8 skills promoted into dot-claude today (to-issues, to-prd, request-refactor-plan, github-triage) carried that path in; corrected to ~/.claude and dot-claude/bin/work-item.sh deployed to ~/.claude/bin so the corrected path resolves. STILL DEAD: those skills also cite `~/.claude/rules/ado-issue-mapping.md`, which exists in no tree and no home. It is Azure DevOps, so it belongs with the EXJOB-01 decision rather than being recreated
- [ ] PILE-01 The 29 forked skills, one decision each, table in state/pile-manifest.jsonl and printed by `python tools/audit/pile.py scan -v`. NOT a merge, 29 merges. The proposed winner is a dumb stated rule (newest git touch, then largest) and is a PROPOSAL: `review` is 22k in dot-agents against 11k in dot-claude, `heidegger-reflect` is 29k against 3k, `frontend-design` 1k against 8k, and picking by policy would discard the larger side unread in three cases. Four of the 29 are the ex-employer skills whose disposition is still open under EXJOB-01, so they cannot be resolved before that is
- [ ] PILE-02 The real architectural question behind 'merge the dirs', which is NOT answerable by a tool: dot-claude, dot-codex and dot-agents are payloads for THREE runtimes (~/.claude, ~/.codex, ~/.agents), so merging them into one source means the three runtimes share one tree and one skill's edit reaches all three. That may well be right, since the forks above are the cost of not doing it, but it changes behaviour for two runtimes at once and is an operator decision, not a dedupe. 29 skills are already byte-identical across trees and can collapse the moment that call is made
- [ ] PILE-03 Session collision, recorded because it is the cost the operator named. On 2026-08-06 this session and lane-a+session-corpus-extractor independently (a) removed the same expired review waiver, (b) hit the same codemap/review artifact loop, and (c) reached the same hookgate rules.rs regen, which that session applied as c30edc7 and this one reverted pending an operator call. Two sessions, same day, same three problems, no shared state. state/claims.jsonl exists precisely to prevent this and neither session read the other's row. GATE-LOOP-01 and HOOKGATE-01 are both already fixed on that branch, so the two waivers this branch added expire on merge rather than on work
- [ ] EXJOB-01 The 8 always-loaded global rules grounded in the ex-employer, in three classes, per docs/analysis/archive/2026-08-06-azure-jira-after-the-job.md. RELABEL (no decision needed, the rule is stack-independent and only its worked example is historical): boundary-contracts, production-means-merged-and-smoked, read-whole-before-reasoning, hidden-trees. Date the example the way calibrated-claims already dates its incidents. REWRITE (principle survives the tenant): foundry-deployment-per-project, pii-handling. RETIRE OR REFACTOR (operator call): jira-comment-drafting, which exists solely to post into a tenant we no longer have and names three colleagues in every session's context, and repo-topology, whose rule is among the most useful here and whose entire worked example is ORM-AGENT
- [ ] EXJOB-02 `azure-activity-watch` recreated against git and gh. The one genuine capability gap the ex-employer audit found rather than inherited: 'who other than me touched this' has no counterpart here, and there is measured local pain for it (two clones on a shared stash, and the 2026-07-31 claim row recording 8 subagents against one shared dirty tree). Everything else on that list is either covered or retirable
- [ ] EXJOB-03 `jira-read` rebound to `gh issue view --comments`, read whole. The skill is held back from the live tree and still in the repo. Its discipline is already a global rule (read-whole-before-reasoning, which was born from the DEV-5062 truncation), so what is missing is only the gh-shaped body. Decide with EXJOB-01 whether jira-task-draft and prod-deploy-rules are retired outright, since to-issues and to-prd already auto-detect GitHub and are now live. TRAP, found by making the mistake: the holdback is NOT durable. The three live in ~/.claude/skills-holdback-2026-08-06 and the next `skills_sync.py deploy --apply` puts every one of them back, because deploy reconciles repo to live and a skill missing from live simply reads as new. It happened once during this session and had to be undone. A holdback with no mechanism is a note, not a state, so either retire them from the payload or teach skills_sync an exclusion list
- [ ] PERSONA-01 0 spawns have ever been recorded in state/agent-spawns.jsonl, and after today's repair all 19 personas are operational, so the ratio is now measurable rather than excused. `python tools/audit/persona_audit.py scan` is the check; wire `--strict` into the gate once EXJOB-01 settles, since it currently passes and would start failing the moment a persona is routed at a skill that cannot load
- [ ] PERSONA-02 The registry's Best-Practices Corpus section tells every persona to use three paths under ~/.claude/corpus/ for coding-practice lookups, persona rule generation, review criteria and architecture decisions. The whole directory is absent on this machine, verified twice. Either build it (build_best_practices_corpus.py is itself one of the three absent files) or cut the section, because a corpus that does not exist is a routing instruction into nothing
- [ ] ABSORB-09 The saved-repo pile, skills half. 17 of the repositories in `state/external-repos.jsonl` were enumerated for SKILL.md content on 2026-08-06 (roughly 370 skills) and 24 carry a decision row in the new `state/external-skills.jsonl`. Seven are adopt-candidates and none is installed, so this row is the unabsorbed remainder: `octocode-skills` (aims at our own skills_sync drift), `octocode-graph-eval`, `octocode-awareness`, `neat-freak`, `caveman-stats`, `resolving-merge-conflicts`, `verification-before-completion`. Two of the seven are metadata depth only and must be opened before adoption. `dmmulroy/.dotfiles` `.skill-lock.json` is adopt-patterns, not vendorable (no declared licence). Evidence and reasoning: docs/analysis/2026-08-06-skill-candidates-dependency-filter.md
- [ ] ABSORB-10 DORA, decided rather than deferred, so it does not come back a third time. Six public DORA skills exist and the best of them (manikumarkv/devrunway-claude-plugin, MIT) needs only git and gh, so it passes the dependency filter. Rejected anyway on our own prior art: docs/specs/archive/2026-07-31-github-native-project-surface.md section 4.1 already concluded the four keys do not transfer to a one-operator repo with no customers, and the transferable half (DORA's pairing of throughput with an instability counter) is already K1-K15 against our ledgers. If this is ever reopened, reopen the spec section, not the skill search
- [ ] SKILLDEP-01 Decide the `az` question, because it governs the largest single block of unrunnable skills. `command -v az` is empty on this WSL host, 9 committed skills open with an `az` invocation, `jira-read` reaches through `az keyvault` for its token, and the gastown registry routes an Azure Ops Utility persona at 8 owned skills. Either install the Azure CLI in WSL or mark that persona Windows-side-only in the registry. Currently it is neither: routed, unrunnable, and silent about it. Measured by `python tools/audit/skill_deps.py counts`
- [ ] SKILLDEP-02 `apt install jq` unblocks 4 committed skills (gws-gmail-read, gws-gmail-triage, pii-scrubber, review) for one command. Trivial, listed so it is not re-derived
- [ ] SKILLDEP-03 Wire `python tools/audit/skill_deps.py scan --strict` into the gate's skills domain, so a newly added skill that cannot run on this host fails at commit rather than at first invocation. Blocked on SKILLDEP-01: with `az` unresolved, strict mode fails today on 26 pre-existing skills, and a check that is red on arrival gets waived instead of fixed
- [ ] ABSORB-06 Coverage boundary of this audit, stated so it is not read as exhaustive. Four external repos and roughly 70 named alternatives inside the 27 prior-art records were checked. NOT checked: whether any of the ~70 alternatives inside those records was absorbed, because the schema has no field to check (that is ABSORB-01). Until ABSORB-01 lands, the true absorption rate across all external evaluation is unknown, not zero

## DONE
- [x] Repo relocated + July state synced + pushed (SETUP-OS #1)
- [x] CLAUDE-OS.md single source of truth (#2)
- [x] Notification fabric: phone push + desktop toast (#3)
- [x] Always-fresh PR review workflow on 22 repos (#4), auth pending
- [x] PRD + 8 ADRs + persona spec + INDEX (this doc set)
- [x] kernel-anchor hook: deep-work discipline injected every prompt, live+wired (#5 partial)
- [x] slop_lint gate (Antislop banlist), verified exit-1 on hits
- [x] Repo portfolio graph: 22 nodes / 72 edges -> d2 + sqlite (#15)
- [x] Git branch health sweep: 22 repos, 80 branches, 20 merged-deletable, 2 drift (#17)
- [x] Daily digest generator over live state + cron 7:03 (#6 partial: needs always-on / Task Scheduler)
- [x] FULL work-setup import from work-archive-2026-07-12: 23 personas + 14 hooks + 36 skills + tower/intent bins + work-docs/ + intent-control-plane/ (2026-07-24, see docs/analysis/2026-07-24-work-archive-import.md)

## P0: Truth & hygiene (L1/L7)
- [x] Authorize OAuth token; distribute to 22 repos (#4), DONE 2026-07-23 (root cause: was stripping #state)
- [ ] Rotate API key (operator), NOT REPRODUCED 2026-07-24: read the תזכורת לעצמי group over CDP, it holds exactly 3 messages (scroll converged, 25 passes) and a presence-only regex probe for `cfat_`/`sk-`/`gh[pousr]_`/32+ hex/"account id" returned 0 hits. So the token is not in that group now. This does NOT clear the item: it may have been deleted from view, or was in a different chat. Operator to confirm whether that credential was ever exposed and rotate if so
- [x] Global default model: superseded by operator decision 2026-07-29. /model set fable-5 as the saved default for new sessions and it runs on this machine; the old row wanted the opposite direction. model-selection.md rewritten with the routing table (fable default and hardest work, opus workhorse, sonnet workers, haiku inventory)
- [ ] Update global CLAUDE.md "Codex is executor" line (ADR-0007 amended: Codex REMOVED)
- [ ] Purge WSL-era paths in /cdp, reground docs
- [ ] Catch docs up to reality: PRD #4 done, #8 partial, ADR-0007 Codex-out

## P1: Deep Work Protocol hooks (L0) + digest (L4)
- [x] SessionStart recall rewired Windows-native (P1.1, deployed+wired)
- [x] Reflex router + flywheel S1 logger, PII-safe (P1.2, SLM #2)
- [x] /slop gate command (P1.5, deployed)
- [x] Memory + web write pipe (P1.3, #14) - real card written + recalled
- [x] Blast-radius grapher (P1.4, #16)
- [ ] handoff-on-stop, postcondition metadata (#5 remainder)
- [ ] RTK bash guard hook, blocked: rtk binary MISSING on Windows
- [ ] Daily digest push from cron (#6, generator+cron done, needs always-on Task Scheduler)

## P2: Review fabric (L5)
- [x] Live review demonstrated: PR #2, GitHub-Claude caught 4/4 seeded defects + 2 bonus; session-Claude replied (two-Claude loop)
- [ ] Second model = FREE Gemini (AI Studio) replaces Codex; wire a2a-gemini bridge + gemini-review workflow (needs free key)
- [ ] a2a ⇄ GitHub agreement-gated review + provenance + audit (#8), needs Gemini actor
- [ ] Persona review economy build (#19), model-agnostic personas; PR-type routing; two reputation axes (persona + model)

## P-DASH: Dashboard / multi-session (NEW, from WhatsApp compare)
- [ ] Evaluate adopting amirfish1/claude-command-center (MIT) as the missing session-dashboard layer (Kanban, spawn/resume, cost, cross-session), DO NOT rebuild (excavate-before-building). Windows-native PS install exists; Mac-first, some features degrade.

## P3: Orchestration (L3)
- [ ] Scheduler consolidation; WSL systemd retired (#11); standing personas
- [ ] Concierge phone topology (#20)

## P4: I/O & frontier (L2/L4/L8)
- [ ] WhatsApp copilot: triage + style drafts + coaching (#9)
- [ ] Learning-card emitter → הסדנה (#10)
- [ ] Memory + web write pipe (#14)

## Continuous
- [ ] Repo portfolio graph (#15) + blast-radius graph (#16)
- [ ] Git branch health sweep (#17)
- [ ] Rules-as-enforcement per repo (#18)
- [ ] Skills estate owned/merged/archived (#12)
- [ ] Weekly self-improvement loop (#13)

## Filed 2026-07-29 (lane B session: retro, split, observability)
- [ ] Stack-lint oracle: rules/*.md stack preferences become mechanical checks (import json vs orjson, pandas vs polars, statistics-over-lists) as a gate domain with selftest + mutation spec. Driver: operator 2026-07-29, "even the basic jsonl orjson is not enforced"; enforcement map in docs/analysis/2026-07-29-session-retro-*.md sec 5
- [ ] Lane-enforcement check in the Stop gate: session cwd and newest claims.jsonl row must agree, else one corrective turn. Closes the L-2026-07-27-a/-c class mechanically
- [ ] Waiver-falsifier execution: gate.py runs the command a waiver reason names and fails the waiver if it cannot run or refutes the reason. Closes L-2026-07-29-c
- [ ] FleetView v0: operator-owned UI over state/sessions/*.json (statusline tap, live 2026-07-29) + handback log; stack chosen via rules/repo-stack-reasoning.md then /diverge; replaces the vendor statusline as the primary surface. Full substrate arrives with ecosystem.db (AUTO-06)
- [x] qwen-code PARKED 2026-07-29 evening (operator: no interactive logins): its OAuth needs a browser login, the QWEN_API_KEY on disk is a 116-char non-key (DashScope keys are ~35), and the qwen model family is already served free through tools/openrouter and tools/nvidia preference lists. Config left on qwen-oauth with a .bak; revisit only if a real DashScope key appears
- [x] GitHub Models LIVE 2026-07-29: gh-models extension installed, 36-model catalog, PONG verified on openai/gpt-4o-mini and meta/llama-3.3-70b-instruct under existing gh auth; their deepseek-v3 catalog id 400s server-side (unknown_model), noted not chased. REMAINING: Groq and Cerebras probes, quotas recorded before wiring
- [ ] case-ledgers.pages.dev custom domain (OPERATOR decision, optional); renaming the project is one variable in deploy.yml + _redirects + canonicals
- [ ] Study CCC's GitHub-Issues-to-worker queue (amirfish1/claude-command-center + watchtower) for the TODO->gate loop; competitive read in the 2026-07-29 retro sec 7
- [ ] Discovery sweep rebuild per docs/archive/HANDOFF-FROM-LEARNING-2026-07-29.md: add google-research org, widen per_page cap, qualify pushed_at by default-branch commits, watch releases beyond claude-code, add changelog/blog feeds; OpenReview needs a browser client (tools/browser/cdp.py), plain HTTP is blocked. Lane A owns the sweep contract; NOT acted on as of 2026-07-29 evening
- [ ] Deterministic preflight per docs/specs/2026-07-29-deterministic-preflight.md: /diverge the recipe format, then pilot ONE activity class with recorded preflight rows keyed to PT ids; Stop-gate check lands only after two measured weeks. Operator-originated 2026-07-29
- [ ] completion_gate extension, advice-without-artifact: block a final turn that proposes future work (numbered moves, timelines, 'before any second attempt') while the turn performed ZERO mutating tool calls; detection keys on tool-call counts first, text patterns second, to dodge the panel.py prose-false-positive class (L-2026-07-29-d). Driver: operator 2026-07-29 on the resume session's promises-with-zero-work output; measured: that session's text passed 5 'clean' stops after its one 14:32 block, so the current check misses advice-shaped handbacks. Oracle edit: needs the 17-test treatment + mutation spec before deploy

## Filed 2026-07-29 (reflection: ungated channel + false-scope plan)
- [ ] Response-channel slop gate: Stop hook runs the slop patterns over the TURN'S RESPONSE TEXT, one corrective turn on a hit. Measured driver: 33 connector violations across 17 of 28 text turns (61%) in session dfcabe1b while every .md written passed slop_lint. Must tolerate dashes inside quoted code/data or it repeats the panel.py false-positive class (L-2026-07-29-d). Lesson L-2026-07-29-g
- [x] CLOSED 2026-07-31 by measurement. scan.py false positives: top 3 ranked proposals claimed SessionStart/PostToolUse/PreCompact hooks were missing; all three exist live (7941/2519/1306 bytes) and session-recall.sh fires every session. The tool CLAUDE.md names for choosing work ranks phantom defects highest. Fix the path resolution, add a positive test per L017
- [x] CLOSED 2026-07-31, and my first reading of it was WRONG. I ran `bus.py inbox`, got an empty result, and wrote that the 19-unread figure was stale. The number was right and the reason was not: a UserPromptSubmit hook drains the bus at every prompt, so a manual `inbox` after it will always look empty, and I had measured the hook's leftovers rather than the queue. Proof arrived in the same session: the hook fired on the next prompt and printed 6 unread to lane A, all `to: ALL`, including the C-017 note that codex IS installed and the C-015 note about the bus's own delivery bug. So the bus is NOT write-only, which is what the original row feared, and the reader is a hook rather than anything a session runs. A second wrong turn worth recording: I diagnosed `state/bus-cursors/A.txt` as holding a hash where an id belongs, because I compared it against each row's `id` field. `row_id()` returns the STORED HASH for a chained row, by design and documented at bus.py:243. The cursor is the last row's hash and resolves correctly. Original row: bus inbox is never read, 19 unread messages to lane A (written as B under the pre-2026-07-30 scheme), oldest 2026-07-25, carrying live findings (160 canonical files never deployed, deploy-setup.sh false-greens, stale-rules warning now resolved-by-time with nothing recording it). Either surface unread count at SessionStart (session-recall.sh already runs) or accept the bus is write-only and say so
- [ ] /reground is hollow in BOTH trees: absent from ~/.claude/commands/, and the canonical dot-claude/commands/reground.md dispatches to /home/shovalbe/.agents/skills/reground/SKILL.md which does not exist on this machine. Operator typed /reground tonight and got nothing. Either write a real Windows-native reground (the 7-command reconciliation sweep is its natural body) or delete the command
- [ ] Inventory reconciliation BEFORE the next build plan: bus inbox, scan.py, refute run, skills_sync (52 drift), pointers (261 absent paths), lane B/C backlogs, gh open work, CLAUDE-OS + INDEX read. Lesson L-2026-07-29-h. The competing frame this evidence supports, and which the architecture plan suppressed, is that inventory bloat is the core problem and adding tickets is the wrong shape
- [ ] No retrieval layer over state/: measured 130M transcript tokens/week and ~20M in one session, so our own state exceeds every context window. Ledgers are append-only and read by tail or grep; nothing indexes them. Surfaced during the long-context critique response and walked past
- [ ] Statusline never observed rendering in a live terminal: unit-tested against synthetic payloads only. FleetView v0 rests on it. Verify in a real session before building on the tap
- [x] STALE 2026-07-29 evening: the fable-vs-opus falsifier due 08-05 was overtaken by the operator setting opus[1m] as the saved default tonight. model-selection.md still records the fable experiment as live; it needs rewriting to say the experiment was ended by operator decision before its falsifier date, and what that means for the effort-level row

## Filed 2026-07-31 (lane A: inventory reconciliation, docs sweep, refutation repair)

Source: `docs/analysis/2026-07-31-inventory-reconciliation-and-the-docs-control-plane.md`.
Every row below was produced by running something today, not by reading a document.
Two rows above were CLOSED by the same measurement and are marked in place.

### Closed by this session

- [x] REFUTE-01 CLOSED 2026-07-31. The falsifier layer returned zero information on Linux: `refute.py run` reported `26 claims: 0 held, 0 REFUTED, 26 broken verifier`, one cause, every row declared `shell: "pwsh"` and neither pwsh nor powershell exists under WSL. The tool never lied (broken is not a pass, and it exits nonzero) but the layer was inert on the host the operator now works from. Two of the seven PowerShell-native verifiers were also AIMED at `$env:USERPROFILE\claude-setup`, the Windows clone, a different working tree. Now `21 held, 5 REFUTED, 0 broken`. Commit `aeaecd3`; 8 tests red before the fix; `mutate --spec refute` 12 of 12 caught
- [x] DOCS-01 CLOSED 2026-07-31. `docs/INDEX.md` listed 22 of 112 prose documents. Rewritten to 113 of 114 (it does not list itself), titles and declared statuses extracted from the files rather than written from memory, and it now passes `slop_lint` where before it had 43 em-dash hits

### Refutations: now visible. Each is a claim this repo makes that its own checker rejects

- [ ] REFUTE-02 C-012: live `~/.claude/CLAUDE.md` is DELETED and `settings.json` was rewritten (7440b to 6807b) since the 2026-07-29 baseline. The global instruction file the harness reasons about is gone and nothing noticed for two days. Decide: re-baseline (accepting the deletion as intended) or restore. NOT a code fix; needs the operator to say which
- [ ] REFUTE-03 C-025: the pre-write snapshot for the pending settings.json write is INCOMPLETE, many `agents/*.md` MISSING, so that write is not revertable from it. A rollback source recorded as present and measured as partial is the same class as C-012
- [ ] REFUTE-04 C-003: 1 of 12 live hook registrations does not resolve. `PreToolUse` points at `tools/hookgate/target/release/hookgate` and the checker finds no script path there. A hook that cannot run fails open and reports nothing
- [ ] REFUTE-05 C-015: `mutate --spec bus` fails against the current tree, so bus.py's selftest is no longer proven able to fail
- [ ] REFUTE-06 C-008: `hiring_engine/ledger.sqlite` is absent at the path the claim names. Lane B owns that ledger, so this is a proposal row for B, not lane A work

### The pattern the sweep found, and the phase it implies

- [ ] RATCHET-01 DECIDE, needs /diverge first (charters rule 2). Every defect found today is the same shape: **a number that is produced and then bound to nothing that stops.** `docmap` prints INDEX reachability at 3% and nothing fails. `pointers.py` counts 271 absent paths, exits FAIL, and is not a gate domain. `skills_sync` reports 49 drifted items and nothing fails. `refute` returned "unknown" 26 times for days. The proposal is a RATCHET (a number that may not get worse) attached to checks that already run, NOT a fourteenth gate domain: the count is already 13 and `docs/reflections/2026-07-29-what-is-going-wrong.md` section 4.2 warns against adding one
- [ ] RATCHET-02 `pointers.py` absent-path count moved 261 to 271 between 2026-07-29 and 2026-07-31, the only reconciled number that got WORSE, and it got worse with nobody watching. First ratchet candidate

### Docs control plane

- [ ] DOCS-02 `tools/slop_lint.py` has no notion of fenced code blocks. Confirmed by reading it: no `fence`, no backtick handling. It lints mermaid diagrams and code samples as prose, so `docs/SYSTEM-MAP.md` carries 5 unfixable hits inside its diagram's `subgraph` labels. Same false-positive class as the panel.py defect (L-2026-07-29-d), in this repo's own prose gate. Oracle edit: needs a regression test that pins a dash inside a fence as CLEAN and the identical dash outside it as a HIT
- [ ] DOCS-03 8 of 18 specs declare no `Status:` line: architecture-build-plan and its -v2, intent-traceability, trace-model-sacred-timeline, data-architecture-and-orchestration, agentic-directory-standard-sota, project-federation, research-corpus-and-cache. `docmap` passes them because it derives a class-based status, which answers what kind of document it is and never whether it is still true. The two architecture-build-plan files supersede each other by title and neither carries the fact
- [ ] DOCS-04 `docs/INDEX.md` has no generator and nothing fails when it drifts, so today's 113-of-114 coverage decays from the next document onward. Either generate it (like CODEBASE-MAP and DOCMAP) or ratchet the reachability number docmap already computes. Do not do both
- [ ] DOCS-05 `CLAUDE.md` says "the full 12-domain contract"; `quality-contract.json` declares 13. One-word fix, filed rather than done because CLAUDE.md is the file every session reads first and it deserves its own pass

### Prior art

- [ ] ABSORB-01 UPDATED 2026-07-31: the record count is 39, not the 27 the original row states, and the finding is unchanged. 0 of 39 carry an absorption field, including the one written this morning. Original row stands as written
- [x] ABSORB-09 CLOSED 2026-08-10 with ABSORB-01, one change, as this row asked. The
  sentence was kept and `verdict_class` added beside it. Grouped, the 41 records are 18
  split, 17 keep-ours, 2 build, 2 wrap, 1 absorb, 1 delete-ours, 0 adopt, which is the
  question that previously cost 41 file reads. I first wrote 17 and 16 here from the
  assignment table rather than from the written files, and the count disagreed; epic #29
  is the row that says any deliverable with more than five derived numbers gets a
  verification pass by something that cannot see the reasoning. Original row below.
- [ ] ABSORB-09 ORIGINAL ROW: `verdict` in the prior-art schema is FREE TEXT. 39 records carry 13 distinct values and four are sentences, including `keep-provisionally, and it is the weakest of the three records written today`. The prose is good and ungroupable, so "how many components did we decide to replace" needs 39 file reads. This is the identical defect `docs/specs/archive/2026-07-31-zion-board-as-product-instrument.md` diagnosed on the board, where hierarchy lived in an `EPIC:` title prefix GitHub could not group on. Same fix: keep the sentence, add the enumerated field beside it. Do this WITH ABSORB-01, one schema change, one backfill, one oracle edit
- [ ] ABSORB-10 (new) `tools/whatsapp` carries verdict `delete-ours` and still exists with 4 tracked files. A decision recorded and not executed is indistinguishable from a decision not taken. Either execute it or record why it was reversed

### Zion

- [x] ZION-01 **READ UNBLOCKED 2026-08-06.** The operator ran the refresh and the token now carries `read:project`. First live read of the board since 07-31: 31 items, 21 fields. **WRITE IS STILL BLOCKED**: `updateProjectV2` answers `INSUFFICIENT_SCOPES ... requires ['project']`, and the granted set is `gist, read:org, read:project, repo, workflow`. One more scope, `gh auth refresh -s project`, and it is operator-only for the same reason as before
- [x] ZION-02 **CLOSED 2026-08-06 by executing the publish, and `zion_fields.py` was
  never written because it would have written nothing.** The operator granted `project`
  and the one remaining command ran:
  `publish_backlog.py --source state/github-backlog-2026-07-31.json --project --fields --execute`.
  Issues **#49** and **#50** created, board **31 items to 33**, and the two new items
  verified against a live read carrying every field the JSON owns: `A harness` /
  `operator-only` on both, `P0` + `S3 60min` + `refuted` on the falsifier epic, `P1` +
  `S4 90min` + `measured` on the ratchet epic. All 33 items read `A harness`.
  The field sync for the other 31 was already complete before this ran, which is why the
  final plan reported `totals skip=165` with zero `set` rows. The tool that would have
  done the work is the tool that proved it was already done, which is the only reason not
  building `zion_fields.py` is a measurement rather than a guess.
  **ONE GAP, named rather than hidden:** `Estimate (min)` is empty on #49 and #50. The
  JSON carries `90 min` and `240 min` for them, but `publish_backlog.py --fields` owns
  five fields (Priority, Ingestion, Lane, Autonomy, Evidence state) and `Estimate` is not
  one of them, so 26 of 33 items have an estimate and the two newest do not. That is the
  tool's declared ownership working as written, not a failure, and closing the gap means
  widening `OWNED` rather than hand-setting a field.
  **WHAT IS LEFT IS NOT TOOLING:** `Status` is unset on all 33 items and 0 of 34 issues
  are closed. Nothing should write `Status` until the operator decides what it means on
  this board, because a status column filled in by a script is the same fiction as a lane
  value copied from a snapshot taken before the change it described.
- [x] ZION-03 **REFUTED 2026-08-06 by reading the board.** `Lane` is `A harness / B resume / C learning / D content` and every one of the 31 items reads `A harness`. The rename landed on 07-31 with option ids preserved, exactly as `docs/prior-art/tools-ghpub.json` recorded and as this row denied. The row was written from `state/backups/zion-project3-2026-07-31.json`, a PRE-change snapshot, and nobody re-read the live board for six days. Same class as the findings-go-stale lesson: a claim sourced from a snapshot taken before the change it describes. The board also carries `Evidence state` (unmeasured/asserted/measured/verified/refuted) as a 21st field, which that backup does not list, so the backup was stale in two ways

- [ ] **Doc structure and reachability are now enforced; absorption is not.** `tools/docmap/strand.py`
  landed 2026-08-03 with a selftest (5 assertions), 9 tests, and two CI steps. First real run
  found 10 structure violations (6 specs with no declared status, 4 with a status outside the
  vocabulary), all fixed, and **0 reachability strandings across 59 governed documents**. That
  zero is the finding: a hand pass the same day judged 7 of 37 analysis documents STRANDED by
  the stronger test, whether their findings ever reached a mechanism. **Link-counting cannot see
  a document that is linked and ignored**, which is stated in the tool's own docstring and in its
  report output. What would close the gap is an edge from a finding to the rule, hook or gate
  domain it produced, which is the cross-artifact graph row below, not more link checking.
- [ ] **The cross-artifact graph, not a code graph.** Prompted 2026-08-03 by Graphify (tree-sitter
  AST to knowledge graph, `EXTRACTED` vs `INFERRED` edge provenance, explicit refusal of a vector
  store). Code navigation is not this repo's measured failure: `codemap.py` covers 417 directories
  and ripgrep covers 23,736 lines. The measured failures are hidden trees and unabsorbed findings.
  The edges worth having are `file -> test that covers it`, `finding -> rule it produced`,
  `claim -> falsifier`, `directory -> prior-art record`. Three of those four already exist as
  one-off scripts; none is queryable. Adopt Graphify's edge-provenance tagging if this is built.
- [ ] **Metamorphic testing is absent, and it is the stronger check for the prose gate.** T5 of
  `docs/analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md`, stranded since it was
  written. `mutate.py` asks "if I break the check, does it notice". Metamorphic asks "if the input
  changes in a way that must not change the verdict, does the verdict hold". For `slop_lint` and
  `panel.py` that is the question that matters, and nothing asks it.

- [ ] **ADR-0021 landed; two preconditions it names are open.** Rust for hot paths, Python for
  oracles, criterion by failure mode. (1) `tools/hookgate` is the reference case and has **no
  selftest verb and is named in no test file**, measured 2026-08-03. A reference case with no
  oracle is the wrong reference. (2) A Rust `bus.py` would move the ledger from mutation-covered
  to mutation-uncovered, because `mutate.py` operates on Python source. `cargo-mutants` is named
  as the candidate and is **not adopted**. Both are blocking preconditions on the rewrite, not
  notes beside it.

- [ ] **57 saved repos captured, triaged once, never compared.**
  `state/saved-repos-2026-07-30.json`, referenced only by
  `docs/analysis/archive/2026-07-30-github-repo-triage.md`. Nothing consumes it, nothing resyncs
  it, and the comparison against current specs was scoped in that document and never run.
- [ ] **ShellCheck belongs in the new `supply-chain` CI job.** The recall hook calls bare
  `python`, which resolves to a `bootstrap.sh` shim; in a bare env `command -v python`
  finds nothing and the block ends in `|| echo '{}'`, so it fails silent. Prior-art
  checked 2026-08-04: this is the named fail-silent class, and the standard fixes are
  `set -euo pipefail`, a `#!/usr/bin/env bash` shebang, and ShellCheck in CI.
- [ ] **The model-selection rule's live-value rows are both stale, and its prescribed row is
  now right.** Live `effortLevel` is `high`, which is what the rule prescribes. The
  2026-07-29 section records live as `xhigh` and the 2026-07-30 correction records `low`.
  **The contradiction that rule exists to hold open closed by drift, not by measurement,
  and nothing recorded that it closed.**

## SETUP-PERSONA: reviewer allocation and identity (spec: docs/specs/2026-08-05-persona-allocation-and-reviewer-identity.md)

- [x] PERSONA-01: the allocator. `tools/review/allocate.py` maps a change to aspects and aspects to actors, decorrelating on `model_family` and never on `host`. Selftest green, 8 checks. It found its own defect on the first real run: it paired `nvidia-nim [VARIES-BY-MODEL]` with `qwen-dashscope [alibaba-qwen]` for `slop`, which is precisely the correlated pair `actors.json`'s contract forbids, because nvidia-nim serves qwen. A reseller family is now admissible only as a solitary reviewer
- [ ] PERSONA-02: **only ONE actor declares `a11y`**, so accessibility can never receive a decorrelated second opinion. This is a registry gap and it was invisible until something read `may_enact`. Either a second actor declares it or the enum admits that a11y is single-opinion by construction. Do not fix it by having the allocator pretend
- [ ] PERSONA-03: `panel.py` runs all five local personas on every change regardless of what changed. Wire it to consume `allocate.py`, so a diff touching only `.md` does not pay for the security rule set. Acceptance is a review artifact naming its allocated actors
- [x] PERSONA-11: the three greppable bans from the restored `boundary-contracts.md` are now enforced. New `boundary` persona in `panel.py` with go-discarded-marshal (HIGH), go-discarded-read (HIGH) and ts-unchecked-json-parse (MED). Go arrives as a fixture language for the first time, since no check declared it before. `tests/test_panel_boundary_bans.py` pins the NEGATIVE cases, which is the half that decides survival: `a, err := json.Marshal(...)` and `_, err := ...` must stay quiet, and so must prose about the ban, which is L-2026-07-31-b and has already cost three review waivers. 8 tests, 436 in the suite, 0 findings on this repo's own tree. Side effect worth naming: the panel/registry vocabulary overlap goes from 2 of 11 words to 3, because `boundary` now has a local rule set as well as four external actors declaring it, so `allocate.py` can plan both halves of one dimension
- [ ] PERSONA-12: **the boundary persona reimplements three mature tools, badly, and the PR said otherwise.** Prior-art gate fired; queries logged: `errcheck golangci-lint unchecked errors blank identifier assignment Go linter`, `typescript unchecked JSON.parse runtime validation zod eslint rule no-unsafe-json-parse`, `awesome static analysis linters list Go TypeScript error handling survey semgrep rules registry`. THREE not-a-gap signals fire: a curated awesome-list (analysis-tools-dev/static-analysis, richvred/awesome-linters, 111 Go tools catalogued), 2026 comparison surveys, and three tools naming the same problem. `errcheck` with `check-blank: true` IS go-discarded-marshal and go-discarded-read, done with type information instead of regex, and its own docs use `num, _ := strconv.Atoi(numStr)` as the example; `dogsled` covers the multi-blank form; `@typescript-eslint/no-unsafe-assignment` already flags the JSON.parse case because JSON.parse returns `any`; zod is the community answer for the actual fix; the Semgrep Registry has 2000+ rules and would express all three natively. WHAT SURVIVES: the panel reads added diff lines with no toolchain, no compilable package and no node_modules, which is the one thing none of those can do. So the persona is a FALLBACK for the diff-only case, not a replacement. ACTION: say so in panel.py, and for any repo that actually builds, recommend golangci-lint and typescript-eslint over these three regexes
- [ ] PERSONA-04: **the two persona vocabularies share 2 words out of 11.** panel has `data`, `ops_release`, `ux_frontend` that no external actor can enact; the registry has `boundary`, `simplicity`, `perf`, `slop`, `tests` that no local rule set covers. Decide whether they converge or stay deliberately separate, and write the reason down either way. `PANEL_TO_ASPECT` currently records two holes as `None` rather than guessing
- [ ] PERSONA-05: **ADR-0012's `auto:low` auto-merge is gated on a both-model approval that does not exist.** No `agreement` domain in the 14-domain contract, no implementation in `tools/`. Either build it on top of PERSONA-01, or amend ADR-0004 and ADR-0012 to record that it is designed and unbuilt. Doing neither leaves the governance docs describing a system nobody has, which is worse than having no docs
- [ ] PERSONA-06: run two allocated actors blind to each other on one real PR. Acceptance is a `state/reviews/*.json` whose `reviewer` is not `persona-panel/local`; all 11 existing artifacts say `external backend not requested`
- [ ] PERSONA-07: **every agent is `ShovalBenjer (User)`.** A GitHub App per lane gives feed comments and PRs a `[bot]` identity; free on a private repo and it sidesteps the free-plan branch-protection constraint ADR-0012 worked around. Attribute the action to the agent, record the owner as the accountable principal
- [ ] PERSONA-08: `from_session` is the empty string in all 25 bus rows. `bus.py:39` already documents why: `CLAUDE_SESSION_ID` is not exported into the hook environment. Settings change, not a design change. Note the field is inside `CHAIN_FIELDS`, so populating it changes what the chain covers going forward but not retroactively
- [ ] PERSONA-10: **decorrelation is DECLARED, not measured, and the literature says that is the wrong quantity.** `Nine Judges, Two Effective Votes` (arXiv 2605.29800) puts a number on it: family-correlated errors reduce a nine-judge panel to 2.5-3.6 effective voters. `Hidden Clones` (arXiv 2603.17111) does it properly with Hierarchical Family Voting and inverse-family-size weighting, and the information-theoretic selection work says correlation matters while accuracy does not. `allocate.py` hard-codes a hand-declared family string as a proxy. The substrate to do it right already exists: run two actors on the same diff, record whether they flag the same lines in `state/reviews/*.json`, and observe the correlation. Blocks on PERSONA-06 (nothing external has ever reviewed). Prior-art queries logged in the spec §3a
- [ ] PERSONA-09: NOT a task, recorded so it is not proposed again. Do not build JWS signing over bus rows. Hash-chaining gives tamper-evidence and not authorship, which is a real gap, but the value here is attribution and not authentication: one human, one machine, no adversary. A2A's signature layer solves a cross-organisation trust problem this estate does not have (ADR-0019: adopt on recorded evidence)

- [x] **WITHDRAWN, filed and retracted within ten minutes on 2026-08-05.** I reported that `strand.py` declares `NOT_A_CONSUMER` and never applies it. It does apply it, at line 199 inside `evaluate()`, one layer after `build_reference_index` where I was looking. The reason I filed it at all is the useful part: my fixture written to reproduce the bug PASSED BEFORE my fix, which is the signal that there was no bug, and I nearly shipped an oracle edit plus two tests that passed for the wrong reason. A parallel session had already pinned the real behaviour properly in `test_generated_inventories_are_not_consumers` and `test_the_exemption_ledger_is_not_a_consumer`. Left in the ledger rather than deleted, because a retraction that vanishes teaches nothing.

## 2026-08-05 session close (lane A): what is red, what is proven, what is next

Ordered by whether it currently blocks a session. Every claim below names the command
that produced it; where a number is asserted rather than measured it says so.

### Blocking now

- [ ] **Nothing enforces the imported standards, and the topology is now measured.**
      See [analysis/2026-08-05-enforcement-topology-measured.md](analysis/2026-08-05-enforcement-topology-measured.md)
      for the five diagrams and the numbers. Headline: 22 global rules and 7 hook events
      load in every session in every repo; all three repos declare a `quality-contract.json`
      and only `claude-setup` has ever run one, with `new-recruit` and `daily-deep-learning`
      at ZERO rows in `state/gate-runs.jsonl`. `code-quality-standard`, `harness-structure`
      and `repo-standards` have zero executable references each, so a standard here must
      have a status and be reachable while nothing reads what it says. 8 of 21 ADRs are
      named by an oracle; 13 by nothing.

- [ ] **The `review` CI job posts "Claude encountered an error after ~40s" on every run
      and exits 1, with the error swallowed by the action.** Four theories tested and
      discarded: the `CLAUDE_CODE_OAUTH_TOKEN` secret exists (set 2026-07-23), the action
      resolves, the repo ships no project-level `.claude/settings.json` so its own Stop
      hooks are not blocking its reviewer, and the action completes its GitHub-side work
      (it posts and updates the PR comment) before failing. `ANTHROPIC_LOG=debug` is now
      set on the step so the next red run names its own cause. NEXT ACTION: read that run,
      do not add a fifth theory. Most likely remaining candidate is the OAuth token, which
      only the operator can rotate.
- [ ] **`skills` domain is waived to 2026-08-12 at 51 items, and 34 of them are the real
      problem.** 34 skills are COMMITTED BUT NOT DEPLOYED, so no session can invoke or read
      them: `ui-ux-pro-max` 527 body lines, `review` 244, `testing-pyramid` 175,
      `pii-scrubber` 172. Seven of those additionally carry dead paths into `~/.codex/` or
      `/home/shovalbe`. The other 17 are genuine repo-vs-live content differences needing a
      per-skill decision. Deploying 34 skills is a live-tree change; `skills_sync.py`'s own
      docstring argues a hollow deployed skill is worse than an absent one, so the seven
      dead-path ones must be repaired before deploy, not deployed as-is.
      Confirm with `python tools/audit/skills_sync.py check`, expect `DRIFT: 51`.

### Refuted claims, measured 2026-08-05 by `python tools/refute/refute.py run` (22 held, 4 refuted)

- [ ] **C-012 refuted for the second time today.** `~/.claude/settings.json` was rewritten
      again at 16:08:19 (6808b to 7001b) against a baseline taken 2026-08-03T13:43:21. Six
      concurrent sessions is normal here. Re-read live config from disk before trusting
      injected context; `--record` only after reading what changed.
- [ ] **C-009: a cdp doc still points at the other machine's `shoval.be` profile.**
- [ ] **C-025: the pre-write snapshot is missing six `agents/` files**, so the
      2026-08-01 `settings.json` rewrite is still not revertable.
- [ ] **C-008: the hiring funnel's phantom `ab_results.csv` ledger.** Lane B, not lane A.

### Proven fixed this session, listed so nobody re-opens them

- [x] **`supply-chain` CI job.** Asked for `google/osv-scanner-action@v2`, a tag that project
      has never published, so it died on action resolution before running a step.
      `continue-on-error` did not help: that governs a step's outcome, not the runner's
      ability to resolve an action. Pinned to `v2.3.8`. It now passes, 1m13s, first time ever.
- [x] **codemap flipping red on the gate's own next run.** `state/reviews` carried a file
      count in `CODEBASE-MAP.md` and `panel.py` writes one JSON per commit sha, so every
      commit moved the count. Cost four regenerate-commit cycles before the mechanism was
      named. NOTE a correction: I "disproved" this earlier by running `panel.py` against a
      sha that already had an artifact, so it overwrote and the count never moved. That test
      did not discriminate and my disproof was wrong. Fixed by gitignoring
      `state/reviews/*.json` plus a `.gitkeep`, since `gate.py:204` already treats the
      directory as its own exhaust and `ship-gate.yml:116` regenerates it in CI. PROVEN: two
      consecutive `gate.py run` invocations, codemap red in neither.
- [x] **Four of the 55 skills-drift items were comparator bugs.** `sha()` hashed raw bytes,
      so a CRLF live file and an LF repo file that are character-identical read as drift:
      `brainstorming`, `explain-simply`, `persona`, `shoval-voice-draft`. Now reported under
      LINE ENDINGS ONLY and excluded from the failing count. Selftest case 14 pins both
      directions and was red before the fix.
- [x] **`rules.rs` was generated from a file that was not the committed one.**
      `regen_rules.py` prefers the LIVE `~/.claude/hooks/safety_gate.py`, which had been
      refined to allow `--force-with-lease` while blocking bare `--force`; the repo copy
      still blocked both. Regenerated and the repo copy imported so source and output agree
      in-tree. `diff_oracle.py`: exact agreement on all 128 commands, 0 security regressions.
- [x] **`pointers` waiver deleted rather than renewed.** I had wired the domain on a local
      exit 0 that became exit 1 on the runner. A parallel session implemented the fix the
      waiver named and improved it, keying the guard on `~/.claude/settings.json` existing
      rather than the directory, because a runner creates the empty directory. Verified
      against `HOME=/tmp/fakehome-no-claude`.

### Withdrawn: kept visible

- [x] **WITHDRAWN: `strand.py` `NOT_A_CONSUMER` declared-but-unapplied.** It is applied, at
      line 199 in `evaluate()`, one layer past where I was reading. The tell was that my
      fixture passed BEFORE my fix. I nearly shipped an oracle edit plus two tests that
      passed for the wrong reason. A parallel session had already pinned the real behaviour.

### The imported research corpus, which is the reason this section cites paths

Ten documents arrived from `new-recruit` and `daily-deep-learning` as evidence and were
stranded: nothing outside `docs/INDEX.md` referenced them, and an exemption block for them
was added and then removed by a parallel session. `docs/strand-exempt.txt` says not to add a
line to make a check go green but to link the document from a surface that gets read. This
is that surface, and each is named with what it is for.

- [ ] **Bind the imported standards to something.** They are read, not maintained, and
      nothing in this repo's oracles consults any of them.
      Speech and research provenance: [ddl-deep-research-2026-07-27.md](analysis/reference/ddl-deep-research-2026-07-27.md),
      [ddl-design-research-nextgen-2026-07.md](analysis/reference/ddl-design-research-nextgen-2026-07.md),
      [ddl-engine-research-prompt-2026-07-24-v3.md](analysis/reference/ddl-engine-research-prompt-2026-07-24-v3.md),
      [ddl-standard-and-grade-2026-07-29.md](analysis/reference/ddl-standard-and-grade-2026-07-29.md),
      [ddl-ui-deep-research-arkheron.md](analysis/reference/ddl-ui-deep-research-arkheron.md).
      Harness and tooling research: [nr-claudecode-tui-research-2026-06-14.md](analysis/reference/nr-claudecode-tui-research-2026-06-14.md),
      [nr-commit-bug-tracing-research-2026-07-05.md](analysis/reference/nr-commit-bug-tracing-research-2026-07-05.md),
      [nr-coverage-aware-eval-research-2026-06-28.md](analysis/reference/nr-coverage-aware-eval-research-2026-06-28.md),
      [nr-technology-corpus-master-prompt-2026-07-24.md](analysis/reference/nr-technology-corpus-master-prompt-2026-07-24.md),
      [nr-technology-corpus-research-report-2026-07-25.md](analysis/reference/nr-technology-corpus-research-report-2026-07-25.md).
- [ ] **The size standard those documents carry is not enforced anywhere.** Module hard
      limit 500 lines, function target 20, hard limit 50. Measured against `tools/**/*.py`
      by AST, 96 modules and 678 functions: 14 modules over 500, 71 functions over 50
      (10.5%), 447 within the 20 target (65.9%). Nine of the ten longest functions are
      `cmd_selftest`, headed by `tools/bus/bus.py:589` at **614 lines** with 37 branches and
      330 calls, 56% literal. The fixture-table defence predicts the longest should be the
      most literal; measured, it is the least. `quality-contract.json` has no size or
      complexity domain at all, and the 300-line `prior_art` threshold is a build-vs-buy
      trigger rather than a size budget despite sharing a number.

### Still open from the prior handoff, unchanged

- [ ] **Row B: 45 skills forked across three trees**, `dot-claude/` canonical because it is
      the only tree with a live counterpart. Each fork needs a recorded decision; picking by
      timestamp is not a decision. Expect a session on its own.
- [ ] **`state/claims.jsonl` has two incompatible row shapes.** Older rows key on
      `proposal_id` with `ts`, newer on `id` with `claimed_at`. A reader expecting one
      silently drops the other.
- [ ] **Three bodies of work landed unclaimed today.** The four 2026-08-03 PRD/spec
      documents, the `tools/antigravity` component, and the docmap strand tooling. Charters
      rule 1 is claim-before-starting and it is the most-logged lesson in the repo.
- [ ] **The LightRAG-vs-sqlite-first contradiction is still unresolved.**
      `docs/archive/gemini-code-1785457549011.md` specs a three-layer vector/graph RAG engine;
      `intent-control-plane/docs/specs/2026-07-11-self-evolving-depth-harness.md` AC-K3
      makes that a non-goal. Neither document references the other. Measured corpus stats
      and the falsifiers that would flip the recommendation are in
      [analysis/2026-08-06-memory-rag-substrate-findings.md](analysis/2026-08-06-memory-rag-substrate-findings.md).

### Modules over the imported 500-line hard limit (15 as of 2026-08-06, was 14 on 08-05)

The standard is `docs/standards/nr-code-quality-standard-2026-07.md`: module hard limit
500, function target 20, hard limit 50. `quality-contract.json` has no size domain, so
none of this is enforced. Filed as rows because a finding in prose is not a backlog.

- [ ] `tools/gate/gate.py` is **1451 lines**, over the 500 limit by 951. worst function `cmd_selftest` at 305 lines
- [ ] `tools/review/panel.py` is **1387 lines**, over the 500 limit by 887. worst function `cmd_selftest` at 330 lines
- [ ] `tools/bus/bus.py` is **1244 lines**, over the 500 limit by 744. worst function `cmd_selftest` at 614 lines
- [ ] `tools/e2e/flow.py` is **1144 lines**, over the 500 limit by 644. worst function `cmd_selftest` at 93 lines
- [ ] `tools/snapshot/snap.py` is **827 lines**, over the 500 limit by 327. worst function `cmd_selftest` at 354 lines
- [ ] `tools/supply/verify.py` is **808 lines**, over the 500 limit by 308. worst function `cmd_selftest` at 158 lines
- [ ] `tools/audit/skills_sync.py` is **752 lines**, over the 500 limit by 252. worst function `cmd_selftest` at 253 lines
- [ ] `tools/browser/cdp.py` is **739 lines**, over the 500 limit by 239. worst function `launch` at 60 lines
- [ ] `tools/timetravel/snapshot.py` is **725 lines**, over the 500 limit by 225. worst function `cmd_selftest` at 174 lines
- [ ] `tools/skilleval/run.py` is **579 lines**, over the 500 limit by 79. worst function `selftest` at 200 lines
- [ ] `tools/audit/pointers.py` is **571 lines**, over the 500 limit by 71. worst function `cmd_selftest` at 103 lines
- [ ] `tools/docmap/docmap.py` is **533 lines**, over the 500 limit by 33. worst function `selftest` at 98 lines
- [ ] `tools/map/codemap.py` is **521 lines**, over the 500 limit by 21. worst function `cmd_selftest` at 85 lines
- [ ] `tools/refute/refute.py` is **510 lines**, over the 500 limit by 10. worst function `cmd_selftest` at 183 lines

- [ ] **daily-deep-learning's contract reaches into a STALE clone.** Its `review` and `e2e`
      domains shell out to `C:/Users/shova/claude-setup/tools/...`, which resolves through
      `/mnt/c` to the third clone, HEAD `f5d697e`. That clone predates today's panel.py
      fixes, so ddl's review domain runs an oracle without the comment-strip or sql-concat
      corrections. Superseded by the central-sweep decision in docs/taste.md 2026-08-05.
- [ ] **Two daily-deep-learning waivers expire today, 2026-08-05: `e2e` and `a11y_ux`.**
      A third, `pipeline`, expires 2026-08-10. Nobody will notice, because that repo has
      never run its contract: zero rows in its `state/gate-runs.jsonl`.
- [x] **WITHDRAWN: 'required reviewers are impossible on this plan'.** I reported branch
      protection as unavailable because `gh api .../branches/main/protection` returned 403
      'Upgrade to GitHub Pro or make this repository public'. The API response is real; the
      CONCLUSION was wrong, because a parallel session is already working the reviewer
      surface. A 403 from one endpoint is evidence about that endpoint, not about whether
      the capability exists. Owner: the other session, not this row.
- [x] **RESOLVED: `gh` now has `read:project`.** Zion is readable: 31 items, all Issues,
      and **all 31 carry no status field at all**, which is why the board reads as zero
      throughput. Nothing is In Progress because nothing has ever been moved out of the
      default column. Discussions and Wiki remain disabled.
- [ ] ~~GitHub Discussions and Wiki are both disabled~~ superseded by the row above; Issues (32 open) and Projects are
      on. If Zion is the board, `gh` needs `read:project` scope before any session can read
      it: `gh auth refresh -s read:project`.

## From the 2026-08-06 external source read (see `docs/analysis/archive/2026-08-06-external-repo-source-read-and-surface-comparison.md`, ledger `state/external-repos.jsonl`)

- [ ] **`a2a-codex-call.sh` corrupts peer responses and no domain looks at it.** VERIFIED
      2026-08-06: the response JSON is built by interpolating shell variables into a
      `python -c` template (lines 128-146), so the peer's text is parsed as a Python string
      literal. Literal `\x41` in a Codex review arrives as `A`; `\t` becomes a tab; a
      Windows path loses its separators. This fails `boundary-contracts.md` points 1, 2 and
      3 in one file. **Fix is 5 lines** (build a dict, `json.dumps` it, pass the text through
      stdin or an env var rather than the source template). Do that before deciding anything
      about ACP. **Acceptance: a test feeding `\x41`, `\t` and `C:\new` through the bridge
      and asserting byte-identical round-trip.**
- [ ] **The prose gate detects 20 lexical patterns and zero rhetorical ones.**
      `petergyang/no-ai-slop` (MIT, so patterns are copyable) names 18 structural patterns
      with rewrite examples; our output-style file already names several and `slop_lint.py`
      cannot see any. About 8 are regex-able: summary-recap openers, rhetorical setups,
      weasel attribution, faux-insight setups, the trailing `-ing` clause, negative listing,
      colon reveals, binary contrast. **Add them as a separate class from `BANNED_PHRASES`
      so a structural hit reports as structural.** Their `eval.md` (a checklist the model
      runs against its own output) is the shape of the unbuilt `dod.py`.
- [ ] **No oracle relates a requirement to a task.** `strand.py` checks status and
      reachability and says in its own docstring that reachability "cannot catch a document
      that is linked and ignored". `github/spec-kit`'s `analyze` supplies the missing shape:
      duplication / ambiguity / underspecification / coverage-gap / inconsistency, severity
      where a constitution MUST violation is automatically CRITICAL, and a coverage
      percentage of requirements with at least one task. **Depends on the existing
      "classify the 48 definition-of-done rows" row; do that first.**
- [ ] **`state/deploy-manifest.tsv` records bytes, not the install.** 84 rows of
      `sha256 <tab> path`, last written 2026-07-31. `affaan-m/ECC` (MIT) requires
      `install-state.v1` with request, resolution, source, operations and `lastValidatedAt`,
      and a `provenance` record with source, created_at, confidence and author on every
      imported skill. **Provenance is the direct answer to the 45 forks**: a fork with a
      recorded source is a merge decision with evidence, which is what the existing row
      means by "picking by timestamp is not a decision".
- [ ] **Three lanes, three repos, no shared architectural view.**
      `docs/specs/2026-07-31-project-federation.md` wants one. `reposwarm/reposwarm`
      (Apache-2.0) generates one `.arch.md` per repo into a central hub and re-analyzes only
      repos whose HEAD moved, with prompt selection driven by a declarative pattern file.
      `codemap.py` is directory-granularity and single-repo by construction. **The
      incremental rule is the part that makes it affordable.**
- [ ] **103 of 115 rows in `state/external-repos.jsonl` are `untriaged`.** 10 repositories
      were read at source on 2026-08-06. `aaif-goose/goose` and `MemPalace/mempalace` are
      cloned and unread. 138 community-shared repositories are resolved and unevaluated.
      **This row exists so the 10 are not read as the whole set.**
- [ ] **STILL OPEN, operator decision, raised 2026-07-30:**
      `docs/analysis/reference/coherence-governor-AGENTS.md`, 17,923 bytes copied verbatim
      from `Master0fFate/just-my-skills`, which still resolves `license: NONE` on 2026-08-06.
      Summarize-and-link, ask for a licence, or accept that this repository cannot go public.

## From the 2026-08-12/13 point-in-time scans

- [ ] **Official `anthropics/claude-code` vs this harness, surface by surface.**
      `docs/analysis/2026-08-12-claude-code-repo-gap.md` reads the public reference repo
      (plugins/examples, not the closed CLI binary) and scores every surface HAVE / PARTIAL /
      LACK / NON-GAP against what this harness already ships. Real gaps found: no
      plugin-authoring skill, no NL-to-hook authoring flow, no guided model-migration skill,
      no differentiated settings profiles (lax/strict/sandbox). Pick up any LACK row here
      before assuming the harness needs it from scratch.
- [ ] **Where the repo's prose/config bloat actually lives (it is not the code).**
      `docs/analysis/2026-08-12-minimalism-audit.md` spot-checked `tools/*.py` (gate.py,
      panel.py, bus.py) for the ponytail lens and found it clean; the recoverable tax is
      per-session prose (`dot-claude/rules/`, ~11,300 words/session, 30-40% recoverable) and
      skill `description:` frontmatter (~60% recoverable). One cut already applied
      (`ui-ux-pro-max`, 119 to 62 words, lossless). The batch pass over the next 14 fattest
      skills is the open follow-on.
- [ ] **Adopt `block/buzz` (Apache-2.0, Rust, self-hostable agent/human workspace) as the
      target UI, not the stdlib Session Lens.** `docs/analysis/2026-08-13-buzz-adoption-handoff.md`
      is the operator's own correction ("the html you wrote is miles away from a polished
      buzz") plus the four-step next-session plan: self-host, wire one session in as an
      agent per `VISION_AGENT.md`, map `state/bus.jsonl` onto its Nostr-relay event log
      (bridge vs replace), then customize. `tools/dashboard` (Session Lens) stays a stopgap
      baseline only; do not extend it further pending this decision.
- [ ] **Cross-project tech-stack and code-quality rethink, seeded but not yet a PRD.**
      `docs/specs/2026-08-13-code-quality-rethink.md` captures the operator's verbatim
      directives: rethink stack choices across all projects, question convention defaults
      (one-line vs full docstrings), add a simulation ladder (static -> compile -> runtime ->
      container -> E2E) to the testing pyramid, and close the gap against named pedagogy
      (Matt Pocock, Andrej Karpathy, BetterStack). No PRD exists yet; this spec is the seed
      and names the research agents to run before one is written.

## 2026-08-23 (lane A): prompts triaged, docs archived, WhatsApp links ledgered

- [ ] **Every claude-setup prompt now has a checklist box on one of 18 themed issues,
      #91 to #108.** Method and counts in `docs/analysis/2026-08-23-prompt-triage.md`.
      The generated block below groups tickets by issue. Next: a session per theme moves
      boxes to OPEN by picking them up; nothing is OPEN yet. Todoist import CSV sits at
      `~/.intent/exports/todoist-import-2026-08-23.csv` (prompt text stays out of git).
- [ ] **Saved-link triage, issue #90.** 15 WhatsApp repos and 9 links with no verdict;
      `docs/analysis/2026-08-23-whatsapp-links-vs-plan.md`. 113 of 125 external-repo rows
      are `untriaged`; the absorption loop stopped on 2026-08-05.
- [x] **docs/books is queryable end to end**: 22 PDFs extracted, 323 txt indexed,
      `tools/corpus/books_check.py` clean. Decision and what stays unreadable (4 mobi,
      1 djvu, duplicates) in `docs/analysis/2026-08-23-books-corpus-wiring.md`.
- [ ] **Dedup the books corpus by content hash** in books-ingest (TDA twice, Grohs and
      Kutyniok three times); install calibre for the 4 mobi, djvulibre for the 1 djvu.
- [ ] **Build the dashboard SQL tab on the stack decided in
      `docs/analysis/2026-08-23-dashboard-stack-and-supply-chain.md`**: rusqlite
      read-only per command, `SqlError` via thiserror across IPC, notify-debounced
      ledger watch pushing Emitter events, tracing on the query path. bun is the web
      package manager (bun.lock, bunfig cooldown, CI on setup-bun). Open from that doc:
      a gate domain for `supply/verify.py verify-ledger`, cosign via TUF bootstrap,
      osv-scanner.
- [ ] **Pocock adopt queue from `docs/analysis/2026-08-23-pocock-skills-delta.md`**:
      wait-what imported and live; still open: to-questionnaire (renders
      accepting-architectures blocks as a fillable form), wizard (generates the bash
      walkthrough for NEEDS OPERATOR steps), resolving-merge-conflicts. Also still open,
      third scan running: the five 08-01 teardown follow-ups (description pruning,
      buckets, negation audit, wayfinder-onto-Zion, router freshness), zero of five done.
- [ ] **`resources.py verify` breaks at row 3893 and nothing runs it** (L-2026-08-23-a).
      Decide: add it to the gate as a domain, or stop calling the ledger chained.
- [x] docs/ root went from 43 files to 18; 25 point-in-time files moved to `docs/archive/`,
      37 analysis snapshots dated on or before 2026-08-08 with no live referrer to
      `docs/analysis/archive/`, 2 self-declared superseded specs to `docs/specs/archive/`.
      References rewritten in 27 files; docmap treats `docs/archive/` as historical-record.

<!-- prompt-tickets:begin generated by tools/intent/render_todo.py, do not hand-edit -->

## Prompt inbox: claude-setup

354 prompts across 44 sessions. 0 workable, 0 awaiting triage (newest n/a), 0 classified as slash commands or acks by rule.

### Triaged into checklist issues, 219 prompts

One box per prompt lives on the issue; the ticket's state moves when the box does. 135 prompts were marked not work (acks, status checks, notifications).

- #94: 32 prompts
- #108: 29 prompts
- #93: 20 prompts
- #99: 18 prompts
- #101: 17 prompts
- #92: 16 prompts
- #91: 15 prompts
- #97: 14 prompts
- #100: 12 prompts
- #98: 12 prompts
- #102: 9 prompts
- #103: 7 prompts
- #106: 7 prompts
- #95: 6 prompts
- #96: 3 prompts
- #105: 2 prompts

<!-- prompt-tickets:end -->

- [x] lane A: ship_gate_stop.py committed-docs-only case. DONE 2026-08-13, commit b43b570 on worktree-repo-gap-analysis, live hook updated. The 2026-08-13 docs-only fix
  classifies the WORKING diff vs HEAD, so a clean tree whose only delta since the last
  gated run is committed docs (e.g. regenerated maps) still hard-blocks. Extend
  is_docs_only to diff HEAD against the last gate-runs.jsonl row's commit for this
  project and downgrade when that delta is all prose. Regression test exists at
  tests/test_ship_gate_docs_only.py to extend.

- [ ] EXT-7 Gate-run hash-chaining, sabotage-resistance for the reporting chain
  (2026-08-19, external review via Agentica after reading CTRL-ALT-DECEIT: Sabotage
  Evaluations for Automated AI R&D, arXiv 2511.09904): the agent that writes code,
  runs the gate, interprets output, and reports the verdict is one trust domain with
  no separation of privilege. Filed as its own ticket rather than folded into PR #87,
  since bundling more scope into a PR the same agent authored is exactly the pattern
  Agentica's fifth point warns against (agents should not be able to expand their own
  evaluation criteria unchecked). Proposed scope: extend the existing bus.jsonl
  hash-chain pattern to gate EXECUTIONS, not just code artifacts, so every gate.py run
  writes a signed append-only record (commit, config version, raw-output hash),
  independently checkable against what gets reported in chat. Operator decision
  needed: build now, defer, or decline. Recovered 2026-08-23 from
  worktree-rules-sync-repo-stack-reasoning before that chain (5 branches, superseded
  by PR #86 for its dashboard work and by the 2026-08-19 EXT-1/EXT-3 gate contract
  entries for the rest) was deleted; this was the one genuinely un-landed item in it.

- [ ] Issue and milestone reasoning is done, GitHub writes are not. See
  `docs/analysis/2026-08-23-issue-and-milestone-reasoning.md` for the full pass
  over all 56 open issues: which of the 33 milestone-linked EPICs are still live
  vs done vs under-evidenced, why M1-M5 are kept, why the T01-T18 prompt-triage
  series (created 2026-08-23, sourced from the operator's own words via
  ~/.intent/intent.db) is the freshest layer and should get `related:` links to
  the EPICs it overlaps, and the root finding that `state/prompt-tickets.jsonl`
  is 2313 rows 100% still CAPTURED with zero ever transitioned to TRIAGED. No
  issue was closed or edited by that pass; it ends with a proposed-next-action
  list awaiting operator sign-off.
