# TODO — Claude OS

One TODO, grouped by layer, ticket-tagged (SETUP-OS + AUTO). Status mirrors
docs/prd/claude-os.md and docs/prd/autonomy-ecosystem.md. Fresh session? Read
docs/SESSION-BOOT.md first.

## AUTO — Autonomy Ecosystem (prd/autonomy-ecosystem.md, spec 2026-07-24)
- [x] ADR-0010..0015 + PRD + spec + charters + SESSION-BOOT + lessons ledger (AUTO-03/08/13/16 seed) — 2026-07-24
- [x] AUTO-01/02 hook fire-proof — CLOSED 2026-07-24 22:44. `state/hook-fires.log`: 7 harness-written SessionStart lines (real session ids incl. `8abb324e-…`) + 11 PreCompact lines + 12 `## compact` snapshots in `state/compact-log.md`. L011 interpreter/path bug fixed and now proven in-harness, not by pipe test
- [x] COMPACTION CHURN measured resolved 2026-07-29: PreCompact per day 47, 250, 2, 1, 0, 0 across 07-24 to 07-29; per-session 15.6 on 07-25 down to 0.0 on 07-28/29. Both suspect env vars (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `CLAUDE_CODE_DISABLE_1M_CONTEXT`) are ABSENT from live settings; sessions run on 1M context. `trigger=` now logged (289 lines). Caveat: the churn ended 2026-07-26 with no config change recorded, so the cause of the fix is not established; reopen if per-session climbs above 1
- [ ] DECIDE (counts re-measured 2026-07-29): live `~/.claude/settings.json` has 7 hook events (UserPromptSubmit added 2026-07-29 for intent capture; PostToolUse is live-only, absent from canonical). The work enforcement layer is still undeployed: PreToolUse protect-infra/rtk-bash-guard, Stop stop-checklist/verification-before-completion/contract-proof-stop, PostToolUse skill-usage-logger. Adopt selectively; these are the checks that would have caught L003/L009 mechanically. Note rtk binary is missing on Windows, so rtk-bash-guard cannot deploy as-is
- [x] Nightly autonomy pilot workflow on claude-setup (AUTO-07) — first scheduled run pending
- [ ] ecosystem.db bootstrap from intent-control-plane schema + tools/eco/db.py (AUTO-06) ← unblocks work-claims (AUTO-04) + FleetView (AUTO-19)
- [x] AUTO-05 CLOSED 2026-07-29: Lane A RETIRED by operator decision (never used once between ADR-0013 and retirement). Intake/routing folded into Lane B as plumbing (docs/charters.md); UserPromptSubmit capture already ledgers intent. Any future RC/phone intake surface is a B feature, not a session lane
- [ ] Merge-policy labels + auto-merge for auto:low (AUTO-11)
- [ ] Scale nightly to tier-1 repos after 7 clean days (AUTO-09)
- [ ] Social: excavate social-media-agent.bundle → draft-first pipeline (AUTO-12/13/14)
- [ ] Research stage in weekly self-improve cron (AUTO-17)
- [ ] Reputation routing once runs-table volume (AUTO-20)
- [x] AUTO-10 UNBLOCKED 2026-07-24 (was falsely BLOCKED(operator), L012): key was already in a local .env; `gh secret list -R ShovalBenjer/claude-setup` now shows `GEMINI_API_KEY 2026-07-24T20:17:02Z`. Value piped via stdin, never echoed. REMAINING: wire the gemini-review workflow to consume it (the secret alone does not make two-model review live)
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

## RT — Research transfer (docs/analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md)

External research on compile-once architectures, commissioned 2026-07-27, landed
five findings on this harness. Ranked by ratio of value to effort.

- [ ] RT-1 Log `{claimed_confidence, action, verified_outcome}` so the CLAUDE-OS.md:45 gate (>=0.90 autonomous) can be calibrated at all. Today the reliability curve is not computable, and the literature says self-reported confidence sits at 80-100 regardless of accuracy, which would make that threshold inert rather than protective. Measure before tuning
- [ ] RT-2 Decision ledger + rejection rate on the daily digest. Three ADRs (0005/0012/0014) rest on human approval; `state/` records 753 gate runs and machine refutations but no human approve-or-reject, so rubber-stamping is undetectable. A ratio that has never seen a rejection IS the finding
- [ ] RT-3 Print the joint claim under `gate.py run`'s VERDICT: which domains were N/A and why, and what a PASS does not assert. Per-domain boundaries are documented; the composite one is not. Strings already exist in quality-contract.json
- [ ] RT-4 Fixture provenance for `tools/skilleval` + one independent audit of the existing 5 before writing the next 42. Self-annotated labels are the BIRD defect (52.8% annotation errors there); expanding coverage without auditing labels scales the defect
- [ ] RT-5 First metamorphic relation (start with codemap: renaming one directory must change exactly one row). The repo has mutation testing, which asks "can this check fail", and nothing that asks "is the output invariant under a transformation that must not change it". `grep -ril metamorphic tools/` returns zero implementations

