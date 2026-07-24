---
PRD: prd/autonomy-ecosystem.md
Ticket: AUTO-01..AUTO-20
Status: active
---

# Implementation spec — Autonomy Ecosystem

How the next-level system gets built, phase by phase, with acceptance criteria and a
premortem per Forge Loop. Assumes sessions die at any moment (ADR-0010): every step
lands on disk or in GitHub before it counts.

## Premortem (5 failure modes → mitigations, each tagged with implementation status)

1. **OAuth token expires/revoked → 22-repo autonomy dies silently.** Mitigation: weekly
   canary (nightly workflow on claude-setup IS the canary — a missed Monday PR = alarm in
   digest; digest checks `gh pr list` age).
2. **Autonomous PR spam / runaway loops.** Mitigation: hard caps — 1 nightly PR per repo
   per day, max 3 open autonomy PRs per repo (workflow checks before opening); reputation
   gate (repo with 2 rejected autonomy PRs in a row → paused in repo_registry).
3. **Convergence returns: two lanes build the same thing.** Mitigation: work-claims —
   a lane UPDATEs proposals.status='claimed' with its lane id in ecosystem.db before
   starting; charters forbid cross-lane implementation; digest surfaces double-claims.
4. **Laptop sleep kills local crons → "autonomous" system silently idle.** Mitigation:
   GitHub `schedule:` is the PRIMARY rail for repo autonomy (cloud, laptop-independent);
   local Task Scheduler only for local-only jobs (digest, WhatsApp); digest shows
   last-run timestamps so silence is visible.
5. **Social auto-post reputational damage.** Mitigation: ADR-0014 hard gate — publish
   step physically requires phone-approved row (approved_at NOT NULL) AND creds live
   only in local keyring, never in repo/Actions.

## P0 — Bootstrap after /clear (day 0)

- New session reads docs/SESSION-BOOT.md (60-second path). AUTO-01.
- PreCompact hook live (AUTO-02): writes state/compact-log.md snapshot + reminds the
  summarizer of the handoff schema (goal/phase/decisions/evidence/next).
- Charters live (AUTO-03): docs/charters.md. Each session opens by naming its lane.
- OPERATOR (3 items, ~10 min): (a) GEMINI_API_KEY at aistudio.google.com/apikey →
  `bash tools/rollout_gemini_key.sh` (sets secret on 22 repos); (b) Task Scheduler
  import per OPERATOR-RUNBOOK §always-on; (c) model default per model-selection rule.

## P0.5 — Phone RC concierge (day 1-2) — AUTO-05

The pain: RC spawns a fresh orphan per connection. The fix makes intake stateless:

1. Concierge launch: a dedicated terminal running `claude` in ~/claude-setup whose
   SessionStart recall names lane A (charter: intake-and-route ONLY).
2. Relaunch artifact: Task Scheduler job `claude-concierge` (logon + daily 07:00)
   starting that terminal; command in OPERATOR-RUNBOOK §always-on.
3. Intake write path: every phone utterance → row in proposals/claims (until db:
   append to state/claims.jsonl with lane target) → PushNotification ack.
4. Acceptance (AUTO-05): a phone→computer round trip — speak an intent, see the
   row on disk, get the ack push — pasted as evidence. Even if RC still spawns
   fresh, the fresh session boots lane A from SESSION-BOOT and loses nothing.

