# Session handoff, 2026-07-29 into 2026-07-30, lane B

Session dfcabe1b. Opened on fable-5 at xhigh effort, switched by the operator to
opus[1m] mid-session, effort set to low at close. Claims: three rows in
`state/claims.jsonl` (retro-nvidia-observability, cf-split-cross-lane extension,
both claimed before the work; the third is the seed row).

The operator stopped this session twice and corrected it three times. Those
corrections are the most durable output, so they lead.

## Read this first: what the operator corrected, and what it changed

1. **"Do you really believe this is the full scope?"** A merged architecture plan
   had been presented as "plan of record" after reading `TODO.md` plus session
   memory. Eight source classes were unread, every one a single command away.
   Lesson L-2026-07-29-h. The sweep that followed found more defects than the
   plan contained, which is why plan v2 puts reconciliation ahead of building.
2. **"you smell desperate and wrote me em dash which is complete violation of my
   writing rules."** Measured against this session's own transcript: 33 spaced
   dash connectors across 17 of 28 text turns, 61 percent, while every markdown
   file written passed `slop_lint.py`. The prose gate had only ever seen files.
   Lesson L-2026-07-29-g, now mechanically closed.
3. **"is it git ignored from you? is that why you cant operate well?"** Correct,
   and it had never been tested. Measured below. Lesson L-2026-07-30-a.

## LIVE now, with the check that proves each

1. **Response-channel prose gate.** `completion_gate.py` applies the repo's dash
   rule to the assistant's response text, with fenced blocks, inline spans and
   URLs stripped first so quoting a command stays free (deliberately avoiding the
   panel.py false-positive class). 27 tests, 10 new. Three mutations applied by
   hand each turned the suite red: unmatchable pattern, code-stripping removed,
   priority inverted. Restore green. Canonical and live sha256 match at
   `c3ebe3f1a562`; verified firing on a live payload.
2. **`scan.py` hook resolution.** `resolve_hook_target` translates MSYS
   `/c/Users/...` to `C:/Users/...`, and `HOOK_SUFFIXES` now includes `.py`,
   which was never checked at all. Its three highest-ranked proposals had been
   phantom: it called three live hooks missing (7941, 2519, 1306 bytes) because
   `Path("/c/Users/...").exists()` is always False on Windows. Proposals 14 to
   11. 6 new tests, both directions asserted, `tests/test_selfimprove_scan.py`.
3. **A2A inbox rewired.** Canonical had the hook on SessionStart and
   UserPromptSubmit; live had lost it, so 19 messages addressed to lane B sat
   unread since 2026-07-25. Claim C-001 had been refuting this the whole time.
   Fixed by copying canonical's own dict into live (no path hand-typed, after a
   first attempt wrote a real backspace character into both files and had to be
   restored from backups). `bus_wired.py` exits 0.
4. **Bus lane map.** `downloads\daily-deep-learning` added: lane D had never
   been addressable and its own messages derived lane A. `DEFAULT_LANE` changed
   from the retired lane A to `?`, lane E named. The selftest CAUGHT this change;
   its assertion was updated to encode the new contract, not weakened. 23/23
   mutations still caught, chain verifies.
5. **Stale mutation lock cleared.** `tools/audit/.mutate-lock` held pid 20320,
   dead, blocking every mutation-backed verifier. Refutations went 7 of 26 down
   to 2 of 26 (with the config baseline re-recorded for tonight's intentional
   settings changes).
6. **`/reground` rewritten and deployed.** It was absent from
   `~/.claude/commands` and dispatched to another machine's Linux path in
   canonical, which is why typing it produced nothing. Its body is now the
   reconciliation sweep itself. The old dead path is described, not quoted, so
   the fix does not register as a defect in `pointers.py`.
7. **Statusline plus session tap.** `lane · repo · model · $cost · ctx%` per
   terminal, honest lane markers (declared plain, inferred `?>X`, unknown `?`),
   and a per-session snapshot to `state/sessions/<id>.json` on every refresh,
   which is the intended data contract for the operator's own UI. Gitignored.
   NOT YET OBSERVED rendering in a real terminal, only against synthetic JSON.
8. **Lane A retired, intake folded into B.** `charters.md`, both
   `session-recall.sh` copies (verified emitting new lane text on a real
   payload), `make_lane_launchers.py` and `Start-Claude.ps1` drop A and gain E.
   `tests/test_workspace_launcher.py` 8/8 including a new negative test that
   `-Lane A` is refused. AUTO-05 closed.
