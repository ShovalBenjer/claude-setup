# 2026-08-15: unfinished work inventory, the full waterfall

Status: MEASURED
Measured against: commit cb3962d (merge of PR #73), branch `claude/unfinished-work-inventory-g4e0ys`, GitHub state as of 2026-08-15T00:54Z.

## Method and trust boundaries

Sources read: `TODO.md` (217 open rows counted now), all 37 open GitHub issues, PR #74 and its review, the 3 closed-unmerged PRs, `docs/INDEX.md` and the 21 specs it indexes, 58 `docs/analysis/` files, 6 reflections, `work-docs/` (~100 files, 2026-01 to 2026-07), the `state/` ledgers, `quality-contract.json` plus `docs/QUALITY-CONTRACT.md`, `.github/workflows/ship-gate.yml`, and a code-marker sweep over `tools/`, `dot-claude/`, `dot-codex/`, `dot-agents/`, `intent-control-plane/`.

Owner classes per row: OPERATOR (needs a human decision or credential) or AGENT (a session can do it). Rows carry their source so nothing here has to be trusted on this file's word.

This container cannot see the live `~/.claude`, so every claim about the deployed home is relayed from repo records, not re-measured. `skills_sync.py check` refuses to run here and `pointers.py scan` defers 593 findings for the same reason.

### Rows elsewhere that this inventory supersedes

These are stale in their home surface and corrected here, per the append-only convention of fixing the record forward:

1. TODO.md skills-waiver rows (51 items, DRIFT 29, DRIFT 16): superseded, `quality-contract.json` records the waiver REMOVED 2026-08-12 with `skills_sync.py check` CLEAN, 81 in sync.
2. TODO.md and the 2026-08-11 milestone plan's PR triage rows for #42/#47/#52/#53/#60/#61: superseded, the 2026-08-12 claims outcome row records all six merged with timestamps.
3. DOCS-05 ("CLAUDE.md says 12 domains, contract says 13"): both numbers stale, the last gate run reports 16 domains.
4. AGENTS.md gotcha numbers: measured now, 13 of 32 `dot-claude/hooks` files are stubs (doc says 12 of 29); the dead home is cited by 319 files, 231 markdown (doc says 359 and 241); `docs/INDEX.md` indexes 21 ADRs (doc says 15).
5. Zion issue #20's claim that `gemini-review.yml` "has still never been written": the file exists on disk at 4868 bytes. What has never happened is a run (AUTO-10).
6. FOG row "90 of 96 open TODO items invisible at boot": the open count is 217 now; the boot-visibility problem is unchanged (the recall hook slices 6 rows).
7. `docs/EXECUTION-PLAN.md` Phase 1 rows P1.1-P1.5 are unchecked there while TODO.md marks them `[x]`: TODO.md is the fresher surface; EXECUTION-PLAN needs the checkboxes reconciled.
8. Closed-unmerged PRs #39 and #40 (lane A rules oracle): read as abandoned unless a later merged PR carried the work; verify before reviving, do not assume dropped.

## Phase 0: operator decisions, time-boxed first

Nothing an agent does unblocks these; several expire this week.

| # | Decision | Deadline | Source |
|---|---|---|---|
| 0.1 | OCI account: upgrade Always Free A1 to PAYG or the instance is terminated | on/after 2026-08-18 | `docs/specs/2026-08-12-open-model-and-scheduling-plan.md` block B |
| 0.2 | Open-model plan blocks A, C, D, E: DeepSeek $5 prepaid; GPU burst budget; arm the two cloud routines plus nightly local gate timer; which lane converts first | with 0.1 | same spec, section 6 |
| 0.3 | Skills picks before the fork waiver expires: deploy-or-drop 4 waiting skills, pick a side on 4 forked ones | 2026-08-19 | `docs/analysis/2026-08-12-plain-handoff.md` item 5 |
| 0.4 | Verify the ElevenLabs key rotation against the provider dashboard; the TODO row closed on operator assertion only | soon | TODO FOG row 1, `docs/analysis/2026-08-10-inbox-secret-exposure.md` |
| 0.5 | Check AWS instance `i-0a9036fae28fe32ee`: still running, still billing; no credentials held here | soon | plain-handoff item 4 |
| 0.6 | S6 autonomous loop: PROPOSE or ACT. Gates the largest open item (the autonomy rails) | none, but blocks Phase 5 | `docs/analysis/2026-08-09-session-scope-ledger.md` B3 |
| 0.7 | Three contested top-level dirs: `dot-agents` (8 live skills have their only repo copy there), `dot-codex`, `intent-control-plane` vs `tools` boundary. Unblocked in the same report: archive `home-dotfiles` and `startup-scripts`, merge `master-plans` into `work-docs` | none | `docs/analysis/2026-08-07-toplevel-dir-decisions.md` |
| 0.8 | HOOKGATE-01: running `regen_rules.py` fixes the failing test and relaxes the force-push guard in the same command. Blocks the `unit` domain (red since 2026-08-05) | none | TODO HOOKGATE-01, `tests/test_hookgate.py` |
| 0.9 | Licence blocker on going public: `docs/analysis/reference/coherence-governor-AGENTS.md` is 17,923 bytes verbatim from a repo with no licence. Summarize-and-link, request a licence, or accept staying private | none | TODO 2026-08-06 block; issue #11 |
| 0.10 | EXJOB-01 retire-or-refactor: `jira-comment-drafting` names three ex-colleagues in every session's context | none | TODO EXJOB-01 |
| 0.11 | PILE-02: one payload tree or three. 29 byte-identical skills collapse the moment this is decided | none | TODO PILE-02 |
| 0.12 | Estate-audit section 8 leftovers: which agent-communication surfaces to widen; DeepSeek pivot order; re-arm crons or not; second Windows clone disposition (17 files exist nowhere else, `chore/delete-dolt` only there) | none | `docs/analysis/2026-08-11-estate-audit.md` section 8 |
| 0.13 | Gmail connector stays off or turns on (zero calls in 1183 sessions vs full-mailbox OAuth scope) | none | TODO connector-catalogue row |
| 0.14 | `perf` domain: becomes real (gate wall clock, hook latency) or stays N/A with corrected wording | none | TODO row; `quality-contract.json:67` |
| 0.15 | REFUTE-02/03: live `~/.claude/CLAUDE.md` deleted and `settings.json` rewritten with an incomplete pre-write snapshot; say re-baseline or restore | none | TODO REFUTE-02, REFUTE-03 |
| 0.16 | voice-metrics preservation: only live-only skill not committed; profiles carry a WhatsApp LID and 9.3 MB lexicons | none | TODO lane-B outcomes block |

## Phase 1: in-flight GitHub work

AGENT-doable, already has review attention, closes fastest.

1.1 PR #74 (reanimation + coffee v2). CI is green and mergeable, but the Claude review comment is unaddressed:
  - High: `tools/reanimation/router.py` `chat()` except-tuple misses `IndexError` and `json.JSONDecodeError`, so one malformed lane response kills the whole persona build instead of failing over.
  - Medium: `tools/reanimation/extract.py` sqlite reads have no error boundary; store schema drift surfaces as a raw traceback.
  - Low: `persona.py` `_json_only()` uses `lstrip("json")` (character set, not prefix); `breakroom.py read -n 0` returns the whole board (`list[-0:]`).
  - Nits: unverified `--contact` chatId silently yields an empty extraction; `.gitignore` `.intent/` entry likely matches nothing; `fingerprint.py` p90 is an index approximation.
  - Reviewer's own caveat: the review was static; run `python -m pytest tests/test_reanimation.py tests/test_coffee.py -q` before merge.
  Close-out: fix or explicitly dismiss each finding, run the tests, merge.

1.2 Issue #57: `tools/e2e/flow.py` state fingerprint never reads `document.documentElement`, so theme and attribute toggles are reported dead (11 of 17 flow failures in the consumer repo are false, and the fail count is non-deterministic, 40 vs 39, leaking into consumer waivers). Fix per the issue: include `documentElement.outerHTML.length`, and the more important half, extend `flow.py selftest` with a planted control whose only effect is an attribute on the html element.

1.3 Issue #58: two lane sessions shared one checkout; a lane C deletion is stranded inside a lane D commit. Untangle and add the guard (relates to ABSORB-03 worktree isolation).

1.4 Issue #56: lane D the-bench brief said one genre, the built skill declares another. Reconcile skill to brief or amend the brief.

1.5 Issue #38: agent-feed recheck due 2026-08-19; if the feed has posts and no engagement, post less.

1.6 Closed-unmerged PRs #39/#40: confirm the rules-oracle work they carried landed elsewhere or re-open deliberately.

## Phase 2: cheap hygiene, hours each, all AGENT

2.1 `.gitattributes`: no eol rule for `*.ps1`, so 7 files are permanently dirty on POSIX and `gate.py status` reports "this tree has never been gated" on every clone. One line unblocks ever gating a clean tree.
2.2 `tools/audit/pointers.py:346`: the printed-kinds tuple omits `wired-unverifiable`, so `scan --fail-on low` prints FAIL with zero findings shown, the exact defect the comment at line 470 says was fixed. Also decide whether the Windows-path skip at line 461 should cover UNC `\\wsl.localhost\...` paths.
2.3 `.github/workflows/ship-gate.yml:303`: `continue-on-error` on `skills_sync.py check` was conditioned on the skills waiver, which was removed 2026-08-12. Drop the line; it currently swallows a checker that correctly returned 1 on 51 real items.
2.4 Delete `dot-claude/bin/pretooluse-ink.sh` and `posttooluse-ink.sh`: both self-describe as retired placeholders safe to delete.
2.5 Correct stale numbers: AGENTS.md (13/32 stubs, 319 files, 231 md, 21 ADRs, 16 domains), DOCS-05, Zion #20 (`gemini-review.yml` exists), Zion #27 item 1 checkbox.
2.6 `a2a-codex-call.sh` lines 128-146: shell vars interpolated into a `python -c` template corrupt peer responses. Five-line fix plus a byte-identical round-trip test feeding `\x41`, tab, and `C:\new`.
2.7 SKILLDEP-02: `apt install jq` unblocks 4 skills (`gws-gmail-read`, `gws-gmail-triage`, `pii-scrubber`, `review`).
2.8 TELEMETRY small rows from the PR #62 review: `post_discussion()` must check the second GraphQL call's stdout, not just the return code, or a data-level error advances the cursor and drops the batch; reject `discussion` numbers below 1.
2.9 Reconcile `docs/EXECUTION-PLAN.md` P1 checkboxes with TODO.md (see superseded row 7).
2.10 `dot-claude/bin/self-improve.py:27` inserts a nonexistent `$HOME/projects/...` path on `sys.path`; fix or retire.

## Phase 3: gate integrity, the P0 epics

3.1 Epic #10 (P0): commit at-risk work and settle absorption verdicts. The measured absorption rate is 1 of 41 records that name what was taken; ABSORB-01/09 left "the real work" as 40 unwritten reviews, first forced decision 2026-09-07 via `recheck_after`. Includes executing or reversing the `tools/whatsapp` `delete-ours` verdict (4 tracked files still present).
3.2 Epic #50 (P1 but gating): bind the instruments that already run to a ratchet. RATCHET-01 needs `/diverge` first (charters rule 2); RATCHET-02 names the first candidate, the pointers absent-path count that went 261 to 271. This inventory's phase counts are a second candidate baseline.
3.3 Epic #28 (P0): a waiver's reason must name the mechanism its falsifier tests.
3.4 GATE-LOOP-01: `codemap` and `review` cannot both be green at once; exclude gate outputs from codemap the way `GATE_OUTPUTS` already does, or key the review artifact by tree fingerprint instead of commit sha (the `review` domain matching by sha is also the dirty-tree staleness gotcha in AGENTS.md).
3.5 `state/claims.jsonl` carries two incompatible row shapes (`proposal_id`+`ts` vs `id`+`claimed_at`); a reader expecting one silently drops the other. Both shapes verified present.
3.6 Gate selftest ledger isolation: workflow-spawned selftests wrote scratch-repo rows into the real `state/gate-runs.jsonl`.
3.7 `skills_sync.py` has no mutation spec (14 specs exist, none for skills); first two mutations are named in TODO.
3.8 Refutation residue: REFUTE-04 (1 of 12 hook registrations does not resolve), REFUTE-05 (`mutate --spec bus` fails against current tree), REFUTE-06 (`hiring_engine/ledger.sqlite` absent, lane B).
3.9 CI verification gaps in `ship-gate.yml`: claim C-018 effectively never runs in CI (`needs: deployed`); `bus.py verify --strict` fails on the 12 pre-chain rows; `refute.py run` permanently excludes C-015, C-022, C-024, C-026. Decide per item: make runnable, or record why not.

## Phase 4: verification infrastructure, the P1 epics

4.1 Epic #20: gate in CI. The `review` job posted "Claude encountered an error after ~40s" with the error swallowed; four theories tested and discarded; `ANTHROPIC_LOG=debug` is now set. Next action per TODO: read that run, do not add a fifth theory. Likeliest remaining cause is the OAuth token (operator rotation). Also: 3 of 5 jobs now depend on the single self-hosted WSL runner, a stated single point of failure.
4.2 Epic #6: dead pointers, stubs, drift. 13 of 32 `dot-claude/hooks` and 17 of 30 `dot-codex/hooks` are one-line stubs into the dead `/home/shovalbe/` home; they fail open and enforce nothing. 319 files still cite that home. Write the hooks or delete them and their wiring.
4.3 Epic #5: reconcile the repo's self-contradictions (the superseded-rows list above is the current worklist; DOCS-03's 8 status-less specs; the two architecture-build-plan files that supersede each other with neither recording it; the LightRAG-vs-sqlite spec contradiction where neither document references the other).
4.4 Epic #34: adopt ast-grep so an oracle can tell code from prose about code. Retires the `panel.py` prose-vs-code false-positive class (third waiver for it) and PERSONA-12's hand-rolled TS rules. Regression oracle named in TODO: same string as comment CLEAN, as code HIT, one file.
4.5 Epic #27: the prose gate measures the ruled form, not the property. `slop_lint.py` still prints "no band fitted"; port density and variance from `voice_score.py` with thresholds fitted on the operator's corpus; add fenced-code awareness (DOCS-02); add the ~8 regex-able structural patterns from the external no-slop list as a class separate from `BANNED_PHRASES`.
4.6 Epics #31, #32, #25: record where the plan was refuted (plan-deviation ledger exists, 5 rows, binding does not); fix data structures and interfaces first; supply-chain verification (osv-scanner steps still `continue-on-error` pending "one real run read"; ShellCheck into the supply-chain job).
4.7 skilleval: 42 of 47 skills carry no fixture; write fixtures with provenance (RT-4: audit the existing 5 first), then turn on `--strict` and `--strict-ties` (one live tie: `gws-gmail` vs `explain-simply`).
4.8 SKILLDEP-01 then SKILLDEP-03: decide the `az` question (9 skills, one persona), then wire `skill_deps.py scan --strict` into the skills domain (strict is currently red on 26 pre-existing skills and consumed by nothing).
4.9 INTENT-01/02: all 467 prompt tickets sit at CAPTURED; the state machine in `tools/intent/tickets.py` is called by nothing. Wire transitions at the two points that already know (claim row written, Stop-gate completion). Measure what dominates the 241 unresolved.
4.10 Docs control plane: generate `docs/INDEX.md` or ratchet docmap's reachability number, not both (DOCS-04); `docs/specs/archive/` does not exist though rule 3 sends superseded specs there; `strand.py` checks 1 of 3 header fields; the persona-review-economy spec header still lies (`Status: active` over a paper spec).
4.11 HOOKPATH-01 remainder: `capture_turn.py` and one other UserPromptSubmit hook still derive `REPO_ROOT` from `__file__` in a mutable working tree; deploy them or wrap fail-open. Related: verbatim prompt capture has been dead since the WSL move, with the hook swallowing the failure by design.
4.12 METRIC-01/02/03: review-finding precision, request-to-outcome transitions, per-task token logging; trivial-baseline comparison beside any self-computed score; connector-description poisoning scan folded into `pointers.py`.
4.13 `intent-control-plane/repo_health.py` enforces file/function/class budgets and is invoked by nothing; wire it or delete it. Related: 14 modules exceed the imported 500-line hard limit (worst: `gate.py` 1451, `panel.py` 1387, `bus.py` 1244 with a 614-line function) and no contract domain measures size at all.
4.14 `tools/audit/skills_sync.py` exits 0 when it cannot measure (no live home); make "unmeasured" distinguishable from "clean" for callers.
4.15 Windows known-failing, deliberately unwaived: 3 intent-control-plane sqlite-teardown test failures; `cdp_driver.py` (`websocket`) and `setup_token_pty.py` (`winpty`) imports declared in no manifest, which also falsifies the `build` domain note claiming `tools/` imports stdlib only.

## Phase 5: native surfaces and autonomy

5.1 Epic #22, AUTO backlog: AUTO-06 `ecosystem.db` bootstrap first (unblocks AUTO-04 work-claims and AUTO-19 FleetView); AUTO-10 `gemini-review.yml` has never run (closes on a real PR showing a Gemini annotation, needs `GEMINI_API_KEY` from the operator); AUTO-18 register the two real schedules and observe one unattended fire; AUTO-11 merge-policy labels; AUTO-09 nightly scale-out after 7 clean days; AUTO-12/13/14 social pipeline; AUTO-15 resume rails; AUTO-17 research stage; AUTO-20 reputation routing.
5.2 CHAN rows: CHAN-03 decide dense-payload encoding before the first dense row lands in the hash-chained bus; CHAN-02 envelope with per-peer capability and router ERROR on `kv` to API-only peers; CHAN-05 wire `roundtrip.py selftest` into CI with a mutation spec; CHAN-04/07/08/09 measured live leg, Kilo template fit, per-leg local-vs-cloud choice, schedule floor check.
5.3 Epic #14, persona economy: PERSONA-06 first external review (all 18 artifacts to date say "external backend not requested"); PERSONA-03 wire `panel.py` to consume `allocate.py`; PERSONA-05 the two-model agreement gate that ADR-0012's auto-merge depends on does not exist, build it or amend the ADRs; PERSONA-07 per-lane bot identity; PERSONA-08 export `CLAUDE_SESSION_ID` into the hook env; PERSONA-02 a second `a11y` actor; PERSONA-10 measure decorrelation (blocked on 06); PERSONA-01 registry routes personas through three `~/.claude/corpus/` paths that do not exist.
5.4 Epics #12 and #16: wire the Claude Code native surface already paid for; run one workflow under the prescribed routing.
5.5 Epic #13: replace the bespoke agent bridge with ACP. Epic #15: Kilo integration (blocked-operator). Epic #11: the licensing and privacy blockers (0.9 above is the hard one).
5.6 intent-control-plane backlog (its TODO is 45 days stale but the items stand): P1 split the 1458-line `cli.py`, isolate the `redact` boundary, wire ruff+mypy+unittest into a commit gate and CI, installed-entrypoint smoke test; P2 declarative kind table, property tests for redaction and ledger invariants, golden retrieval fixture; 2026-07-05 enhancements (accountability gates before SHIPPED, git ingestion contracts).
5.7 Prompt inbox: 304 prompts awaiting triage (0 workable), 12 surfaced as PT rows; run the triage or build the agentic pass that proposes a state per ticket (intent-traceability spec question 4).
5.8 EXJOB-02/03: rebuild `azure-activity-watch` against git+gh; the `jira-read` holdback is not durable against the next `skills_sync.py deploy --apply`, either retire it from the payload or teach skills_sync an exclusion list.

## Phase 6: scale, absorption, research

6.1 Epic #8: shrink 1682 tracked files toward 600. Feeds on: work-docs archaeology (the 2026-01 to 2026-06 plans are superseded and unmarked: the Codex-delegation backlog contradicts ADR-0007, `MODEL-MIGRATION-PLAN.md` is superseded by the 2026-08-12 spec with no link), the 0.7 archive calls, and PILE decisions.
6.2 ABSORB backlog: ABSORB-05 FleetView is specced with zero code, and P-DASH says evaluate buying `claude-command-center` before building; ABSORB-03 rebuild albert's two mechanisms (worktree isolation per producer, producers never grade themselves); ABSORB-07 the saved-link corpus (806 URLs, brief ready to run); ABSORB-08 vulture triage of 70 findings plus gate wiring; ABSORB-09 7 adopt-candidate skills, none installed; ABSORB-02 DoltHub-style point-in-time reconstruction for gitignored ledgers (epic #26), with the hiring ledger as the concrete need.
6.3 External-source debt: 103 of 115 rows in `state/external-repos.jsonl` untriaged; 57 saved repos captured once and never compared; 138 community repos resolved and unevaluated; the repo-compare skill produced 4 adopt proposals with named trial gates, none started.
6.4 Epic #23, research transfer RT-1 to RT-5: calibration logging for the autonomy gate; decision ledger with rejection rate (753 gate runs, zero human approve-or-reject recorded); print the joint claim under the gate VERDICT; fixture provenance; first metamorphic relation (codemap: renaming one directory must change exactly one row). Metamorphic is cited in four places and built in none.
6.5 Epics #35, #29, #33, #21, #17, #7, #9, #24, #19, #18: repo-clear as enforced standard; review recomputes its own numbers; artifact through a measurement function; agent-maintained repo standards; design foundations; phase D reclamation; WSL2 launcher; RTK adoption; absorb open-design and OpenGame; The Construct v4.
6.6 No retrieval layer over `state/`: roughly 130 M transcript tokens a week, ledgers read by tail and grep; the session-rag index claim row explicitly left embeddings and `tools/intent` integration unclaimed.
6.7 Six imported standards bound to nothing, and two structure standards unreconciled; 48 definition-of-done rows that zero tools read (classify before building a checker); the cross-artifact graph (three of four edges exist as one-off scripts, none queryable).
6.8 Stranded analyses with live work behind them: `2026-07-24-creativity-wow-gap.md` and `2026-07-24-research-wiring-audit.md` (the designed `research_sweep.py` remains unbuilt).
6.9 `tools/selfimprove/proposals.jsonl` does not exist on disk while `docs/INDEX.md` and `docs/charters.md` both point at it as the ranked-work sink; either run `scan.py` and commit the output path decision, or fix the two pointers.
6.10 `nexus-engine-rs/` (4 Rust files) sits outside `quality-contract.json` with no tests; name it in the contract or archive it.

## Appendix A: dedup map

Items claimed by three or more surfaces, so a fix in one place should close all of them:

| Item | Surfaces |
|---|---|
| ElevenLabs key rotation | TODO FOG 1; estate audit 1 and 8.1; milestone plan; plain-handoff; lesson L-2026-08-11-b; inbox-secret analysis |
| Skill forks / three trees / canonical tree | TODO B; PILE-01/02/04; milestone decisions 5-6; three-trees analysis; plain-handoff; pile-manifest ledger |
| FleetView / command-center | AUTO-19; ABSORB-05; P-DASH; command-center spec; plain-handoff paper table; repo-compare proposal 4 |
| ecosystem.db | AUTO-06; charters rule 1; ADR-0011; FleetView substrate |
| Metamorphic testing | RT-5; TODO row; HANDOFF-2026-08-05; research-transfer analysis |
| panel.py prose-vs-code | SETUP-OS rows; lane-B outcomes; L-2026-07-29-d; PERSONA-12; epic #34 |
| slop_lint form-vs-property | SETUP-OS row; Zion #27 item 2; density-gate analysis; epic #27 |
| S6 propose-vs-act | FOG row; scope-ledger B3; delegation plan item 1; autonomy PRD; estate audit |
| Two-model agreement gate | PERSONA-05; ADR-0004; ADR-0012; AUTO-10; EXECUTION-PLAN Phase 2 |
| Codex removed but still cited | ADR-0007; P0 row; EXECUTION-PLAN Phase 0; the 35 KB work-docs backlog; estate-audit addendum |
| 500-line limit unenforced | 14 TODO rows; repo_health.py; nr-code-quality standard; no contract domain |
| Prompt tickets all CAPTURED | INTENT-01; prompt-inbox block; intent-traceability question 4; plain-handoff |
| Gastown crons / scheduler | estate audit 2; open-model plan 5 and block D; L-2026-08-11-a; AUTO-18 |
| 57 saved repos never compared | TODO row; HANDOFF-2026-08-05; github-repo-triage analysis; 2026-08-10 claim row; estate audit |

## Appendix B: counted baselines for the ratchet

Numbers measured for this inventory, dated 2026-08-15, offered as ratchet baselines (epic #50): TODO.md open rows 217; open issues 37 (epic checklist completion 5 of 184); stub hooks 30 (13 + 17); dead-home files 319; skilleval fixtures missing 42 of 47; prompt tickets at CAPTURED 467; external repos untriaged 103 of 115; absorption reviews unwritten 40 of 41; specs at PAPER 13 of 26 verdicted; pointers absent-path findings 594 total (14 high); modules over 500 lines 14.
