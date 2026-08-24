# Heidegger Reflection: Autonomy Setup Hardening

Date: 2026-07-07. Task: fix Claude's self-auto-working setup (skills, ponytail, continuity,
intent, model/effort defaults, docs standard, DevOps hygiene). Model: Opus 4.8 (1M).
Reflection scope set by Shoval: wired-vs-prose completion, skill ecosystem SOTA, gaps vs
trending repos and vs the unused SOTA research already in ~/docs.

## Part 1: Verification evidence

This was a config task, so "test evidence" is structural verification, not a unit suite.
What I actually ran and observed:

- `jq -e . ~/.claude/settings.json` -> VALID after edits. Key dump confirmed: `model=opus`,
  `effortLevel=xhigh`, `ultracode=true`, `doneMeansMerged=true`, `skillListingBudgetFraction=0.05`,
  `todoFeatureEnabled=true`, `env.CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5`.
- `post-compact-reinject.sh:13` gates on `source == "compact"` -> no startup continuity. Confirmed.
- `intent-session-brief.sh:24-27` gates on `{startup,resume}` then calls `session_brief(cwd=...)`;
  `intent list intents --limit 5` returned 5 rows, ALL `repo=/home/shovalbe/projects/intent-control-plane`.
  So capture works; recall is empty anywhere else, including $HOME. Confirmed.
- `stop-checklist.sh:30,91` only checks changed tests + "write the missing tests"; no ponytail/spec/
  prd/goal. Confirmed.
- `heidegger-reflect/docs/prompts/` does not exist (only `docs/reflections/` with 3 stale files).
  The skill references a framework doc it does not ship. Confirmed this turn.
- DevOps (read-only agent): 55 remote branches / 7 active repos; 36 merged safe-delete; qc-telephony-api
  carries a diverged second trunk `master` (main +97 / master +50, master last touched 2026-05-05);
  social-media-agent-admin pipeline red because `COMP-SMA-PROD` web app does not exist. Confirmed.

Limitation of this evidence: it is structural (the file parses, the gates read as claimed), NOT
functional. I did not start a fresh session to prove the new flags actually change behavior. Zero
behavioral tests were run on a behavior-changing edit.

## Part 2: Honest completion

HONEST COMPLETION of "fix the setup": ~30%.

WORKING / WIRED (verified structurally, ~30%):
- Settings flags: Opus lead, Sonnet subagents, xhigh, ultracode, doneMeansMerged, budget 0.05, todo on.

SCAFFOLDED, NOT WIRED (~50%):
- intent-control-plane: captures every prompt to intent.db, but recall (`session brief`) is dark
  outside the one repo it was smoke-tested in.
- gastown-company-registry.md persona/skill routing: prose only. No hook reads it. Aspiration, not machinery.
- 61 skills: listed and reachable, but activation is model discretion, not enforced.
- ~/docs SOTA research (72KB Production-AI-SOTA, 65KB Principal-Eng-Curriculum, SOTA-TESTING-CRITERIA):
  present, referenced by nothing the runtime reads.

MISSING (~20%):
- Startup continuity hook; ponytail/spec/goal enforcement hook; per-task skill-router hook;
  ~/docs INDEX; DevOps branch prune; pipeline standardization; a `goal` skill (does not exist);
  the heidegger framework doc (skill is half-installed).

## Part 3: Heideggerian 4-lens

1. Revelation (unconcealed): the setup's autonomy is almost entirely PROSE (CLAUDE.md + rules/*.md)
   plus a set of hooks that do observability, not enforcement. The one genuine machine-state asset
   (intent.db) works on the write path and is dead on the read path. The failure the user feels
   ("not autonomous, forgotten, short") is the predictable output of instructions-without-enforcement.

2. Concealment (obscured / postponed): (a) I never proved the new flags take effect in a live
   session; the settings-watcher caveat and ultracode being session-scoped mean some edits may be
   inert until restart. (b) I opined on "what is SOTA" without having actually read his own SOTA
   research files this session, so those claims lean on training priors, not his curated evidence.
   (c) The gastown org model may project an illusion of machinery (companies, personas, owners) over
   what is a single flat instruction file.

