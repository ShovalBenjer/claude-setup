# TODO — Claude OS

One TODO, grouped by layer, ticket-tagged (SETUP-OS). Status mirrors docs/prd/claude-os.md.

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

## P0 — Truth & hygiene (L1/L7)
- [ ] Rotate API key found in תזכורת לעצמי group (operator)
- [ ] Global default model fable[1m] → sonnet per model-selection (operator OK)
- [ ] Update global CLAUDE.md "Codex is executor" line → reviewer-only (ADR-0007)
- [ ] Purge WSL-era paths in /cdp, reground, session-recall docs
- [ ] Authorize subscription OAuth token; distribute secret to 22 repos (#4)

## P1 — Deep Work Protocol hooks (L0) + digest (L4)
- [x] SessionStart recall rewired Windows-native (P1.1, deployed+wired)
- [x] Reflex router + flywheel S1 logger, PII-safe (P1.2, SLM #2)
- [x] /slop gate command (P1.5, deployed)
- [ ] handoff-on-stop, postcondition metadata (#5 remainder)
- [ ] RTK bash guard hook (efficiency; was WSL-era, re-wire Windows)
- [x] Memory + web write pipe (P1.3, #14) - real card written + recalled
- [ ] Daily digest push from cron (#6, generator+cron done, needs always-on)

## P2 — Review fabric (L5)
- [ ] Run live two-Claudes review on test PR #1 (seed for persona economy)
- [ ] a2a ⇄ GitHub agreement-gated review + provenance + audit (#8)
- [ ] Persona review economy build (#19) — per spec

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
