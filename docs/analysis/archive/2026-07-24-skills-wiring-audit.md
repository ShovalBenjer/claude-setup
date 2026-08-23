# Skills-estate wiring audit — 2026-07-24

Point-in-time scan (docs-control-plane: `analysis/`). Answers the operator question
"what about the skills — are they wired?". Feeds open TODO #12 "Skills estate
owned/merged/archived" (TODO.md line 75).

Short answer: **registered, yes; wired, no.** All 99 registry skills exist somewhere
in the repo, but 60 of 99 are unreachable in a live session, 35 of the 62
`dot-claude/skills` entries are dead one-line WSL stubs, all 23 Gastown personas are
repo-only (live `~/.claude/agents` does not exist), and the registry itself is not
deployed to `~/.claude/rules`.

Evidence classes: VERIFIED = command output in this session. STAGED = exists on disk
/ in repo but not active in the live harness. ASSUMED = inference, not directly tested.

---

## 1. Inventory per estate

| # | Estate | Path | Entries | Real skill dirs | Dead stubs | Class |
|---|--------|------|--------:|----------------:|-----------:|-------|
| 1 | Repo Claude | `C:/Users/shova/claude-setup/dot-claude/skills/` | 62 | 27 | 35 | VERIFIED (`ls` + file-type loop) |
| 2 | Repo Agents | `C:/Users/shova/claude-setup/dot-agents/skills/` | 71 | 71 | 0 | VERIFIED |
| 3 | Repo Codex | `C:/Users/shova/claude-setup/dot-codex/skills/` | 63 | 28 | 35 | VERIFIED (incl. stray file `heidegger-reflection.md`; also a `.system/` dir) |
| 4 | Live Claude | `C:/Users/shova/.claude/skills/` | 30 | 30 | 0 | VERIFIED |
| 5 | Live Agents | `C:/Users/shova/.agents/skills/` | — | — | — | VERIFIED MISSING: `C:/Users/shova/.agents` does not exist at all |
| 6 | Live Codex | `C:/Users/shova/.codex/skills/` | 0 | 0 | 0 | VERIFIED empty (only a `.system/` dir) |

Adjacent estates observed (not in scope but they change the dedup picture):

| Estate | Path | Entries | Class |
|--------|------|--------:|-------|
| new-recruit project skills | `C:/Users/shova/Downloads/new-recruit/.claude/skills/` | 27 | VERIFIED |
| new-recruit project commands | `.../new-recruit/.claude/commands/` | 5 (cdp, commit-push-pr, insights, pickup-reviews, reground) | VERIFIED |
| Live commands | `C:/Users/shova/.claude/commands/` | 4 (cdp, commit-push-pr, diverge, slop) | VERIFIED |
| Plugin marketplace | `C:/Users/shova/.claude/plugins/marketplaces/claude-plugins-official/` | ~31 SKILL.md (frontend-design, skill-creator, plugin-dev, ...) | VERIFIED |
| video-understanding scoped skill | `.../new-recruit/projects/video-understanding/ui-ux-pro-max-skill/` (skill.json format) | 1 | VERIFIED |

### The stub defect (the single biggest data-integrity finding)

35 entries in `dot-claude/skills` and 35 in `dot-codex/skills` are NOT skills. They
are one-line text files containing a dead WSL path, e.g.
`dot-claude/skills/code-simplifier` → contents `/home/shovalbe/.codex/skills/code-simplifier`
(VERIFIED by `cat`). These were cross-estate symlinks in the WSL work setup,
flattened into plain files by the 2026-07-24 archive import (commit `8d2277b`,
2026-07-24 19:46:19 +0300, VERIFIED `git show`). `git ls-files -s` shows mode 100644,
not 120000, so they are committed as broken text files, not symlinks (VERIFIED).

