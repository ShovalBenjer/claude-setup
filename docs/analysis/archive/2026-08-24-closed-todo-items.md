# Closed TODO items

Archived from TODO.md on 2026-08-24. 70 completed items.

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
- [x] review domain: sql-concat required a verb and a concatenation and never required SQL, so English prose ("Delete ~380 lines ... + their selftest") was a HIGH; and added_lines reported lines this branch added and then deleted. Both fixed in tools/review/panel.py, 20 pinned cases, mutate --spec panel 10/10 caught, panel 5 high -> 0 high. Waiver replaced (2026-08-12 -> 2026-08-02) recording the old reason as wrong rather than deleting it (closed 2026-07-31). **THE "0 high" HALF OF THIS ROW IS FALSIFIED, 2026-08-01.** The waiver it wrote carried its own falsifier, the falsifier was run, and `panel.py run --project .` returns CHANGES-REQUESTED with 3 high. Two are real (vendored innerHTML in dot-claude/skills/brainstorming/scripts/helper.js:57,59) and one is the comment-matching mechanism this row claimed was eliminated, still live in a different check. The two fixes landed; the generalisation did not, and the row said otherwise. Waiver text corrected in quality-contract.json rather than the number being chased
- [x] ADR-0010..0015 + PRD + spec + charters + SESSION-BOOT + lessons ledger (AUTO-03/08/13/16 seed), 2026-07-24
- [x] AUTO-01/02 hook fire-proof, CLOSED 2026-07-24 22:44. `state/hook-fires.log`: 7 harness-written SessionStart lines (real session ids incl. `8abb324e-…`) + 11 PreCompact lines + 12 `## compact` snapshots in `state/compact-log.md`. L011 interpreter/path bug fixed and now proven in-harness, not by pipe test
- [x] COMPACTION CHURN measured resolved 2026-07-29: PreCompact per day 47, 250, 2, 1, 0, 0 across 07-24 to 07-29; per-session 15.6 on 07-25 down to 0.0 on 07-28/29. Both suspect env vars (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `CLAUDE_CODE_DISABLE_1M_CONTEXT`) are ABSENT from live settings; sessions run on 1M context. `trigger=` now logged (289 lines). Caveat: the churn ended 2026-07-26 with no config change recorded, so the cause of the fix is not established; reopen if per-session climbs above 1
- [x] Nightly autonomy pilot workflow on claude-setup (AUTO-07), first scheduled run pending
- [x] AUTO-05 CLOSED 2026-07-29: Lane A RETIRED by operator decision (never used once between ADR-0013 and retirement). Intake/routing folded into Lane B as plumbing (docs/charters.md); UserPromptSubmit capture already ledgers intent. Any future RC/phone intake surface is a B feature, not a session lane
- [x] CHAN-01 CLOSED 2026-07-30: ADR-0018 two-tier inter-agent channel (`text` / `dense-text` / `kv`, no silent downgrade, `kv` only on open-weight legs) + `tools/channel/roundtrip.py` round-trip fidelity oracle. Evidence: `selftest` exit 0 (identity 1.0 PASS, half-truncation FAIL, unreachable peer FAIL, absent-answer probe rejected); `run --channel truncate` exits 1 at fidelity 0.6667. Grounded in arXiv 2606.19857 (SJTU et al., 2026-06-18) and 2607.26773 (2026-07-29)
- [x] CHAN-06 RESOLVED 2026-07-30: Kilo trigger provisioning is UI-only, and that does NOT cap autonomy. Measured: `kilo --version` 7.3.12, and `kilo help` grepped for trigger/webhook/cloud/inbound/schedule/cron matches exactly one line, `--cloud-fork` (fetch a session FROM cloud). No create-trigger verb exists in the CLI and the docs confirm UI-only for both webhook and scheduled triggers. BUT a trigger is durable and reusable: one UI provisioning step, then unlimited inbound POSTs with no reconfiguration. So the manual step is one-time provisioning, not per-run. Earlier claim in this session that the manual step 'caps how autonomous any of this gets' was WRONG and is retracted
- [x] AUTO-10 UNBLOCKED 2026-07-24 (was falsely BLOCKED(operator), L012): key was already in a local .env; `gh secret list -R ShovalBenjer/claude-setup` now shows `GEMINI_API_KEY 2026-07-24T20:17:02Z`. Value piped via stdin, never echoed. REMAINING: `.github/workflows/gemini-review.yml` was written 2026-07-31 and consumes the secret, diff-only, advisory. It has NEVER RUN, so two-model review is still not measured; a workflow on disk is the same class of claim the secret was. Closes when a real PR shows a Gemini annotation. The actor itself IS reachable: a live diff-only call on 2026-07-31 returned two correct CWE-anchored findings (probe used a synthetic diff, no repo content sent)
- [x] Intent capture slice LIVE: UserPromptSubmit hook, `tools/intent/capture_turn.py`, writes `~/.intent` (event + intent card + CAPTURED transition) plus chained `state/prompt-tickets.jsonl` (content-covered hash, no prompt text in git). Acceptance query returns ticket id + goal. Corpus backfill NOT scheduled: transcript format is vendor-internal (L-2026-07-29-e)
- [x] Resource ledger LIVE: `tools/intent/resources.py` + scanner. Backfill wrote 3855 sightings across 2712 resources from 494 files in 1.1s. TRUE coverage baseline 0.2% (5 noted of 2716); only a human-attached note moves it, the scanner mints sightings only
- [x] Autonomy Stop gate LIVE: completion_gate.py now blocks a turn that ends by handing the decision back with no blocker named (measured cause: ~31% of reacted-to answers; 940 min/week idle). Loop-safe via stop_hook_active; every stop logged to state/handback-log.jsonl (gitignored; a per-turn write inside the fingerprint made every gate PASS self-invalidating)
- [x] EXT-1 Append-only-write oracle for `state/*.jsonl`: `tools/audit/append_only.py` (static scan for truncating writers + git-history line-count check), `selftest` green, `check` clean against this repo. Gate-wired 2026-08-19: `check`+`selftest` now chained into quality-contract.json's `unit` domain cmd, so a truncating writer fails `gate.py run`, not just a manual invocation. Before this it existed and passed but nothing enforced it, per a fresh audit finding.
- [x] EXT-2 Risk-classified pre-action guard: `dot-claude/hooks/pretooluse-risk-guard.py`, payload-only (not wired into settings.json), `selftest` green
- [x] EXT-3 Skill-routing accuracy as a measured number: `tools/audit/routing_accuracy.py report`, reads `state/agent-spawns.jsonl` (router_named vs subagent_type) + `state/routing.jsonl` (activation volume); measured live 2026-08-17: 1/6 (17%) overall spawn agreement, 31/37 spawns with no router_named on record. Gate-wired 2026-08-19: `selftest`+`report` now chained into quality-contract.json's `unit` domain cmd (selftest gates, report is informational since the metric has no pass/fail threshold by design). Same "existed, passed, nothing ran it" gap as EXT-1.
- [x] GATE-COV-1 Fail-closed coverage declaration (operator-approved 2026-08-19, prompted by external review Agentica independently converging on the DASH-1 finding and naming the general fix): `tools/audit/coverage_map.py` + `docs/coverage-map.txt` + `quality-contract.json`'s new `coverage_map` domain. Every top-level tracked directory now needs a `covered-by:<domain>` or `exempt` row or the gate FAILs; unlisted is blocked, not silently ungoverned (the inverse default from `docs/prior-art/out-of-scope.txt`, on purpose). First real run found a SECOND live instance of the DASH-1 class: `nexus-engine-rs` (a second Rust crate, 8 `#[test]` functions, its own README documenting `cargo test`, zero gate coverage), recorded as an admitted exemption naming the gap rather than silently passed. `nexus-engine-rs` gate wiring itself is a follow-up, out of scope for this ticket.
- [x] GPU-C Open-model plan block C answered in practice (operator, 2026-08-17): Modal API key provisioned (~/.env plus ~/.modal.toml, profile shovalbenjer, auth verified via `uvx modal app list`; one prior app glimmer-lab deployed 2026-08-13). GPU bursts for the training-interpretability lane (SAE/crosscoder/KAN on small models, LoRA when the trajectory corpus is ready) run on Modal per burst; the spec's RunPod/Vast rows stand as fallback pricing, no monthly subscription, which was the spec's own recommendation
- [x] EXT-6 Connector-use ledger BUILT and wired live (2026-08-17): state/connector-use.jsonl fed by dot-claude/hooks/connector-usage-log.sh (PostToolUse matcher mcp__.*, deployed to live settings.json same turn, selftested with a synthetic payload). Registry gained rows for ElevenLabs, Zapier, AWS and the measured-usage clause. Census same date: ~24 servers surfaced, 10 routed, 11 ruled irrelevant, 2 ever actually called (claude-in-chrome, ElevenLabs); the ledger turns that from a one-off count into a running number
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
- [x] ABSORB-02a Dolt-as-database CLOSED, rejected with reasons (operator, 2026-08-17): Python access needs a standing dolt sql-server (violates no-unowned-server; the beads "Embedded Dolt" workaround is Go-only), and Dolt's content-addressed binary chunk store would replace today's PR-reviewable JSONL diffs with opaque blobs. Git-tracked JSONL already absorbs diff/history/blame. Full comparison in the 2026-08-17 DB-substrate research (session b771656c); the point-in-time reconstruction remainder stays open as ABSORB-02 below
- [x] ABSORB-04 just-my-skills coherence-governor, "steal one page". Recommended 2026-07-24 with the exact curl to run; the curl was never run and `docs/analysis/reference/` did not exist. DONE 2026-07-29: 419 lines saved to docs/analysis/reference/coherence-governor-AGENTS.md. The two pages worth taking are the 8-row Drift Sentinels table (line 262) and the 7-level Authority Order (line 43), both more compact than the equivalent scattered across five `.claude/rules/*.md` files. Merging either into calibrated-claims.md is a separate decision, not done here
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
- [x] Authorize OAuth token; distribute to 22 repos (#4), DONE 2026-07-23 (root cause: was stripping #state)
- [x] Global default model: superseded by operator decision 2026-07-29. /model set fable-5 as the saved default for new sessions and it runs on this machine; the old row wanted the opposite direction. model-selection.md rewritten with the routing table (fable default and hardest work, opus workhorse, sonnet workers, haiku inventory)
- [x] SessionStart recall rewired Windows-native (P1.1, deployed+wired)
- [x] Reflex router + flywheel S1 logger, PII-safe (P1.2, SLM #2)
- [x] /slop gate command (P1.5, deployed)
- [x] Memory + web write pipe (P1.3, #14) - real card written + recalled
- [x] Blast-radius grapher (P1.4, #16)
- [x] Live review demonstrated: PR #2, GitHub-Claude caught 4/4 seeded defects + 2 bonus; session-Claude replied (two-Claude loop)
- [x] qwen-code PARKED 2026-07-29 evening (operator: no interactive logins): its OAuth needs a browser login, the QWEN_API_KEY on disk is a 116-char non-key (DashScope keys are ~35), and the qwen model family is already served free through tools/openrouter and tools/nvidia preference lists. Config left on qwen-oauth with a .bak; revisit only if a real DashScope key appears
- [x] GitHub Models LIVE 2026-07-29: gh-models extension installed, 36-model catalog, PONG verified on openai/gpt-4o-mini and meta/llama-3.3-70b-instruct under existing gh auth; their deepseek-v3 catalog id 400s server-side (unknown_model), noted not chased. REMAINING: Groq and Cerebras probes, quotas recorded before wiring
- [x] CLOSED 2026-07-31 by measurement. scan.py false positives: top 3 ranked proposals claimed SessionStart/PostToolUse/PreCompact hooks were missing; all three exist live (7941/2519/1306 bytes) and session-recall.sh fires every session. The tool CLAUDE.md names for choosing work ranks phantom defects highest. Fix the path resolution, add a positive test per L017
- [x] CLOSED 2026-07-31, and my first reading of it was WRONG. I ran `bus.py inbox`, got an empty result, and wrote that the 19-unread figure was stale. The number was right and the reason was not: a UserPromptSubmit hook drains the bus at every prompt, so a manual `inbox` after it will always look empty, and I had measured the hook's leftovers rather than the queue. Proof arrived in the same session: the hook fired on the next prompt and printed 6 unread to lane A, all `to: ALL`, including the C-017 note that codex IS installed and the C-015 note about the bus's own delivery bug. So the bus is NOT write-only, which is what the original row feared, and the reader is a hook rather than anything a session runs. A second wrong turn worth recording: I diagnosed `state/bus-cursors/A.txt` as holding a hash where an id belongs, because I compared it against each row's `id` field. `row_id()` returns the STORED HASH for a chained row, by design and documented at bus.py:243. The cursor is the last row's hash and resolves correctly. Original row: bus inbox is never read, 19 unread messages to lane A (written as B under the pre-2026-07-30 scheme), oldest 2026-07-25, carrying live findings (160 canonical files never deployed, deploy-setup.sh false-greens, stale-rules warning now resolved-by-time with nothing recording it). Either surface unread count at SessionStart (session-recall.sh already runs) or accept the bus is write-only and say so
- [x] STALE 2026-07-29 evening: the fable-vs-opus falsifier due 08-05 was overtaken by the operator setting opus[1m] as the saved default tonight. model-selection.md still records the fable experiment as live; it needs rewriting to say the experiment was ended by operator decision before its falsifier date, and what that means for the effort-level row
- [x] REFUTE-01 CLOSED 2026-07-31. The falsifier layer returned zero information on Linux: `refute.py run` reported `26 claims: 0 held, 0 REFUTED, 26 broken verifier`, one cause, every row declared `shell: "pwsh"` and neither pwsh nor powershell exists under WSL. The tool never lied (broken is not a pass, and it exits nonzero) but the layer was inert on the host the operator now works from. Two of the seven PowerShell-native verifiers were also AIMED at `$env:USERPROFILE\claude-setup`, the Windows clone, a different working tree. Now `21 held, 5 REFUTED, 0 broken`. Commit `aeaecd3`; 8 tests red before the fix; `mutate --spec refute` 12 of 12 caught
- [x] DOCS-01 CLOSED 2026-07-31. `docs/INDEX.md` listed 22 of 112 prose documents. Rewritten to 113 of 114 (it does not list itself), titles and declared statuses extracted from the files rather than written from memory, and it now passes `slop_lint` where before it had 43 em-dash hits
- [x] ABSORB-09 CLOSED 2026-08-10 with ABSORB-01, one change, as this row asked. The
  sentence was kept and `verdict_class` added beside it. Grouped, the 41 records are 18
  split, 17 keep-ours, 2 build, 2 wrap, 1 absorb, 1 delete-ours, 0 adopt, which is the
  question that previously cost 41 file reads. I first wrote 17 and 16 here from the
  assignment table rather than from the written files, and the count disagreed; epic #29
  is the row that says any deliverable with more than five derived numbers gets a
  verification pass by something that cannot see the reasoning. Original row below.
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
- [x] PERSONA-01: the allocator. `tools/review/allocate.py` maps a change to aspects and aspects to actors, decorrelating on `model_family` and never on `host`. Selftest green, 8 checks. It found its own defect on the first real run: it paired `nvidia-nim [VARIES-BY-MODEL]` with `qwen-dashscope [alibaba-qwen]` for `slop`, which is precisely the correlated pair `actors.json`'s contract forbids, because nvidia-nim serves qwen. A reseller family is now admissible only as a solitary reviewer
- [x] PERSONA-11: the three greppable bans from the restored `boundary-contracts.md` are now enforced. New `boundary` persona in `panel.py` with go-discarded-marshal (HIGH), go-discarded-read (HIGH) and ts-unchecked-json-parse (MED). Go arrives as a fixture language for the first time, since no check declared it before. `tests/test_panel_boundary_bans.py` pins the NEGATIVE cases, which is the half that decides survival: `a, err := json.Marshal(...)` and `_, err := ...` must stay quiet, and so must prose about the ban, which is L-2026-07-31-b and has already cost three review waivers. 8 tests, 436 in the suite, 0 findings on this repo's own tree. Side effect worth naming: the panel/registry vocabulary overlap goes from 2 of 11 words to 3, because `boundary` now has a local rule set as well as four external actors declaring it, so `allocate.py` can plan both halves of one dimension
- [x] **WITHDRAWN, filed and retracted within ten minutes on 2026-08-05.** I reported that `strand.py` declares `NOT_A_CONSUMER` and never applies it. It does apply it, at line 199 inside `evaluate()`, one layer after `build_reference_index` where I was looking. The reason I filed it at all is the useful part: my fixture written to reproduce the bug PASSED BEFORE my fix, which is the signal that there was no bug, and I nearly shipped an oracle edit plus two tests that passed for the wrong reason. A parallel session had already pinned the real behaviour properly in `test_generated_inventories_are_not_consumers` and `test_the_exemption_ledger_is_not_a_consumer`. Left in the ledger rather than deleted, because a retraction that vanishes teaches nothing.
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
- [x] **WITHDRAWN: `strand.py` `NOT_A_CONSUMER` declared-but-unapplied.** It is applied, at
      line 199 in `evaluate()`, one layer past where I was reading. The tell was that my
      fixture passed BEFORE my fix. I nearly shipped an oracle edit plus two tests that
      passed for the wrong reason. A parallel session had already pinned the real behaviour.
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
- [x] **docs/books is queryable end to end**: 22 PDFs extracted, 323 txt indexed,
      `tools/corpus/books_check.py` clean. Decision and what stays unreadable (4 mobi,
      1 djvu, duplicates) in `docs/analysis/2026-08-23-books-corpus-wiring.md`.
- [x] docs/ root went from 43 files to 18; 25 point-in-time files moved to `docs/archive/`,
      37 analysis snapshots dated on or before 2026-08-08 with no live referrer to
      `docs/analysis/archive/`, 2 self-declared superseded specs to `docs/specs/archive/`.
      References rewritten in 27 files; docmap treats `docs/archive/` as historical-record.
- [x] lane A: ship_gate_stop.py committed-docs-only case. DONE 2026-08-13, commit b43b570 on worktree-repo-gap-analysis, live hook updated. The 2026-08-13 docs-only fix
  classifies the WORKING diff vs HEAD, so a clean tree whose only delta since the last
  gated run is committed docs (e.g. regenerated maps) still hard-blocks. Extend
  is_docs_only to diff HEAD against the last gate-runs.jsonl row's commit for this
  project and downgrade when that delta is all prose. Regression test exists at
  tests/test_ship_gate_docs_only.py to extend.