## ABSORB: external resources evaluated but never absorbed

Operator directive 2026-07-29: every external resource we look at must end in
absorbed (idea taken into our code), adopted (dependency added), or used as-is.
"Evaluated and shelved" is not an outcome, and 0 features may be neglected.
Audit of every external resource this repo has evaluated is below. Nothing here
deletes an existing row; these are the rows that were silently dropped.

- [ ] ABSORB-01 ROOT CAUSE: the prior-art record schema cannot express absorption. All 27 records carry the same 14 fields (`verdict`, `why`, `strongest_counterargument`, `migration_loc`, `our_loc`, `recheck_after`, ...) and not one of them names what was taken from the alternative. So absorption is unrepresentable, therefore unchecked, therefore never happens. Add `absorbed` (what we took and the file it landed in) and `absorption_status` (absorbed / adopted / used-as-is / rejected-with-reason), backfill all 27 records, and have `codemap.py prior-art` fail on a record whose status is unset. Extends an oracle that already runs rather than adding a thirteenth domain (see the 4.2 warning in docs/reflections/2026-07-29-what-is-going-wrong.md)
- [ ] ABSORB-02 DoltHub option (c), the deferred half. Three of Dolt's five features (diff, history, blame) were genuinely absorbed on 2026-07-25: `state/*.jsonl` is append-only in git, so `git show <rev>:state/x.jsonl` answers "what did this say on the 25th". The unabsorbed piece is point-in-time reconstruction for the ledgers that are gitignored and therefore have NO history at all, named in docs/analysis/2026-07-25-our-own-dolt.md section 4(c) as roughly 150 lines and deferred "only when a concrete need appears". It was never ticketed anywhere, which is how it got neglected. The concrete need now exists: `hiring_engine/ledger.sqlite` holds 272 jobs, 4 applications and 21 approvals with zero history (docs/analysis/2026-07-29-local-dependency-audit.md section 4). Lane C owns that ledger, so this is a lane-B proposal row, not lane-B work
- [ ] ABSORB-03 albert (Sdraugel/albert), two mechanisms. Code reuse is blocked by PolyForm Noncommercial 1.0.0, so these get rebuilt, not copied: (a) git-worktree isolation per concurrent producer, which structurally kills the one-tree race that is open risk 1 and that fired again during this session's own verification run; (b) producers-never-grade-themselves enforced by role rather than asserted in prose, starting with the prior-art records, which are currently written and self-graded by their own author. Verdict and license reasoning in docs/analysis/2026-07-29-albert-prior-art-verdict.md
- [x] ABSORB-04 just-my-skills coherence-governor, "steal one page". Recommended 2026-07-24 with the exact curl to run; the curl was never run and `docs/analysis/reference/` did not exist. DONE 2026-07-29: 419 lines saved to docs/analysis/reference/coherence-governor-AGENTS.md. The two pages worth taking are the 8-row Drift Sentinels table (line 262) and the 7-level Authority Order (line 43), both more compact than the equivalent scattered across five `.claude/rules/*.md` files. Merging either into calibrated-claims.md is a separate decision, not done here
- [ ] ABSORB-05 CCC (amirfish1/claude-command-center) is NOT a new row on purpose: AUTO-19 above already owns it and the operator said not to duplicate or delete tasks. Recording the absorption status against it instead. Verdict was ADOPT-PARTIAL on 2026-07-24 with one idea named worth taking (jsonl-on-disk as truth, replacing the dead WSL intent.db path); `docs/specs/2026-07-24-command-center-superior.md` carries a 12-row feature table, 5 premortems and an 18-item acceptance checklist; `tools/fleetview/` still does not exist. Status: SPECCED, ZERO CODE, 5 days
- [ ] ABSORB-07 The saved-link corpus, which is the real unabsorbed pile and dwarfs the four repos audited above. `wa-export-archive/SENSITIVE-self-chat/_chat.txt` holds 8546 lines over roughly 14 months: 984 URL occurrences, 806 unique, 80 unique github.com repos, 12 arxiv papers, 14 learn.microsoft.com pages, 166 youtube. Save rate rose five to ten times in July 2026, so recency signals current intent. Named by docs/HANDOFF-FROM-LEARNING-2026-07-27.md section 3.6 on 2026-07-27 as "better curated than the learning platform's 11 world-scan sources because it is filtered by his actual attention. It is unwired." Two days later it was still unwired. Links and dates extracted 2026-07-29 to `C:\Users\shova\wa-export-archive\self-chat-links-2026-07-29.csv` (no message text copied, source is marked SENSITIVE and stays local). External brief ready at docs/2026-07-29-external-absorption-brief.md; run it in Claude Desktop with the CSV attached, then file the returned table against this section
- [ ] ABSORB-08 vulture ADOPTED 2026-07-29, the first genuine third-party tool in this repo's quality loop, run via `uvx vulture` so it adds no install footprint. Result: 0 findings at >=80% confidence, 70 at >=60%, and the distribution is the finding. 57 of 70 are in `intent-control-plane/src/intent_control_plane/` (memory.py 6, durable.py 6, roster_evolution.py 5, provenance.py 5, reliability_policy.py 4), which is the operator's own observation that parts of the code cannot possibly be connected, now measured. NOT YET DONE: (a) whole-module connectivity, which vulture does not measure, since it finds unused symbols and not modules no one imports; (b) triage of the 70 into genuinely-dead versus CLI-dispatched false positives; (c) wiring `uvx vulture` into the gate as a check rather than a one-off. Websearch 2026-07-29 says the current standard pairing is ruff for fast local unused-import checks plus vulture for cross-module scanning, with `albertas/deadcode` as the more configurable alternative presented at EuroPython 2024
- [ ] ABSORB-06 Coverage boundary of this audit, stated so it is not read as exhaustive. Four external repos and roughly 70 named alternatives inside the 27 prior-art records were checked. NOT checked: whether any of the ~70 alternatives inside those records was absorbed, because the schema has no field to check (that is ABSORB-01). Until ABSORB-01 lands, the true absorption rate across all external evaluation is unknown, not zero

