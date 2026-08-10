# Milestone task plan, 2026-08-10

Status: active. Supersedes nothing. Re-derive before acting if the date above is more
than a week old, because half the rows below were produced by running a command and the
other half by reading a board that was published on 2026-07-31.

Lane A. Claim row `session-2026-08-10-milestone-task-plan` in `state/claims.jsonl`.

## What this is and how it was produced

One ordered task list across four sources that had never been reconciled against each
other: the 21 specs and 5 PRDs under `docs/`, the 137 open rows in `TODO.md`, the 37 open
GitHub issues of which 33 are Zion epics carrying 184 checklist items, and the 6 unmerged
pull requests. The milestones are the Zion board's own M1 to M5, plus an M0 that the board
does not have and needs, because six branches of finished work are sitting unmerged and
every one of them changes what the other milestones say.

Nothing here closes an issue, edits an issue body, or touches the backlog JSON. Per the
Zion spec section 6 the JSON is edited and then published by `tools/ghpub/publish_backlog.py`,
and ZION-01 is still blocked on the `read:project` token scope, so a hand edit now would be
drift with no diff.

### Host caveat, stated first because two numbers below are worthless without it

This ran in a remote container, not the operator's WSL host. `~/.claude` here holds a
container-local `skills/` tree and **no `settings.json` at all**. So:

- `skills_sync.py check` printing `DRIFT: 87` is a fact about this container and says
  nothing about the operator's drift, which the contract records as 28.
- `refute.py run` reporting `26 claims: 16 held, 10 REFUTED, 0 broken verifier` is the
  same. Nine of the ten refutations are claims about live hooks, live personas and live
  settings, none of which exist here. This is lesson class L-2026-07-31-g and the readings
  are labelled rather than filed.

The readings that are host independent, and therefore real: `codemap.py check` clean at
416 directories, `pointers.py scan` PASS, `gate.py status`, the contract's domain count,
and everything read out of git or the GitHub API.

## Ground truth measured 2026-08-10

| what | measured | the repo currently says |
|---|---|---|
| gate verdict | `PARTIAL` at `2026-08-08T01:33`, tree `9601c905`; current tree has never been gated | last verdict is the only status surface |
| contract domains | **16** | `AGENTS.md` says 12, `TODO.md` DOCS-05 says 13, PR 59 implies 14 |
| waivers live | exactly one, `skills`, expiring **2026-08-12** with `confirm: "DRIFT: 28"` | TODO carries three historical waiver rows as if open |
| open issues | 37, of which **33 are Zion epics** | TODO says 31 epics |
| checklist items | 184 across the epics, 5 checked | same, and still accurate |
| open PRs | **6**, oldest 2026-08-05 | TODO names none of them |
| open TODO rows | 137 | the FOG header says 133, itself a correction of 96 |
| prior-art records | 41, earliest expiry 2026-09-07 | TODO ABSORB-01 says 39, itself a correction of 27 |
| codemap | clean, 416 directories | matches |
| pointers | PASS, 2 Windows-path findings skipped on this host | Zion #6 says 271 absent paths and not a gate domain |

## Corrections: board rows that measurement now contradicts

These are the rows to fix in `state/github-backlog-2026-07-31.json` on the next publish.
Listing them is the cheap half; the publish is ZION-02 and is blocked.

1. **#20 "Write gemini-review.yml ... has still never been written".** It is on disk at
   `.github/workflows/gemini-review.yml` and the `pipeline` domain names it. Already noted
   in TODO; still unfixed on the board.
2. **#20 "Push ship-gate.yml and observe one real CI run".** It ran, four times red, then
   green on main 2026-08-03. The live successor is per branch, not per workflow.
3. **#6 "pointers.py counts 271 absent paths and is not a gate domain".** `pointers` is a
   domain in `quality-contract.json` and the scan returns PASS.
4. **#4 "26 claims, 22 held, 2 refuted, 2 broken. A broken verifier is unknown".** Broken
   is now 0 on every host measured since 2026-07-31.
5. **#28 "The review waiver expires 2026-08-02".** It was removed rather than renewed. The
   only waiver left is `skills`.
6. **#50 and #6 quote skills drift at 49, 51, 52 and 55.** The contract records 28. Four of
   the original 55 were a comparator bug over line endings.
