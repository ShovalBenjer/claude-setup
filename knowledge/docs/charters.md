# Session charters: four live lanes A/B/C/D (ADR-0013, renumbered by ADR-0016)

A session opens by naming its lane. A lane implements ONLY inside its charter.
Cross-lane needs → proposal row in ecosystem.db (until db lands: tools/selfimprove/
proposals.jsonl), never doing the other lane's work. This file is the structural fix
for cross-session convergence: different queues, different repos, different voices.

## Letters were renumbered 2026-07-30. Read this before trusting an old row

The lanes were B/C/D/E until 2026-07-30 and are now A/B/C/D. Only the labels moved;
no charter's scope changed. The shift closed the hole left at the front when the
original Lane A (concierge) was retired on 2026-07-29 having never been used once.

| scope | letter before 2026-07-30 | letter now |
|---|---|---|
| concierge / phone intake | A | retired, scope folded into A |
| claude-setup harness | B | **A** |
| resume / hiring engine | C | **B** |
| learning (הסדנה) | D | **C** |
| content and publishing | E | **D** |

The letters therefore COLLIDE across the cutover: a `{"lane": "B"}` row written on
2026-07-29 means the harness, and the identical row written on 2026-07-31 means the
resume engine. The append-only ledgers under `state/` were deliberately NOT rewritten
because `state/bus.jsonl` is hash-chained, and falsifying 400+ historical rows to make a
cosmetic rename look tidy is worse than carrying the ambiguity explicitly. Any code
reading a lane letter out of a ledger resolves it through `tools/lib/lanes.py`, which
requires the row's own timestamp for exactly this reason.

## Lane A: Claude setup (harness)

- Owns: ~/claude-setup. Rules, hooks, skills, schedulers, review fabric, a2a
  bridges, ecosystem.db, FleetView, autonomy rails, social pipeline PLUMBING,
  and intent intake/routing surfaces (inherited from the retired concierge lane).
- Does NOT: hiring logic (B), learning content (C), posting content decisions (operator).

## Lane B: Resume engine (ongoing project)

- Owns: `~/work/repos/new-recruit`. Hiring machine, arms, applications, job scans.
- Gets from A: crons, review workflows, push approvals, db tables. Nothing else.
- Path corrected 2026-07-31. It read `~/Downloads/new-recruit` until then, and
  that directory had been emptied by a declutter sweep that morning, so the
  charter named a lane by a path that did not exist. The repo gained its first
  remote the same day (`github.com/ShovalBenjer/new-recruit`, private), and the
  WSL tree is authoritative; the Windows copy at `C:/Users/shova/new-recruit` was
  measured to hold nothing the WSL tree lacks and is being retired.

## Lane C: Learning (הסדנה)

- Owns: `~/work/repos/daily-deep-learning`. PWA, learning cards, study loops.
- Gets from A: learning-card emitter hook (SETUP-OS #10), nothing else.

## Lane D: Content and Publishing (added 2026-07-29 as Lane E)

- Owns: `~/work/repos/daily-deep-learning/writing`. The personal
  writing/case-study artifacts and their syndication strategy. The-bench case-ledger post lives at
  `daily-deep-learning/writing/` (hosted on the הסדנה domain, which is the
  public site) but is Content, not learning material; C hosts it, D owns it.
- Skills (currently in `~/.claude/skills`, to sync to claude-setup canonical):
  `case-ledger-post` (post authoring + rubric), `syndication-engine`
  (POSSE projector, per-platform hooks, dev.to draft path), `voice-metrics`
  (voice scoring for outreach drafts).
- Gets from A: social pipeline PLUMBING (posting mechanics, credentials).
- Does NOT: hiring logic (B), learning content (C).
- Posting decisions stay with the operator; nothing publishes without an
  explicit yes, and public syndication is gated behind a PII/consent pass
  (the-bench uses a real person's WhatsApp corpus).
- Why it exists: this work grew across a resume-lane session with no owner
  (a 26/30 post, a syndication engine, per-platform strategy). Homeless
  content work is what let a cross-lane effort run silently under the resume lane.

## Anti-convergence rules (all lanes)

1. Claim before work: append `{"proposal_id","lane","ts"}` to `state/claims.jsonl`
   (the scanner never touches that file, so claims survive rescans; ecosystem.db
   replaces it at AUTO-06). A claimed id is another lane's property.
2. Design decisions run /diverge (5 candidates, weird-first); picks append to taste.md.
3. Open each session distinctly: state lane + top queue item, not a generic greeting.
4. Double-claims and charter violations are lessons (state/lessons.jsonl), so log them.
