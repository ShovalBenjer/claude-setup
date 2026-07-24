# TODO — Claude OS

One TODO, grouped by layer, ticket-tagged (SETUP-OS + AUTO). Status mirrors
docs/prd/claude-os.md and docs/prd/autonomy-ecosystem.md. Fresh session? Read
docs/SESSION-BOOT.md first.

## AUTO — Autonomy Ecosystem (prd/autonomy-ecosystem.md, spec 2026-07-24)
- [x] ADR-0010..0015 + PRD + spec + charters + SESSION-BOOT + lessons ledger (AUTO-03/08/13/16 seed) — 2026-07-24
- [ ] AUTO-01/02 hook fire-proof: confirm `state/hook-fires.log` gains a harness-written SessionStart line (new session) + PreCompact line (real /compact). Interpreter/path bug fixed 2026-07-24 (L011); status STAGED until the log shows it
- [ ] DECIDE: live `~/.claude/settings.json` has 4 hook events; canonical `dot-claude/settings.json` carries 6 incl. the work enforcement layer (PreToolUse protect-infra/rtk-bash-guard, Stop stop-checklist/verification-before-completion/contract-proof-stop, PostToolUse skill-usage-logger). Adopt selectively — these are the checks that would have caught L003/L009 mechanically
- [x] Nightly autonomy pilot workflow on claude-setup (AUTO-07) — first scheduled run pending
- [ ] ecosystem.db bootstrap from intent-control-plane schema + tools/eco/db.py (AUTO-06) ← unblocks work-claims (AUTO-04) + FleetView (AUTO-19)
- [ ] RC concierge pattern test: durable lane-A session + intake flow (AUTO-05)
- [ ] Merge-policy labels + auto-merge for auto:low (AUTO-11)
- [ ] Scale nightly to tier-1 repos after 7 clean days (AUTO-09)
- [ ] Social: excavate social-media-agent.bundle → draft-first pipeline (AUTO-12/13/14)
- [ ] Research stage in weekly self-improve cron (AUTO-17)
- [ ] Reputation routing once runs-table volume (AUTO-20)
- [ ] AUTO-10 BLOCKED(operator): GEMINI_API_KEY → bash tools/rollout_gemini_key.sh (script now exists)
- [ ] AUTO-15: split resume rails into verifiable rows (job-scan cron, review wf on hiring repo, lane-C tables)
- [ ] AUTO-18 BLOCKED(operator): Task Scheduler always-on (runbook §5); GitHub schedule live via AUTO-07

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
- [ ] Rotate API key still in תזכורת לעצמי group (operator) — Account id + cfat_ token still visible
- [ ] Global default model fable[1m] → sonnet per model-selection (operator OK)
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
