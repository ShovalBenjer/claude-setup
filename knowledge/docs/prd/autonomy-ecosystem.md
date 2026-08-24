---
surface: autonomy-ecosystem
tickets: AUTO-01..AUTO-20
status: living
owner: Shoval (operator) + Claude setup session (lane B)
created: 2026-07-24
---

# PRD — Autonomy Ecosystem (Claude OS v2)

The next level above the harness PRD (prd/claude-os.md, SETUP-OS): a live ecosystem
that works Shoval's GitHub repos, runs the social-media posting project, and rails the
resume engine — autonomously, on the Claude subscription, surviving laptop sleep and
session death. Evolves via its own lessons ledger and research loop. Spec:
specs/2026-07-24-autonomy-implementation.md. ADRs 0010-0014 fix the costly decisions.

## North star

Capture intent anywhere → verified action comes back to the phone — with the system
generating most of its own work. Operator role shifts from prompting to approving.

## Acceptance table

| # | Ticket | Acceptance criterion | Status | Evidence |
|---|--------|---------------------|--------|----------|
| 1 | AUTO-01 | Any fresh session reaches full working context in <60s from disk only (SESSION-BOOT.md path) | DONE | VERIFIED 2026-07-24 22:44. `state/hook-fires.log` carries harness-written SessionStart lines with real payloads, e.g. `2026-07-24T22:35:38 SessionStart {"session_id":"8abb324e-0798-4b21-93eb-0d3e8f7c5e0f","transcript_path":...}` — a session id the harness minted, not a pipe test. Injection confirmed end-to-end: the recall block (memory index + 6 open TODO items + BOOT PATH) is present in that session's context at turn 0, zero tool calls, so the <60s bound holds trivially. Was STAGED after L011 (bare `bash` = WSL bash + mangled backslash args); fix was explicit Git Bash interpreter + POSIX `/c/` arg |
| 2 | AUTO-02 | Compaction/clear loses zero decisions: PreCompact hook writes durable snapshot; disk is the only memory (ADR-0010) | DONE (mechanism) | VERIFIED 2026-07-24: 11 harness-written PreCompact lines in `state/hook-fires.log`, and `state/compact-log.md` holds 12 `## compact` snapshots with git status/log captured at each. Round-trip evidenced once end-to-end: session 8abb324e was compacted and resumed with goal, lane, decisions and next action intact. CAVEAT (not yet measured): "loses zero decisions" rests on that single observed round trip, not a series. Steering lives in SessionStart source=compact — PreCompact carries no additionalContext (verified vs hooks docs) |
| 3 | AUTO-03 | 4 session lanes chartered (concierge/setup/resume/learning); no two lanes implement the same thing | DONE | docs/charters.md |
| 4 | AUTO-04 | Cross-session convergence broken: lanes read distinct work queues; design decisions pass /diverge | PARTIAL | charters + /diverge + state/claims.jsonl (scanner-safe interim); db claims at AUTO-06 |
| 5 | AUTO-05 | Phone RC reaches a durable concierge (not a fresh orphan session); concierge routes to lanes | TODO | spec §P0.5: concierge launch + relaunch job + approval round-trip; acceptance = phone→disk→ack evidence |
| 6 | AUTO-06 | ecosystem.db (SQLite) is system-of-record: sessions, proposals, runs, lessons, reputation, post_queue, repo_registry | TODO | seed from intent-control-plane schema (ADR-0011) |
| 7 | AUTO-07 | Nightly server-side autonomy pilot: scheduled GitHub Action runs Claude maintenance pass on claude-setup, opens PR — laptop off | STAGED | workflow v2 (no-Bash agent, deterministic branch-scoped PR step, fail-closed auto/* cap, in-run review job; label created). DONE requires: PR URL + autonomy label + posted review from run 1 |
| 8 | AUTO-08 | Autonomous changes ship ONLY via PR + review gate; never direct to main (ADR-0012) | DONE (structural v2) | ADR-0012 corrected: agent step has no Bash; only push is branch-scoped auto/*; review guaranteed in-run (GITHUB_TOKEN PRs trigger no workflows) |
| 9 | AUTO-09 | Repo autonomy scaled to tier-1 repos (3+) with per-repo run caps and reputation gate | TODO | after AUTO-07 proves clean for 1 week |
| 10 | AUTO-10 | Two-model review live on autonomy PRs (Claude + Gemini family-decorrelated) | BLOCKED(operator) | needs GEMINI_API_KEY secret |
| 11 | AUTO-11 | Merge policy: low-risk class auto-merge on green + agreement; risky class = phone push approval | TODO | policy in spec §P2 |
| 12 | AUTO-12 | Social pipeline excavated from social-media-agent.bundle (44 refs) — not rebuilt | TODO | bundle in work-archive; ADR-0014 |
| 13 | AUTO-13 | Social posts are draft-first: phone approval before ANY external publish, no publish creds in repo | POLICY-SET | ADR-0014 + spec §P0.5 approval round-trip (inbound: RC 'approve <id>' or tools/eco/db.py approve) |
| 14 | AUTO-14 | Content calendar in ecosystem.db feeds drafts in Shoval voice (taste.md + shoval-voice-draft) | TODO | after AUTO-06 |
| 15 | AUTO-15 | Resume engine gets rails only (schedulers, review, push approvals); hiring logic stays in lane C | POLICY-SET | charters.md lane boundary |
| 16 | AUTO-16 | Lessons ledger live and seeded; every incident → ledger row → enforced rule/hook (never prose-only) | PARTIAL | 8 seeded; digest surfaces open lessons (live run 2026-07-24: '3 open lessons' in push); durable schedule pending AUTO-18 |
| 17 | AUTO-17 | Weekly research sweep converts papers → practice-diff proposals into the self-improve queue | TODO | weekly cron is session-only (dies with session — contradicts AUTO-18 until Task Scheduler); research_sweep.py unbuilt |
| 18 | AUTO-18 | All schedules survive laptop sleep: Task Scheduler (local) + GitHub schedule (cloud) as primary | BLOCKED(operator) | runbook has commands; GitHub-side live via AUTO-07 |
| 19 | AUTO-19 | FleetView built ON intent-control-plane/ + tower (excavated ancestors), reads ecosystem.db | TODO | spec 2026-07-24-command-center-superior.md |
| 20 | AUTO-20 | Reputation-driven routing (Thompson) allocates autonomy budget across repos/personas from external truth only | TODO | ADR-0008; needs volume from AUTO-09 |

## Non-goals

Full no-approval autonomy (publish/merge-risky stays human-gated); paid API spend
(subscription OAuth only, ADR-0002); building social/resume product logic inside lane B.