7. **Every epic's `Lane` field is one cutover behind ADR-0016.** The board selects B/C/D/E;
   the lanes are A/B/C/D. This is ZION-03 and it makes every lane value on the board
   ambiguous in exactly the way `docs/charters.md` warns about.

## M0. Unmerged work, which is not a milestone the board has

Six branches carry finished, evidenced work. Four are drafts, two are ready. Three of the
six report `mergeable_state: dirty`, meaning they need a base merge before anything else.
This is the highest-value milestone on the page because merging it deletes rows from the
others.

- [ ] **PR 59, `na-domains-and-run-duration`, ready, clean, CI pending.** Gate runs now
  record `duration_seconds` and `domain_seconds`, which is what makes the `unit` domain's
  own 900-second falsifier evaluable for the first time across 8571 rows. First
  measurement 208.6s total, `unit` 153.7s. Also corrects the `perf` N/A reason and carries
  the connector and Zion inheritance reports. **Merge this first**: it is clean, it is not
  a draft, and 14 review comments are already resolved against it.
- [ ] **PR 60, `session-prompt-db-and-per-project-todo`, draft, clean.** Recovers ten days
  of prompt text that a `ModuleNotFoundError` under the wrong interpreter silently dropped,
  545 hashes against 23 events. Backfills 1,127 events over 191 sessions with a verified
  chain, and gives each project its own TODO inbox between markers. Decide the one open
  question in its own "not in scope" list: whether `render_todo.py --check` joins the gate
  `docs` domain, which turns one finding into an estate-wide red until every repo has the
  block.
- [ ] **PR 42, `boundary-contract-bans`, ready, dirty.** Three greppable bans so the
  restored `boundary-contracts.md` can fail something, plus Go as a fixture language for
  the first time. Needs a base merge. Blocked behind nothing else.
- [ ] **PR 47, `skill-dependency-filter`, draft, dirty, gate FAIL on `unit`.** The finding
  is worth the merge on its own: the filter written to reject a Notion-shaped skill rejects
  26 of our own 71, of which 11 are hard dependencies on an absent `az`. Blocked on
  **HOOKGATE-01**, an operator call, below.
- [ ] **PR 53, `session-corpus-extractor`, draft, dirty.** Conversational corpus extractor,
  1,108 unique turns. Overlaps PR 47 and PR 60 on the hookgate fix and the waiver removal,
  so merge order matters: 59, then 60, then 42, then whichever of 47 and 53 goes first
  rebases the other.
- [ ] **PR 52, `wsl-windows-cdp-bridge`, draft.** Bridges Claude in Chrome from WSL to
  Windows Chrome. Oldest untouched branch, last updated 2026-08-06. Decide: finish or close.
- [ ] **Decide the branch policy that produced this pile.** Six branches, five of them
  touching `quality-contract.json` or the hookgate, is the same one-tree race that issue
  #58 filed against two sessions sharing a checkout and that ABSORB-03 names for subagents.

## M1. Instruments trustworthy

The largest milestone, 14 epics. The theme holds: an oracle that runs is worth more than
one that is designed, and a number that is produced and bound to nothing is the repeating
defect.

### Blocking now