The split is complementary: the 35 dot-claude stubs and 35 dot-codex stubs point at
each other's real copies. A recoverability loop VERIFIED that **every dot-claude stub
has a real directory in dot-codex or dot-agents**, and every dot-codex stub except
the stray `heidegger-reflection.md` has a real directory in dot-claude or dot-agents.
Nothing is lost; it just needs materializing (move #2 below).

dot-claude stubs (35), VERIFIED list:
apify-mcp, azure-devops, azure-keyvault-secrets, cleanup-crew, code-simplifier,
commit-push-pr, deep-research, elevenlabs-mcp, end-session, eval-runner,
feature-investor, grill-me, heidegger-reflect, heygen-mcp, humanize, kill-stale,
mcp-activation, meme-control, mutation-runner, ops-status, ponytail, ponytail-audit,
ponytail-help, ponytail-review, property-test-gen, red-team, red-team-review,
reground, shoval-voice-draft, triage-tests, visual-explainer, voice-explainer,
watchdog, web-inspect, workspace-brain.

`dot-agents/skills` is the only fully-materialized repo estate (71 real dirs, 0
stubs, VERIFIED).

### Registry

`gastown-company-registry.md` defines **19 personas owning 99 skills** (VERIFIED:
`grep -oE '^- \x60[a-zA-Z0-9_-]+\x60$' | sort -u | wc -l` = 99). Copies:

| Copy | State | Class |
|------|-------|-------|
| `claude-setup/dot-claude/rules/gastown-company-registry.md` | real, canonical | VERIFIED |
| `new-recruit/.claude/rules/gastown-company-registry.md` | identical modulo CRLF | VERIFIED (`diff --strip-trailing-cr` empty) |
| `claude-setup/dot-codex/rules/gastown-company-registry.md` | dead WSL stub (one line) | VERIFIED |
| `~/.claude/rules/gastown-company-registry.md` | **does not exist** — live rules dir holds ONLY `calibrated-claims.md` | VERIFIED `ls` |

The hive-mind rule says "Route through `~/.claude/rules/gastown-company-registry.md`";
that path resolves to nothing on this machine. The routing map is not live.

---

## 2. Deployed vs repo-only

### Personas: 23 imported, 0 deployed

- Repo `dot-claude/agents/`: 23 files (VERIFIED list): the 19 registry personas
  (architecture-office, azure-ops-utility, communications-desk, conversation-layer,
  data-bureau, engineering-firm, evidence-clerk, latent-systems-lab, learning-desk,
  mayor-opus, mcp-tooling-office, product-studio, qa-lab, release-bureau,
  review-board, runtime-agents-division, security-compliance-office,
  voice-media-studio, workflow-clerk) + 4 task specialists NOT in the registry
  (azure-resource-investigator, eval-row-diagnoser, foundry-agent-inspector,
  tdd-slice-planner).
- Live `~/.claude/agents/`: **directory does not exist** (VERIFIED). Every Gastown
  persona is STAGED only. The whole virtual-company layer the registry routes
  through cannot be invoked as custom agents in a live session.

### Skills: repo dot-claude (62) vs live ~/.claude/skills (30)

- **In repo, NOT live: 39** (VERIFIED `comm`): LTMD, advisor, apify-mcp,
  azure-cert-coach, azure-devops, azure-keyvault-secrets, blog, blonde-designer,
  cleanup-crew, context-bounded-analyst, decision-grade, elevenlabs-mcp,
  end-session, feature-investor, heygen-mcp, jira-read, jira-task-draft, kill-stale,
  mcp-activation, meeting-notes, mutation-runner, ops-status, pii-scrubber,
  ponytail, ponytail-audit, ponytail-help, ponytail-review, prod-deploy-rules,
  property-test-gen, red-team, reground, requirement-anchor, review,
  testing-pyramid, triage-tests, ui-ux-pro-max, watchdog, web-inspect,
  workspace-brain. (Some reachable per-project via new-recruit's 27 project skills,
  but not from any other cwd.)
- **Live, NOT in repo dot-claude: 7** (VERIFIED): frontend-design (exists in
  dot-agents but content differs, VERIFIED diff) + the Gmail suite: gws-gmail,
  gws-gmail-read, gws-gmail-triage, gws-shared, recipe-create-gmail-filter,
  recipe-label-and-archive-emails. The 6 Gmail skills exist in NO repo estate —
  unbacked-up live-only work (VERIFIED against all three repo estates).
- **Registry skills reachable NOWHERE live** (not in `~/.claude/skills`, not in
  new-recruit project skills): **60 of 99** (VERIFIED `comm`): agent-team,
  answer-question, apify-mcp, azd, azure-devops, azure-foundry,
  azure-keyvault-secrets, azure-wiki-onepager, brainstorming, caveman, cleanup-crew,
  codex-ci, context-hygiene, context-i-forgot, deploy-prod, design-an-interface,
  domain-model, edit-article, elevenlabs-mcp, end-session, feature-investor,
  git-guardrails-claude-code, github-triage, heygen-mcp,
  improve-codebase-architecture, kill-stale, mcp-activation, memory-curator,
  migrate-to-shoehorn, mutation-runner, notebook, obsidian-vault, ops-status,
  plant-task, ponytail, ponytail-audit, ponytail-help, ponytail-review,
  pre-ship-clean, project-intake, project-state, property-test-gen, qa,
  quick-respond, red-team, reground, request-refactor-plan, scaffold-exercises,
  setup-pre-commit, tdd, to-issues, to-prd, triage-issue, triage-tests,
  ubiquitous-language, watchdog, web-inspect, workspace-brain, write-a-skill,
  zoom-out. (Footnote: reground/commit-push-pr/cdp have command-form copies in
  new-recruit `.claude/commands/`, which is a different mechanism.)
- Dead reference: global `~/.claude/CLAUDE.md` cites `~/.agents/skills/tdd/SKILL.md`
  as the TDD philosophy source; `~/.agents` does not exist (VERIFIED). The only tdd
  skill copy is repo `dot-agents/skills/tdd` (STAGED).

### Rules: 17 in repo, 1 deployed

Repo `dot-claude/rules/` has 17 rule files including the registry; live
`~/.claude/rules/` has exactly one (`calibrated-claims.md`, created 2026-07-24
20:13). VERIFIED. Rule deployment started today and stopped at one file.

---

## 3. Unwired skills

### Installed somewhere but NOT in the registry (8) — VERIFIED `comm`

| Skill | Where installed | Note |
|-------|-----------------|------|
| gws-gmail | live only | Gmail suite, built 2026-07-15, never registered, never repo-backed |
| gws-gmail-read | live only | same |
| gws-gmail-triage | live only | same |
| gws-shared | live only | same |
| recipe-create-gmail-filter | live only | same |
| recipe-label-and-archive-emails | live only | same |
| heygen-skills | dot-agents | near-certain rename twin of registered `heygen-mcp` (ASSUMED same family; content not diffed) |
| prod-deploy-rules | dot-claude, dot-codex, new-recruit | a rule shipped as a skill; either register (Release Bureau) or reclassify into `rules/` |

Unregistered agent files (4): azure-resource-investigator, eval-row-diagnoser,
foundry-agent-inspector, tdd-slice-planner — in `dot-claude/agents/` but absent from
the registry's persona list (VERIFIED). Per the registry's own hard boundary
("installed and not listed here = unwired"), these are unwired.

### In registry but missing from disk: NONE

All 99 registry skills exist in at least one repo estate (VERIFIED: `comm -23
reg.txt installed_all.txt` returned empty). The registry has no phantom entries.
The failure mode is reachability, not existence.

---

## 4. Duplicates and conflicts across estates

1. **dot-claude vs dot-codex: mirrored half-estates.** Identical 62-name sets
   (VERIFIED `diff` of name lists), but complementary real-dir/stub splits (27/35 vs
   28/35). They were one cross-linked WSL estate; imported flat, each is now half
   broken. Includes the stray `dot-codex/skills/heidegger-reflection.md` stub.
2. **ui-ux-pro-max: 5 copies, at least 3 distinct versions.** dot-claude (57 files)
   and dot-agents (55 files) share SKILL.md md5 `9e67626a...` (VERIFIED); new-recruit
   project copy (26 files) has md5 `333e886d...` — an older divergent version
   (VERIFIED); dot-codex copy is a dead stub (VERIFIED); plus the skill.json-format
   scoped copy at `new-recruit/projects/video-understanding/ui-ux-pro-max-skill/`
   (VERIFIED exists; content overlap ASSUMED).
3. **Live May-state vs repo July-state: 11 silently diverged skills.** Of the 23
   names present in both live `~/.claude/skills` (mtime 2026-05-25) and repo
   dot-claude (July work state), 11 have REAL content diffs even after CRLF
   stripping (VERIFIED): agent-builder, azure-activity-watch, azure-audit,
   azure-runtime, codex-call, coverage-enforcer, dispatch, openai-agents, persona,
   premortem, refactor-pre-push. Example: repo azure-audit carries an
   `allowed-tools` frontmatter line the live copy lacks (VERIFIED diff). Direction
   (repo = newer work revisions) is ASSUMED from the import provenance; review
   before clobbering either way.
4. **frontend-design: 3 sources.** Live `~/.claude/skills/frontend-design` (plugin
   install, 2026-07-23), repo `dot-agents/skills/frontend-design` (differs,
   VERIFIED), and the marketplace plugin copy under
   `plugins/marketplaces/claude-plugins-official/plugins/frontend-design/`.
5. **heygen-mcp vs heygen-skills** — same capability, two names, two estates;
   registry knows only `heygen-mcp` (MCP and Tooling Office).
6. **commit-push-pr triple-form**: live command (`~/.claude/commands/commit-push-pr.md`),
   new-recruit project command, repo skill (stub in dot-claude, real dir in
   dot-codex, real dir in dot-agents). Shows up twice in the session skill list.
7. **Registry itself**: two real copies (identical modulo CRLF) + one stub + zero
   live. Not a content conflict today, but nothing keeps the two real copies in sync
   (ASSUMED risk).

---

## 5. Top 10 wiring moves, ranked by leverage

All commands are git-bash, from any cwd. Moves 1–6 are additive or repo-internal;
move 7 adds enforcement (ADR-0005); 8–10 are edits/deletes — propose-first per the
authorization rule.

1. **Deploy the 23 personas live** — unblocks the entire Gastown routing layer the
   registry and hive-mind rules assume exists. Additive.
   `mkdir -p ~/.claude/agents && cp -r /c/Users/shova/claude-setup/dot-claude/agents/. ~/.claude/agents/`

2. **Materialize the 35 dead stubs in dot-claude/skills** from their real sibling
   copies (all recoverable in-repo, VERIFIED). Repo-internal; commit after.
   `cd /c/Users/shova/claude-setup && for f in dot-claude/skills/*; do [ -f "$f" ] || continue; n=$(basename "$f"); src=""; [ -d "dot-codex/skills/$n" ] && src="dot-codex/skills/$n"; [ -z "$src" ] && [ -d "dot-agents/skills/$n" ] && src="dot-agents/skills/$n"; [ -n "$src" ] && rm "$f" && cp -r "$src" "dot-claude/skills/$n" && echo "materialized $n"; done`

3. **Back up the 6 live-only Gmail skills into the repo** BEFORE any live-estate
   overwrite — they exist nowhere else.
   `cd /c/Users/shova/claude-setup && cp -r ~/.claude/skills/gws-gmail ~/.claude/skills/gws-gmail-read ~/.claude/skills/gws-gmail-triage ~/.claude/skills/gws-shared ~/.claude/skills/recipe-create-gmail-filter ~/.claude/skills/recipe-label-and-archive-emails dot-claude/skills/`

4. **Deploy the full skills estate live** (after moves 2+3), adopting July repo
   versions over the 11 stale May live copies. Overwrites live copies — get OK
   first; the pre-diff is the review artifact.
   Pre-diff: `diff -rq --strip-trailing-cr /c/Users/shova/claude-setup/dot-claude/skills ~/.claude/skills | grep -v '^Only'`
   Deploy: `cp -r /c/Users/shova/claude-setup/dot-claude/skills/. ~/.claude/skills/`

5. **Deploy the rules + registry live** so `~/.claude/rules/gastown-company-registry.md`
   stops being a dead route (16 of 17 rules currently missing live). Additive.
   `cp -rn /c/Users/shova/claude-setup/dot-claude/rules/. ~/.claude/rules/`

6. **Restore `~/.agents` as a junction to the repo estate** — fixes the dead
   `~/.agents/skills/tdd/SKILL.md` reference in global CLAUDE.md and makes all 71
   dot-agents skills live-reachable with zero duplication (junction = no admin
   needed).
   `mkdir -p /c/Users/shova/.agents && cmd //c "mklink /J C:\Users\shova\.agents\skills C:\Users\shova\claude-setup\dot-agents\skills"`

7. **Add an enforcement script** (ADR-0005: enforcement over prose) that re-runs this
   audit — registry vs estates, stub detection, live-vs-repo drift — and fails CI on
   new orphans/stubs. Seed:
   `cat > /c/Users/shova/claude-setup/tools/audit-skills-wiring.sh` with the comm/stub
   loops from this analysis (registry extraction one-liner:
   `grep -oE '^- \x60[a-zA-Z0-9_-]+\x60$' dot-claude/rules/gastown-company-registry.md | tr -d '\x60' | sed 's/^- //' | sort -u`), then wire into the existing CI.

8. **Register the 12 orphans** — edit
   `dot-claude/rules/gastown-company-registry.md` (then re-sync the new-recruit
   copy): Gmail suite (6) → Communications Desk or MCP and Tooling Office;
   prod-deploy-rules → Release Bureau (or reclassify to `dot-claude/rules/`);
   heygen-skills → resolve via move 9; agents azure-resource-investigator → Azure
   Ops Utility, eval-row-diagnoser → QA Lab, foundry-agent-inspector → Runtime
   Agents Division, tdd-slice-planner → Engineering Firm.

9. **Merge the name-twin and delete the stray stub.** Needs OK (delete + rename):
   `cd /c/Users/shova/claude-setup && git rm dot-codex/skills/heidegger-reflection.md`
   then either `git mv dot-agents/skills/heygen-skills dot-agents/skills/heygen-mcp`
   (align to registry) after diffing against the dot-codex `heygen-mcp` real copy, or
   keep both names and register `heygen-skills` — pick one, not both.

10. **Deduplicate ui-ux-pro-max to one canonical copy.** Canonical = dot-claude
    57-file July version (superset of dot-agents twin, same SKILL.md). Then:
    replace the dot-codex stub (`rm dot-codex/skills/ui-ux-pro-max && cp -r
    dot-claude/skills/ui-ux-pro-max dot-codex/skills/`), refresh the stale 26-file
    new-recruit copy (`rm -r /c/Users/shova/Downloads/new-recruit/.claude/skills/ui-ux-pro-max && cp -r /c/Users/shova/claude-setup/dot-claude/skills/ui-ux-pro-max /c/Users/shova/Downloads/new-recruit/.claude/skills/`),
    and decide whether the dot-agents twin and the video-understanding skill.json
    variant stay (diff first). Deletes/overwrites — get OK first.

---

## Bottom line

The registry is complete on paper (99/99 skills exist, 0 phantoms) but the live
harness runs on a 30-skill, 0-persona, 1-rule subset of a 99-skill, 23-persona,
17-rule system. Today's archive import (8d2277b) put everything in the repo; nothing
has been deployed out of it yet, and 70 of the repo's skill entries (35+35) are dead
WSL stub files. Moves 1, 2, and 6 alone take live coverage from 30/99 skills and
0/23 personas to ~99/99 and 23/23.