**Approval round-trip (closes the ADR-0014/AUTO-11 gap):** push notifications are
outbound-only. Inbound approval = operator replies via RC to the concierge ("approve
<id>") OR runs `python tools/eco/db.py approve <id>` locally; either writes
approved_at. No approval row, no publish/merge — the adapter checks the row, not
the conversation.

## P1 — Ecosystem state (week 1) — AUTO-06

Excavate, don't rebuild: seed from `intent-control-plane/` (imported 2026-07-24).
`state/ecosystem.db` tables:

- `sessions(id, lane, started_at, last_seen, charter)` — heartbeat via SessionStart hook.
- `proposals(id, source, repo, title, kind, risk, score, status[open|claimed|done|rejected], lane, evidence)` — scanner output migrates here from proposals.jsonl.
- `runs(id, kind[nightly|weekly|social|digest], repo, started, finished, outcome, pr_url)` — every autonomous run logs here.
- `lessons(id, date, incident, lesson, enforcement, status)` — mirror of state/lessons.jsonl.
- `reputation(actor, kind[persona|model|repo], wins, losses, updated)` — ADR-0008 external truth only.
- `post_queue(id, channel, draft, taste_refs, drafted_at, approved_at, posted_at, post_url)` — ADR-0014 gate = approved_at.
- `repo_registry(repo, tier, autonomy[on|paused], open_prs, last_nightly)` — from tools/graph/repo_graph.py.

CLI: `tools/eco/db.py` (init, migrate-jsonl, claim, log-run). FleetView (AUTO-19) reads this.

## P2 — Repo autonomy (weeks 1-2) — AUTO-07/09/11

The cloud rail (works with laptop off, subscription token already on all 22 repos):

1. **Pilot (STAGED)**: `.github/workflows/claude-nightly.yml` on claude-setup —
   `schedule:` cron, runs claude-code-action with a maintenance prompt (self-improve
   scan spirit: tests for untested tools, doc drift, dead code, TODO advancement),
   opens ONE PR max, never touches main. Existing claude-code-review.yml + Gemini
   review it like any PR (the autonomy loop reviews itself).
2. **Merge policy (AUTO-11)**: label from PR-type classifier — `auto:low` (docs, tests,
   comments, lint) auto-merges on CI green + both-model approval; `auto:risky`
   (logic, config, deps) sends PushNotification, merges only on operator OK.
3. **Scale (AUTO-09)**: after 7 clean days, roll nightly to tier-1 repos (pick 3 from
   repo_registry by activity); expand/pause by reputation (premortem #2 caps).

## P3 — Social media project (weeks 2-3) — AUTO-12/13/14

1. Excavate: `git clone work-archive-2026-07-12/social-media-agent.bundle` → mine its
   posting adapters, content models, scheduling (44 branches of prior art; found spec
   is INPUT not template).
2. Pipeline: calendar row in post_queue → draft in Shoval voice (taste.md +
   shoval-voice-draft + slop_lint gate) → PushNotification with draft text → operator
   approves on phone (approved_at set) → publish adapter posts → post_url logged.
3. Channels: start LinkedIn (job-search synergy with lane C), then X. Creds in
   Windows Credential Manager only.

## P4 — Resume-engine rails (ongoing) — AUTO-15

Lane B provides ONLY: schedulers (job-scan cron), review fabric on hiring_engine
repo, push approvals for applications, ecosystem.db tables lane C reads/writes.
Hiring logic, arms, apply flows stay in lane C (new-recruit session). Boundary is
charters.md; violations are lessons.

## P5 — Live adaptation (continuous) — AUTO-16/17/20

- **Lessons loop**: incident → row in lessons.jsonl/db → enforcement artifact (rule
  file, hook, gate) → PR. A lesson without enforcement is `status:open`, surfaced in
  every digest until closed (ADR-0005).
- **Research loop**: weekly self-improve cron gains a research stage — sweep new papers
  (arXiv agents/harness) → diff against CLAUDE-OS §2b practices → proposals with
  citations. Perplexity corpus (perplexity_research-11.5.26/) is the seed shelf.
- **Reputation routing (AUTO-20)**: once runs table has volume, Thompson-sample
  autonomy budget across repos and personas; external truth only (merged? reverted?
  escaped defect?) per ADR-0008.

## Verification per phase

Each phase closes only with: command + real output in the PRD Evidence column, and a
lesson row if anything surprised us. "Done" = evidence + intent-coverage statement
(feedback_loop-until-intent-met).