- [ ] **The `skills` waiver expires 2026-08-12, in two days, and was deliberately not
  extended** (#28, TODO A2). 13 of the differences are the single line
  `disable-model-invocation: true`, added to the repo copies by `3df7704` and never
  deployed, so live currently auto-invokes 13 skills the repo says it should not.
  Deploying is a live-tree behaviour change and is the operator's. Three outcomes are
  legitimate: deploy and let the waiver lapse, restate the waiver with a true number and a
  burn-down, or let it expire red on purpose.
- [ ] **The waiver's `confirm` string is host-shaped.** It pins `DRIFT: 28`; this container
  prints 87. The `exit 2 means cannot-measure` path added on 2026-08-07 covers a missing
  tree, not a present-but-different one, so a CI runner with a partial `~/.claude` fails the
  domain for a reason unrelated to drift. Extend the structural read or pin the confirm to
  a host-independent substring.
- [ ] **HOOKGATE-01, operator call, blocks PR 47 and PR 53.** `tests/test_hookgate.py` has
  been red since at least 2026-08-05. The fix its own error message names would relax a
  safety guard: committed `rules.rs` blocks `--force` and `--force-with-lease` alike, live
  `safety_gate.py` permits force-with-lease. A test going green is not a reason to change a
  safety oracle. Note PR 53 already did the regen with a diff oracle showing exact agreement
  on 128 commands and 0 security regressions, so the evidence exists; what is missing is the
  decision.
- [ ] **The `review` CI job posts "Claude encountered an error after ~40s" and exits 1.**
  Four theories tested and discarded. `ANTHROPIC_LOG=debug` is set on the step. Read that
  run and do not add a fifth theory. Most likely remaining candidate is the OAuth token,
  which only the operator can rotate.

### #4 Gate and fingerprint integrity, P0

- [ ] Wire `tools/docmap` into the gate `docs` domain. It exists, checks clean, and nothing
  enforces it on future commits.
- [ ] Mutation control proving the docmap selftest can go red, so it meets the repo's own
  four-layer standard.
- [ ] Selftest ledger pollution: workflow-spawned selftests wrote 5 scratch-repo rows into
  the real `state/gate-runs.jsonl` and produced FAIL-then-PASS on one fingerprint. Same
  class as the handback-log fix. Note PR 60's closing audit found 58 more synthetic rows
  written into the real prompt ledger by the test suite, so this is now two ledgers.
- [ ] RT-3: print the joint claim under `VERDICT`, naming which domains were N/A, why, and
  what a PASS does not assert. The strings already exist in `quality-contract.json` and PR
  59 corrected two of them.

### #49 The falsifier layer, P0, refuted

Five claims stand refuted on the operator's host and each needs a decision, not a fix.

- [ ] **C-012**: live `~/.claude/CLAUDE.md` is deleted and `settings.json` keeps being
  rewritten by concurrent sessions. Re-baseline or restore. Refuted twice on 2026-08-05
  alone. The deeper task is that six concurrent sessions make a single baseline the wrong
  shape; consider a baseline per session start instead of per record.
- [ ] **C-025**: the pre-write snapshot is incomplete, six `agents/*.md` missing, so the
  2026-08-01 `settings.json` write is still not revertable.
- [ ] **C-003**: one of 12 live hook registrations does not resolve, `PreToolUse` pointing
  at the hookgate binary. A hook that cannot run fails open and reports nothing.
- [ ] **C-015**: recorded as bus mutation failure. TODO closed this on 2026-08-04 at 23 of
  23 caught. Re-run and either close the claim or restate it.
- [ ] **C-008**: `hiring_engine/ledger.sqlite`. Lane B owns it. Proposal row, not lane A work.

### #28 Waivers, P0

- [ ] Audit every waiver against the test the epic names: does the reason name a mechanism,
  and can its falsifier tell that mechanism from the alternatives. Cheap now, since only one
  waiver remains.
- [ ] Report a waiver past its second renewal as a class rather than as a fresh decision.
  Three renewals happened before anyone re-read the reason.
- [ ] Audit the 1,260 lines `drop_stale_lines` removes. Each should be a line the tree does
  not contain at the claimed position. None has been checked individually.

### #27 The prose gate, P1

- [ ] Port hyphen density and sentence-length variance from `voice-metrics/voice_score.py`
  into `tools/slop_lint.py`. TODO already corrects the shape of this: the measurement half
  exists and prints `no band fitted`, so this is threshold fitting, not porting.
- [ ] Fit thresholds against the operator's own corpus, n=35,472 messages. A guessed
  threshold is a second ruled rule wearing a number.
- [ ] Regression tests both directions, plus a mutation control.
- [ ] Warn before it blocks: collect a week of scores, then decide from the distribution.
- [ ] **DOCS-02**: `slop_lint.py` has no notion of fenced code blocks, so it lints mermaid
  and code samples as prose. Pin a dash inside a fence as clean and the identical dash
  outside it as a hit.

### #34 ast-grep, P1

- [ ] Prove it in a scratch rule file against the three `sql-concat` false positives and the
  planted selftest defect. Do not touch `tools/hookgate` while PR 47 and PR 53 are open.
- [ ] Compare like for like against the two lookaheads now in `panel.py`, on the same
  corpus. If the regex wins, say so and stop.
- [ ] This is the general fix for the `py-shell-true` hit on `codemap.py:66`, where the
  matched line is a comment explaining why that form is not used.

### #31 Plan deviations, #32 interfaces, #29 review recompute, #33 measurement harness

- [ ] A capture command so recording a deviation costs one line (#31). Anything more
  expensive than narrating it will lose to narrating it.
- [ ] Group deviations by `class` after ten rows; if the classes do not recur, the field is
  decoration and should be dropped (#31).
- [ ] A planning stage that emits types and signatures rather than paragraphs (#32).
  Retrofit the one that cost the most: whether `run_local` reviews a line or a file.
- [ ] Make `/premortem` output a signature block (#32).
- [ ] A convention marking a measured number apart from an inferred one inside a
  deliverable (#29). This document uses one informally and it should be a rule.
- [ ] Extend `tools/refute` to accept a deliverable's numeric claims as falsifiers (#29).
- [ ] The artifact measurement harness and its CDP backend (#33), acceptance being that
  re-running it reproduces the takeaway-clipping table without a human reading a screenshot.

### #23 Research transfer, P2

- [ ] **RT-1** log `{claimed_confidence, action, verified_outcome}`. The CLAUDE-OS threshold
  of 0.90 for autonomous action is currently not computable, and the literature says
  self-reported confidence sits at 80 to 100 regardless of accuracy, which would make that
  threshold inert rather than protective.
- [ ] **RT-2** decision ledger and rejection rate on the daily digest. Three ADRs rest on
  human approval and nothing records an approve or reject. A ratio that has never seen a
  rejection is itself the finding.
- [ ] **RT-4** fixture provenance for `tools/skilleval` and one independent audit of the
  existing 5 before writing the next 42.
- [ ] **RT-5** first metamorphic relation, starting with codemap: renaming one directory
  must change exactly one row. `grep -ril metamorphic tools/` still returns zero.

### #25 Supply chain, P1

- [ ] `tools/supply/verify.py` writing provenance to an append-only ledger, refusing to mark
  an artifact adopted with no recorded hash.
- [ ] Pick from Trivy, Grype plus Syft, OSV-Scanner, cargo-audit, cargo-deny, cargo-vet,
  pip-audit, cosign. Note the `supply-chain` job already passes after being pinned to
  `osv-scanner-action@v2.3.8`, so this epic starts from a working job rather than nothing.
- [ ] An ADR on pipe-to-shell installs, a `supply_chain` domain, and a backfill of what is
  already installed.

### #26 Point-in-time reconstruction, P2

- [ ] `tools/timetravel/snapshot.py`: content-addressed snapshots of the **gitignored**
  ledgers with a committed manifest. Do not rebuild what git already gives for tracked files.
- [ ] The original need belongs to lane B and stays a proposal row.

### #50 The ratchet, P1, blocked on /diverge

- [ ] Run `/diverge` first. Five candidates with stated `p_conventional`. Charters rule 2,
  and the epic's own first row forbids implementing from it.
- [ ] Then: either generate `docs/INDEX.md` like CODEBASE-MAP and DOCMAP, or ratchet the
  reachability number docmap already computes. Not both.
- [ ] **RATCHET-02** is the concrete first candidate: the pointers absent-path count moved
  261 to 271 with nobody watching, the only reconciled number that got worse.

### #5 Contradictions the repo states about itself, P1

- [ ] `AGENTS.md` says 12 domains, the contract declares 16. Fix in `AGENTS.md`, which is
  the file every session reads first, and derive the number rather than asserting it.
- [ ] Root `CLAUDE.md` untracked, test count asserted rather than derived, `INDEX.md` line 8
  on the pre-ADR-0016 lane letters, `SYSTEM-MAP.md` rows marked VERIFIED that are false.
- [ ] **The general fix, and the one worth doing instead of the eight instances**: no
  hand-written count of a thing the repo can count. Every instance above is the same defect.

### Structural rows from TODO that no epic owns

- [ ] **48 definition-of-done rows exist and zero tools read them.** Classify the 48 before
  building a checker, because the count of mechanically checkable rows is unknown and below 48.
- [ ] **The docs control plane enforces one field of three.** `strand.py` checks `Status:`
  and reachability, not the `PRD:` / `Ticket:` header the rule names first, and
  `docs/specs/archive/` does not exist so rule 3 is unenforceable by construction.
- [ ] **20 of 21 specs and 4 of 5 PRDs declare no status line** in the form this document
  uses. Measured today. Only `2026-08-03-unified-architecture.md` carries one.
- [ ] **No retrieval layer over `state/`.** 130M transcript tokens a week, ledgers read by
  tail and grep, nothing indexes them. PR 60's per-project store is the first half of this.
- [ ] **Metamorphic testing absent**, which is RT-5 arriving from the other direction.
- [ ] **The cross-artifact graph**: `file -> test that covers it`, `finding -> rule it
  produced`, `claim -> falsifier`, `directory -> prior-art record`. Three of the four exist
  as one-off scripts and none is queryable. Adopt Graphify's edge-provenance tagging if built.
- [ ] **No size or complexity domain.** 14 modules over 500 lines, 71 functions over 50,
  `bus.py:589 cmd_selftest` at 614 lines. The imported standard says 500 and 50 and nothing
  reads it.
- [ ] **Nothing enforces coding style on `tools/`**, which is most of the repo's code. Ruff
  and mypy see one subdirectory. Extending scope surfaces a backlog, so it ships with a
  waiver carrying a real number and a burn-down.

## M2. Consolidation and shrinkage

### #10 Commit at-risk work and settle absorption, P0

- [ ] **ABSORB-01, and do it with ABSORB-09 as one change.** The prior-art schema cannot
  express absorption: 41 records, 0 with an `absorbed` field, and `verdict` is free text
  carrying 13 distinct values of which four are sentences. Add `absorbed` and
  `absorption_status`, add the enumerated verdict beside the sentence, backfill 41, and fail
  `codemap.py prior-art` on unset. This is the root cause row: absorption is unrepresentable,
  therefore unchecked, therefore never happens.
- [ ] **ABSORB-10**: `tools/whatsapp` carries verdict `delete-ours` and still exists with 4
  tracked files. Execute the decision or record why it was reversed.
- [ ] **ABSORB-07**: the saved-link corpus, 806 unique URLs over 14 months, filtered by the
  operator's actual attention and still unwired. The external brief is ready.
- [ ] **ABSORB-08**: triage vulture's 70 findings at 60 percent, measure whole-module
  connectivity which vulture does not do, and wire `uvx vulture` into the gate.
- [ ] **ABSORB-03**: albert's two mechanisms, rebuilt not copied under PolyForm
  Noncommercial. Worktree isolation per concurrent producer is the direct fix for M0's
  branch pile and issue #58.
- [ ] 57 saved repos captured, triaged once by metadata, never compared file by file, and
  nothing consumes or resyncs the JSON.

### #6 Dead pointers, stubs and drift, P1

- [ ] **Row B, the big one: 52 diverged skills across four trees.** 121 distinct names, 84
  shared, 30 identical. Each fork needs a recorded decision and picking by timestamp is not
  a decision. Two corrections to carry in: 33 of the counted forks in `dot-codex/skills` are
  one-line dead pointers rather than divergent content, so the real fork count is smaller;
  and `dot-claude/` is canonical by evidence, being the only tree with a live counterpart.
- [ ] **The loudest unexplained number in the repository**: live skills went 40 to 79 in two
  days and nothing can date or attribute it. `state/snapshots` holds one manifest from
  2026-07-25 and does not span the gap. Resolve before any merge decision, because it
  governs every skills count under it.
- [ ] **34 skills committed and not deployed**, so no session can invoke them, including
  `ui-ux-pro-max` at 527 body lines. Seven carry dead paths and must be repaired before
  deploy, not deployed as-is.
- [ ] **23 of 29 hooks are wired nowhere** in live settings, and 12 of those are one-line
  pointers into `/home/shovalbe/`, a home that does not exist. Some are legitimately
  superseded; the rest have never been adopted. Presence in the tree is not deployment.
- [ ] **`dot-claude/bin/self-improve.py:27` is a live broken consumer**, inserting a
  `$HOME/projects/` path that does not exist. Its sibling uses a repo-relative path and works.
- [ ] **Three top-level directories are waiting on an operator call** and the report exists
  at `docs/analysis/2026-08-07-toplevel-dir-decisions.md`: `dot-agents`, `dot-codex`, and the
  `intent-control-plane` versus `tools` boundary, which is nominal anyway since all six
  external consumers reach the package through `sys.path.insert`.
- [ ] The clear calls in that same report are blocked on nothing: archive `home-dotfiles` and
  `startup-scripts`, merge `master-plans` into `work-docs`.
- [ ] `whatsapp-query` leaves 86.9 MB of decrypted plaintext on disk after a query. Second
  occurrence. The fix belongs in the skill, not in a habit.

### #8 Shrink to under 600 files, #35 Repo Clear, #7 Phase D, #9 WSL2, #24 RTK, #11 licensing

- [ ] 126 tracked cron run outputs are logs, 237 vendored third-party files are tracked, and
  59 paths have drifted between the three `dot-*` copies (#8).
- [ ] `tools/repoclear/scan.py`, read-only, one report over four repos, zero deletions (#35).
- [ ] Repo Clear blocks the WSL2 move: relocating 5,717 markdown files of which 2,479 are
  duplicates is paying to move garbage (#35, #9).
- [ ] Phase D reclamation with Pictures excluded entirely per operator instruction (#7).
- [ ] Decide `rtk-bash-guard.sh`: deploy it, or delete the rule and the guard. A mandatory
  prefix nobody can enforce is the worst of the three. Measured saving is 20 percent, not
  the advertised 60 to 90 (#24).
- [ ] **Licensing is the gate on going public** (#11): a tracked verbatim 17,923-byte copy of
  a repo with no license, third-party PII in `research-papers/el-vadt`, 17 of 56 saved repos
  concepts-only, and no push of any no-remote repo until a credential audit has run over every
  commit tree rather than HEAD.
- [ ] **`voice-metrics` needs an operator decision.** The only live-only skill not committed;
  its `profiles.json` keys include a WhatsApp linkable id and 9.3 MB of lexicons.

## M3. Delegation that has actually run

The milestone title is the acceptance criterion and nothing in it has met it.

### #12 Native surface, P1

- [ ] **SubagentStop hook.** The only native point that can gate a subagent's output before
  it returns, which is exactly where the agreement gate belongs. Referenced nowhere except
  three 2026-05 master plans.
- [ ] An output style, since `completion_gate.py` currently polices the response channel with
  regexes after generation.
- [ ] `CLAUDE.md` @import, project-scoped `.mcp.json`, a SessionEnd hook so durable handoff
  stops depending on PreCompact firing, and at least one installed plugin. The
  marketplace was registered on 2026-07-30 and zero plugins are installed.

### #14 Persona review economy, P2, and the SETUP-PERSONA rows

- [ ] **PERSONA-06 is the unblocking row: run two allocated actors blind to each other on one
  real PR.** All 11 existing review artifacts say `external backend not requested`. Everything
  else in this epic is downstream of one external review having happened.
- [ ] **PERSONA-10**: decorrelation is declared, not measured, and the literature says the
  declared quantity is the wrong one. `allocate.py` hard-codes a hand-declared family string.
  The substrate to do it right exists; it blocks on PERSONA-06.
- [ ] **PERSONA-05**: ADR-0012's `auto:low` auto-merge is gated on a both-model approval that
  does not exist, in any domain or any tool. Build it on PERSONA-01 or amend ADR-0004 and
  ADR-0012 to record that it is designed and unbuilt. Doing neither leaves the governance
  docs describing a system nobody has.
- [ ] **PERSONA-03**: wire `panel.py` to consume `allocate.py`, so a diff touching only `.md`
  does not pay for the security rule set.
- [ ] **PERSONA-02**: only one actor declares `a11y`, so it can never receive a decorrelated
  second opinion. Either a second actor declares it or the enum admits it is single-opinion.
- [ ] **PERSONA-04**: the two persona vocabularies share 2 words out of 11. PR 42 closes one
  of the gaps by giving `boundary` both a rule set and an actor.
- [ ] **PERSONA-07**: every agent is `ShovalBenjer (User)`. A GitHub App per lane is free on a
  private repo and attributes the action to the agent while keeping the owner accountable.
- [ ] **PERSONA-08**: `from_session` is empty in all bus rows because `CLAUDE_SESSION_ID` is
  not exported into the hook environment. A settings change, not a design change.

### #13 ACP, #15 Kilo, #16 one routed workflow

- [ ] `kilo acp` already exists in the installed CLI, so ACP can be tested without writing an
  adapter (#13). Then decide whether it replaces the bespoke bridge.
- [ ] Reconcile ADR-0007: its amendment moved the reviewer role off Codex because the
  subscription was cancelled, and Codex is now included in ChatGPT Free with CLI access (#13).
- [ ] An oracle that fails when the agreement gate is claimed and `audit.jsonl` shows no call
  for the current commit (#13). Today the absence is only discoverable by thinking to look.
- [ ] **Kilo has the only hard external deadline on this page: migrate custom instructions to
  `REVIEW.md` before 2026-08-31** (#15). Also harden the trigger template, since their own docs
  warn webhook payloads are a prompt-injection surface and `{{body}}` must not land in
  instruction position.
- [ ] Decide reviewer contract versus implementer contract for cloud agents, whose auto mode
  is not optional and can auto-commit (#15). Operator decision.
- [ ] **Write and run one workflow under the routing `model-selection.md` prescribes** (#16),
  record the run, and measure it. No ledger of workflow runs exists at all.
- [ ] CHAN-02 through CHAN-05 and CHAN-07 through CHAN-09: the channel envelope work, of
  which CHAN-05 is the cheapest and most overdue, wiring `roundtrip.py selftest` into the
  gate as a named step so the oracle is covered the way the others are.

### AUTO rows with no epic of their own

- [ ] **AUTO-06 `ecosystem.db` is the keystone**: it unblocks work-claims (AUTO-04) and
  FleetView (AUTO-19), and ADR-0017 has settled which schema copy is authoritative.
- [ ] **AUTO-19 FleetView**: 12-row feature table, five premortems, an 18-item checklist,
  zero code, five days and counting. Either build v0 over `state/sessions/*.json` or record
  that it is specced and unbuilt.
- [ ] **AUTO-18**: register the real scheduled tasks and observe one unattended fire. The
  passwordless S4U probe already succeeded and was removed.
- [ ] AUTO-11 merge-policy labels and auto-merge for `auto:low`, which depends on PERSONA-05.
- [ ] AUTO-09 scale nightly to tier-1 repos after seven clean days. AUTO-17 research stage in
  the weekly cron. AUTO-12 to 14 social, draft-first. AUTO-15 split resume rails. AUTO-20
  reputation routing once volume exists.
- [ ] **Decide the undeployed enforcement layer**: PreToolUse protect-infra and rtk-bash-guard,
  Stop stop-checklist and verification-before-completion and contract-proof-stop, PostToolUse
  skill-usage-logger. These are the checks that would have caught L003 and L009 mechanically.

## M4. Design with an anchor

Smallest milestone and the one with the least evidence behind it. Three epics, all P2 or P3.

- [ ] **Create `DESIGN.md`** with open-design's section skeleton, then a token file plus a
  parity guard so it cannot silently drift from the tokens it claims to describe (#17). The
  parity guard is what makes it an oracle rather than a wish, and it is the only part of this
  milestone that matches the repo's own standard.
- [ ] **Run `/diverge` on a real UI decision and write the first `taste.md` UI row** (#17).
  Rule 1 forbids the conventional mode as a final answer and it has never been enforced on a
  visual choice.
- [ ] Create the dataviz skill that `out-of-distribution.md` already instructs sessions to
  load and that exists nowhere (#17).
- [ ] Deploy `blonde-designer`, `ui-ux-pro-max` and `requirement-anchor`, or delete them (#17).
- [ ] **The Construct v4** (#18): decide the medium and commit, since v3 targets Textual and
  shipped web HTML. Three named directions with stated `p_conventional`, at least two below
  0.30, operator picks before implementation. Ship the reliability panel in its empty state
  first, because RT-1 says the inputs are not logged so the curve is not computable. Resolve
  the reward inversion where a failed assertion pays out loot.
- [ ] **Absorb open-design and OpenGame** (#19): verify the `od` daemon has a Windows path
  before adopting; take the three patterns rather than the vendored brand systems; take
  OpenGame's two concepts, the execution-plus-judge benchmark shape for `e2e` and `a11y_ux`,
  and the living protocol of verified fixes, since we accumulate failure classes and
  falsifiers and accumulate no fixes.
- [ ] `petergyang/no-ai-slop`, MIT, 20-plus patterns: compare against `slop_lint.py` and take
  what MIT permits. This belongs to M1's prose-gate epic as much as here.

## M5. Autonomy and CI

- [ ] **Wire `refute.py run` into `ship-gate.yml` as a named step** (#20). It returned 26
  broken verifiers for days on the WSL host and nothing surfaced it, because nothing ran it.
  Cheapest real row in this milestone.
- [ ] **Branch protection costs money on a private repo or requires publishing** (#20).
  Operator decision, and it is the precondition ADR-0012 worked around rather than met.
- [ ] **Correct the two false rows in #20** as listed in the corrections section above.
- [ ] **A branch has been failing Ship gate since 2026-08-04**, `lane-a/panel-comment-strip`,
  with Claude Code Review also red. Not on the open-PR list, so it is a branch with no PR.
  Find its owner or delete it.
- [ ] Repo standards maintained by an agent (#21): Discussions as the public surface, SemVer
  with a hand-written changelog, PR-to-issue linking enforced by CI, and a named maintenance
  owner per free feature.
- [ ] **Wire the other actors to the Zion board** (#21): codex, kilocode, Claude Code Review,
  gemini, qwen, nvidia. This is the row that would make the board a working surface rather
  than a published one.
- [ ] **Zion board throughput is zero**: 31 epics open, 0 closed, 184 items with 5 checked at
  2 percent. The checklists are specific and real, so this is unstarted work rather than
  scaffold. **Decide whether an epic-only board with no task issues is the surface that gets
  used**, because nothing has ever moved on it. That decision belongs before any further
  publish.
- [ ] **ZION-01 blocks the board entirely**: the token has no `read:project` scope. Unblock
  with `gh auth refresh -s read:project,project`, one interactive browser step, with
  `$BROWSER` already bridged to Windows Chrome.
- [ ] **ZION-03**: the `Lane` field is a select of B/C/D/E and the lanes are A/B/C/D.
- [ ] **ZION-02**: after ZION-01, publish the corrections through the JSON and never by hand.

## Cross-cutting, and what actually blocks what

Dated deadlines, in order:

1. **2026-08-12**, in two days: the `skills` waiver expires and was deliberately not extended.
2. **2026-08-31**: Kilo custom instructions must move to `REVIEW.md`.
3. **2026-09-07**: the earliest prior-art expiry, `tools-whatsapp`, whose verdict is
   `delete-ours` and which still exists. That one is already overdue in substance.

Operator decisions that block agent work, gathered so they can be answered in one pass:

1. HOOKGATE-01, whether the compiled binary stops blocking force-with-lease. Blocks PR 47,
   PR 53, and the `unit` domain.
2. Deploy or do not deploy the 13 `disable-model-invocation` skills. Blocks the waiver.
3. The three top-level directory calls: `dot-agents`, `dot-codex`, `intent-control-plane`.
4. C-012, re-baseline or restore the deleted live `CLAUDE.md`.
5. Branch protection, which costs money or publication.
6. Kilo cloud agents: reviewer contract or implementer contract.
7. `voice-metrics` preservation, given the linkable id in its profiles.
8. Whether the Zion board stays epic-only.
9. ZION-01, one interactive `gh auth refresh`.

Two structural claims worth deciding before picking up any row above, because both would
change what the rows are:

- **Inventory bloat may be the core problem and adding tickets the wrong shape.** That is
  lesson L-2026-07-29-h and this document is itself an instance of the thing it warns about.
  137 open TODO rows, 184 board items, 41 prior-art records and 5 unread milestones is not a
  backlog anyone reads. The counter-argument is that the rows are specific and measured,
  which is unusual and is why they are worth keeping.
- **Arrival creates no obligation**, which is TODO row D. Everything that has silently
  accumulated shares that property: 23 unwired hooks, 78 unlive skills, 6 unbound standards,
  a tool built and wired to nothing. Prior-art records are the only category with an expiry
  and the only one that has not rotted. Generalising that expiry, so an adopted artifact
  declares who binds it and when the binding is rechecked, is the single structural change
  with the largest reach on this page. It has had no prior-art pass; run one before building.

## What this document does not do

- It does not order M1's 14 epics against each other beyond marking what blocks now. That
  ordering needs the operator's answer to the nine decisions above.
- It does not touch `state/github-backlog-2026-07-31.json`, any issue body, or any issue
  state. The seven corrections are listed for the next publish and ZION-01 blocks that publish.
- It does not re-measure the operator's live tree. Two numbers it would have needed are
  host-shaped and are labelled rather than reported.
- It does not close any TODO row. Rows that measurement contradicts are named in the
  corrections section and stay open until someone with the live host confirms them.
