# Closed items - archived from TODO.md (2026-08-24)

Moved here when `TODO.md` was converted from a task tracker to a roadmap
(`docs/archive/MIGRATION-NOTES.md`). These rows were marked `[x]` / `CLOSED` in the prior
tracker and are preserved for history, not for action.

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
- [x] FULL work-setup import from work-archive-2026-07-12: 23 personas + 14 hooks + 36 skills
      + tower/intent bins + work-docs/ + intent-control-plane/ (2026-07-24)
- [x] Authorize OAuth token; distribute to 22 repos (#4), DONE 2026-07-23
- [x] Global default model: superseded by operator decision 2026-07-29 (model-selection.md rewritten)
- [x] SessionStart recall rewired Windows-native (P1.1, deployed+wired)
- [x] Reflex router + flywheel S1 logger, PII-safe (P1.2, SLM #2)
- [x] /slop gate command (P1.5, deployed)
- [x] Memory + web write pipe (P1.3, #14) - real card written + recalled
- [x] Blast-radius grapher (P1.4, #16)
- [x] Live review demonstrated: PR #2, GitHub-Claude caught 4/4 seeded defects + 2 bonus
- [x] **CI red closed 2026-08-01:** `gate` job missing pytest dep; fixed by adding pytest to
      the step (UNVERIFIED until a run goes green on the runner).
- [x] **Bus mutation control closed 2026-08-01:** `bus.py selftest` now parses its own
      `__file__` with `ast` and asserts every write is inside the `with file_lock(...)` block
      (spec bus 23/23 caught, 0 survived).
- [x] **skills_sync check closed 2026-08-01:** drift now reported truthfully.
- [x] **ElevenLabs key rotated 2026-08-12** (operator assertion; not independently verified).

See `TODO.md` for the live roadmap and `docs/analysis/` for the dated-snapshot write-ups
behind each row.