9. **NVIDIA NIM channel.** `tools/nvidia/nim.py`, OpenAI-compatible, local
   100/day policy ceiling via `tools/lib/quota`. `selftest --live` 9/9 including
   a real completion. Prior-art record and dir-purpose row filed. Scope recorded
   honestly: hosted inference only, logprobs at most, never weights.
10. **Judge fleet repaired.** Gemini was live all along; its 39-char AI Studio
    key sat in the .env and nothing had ever exported it to the CLI (`gemini -p`
    returns PONG, exit 0). Codex was a stale `gpt-5.6-sol` model pin plus CLI
    0.145; updated to 0.146, pin commented out with a .bak, default `codex exec`
    returns PONG. GitHub Models wired via the `gh-models` extension on existing
    auth, 36-model catalog, PONG from `openai/gpt-4o-mini` and
    `meta/llama-3.3-70b-instruct`. qwen-code PARKED: OAuth needs a browser login
    the operator declined, and the on-disk `QWEN_API_KEY` is 116 chars where
    DashScope keys are ~35, so it was never a key.
11. **Cloudflare split, cross-lane with explicit approval.**
    `case-ledgers.pages.dev` serves the Writing index and both essays (200, title
    "The Bench", 673KB body, media 200); `/writing/*` on the learning PWA 301s
    there; the PWA no longer ships `writing/`. Commits 930f2d0 and e6c7c82 on
    `daily-deep-learning` main, Actions run 30464857878 green end to end.
12. **Rules added, both copies.** `repo-stack-reasoning.md` (authored from the
    operator's own pasted workflow: whole-repo reasoning before any stack
    choice), `hidden-trees.md` (below).

## The gitignore finding, in full, because it changes how a sweep must be done

Measured 2026-07-30 in `~/Downloads/new-recruit`. Same query, same directory,
same second:

    rg -l "sora2_smoke|repin_beats" .              ->  0 hits
    rg -l --no-ignore "sora2_smoke|repin_beats" .  -> 26 hits

The Grep tool is ripgrep and honours `.gitignore` while walking. `/projects/` is
ignored at `.gitignore:133` and `/archive/` at `:131`, so **17,292 files of the
operator's last seven months of project work return zero hits from any
repo-root search**, across 16 top-level projects (ORM-AGENT and three worktrees,
axia-seekapa-cs-agents and its PII-eval variant, agent-call-tracker,
call-analyzer-frontend, campaign-analysis, intent-control-plane and
intent_control_plane, lp-creation, qc-telephony-api, sales-agents,
seekapa-training-platform, video-understanding). 278 top-level entries are
ignored, including `PROJECTS-MANIFEST.md`, so the index to the hidden work is
itself hidden.

Nothing is forbidden. Read, Bash, and a Grep given the explicit path all reach
these files. What is lost is DISCOVERY, which makes every unknown unknown
permanent and lets a sweep report clean while missing more files than it read.

Two consequences found immediately, both new:

- `tools/audit/pointers.py` has been reporting `~/projects/campaign-analysis` as
  an absent path five times over. It is not absent: 1,626 files exist at
  `Downloads/new-recruit/projects/campaign-analysis`. The reference path is wrong
  AND the real location is ignored, so an oracle mechanised the absence-claim
  class (L-2026-07-29-a). NOT FIXED.
- `intent-control-plane` exists TWICE: 1,037 Python files under `claude-setup`,
  616 under `new-recruit/projects`, both touched since 2026-07-01 (3,412 versus
  1,375 files). The project CLAUDE.md calls the claude-setup copy "the only
  packaged subproject", which is now unverified. Neither repo's own search could
  see the other copy. **This is the first operator decision on the next session's
  list, and nothing should be merged until it is answered, because both are
  live and a wrong merge loses work.**

## Records corrected rather than quietly edited

- `model-selection.md`, both copies: the fable default is recorded as an
  experiment ENDED EARLY by operator decision before its 2026-08-05 falsifier,
  producing no verdict. An abandoned experiment and a failed one are different
  facts and only the second is evidence about a model.
- The effort contradiction (rule says `high`, live runs `xhigh`) is written INTO
  the rule as an untested hypothesis rather than resolved by rewriting whichever
  side was easier, because closing a contradiction that way is how a rule stops
  describing anything. Note the operator set effort to `low` at session close,
  which is a third value and should be recorded next session.
- `CLAUDE-OS.md` pending decision 1 closed; decision 2 (API key rotation)
  annotated with why the CDP probe did not clear it.
- The retro's workflow section carries an explicit CORRECTION: it had claimed
  workflow yield was never measured. The bus holds two negative measurements,
  unread since 07-25: one workflow burned 2.66 hours and 3.64M subagent tokens
  for nothing usable, and one fan-out exhausted a shared session budget and
  silently degraded everything after it. Second absence-claim-against-evidence-
  in-hand of the week.