## DONE
- [x] Repo relocated + July state synced + pushed (SETUP-OS #1)
- [x] CLAUDE-OS.md single source of truth (#2)
- [x] Notification fabric: phone push + desktop toast (#3)
- [x] Always-fresh PR review workflow on 22 repos (#4) — auth pending
- [x] PRD + 8 ADRs + persona spec + INDEX (this doc set)
- [x] kernel-anchor hook: deep-work discipline injected every prompt, live+wired (#5 partial)
- [x] slop_lint gate (Antislop banlist), verified exit-1 on hits
- [x] Repo portfolio graph: 22 nodes / 72 edges -> d2 + sqlite (#15)
- [x] Git branch health sweep: 22 repos, 80 branches, 20 merged-deletable, 2 drift (#17)
- [x] Daily digest generator over live state + cron 7:03 (#6 partial: needs always-on / Task Scheduler)
- [x] FULL work-setup import from work-archive-2026-07-12: 23 personas + 14 hooks + 36 skills + tower/intent bins + work-docs/ + intent-control-plane/ (2026-07-24, see docs/analysis/2026-07-24-work-archive-import.md)

## P0 — Truth & hygiene (L1/L7)
- [x] Authorize OAuth token; distribute to 22 repos (#4) — DONE 2026-07-23 (root cause: was stripping #state)
- [ ] Rotate API key (operator) — NOT REPRODUCED 2026-07-24: read the תזכורת לעצמי group over CDP, it holds exactly 3 messages (scroll converged, 25 passes) and a presence-only regex probe for `cfat_`/`sk-`/`gh[pousr]_`/32+ hex/"account id" returned 0 hits. So the token is not in that group now. This does NOT clear the item: it may have been deleted from view, or was in a different chat. Operator to confirm whether that credential was ever exposed and rotate if so
- [x] Global default model: superseded by operator decision 2026-07-29. /model set fable-5 as the saved default for new sessions and it runs on this machine; the old row wanted the opposite direction. model-selection.md rewritten with the routing table (fable default and hardest work, opus workhorse, sonnet workers, haiku inventory)
- [ ] Update global CLAUDE.md "Codex is executor" line (ADR-0007 amended: Codex REMOVED)
- [ ] Purge WSL-era paths in /cdp, reground docs
- [ ] Catch docs up to reality: PRD #4 done, #8 partial, ADR-0007 Codex-out

## P1 — Deep Work Protocol hooks (L0) + digest (L4)
- [x] SessionStart recall rewired Windows-native (P1.1, deployed+wired)
- [x] Reflex router + flywheel S1 logger, PII-safe (P1.2, SLM #2)
- [x] /slop gate command (P1.5, deployed)
- [x] Memory + web write pipe (P1.3, #14) - real card written + recalled
- [x] Blast-radius grapher (P1.4, #16)
- [ ] handoff-on-stop, postcondition metadata (#5 remainder)
- [ ] RTK bash guard hook — blocked: rtk binary MISSING on Windows
- [ ] Daily digest push from cron (#6, generator+cron done, needs always-on Task Scheduler)

## P2 — Review fabric (L5)
- [x] Live review demonstrated: PR #2, GitHub-Claude caught 4/4 seeded defects + 2 bonus; session-Claude replied (two-Claude loop)
- [ ] Second model = FREE Gemini (AI Studio) replaces Codex; wire a2a-gemini bridge + gemini-review workflow (needs free key)
- [ ] a2a ⇄ GitHub agreement-gated review + provenance + audit (#8) — needs Gemini actor
- [ ] Persona review economy build (#19) — model-agnostic personas; PR-type routing; two reputation axes (persona + model)

## P-DASH — Dashboard / multi-session (NEW, from WhatsApp compare)
- [ ] Evaluate adopting amirfish1/claude-command-center (MIT) as the missing session-dashboard layer (Kanban, spawn/resume, cost, cross-session) — DO NOT rebuild (excavate-before-building). Windows-native PS install exists; Mac-first, some features degrade.

## P3 — Orchestration (L3)
- [ ] Scheduler consolidation; WSL systemd retired (#11); standing personas
- [ ] Concierge phone topology (#20)

## P4 — I/O & frontier (L2/L4/L8)
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
- [ ] Discovery sweep rebuild per docs/HANDOFF-FROM-LEARNING-2026-07-29.md: add google-research org, widen per_page cap, qualify pushed_at by default-branch commits, watch releases beyond claude-code, add changelog/blog feeds; OpenReview needs a browser client (tools/browser/cdp.py), plain HTTP is blocked. Lane B owns the sweep contract; NOT acted on as of 2026-07-29 evening
- [ ] Deterministic preflight per docs/specs/2026-07-29-deterministic-preflight.md: /diverge the recipe format, then pilot ONE activity class with recorded preflight rows keyed to PT ids; Stop-gate check lands only after two measured weeks. Operator-originated 2026-07-29
- [ ] completion_gate extension, advice-without-artifact: block a final turn that proposes future work (numbered moves, timelines, 'before any second attempt') while the turn performed ZERO mutating tool calls; detection keys on tool-call counts first, text patterns second, to dodge the panel.py prose-false-positive class (L-2026-07-29-d). Driver: operator 2026-07-29 on the resume session's promises-with-zero-work output; measured: that session's text passed 5 'clean' stops after its one 14:32 block, so the current check misses advice-shaped handbacks. Oracle edit: needs the 17-test treatment + mutation spec before deploy

## Filed 2026-07-29 (reflection: ungated channel + false-scope plan)
- [ ] Response-channel slop gate: Stop hook runs the slop patterns over the TURN'S RESPONSE TEXT, one corrective turn on a hit. Measured driver: 33 connector violations across 17 of 28 text turns (61%) in session dfcabe1b while every .md written passed slop_lint. Must tolerate dashes inside quoted code/data or it repeats the panel.py false-positive class (L-2026-07-29-d). Lesson L-2026-07-29-g
- [ ] scan.py false positives: top 3 ranked proposals (score 8) claim SessionStart/PostToolUse/PreCompact hooks are missing; all three exist live (7941/2519/1306 bytes) and session-recall.sh fires every session. The tool CLAUDE.md names for choosing work ranks phantom defects highest. Fix the path resolution, add a positive test per L017
- [ ] Bus inbox is never read: 19 unread messages to lane B, oldest 2026-07-25, carrying live findings (160 canonical files never deployed, deploy-setup.sh false-greens, stale-rules warning now resolved-by-time with nothing recording it). Either surface unread count at SessionStart (session-recall.sh already runs) or accept the bus is write-only and say so
- [ ] /reground is hollow in BOTH trees: absent from ~/.claude/commands/, and the canonical dot-claude/commands/reground.md dispatches to /home/shovalbe/.agents/skills/reground/SKILL.md which does not exist on this machine. Operator typed /reground tonight and got nothing. Either write a real Windows-native reground (the 7-command reconciliation sweep is its natural body) or delete the command
- [ ] Inventory reconciliation BEFORE the next build plan: bus inbox, scan.py, refute run, skills_sync (52 drift), pointers (261 absent paths), lane C/D backlogs, gh open work, CLAUDE-OS + INDEX read. Lesson L-2026-07-29-h. The competing frame this evidence supports, and which the architecture plan suppressed, is that inventory bloat is the core problem and adding tickets is the wrong shape
- [ ] No retrieval layer over state/: measured 130M transcript tokens/week and ~20M in one session, so our own state exceeds every context window. Ledgers are append-only and read by tail or grep; nothing indexes them. Surfaced during the long-context critique response and walked past
- [ ] Statusline never observed rendering in a live terminal: unit-tested against synthetic payloads only. FleetView v0 rests on it. Verify in a real session before building on the tap
- [x] STALE 2026-07-29 evening: the fable-vs-opus falsifier due 08-05 was overtaken by the operator setting opus[1m] as the saved default tonight. model-selection.md still records the fable experiment as live; it needs rewriting to say the experiment was ended by operator decision before its falsifier date, and what that means for the effort-level row