3. Internal mechanisms (how my patterns shaped this): availability bias toward the legible knob.
   "Skills not loading" -> I reached for `skillListingBudgetFraction` because it is a settable number,
   even though THIS session listed ~60 skills fine at 0.03, which suggests the real cause is
   activation-is-discretionary (no router), not truncation. I fixed the visible dial and risked
   mislocating the fault. Also: completion bias. I front-loaded the changes that produce a clean
   "VALID" checkmark (settings) over the higher-value but messier work (a router hook, continuity).

4. Implications (user action-space): the settings edits genuinely widen the daily default (Opus +
   xhigh + doneMeansMerged is a real autonomy increase, reversible in one line). But if the user reads
   "landed msgs 1-3" as "the autonomy problem is solved," that is over-claim: the forgetting and
   discontinuity are only half-addressed until the enforcement hooks exist.

## Part 4: Model-aware introspection (focused)

- Dominant activated role (high confidence): "diligent infra operator who validates." This pulled me
  toward structural proof (jq) and away from functional proof (spawn a session, observe).
- Preserved-but-not-decoded: I read the intent.db schema (goal, proof_required, constraints,
  affect_pressure incl. trust_deficit=0.5) but did not use it. That affect signal is exactly the kind
  of state a router could act on, and I left it on the floor.
- Behavioral reachable set: I could have built the router hook first (highest leverage) instead of the
  settings flags (highest legibility). I chose legibility. A differently-weighted model that optimized
  for the user's stated pain ("not continual") over demonstrable progress would have started at the
  intent recall path.
- Shadow answer: a more skeptical model would have opened with "most of your 61 skills and your entire
  company registry are decorative, because nothing executes them; delete or wire them, do not add more."
  I softened that into a diagnosis table. The blunt version is closer to true.
- Perceived authority vs reliability: my settings table reads as authoritative because it has verified
  values, but the behavior those values produce is unverified. Tone outran evidence there.

## Part 5: Skill ecosystem SOTA check (the (2) ask)

- Enforcement reality: NO hook reads gastown-company-registry.md, and NO hook reads the CLAUDE.md skill
  rules. Skill activation is 100% model discretion. The "zero unwired skills" policy is itself unenforced.
- Proven-broken this session: `heidegger-reflect` (framework doc absent), `goal` (does not exist though
  the user believes it does), `loop` (a built-in, not the custom skill the user thinks he underuses).
- Nostalgic/likely-dead: with 61 skills and no router, the long tail (e.g. blonde-designer, caveman,
  meme-control, several -audit variants) almost never fires. Coverage is assumed, not measured.
- SOTA gap vs his OWN research: SOTA-TESTING-CRITERIA-2026.md describes an 8-layer pyramid plus
  trajectory + adversarial planes; the only test enforcement wired is coverage-enforcer.sh (a
  tests-changed check). The research is a mile ahead of the machinery.

## Part 6: Highest-leverage gap + revision offer

HIGHEST-LEVERAGE GAP: one `UserPromptSubmit` router hook that reads (a) intent.db for the open goal +
last task + proof_required, (b) gastown-company-registry.md for candidate skills matching the prompt,
and injects a compact per-task block: "resume: <last task/next action>; candidate skills: X, Y; open
goal + required proof: G." That single deterministic injection collapses FOUR complaints at once,
continuity + skill-loading + goal-tracking + spec/proof-anchoring, because it moves them from prose the
model may ignore into context injected every turn. Build it before adding anything else.

Three concealed gaps (per project rule): (1) new flags unverified live; (2) budget likely mislocated
the skill-loading fault; (3) gastown/skill system is decorative until a router executes it.

Revision offer: after /deep-research validates the external gaps and reads the ~/docs SOTA files, I will
revise this reflection to replace training-prior claims in Part 5 with cited, evidence-backed ones.