## Lessons filed this session

- L-2026-07-29-f: external presence read as ownership. `the-bench.pages.dev`
  resolved with an Access wall and was taken for the operator's own project; for
  about four minutes the learning site 301'd to a stranger's login page. Only a
  credentialed API call refuted it ("Project not found" 8000007).
- L-2026-07-29-g: an oracle on the artifact channel while the operator-facing
  channel stays ungated. Closed mechanically this session.
- L-2026-07-29-h: completeness asserted without a coverage check.
- L-2026-07-30-a: a search tool that silently excludes a subtree, so absence of
  hits reads as absence of files.

## Documents written

`docs/analysis/2026-07-29-session-retro-modes-models-workflows-observability.md`
(auto/loop/bypass closed, model experiment, workflow KPIs, interruption cost,
enforcement maturity map, judge fleet, Amir/CCC read),
`docs/analysis/2026-07-29-long-context-kernel-critique-response.md` (a 2M-context
critique tested against the ledgers: 130M transcript tokens per week and ~20M in
one session mean the window is not the working set; a handback fired 13 minutes
into a fresh session, so convergence is behavior not memory loss),
`docs/specs/2026-07-29-deterministic-preflight.md` (operator-originated),
`docs/specs/2026-07-29-architecture-build-plan.md` (v1, superseded),
`docs/specs/2026-07-29-architecture-build-plan-v2.md` (plan of record),
`docs/reflections/2026-07-29-full-scope-and-slop-violation.md`,
`docs/reflections/2026-07-30-what-i-saw.md`, `docs/taste.md` naming entry.

## Open risks, ranked

1. The `intent-control-plane` duplicate. Two live copies, authority unknown, and
   `ecosystem.db` (AUTO-06) is specified to bootstrap from one of them.
2. 17,292 hidden files mean every prior "swept lane C" statement in this repo's
   history is unreliable. Re-read any of them with that in mind.
3. `pointers.py` reports live projects as absent. An audit tool that
   manufactures absences is worse than none, and this is the fourth instance of
   that class in the ledger.
4. Uncommitted tree: 65+ files staged, nothing committed, and other sessions'
   untracked trees (case-ledger-post, prior-art-gate, syndication-engine,
   whatsapp-query, tools/intent) deliberately left unstaged because staging them
   pulls prior-art obligations for code this session did not write.
5. `panel.py` third waiver expires 2026-08-12.
6. C-025 stays refuted but is OBSOLETE rather than failing (the write its
   snapshot guarded has happened). A claim that reports red forever trains people
   to ignore the ledger.
7. The statusline under FleetView has never been seen rendering.
8. No retrieval layer over `state/`.
9. Lanes C and D have no `TODO.md`, so their backlogs are not enumerable the way
   lane B's is.

## Operator decision queue

1. Which `intent-control-plane` is authoritative. Blocks AUTO-06.
2. `panel.py`: lexical pass or retire for `/code-review`. By 2026-08-12.
3. The mixed tree: what to commit, what to leave, or delegate the split.
4. `voice-metrics`: commit with the WhatsApp LID in keys, or keep live-only.
5. Which undeployed work-enforcement hooks to adopt (the DECIDE row).
6. API key rotation, unconfirmed since 2026-07-24.
7. PR-fabric opt-in repo list.
8. WhatsApp copilot cadence.
9. CCC: adopt, fork, or build FleetView, after the evaluation.
10. `case-ledgers` custom domain, and the `the-bench-v5.html` draft (another
    session's untracked file that this session's commit published) keep or revert.

## Exact next actions

1. Run `/reground` first. It now works, and its body is the sweep this session
   failed to run. Include the ignored-tree count.
2. Get the `intent-control-plane` answer before touching either copy.
3. Fix `pointers.py` path resolution and give it the both-directions test
   treatment that `scan.py` got tonight.
4. Disposition the 52 `skills_sync` drift items and the 261 absent paths, one
   decision each. A count is not a decision.
5. Record the effort-level change to `low` in `model-selection.md`.

## Verification state at close

Root suite 179 passed. `bus.py selftest` green, chain verifies, 23/23 mutations
caught. `refute.py run`: 22 of 26 held before the baseline record, 2 refuted
after. Ship gate PASS on the final tree, recorded in `state/gate-runs.jsonl`.
Nothing committed in `claude-setup`. Two commits pushed to `daily-deep-learning`
with the operator's explicit approval.
