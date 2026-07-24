# Work-archive import — full sync of the work Claude setup (2026-07-24)

Point-in-time record of what the work archive contains, what is now IN this repo,
and what deliberately stays bundle-only. Answers "does claude-setup include what
I had at work?" — after this import: YES, the full harness, verified by file diff.

## The archive (source of truth for restore)

`C:\Users\shova\Downloads\new-recruit\work-archive-2026-07-12\` — 1.4 GB, made
2026-07-12 (the day of the sacking). 13 git bundles (complete repos: all branches,
tags, stashes) + `HOME-setup-uncommitted.tgz` (the last uncommitted state of the
HOME harness: tower, gastown-spawn, hud-statusline, subagent-hud, final
CLAUDE.md/settings.json, July research docs) + `MANIFEST.md` (restore commands).

## What was imported into this repo (this commit)

The 2026-07-23 "synced to July work state" note in README overstated: the sync was
partial (~half of `.claude`, none of `docs/`, none of the tgz). Closed today by
materializing `HOME-setup.bundle` master + tgz overlay (1,024 files, 26 MB) and
merging no-clobber (repo-adapted files win):

| work path | repo path | what was missing before |
|---|---|---|
| `.claude/` | `dot-claude/` | 118 files: ALL 23 `agents/` (Gastown personas: mayor-opus, qa-lab, review-board, evidence-clerk…), 14 hooks (stop-checklist, rtk-bash-guard, verification-before-completion, post-compact-reinject, intent-capture, coverage-enforcer, watchdog-verify, protect-infra, hive-review-bridge…), 36 skill dirs (reground, ponytail×4, red-team×2, shoval-voice-draft, heidegger-reflect, ui-ux-pro-max, deep-research, grill-me…), 8 bin (tower, cx, intent, claude-provider…), 4 rules (no-emojis, no-mocks, task-verification, tdd-enforcement), work CLAUDE.md + settings.json |
| `.codex/` | `dot-codex/` | 87 files: 48 skills, 20 hooks, 12 rules, 6 bin, AGENTS.md |
| `.agents/` | `dot-agents/` | 31 files (ui-ux-pro-max data) |
| `docs/` | `work-docs/` | ALL 240+ files: audits, reflections, specs, eval-results, wiki, azure-snapshots, root-cleanup analyses, repo-standards, July research (sol5.6-harness, code-quality-standard-2026-07…) |
| root files | `home-dotfiles/` | RTK.md, TESTING-SOTA-2026-GAPS.md; AGENTS.md updated May→July |
| root plan | `master-plans/` | CLAUDE-CODE-MASTER-PLAN-2026-05-03.md updated to July revision |
| `intent-control-plane.bundle` | `intent-control-plane/` | whole personal repo folded in at `feat/preserve-wip-2026-07-12` (114 files: intent.db control plane, spawn_grade, redaction gateway — tower's backend), `.git` stripped per repo-topology no-nested-repo |

Secrets scan before commit: zero real hits across both trees. The only pattern
matches were intent-control-plane's OWN redaction regexes + fake test fixtures
(`sk-proj-abc123`) — its purpose, not a leak. Work settings.json env block holds
model-routing flags only.

One tgz entry skipped: `.codex/hooks/skill-usage-logger.sh` is a symlink to the
`.claude` copy (unrepresentable on Windows); the target file is imported.

## What stays bundle-only (deliberate)

The 11 work PROJECT repos are portfolio, not Claude setup — restore from bundle
when needed (`git clone <name>.bundle`): ORM-AGENT (39 refs), social-media-agent
(44), qc-telephony-api (34), campaign-analysis (31), campaign-Onesignal (31),
seekapa-training-platform (19), video-understanding (18, 902M), agent-call-tracker
(17), sales-agents (11, 352M), call-analyzer-frontend (7), lp-creation-ebook-task
(4). intent-control-plane's other 9 branches also remain in its bundle.

## Follow-ups this unlocks

- P1 handoff-on-stop: adapt `dot-claude/hooks/stop-checklist.sh` (work version now in-repo).
- RTK guard: `dot-claude/hooks/rtk-bash-guard.sh` + `home-dotfiles/RTK.md` (still needs rtk binary on Windows).
- Gastown personas: the 23 agent files the company-registry rule references now exist in `dot-claude/agents/`.
- FleetView: `intent-control-plane/` + `dot-claude/bin/tower` are the working ancestor (excavate-before-building).
