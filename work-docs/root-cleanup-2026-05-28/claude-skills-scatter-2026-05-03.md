# Skills / Hooks / Agents — Scatter Inventory + Consolidation Plan

> **APPENDIX NOTE (2026-05-04):** This is a detailed audit feeding into the canonical plan. **For current status and decisions see `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md`.** Use this file only when actually executing the consolidation move (it has dir-by-dir breakdowns the master plan compresses).

**Date:** 2026-05-03
**Trigger:** User flagged scattered config across `$HOME/` and `$HOME/projects/`. This is the audit.
**TL;DR:** You have **94 unique skill files across 5 directories**, **2 different hooks subsystems** (Claude vs Codex), **0 skills loaded by Claude globally**, and **4 projects where `CLAUDE.md` and `AGENTS.md` have diverged**. The scatter is the bottleneck — it's why Layer 4 of the 2030 vision (custom skills) shows zero progress despite 94 skill files existing.

---

## 1. Skills inventory (where they actually live)

| Location | Count | Loaded by | Status |
|---|---|---|---|
| `~/.agents/skills/` | **52** | "agents" CLI (sketch.dev / claude-agent format) | ✅ canonical-looking, mostly unique skills |
| `~/.codex/skills/` | 25 | Codex CLI (per `~/AGENTS.md`) | ✅ active for Codex, partial overlap with `.agents` |
| `~/friday-meeting/skills/skills/` | 20 | nothing — extracted from `friday-meeting.zip` | ⚠️ backup/duplicate, can archive |
| `~/projects/cs-agent/.agents/skills/` | 2 | project-scoped agents CLI | ✅ project-specific (`claude-eval-cs`) |
| `~/projects/figma-4-all/.codex/skills/` | 15 | project-scoped Codex | ✅ includes `banner-analyzer`, `perplexity-mcp`, `cleanup-crew` |
| **`~/.claude/skills/`** | **0** | Claude Code | ❌ **does not exist — Claude has zero global skills** |

### Duplicates between `.agents` and `.codex`

These 6 skills exist in both — same name, possibly different content:

`azure-devops`, `azure-keyvault-secrets`, `commit-push-pr`, `mutation-runner`, `property-test-gen`, `red-team`

**Action needed:** diff each pair, pick canonical version, symlink the other.

### Only in `~/.agents/` (46 skills, the biggest unique set)

```
agent-team, answer-question, azd, azure-foundry, azure-wiki-onepager, brainstorming,
caveman, codex-ci, context-hygiene, context-i-forgot, deep-research, deploy-prod,
design-an-interface, domain-model, edit-article, end-session, frontend-design,
git-guardrails-claude-code, github-triage, grill-me, heidegger-reflect, humanize,
improve-codebase-architecture, meme-control, memory-curator, migrate-to-shoehorn,
notebook, obsidian-vault, plant-task, pre-ship-clean, project-intake, project-state,
qa, quick-respond, reground, request-refactor-plan, review, scaffold-exercises,
setup-pre-commit, tdd, to-issues, to-prd, triage-issue, ubiquitous-language,
write-a-skill, zoom-out
```

Note: this includes `memory-curator`, `obsidian-vault`, `deep-research`, `agent-team` — which are exactly the Layer 3/4/7 components the 2028 vision doc says you need. **They already exist; they're just not where Claude can find them.**

### Only in `~/.codex/` (19 skills)

```
apify-mcp, cleanup-crew, code-simplifier, elevenlabs-mcp, eval-runner,
feature-investor, heidegger-reflection.md, heygen-mcp, kill-stale, mcp-activation,
ops-status, red-team-review, shoval-voice-draft, triage-tests, visual-explainer,
voice-explainer, watchdog, web-inspect, workspace-brain
```

Includes `voice-explainer` + `visual-explainer` (the ones the existing Claude hooks at `~/.claude/hooks/*-trigger.sh` invoke via `~/.claude/bin/generate-{voice,visual}.py`). Currently the trigger lives in Claude land but the skill body lives in Codex land — fragile coupling.

---

## 2. Hooks scatter

| Location | Files | What |
|---|---|---|
| `~/.claude/hooks/` | 2 | `voice-explainer-trigger.sh`, `visual-explainer-trigger.sh` (UserPromptSubmit) |
| `~/.codex/hooks/` | 6 | `post-compact-reinject.sh`, `protect-infra.sh`, `session-context.sh`, `stop-checklist.sh`, `verification-before-completion.sh`, `watchdog-verify.sh` |
| `~/projects/social-intelligence-unit/.claude/hooks/` | ? | project-scoped |
| `~/projects/figma-4-all/.claude/hooks/` + `.codex/hooks/` | ? | both |
| `~/projects/claude-meme-hooks/hooks/` | — | third-party clone, not your content (ignore for consolidation) |
| project `.git/hooks/` (5 projects) | — | git-managed, ignore |

The Codex hooks (`post-compact-reinject`, `verification-before-completion`, `watchdog-verify`) are exactly what the 2028 vision doc lists as Layer 2 priorities for Claude. **Same problem as skills — they exist, they're just on the wrong side of the Codex/Claude split.**

---

## 3. Agents directories (mostly empty)

| Location | Count |
|---|---|
| `~/.claude/agents/` | **0** (empty) |
| `~/projects/.claude/agents/` | 0 (orphan parent dir) |
| `~/projects/qc/.claude/agents/` | 0 |
| `~/projects/football/.claude/agents/` | 0 |
| `~/projects/video-generations/.claude/agents/` | 0 |
| `~/projects/cs-agent/.claude/agents/` | 0 |
| `~/projects/openclaw-poc/.claude/agents/` | 0 |
| `~/projects/campaign-analysis/{agents,.claude/agents}/` | ? (two dirs) |
| `~/projects/seekapa-training-platform/.claude/agents/` | 0 |
| `~/projects/social-intelligence-unit/{.kilocode/agents,.claude/agents}/` | ? |

Empty `agents/` directories everywhere — Anthropic's project scaffolding creates them but you never populated. Fine as-is unless we're using them.

---

## 4. Project-level `CLAUDE.md` vs `AGENTS.md` — divergence audit

**4 of 4 projects with both files have diverged content** (different bytes):

| Project | Status |
|---|---|
| `~/projects/qc/` | DIVERGED |
| `~/projects/cs-agent/` | DIVERGED |
| `~/projects/social-intelligence-unit/` | DIVERGED |
| `~/projects/seekapa-training-platform/` | DIVERGED |

This means: instructions for Claude vs Codex have drifted apart. One is stale or one is more current. Need to diff each pair and either:
(a) make `AGENTS.md` a symlink to `CLAUDE.md` (one source of truth),
(b) reconcile content and pick a primary,
(c) accept divergence and document the difference per project.

Other CLAUDE/AGENTS files at risk:
- `~/AGENTS.md` (30 bytes pointing to RTK.md) — Codex root, no Claude equivalent
- `~/.codex/AGENTS.md` is identical: `@/home/shovalbe/.codex/RTK.md`
- Bun cache + VSCode extension `CLAUDE.md` — third-party noise, ignore

---

## 5. Other config worth noting

| Path | What |
|---|---|
| `~/projects/.claude/` (parent dir) | Orphan dir with empty `agents/`, empty `commands/`, and `settings.local.json` (236 bytes) — likely from a `claude code` invocation in `~/projects/` itself |
| `~/agent-prompts/` | NOT Claude config — it's your Seekapa v100→v108 + Axia v20→v30 system prompt history. Useful project artifact, leave alone. |
| `~/.claude-ink-tui/` | Untracked dir from git status — separate Ink-based TUI experiment, not your config |
| `~/mcp-servers/onesignal-mcp` | One MCP at HOME root |
| `~/.claude/mcp-servers/azure-foundry-mcp` | Another MCP under `.claude/` |
| `~/.codex/migrated-from-claude/CLAUDE.md` | Frozen pre-Codex Claude config, archive value only |
| `~/projects/.archive/claude-orchestration/` | Archived old orchestration project — ignore |
| `~/friday-meeting/` | Unzipped from `friday-meeting.zip`. Has `CLAUDE.md` + `skills/skills/` (20 dup skills) — looks like a snapshot from a meeting prep |

---

## 6. The consolidation plan (proposed, awaiting OK)

### Goal

One source of truth for skills, hooks, and rules — readable by both Claude Code and Codex via symlinks, versioned in a private dotfiles repo, project-level overrides only when actually needed.

### Target layout

```
~/.dotfiles/                          ← new private repo (github.com/ShovalBenjer/dotfiles)
├── skills/                           ← canonical skills (one per name)
│   ├── commit-push-pr/SKILL.md
│   ├── memory-curator/SKILL.md
│   ├── voice-explainer/SKILL.md
│   └── ... (~70 unique after dedup)
├── hooks/                            ← canonical hooks
│   ├── voice-explainer-trigger.sh
│   ├── visual-explainer-trigger.sh
│   ├── post-compact-reinject.sh     ← from Codex
│   ├── protect-infra.sh              ← from Codex
│   ├── verification-before-completion.sh
│   ├── watchdog-verify.sh
│   ├── session-context.sh
│   └── stop-checklist.sh
├── bin/                              ← currently ~/.claude/bin
│   ├── generate-voice.py
│   ├── generate-visual.py
│   └── pop-* wrappers
├── rules/                            ← shared behavioral contracts
│   └── *.md
└── CLAUDE.md → AGENTS.md             ← one rules file, two names

# Then:
~/.claude/skills    → symlink to ~/.dotfiles/skills
~/.claude/hooks     → symlink to ~/.dotfiles/hooks
~/.claude/bin       → symlink to ~/.dotfiles/bin
~/.claude/CLAUDE.md → symlink to ~/.dotfiles/CLAUDE.md
~/.codex/skills     → symlink to ~/.dotfiles/skills
~/.codex/hooks      → symlink to ~/.dotfiles/hooks
~/.agents/skills    → symlink to ~/.dotfiles/skills (or remove if `.agents` CLI not used anymore)
~/AGENTS.md         → symlink to ~/.dotfiles/CLAUDE.md
```

### Migration steps (each one reversible, each needs OK)

**Step 0 — Snapshot first.** Tar everything before any moves:
```
tar -czf ~/dotfiles-backup-2026-05-03.tar.gz \
  ~/.agents ~/.codex ~/.claude ~/AGENTS.md \
  ~/projects/.claude ~/projects/cs-agent/.agents \
  ~/friday-meeting
```

**Step 1 — Create the dotfiles repo.** `mkdir ~/.dotfiles && cd ~/.dotfiles && git init`. Push to private `github.com/ShovalBenjer/dotfiles`. (Requires `gh` install first, per master plan.)

**Step 2 — Copy `~/.agents/skills/` → `~/.dotfiles/skills/` as the base.** It's the largest unique set (46 unique). Manual review: any skills you don't want anymore, delete here.

**Step 3 — Merge `~/.codex/skills/` in.** For the 19 unique-to-Codex skills, copy them in. For the 6 duplicates (`azure-devops`, `azure-keyvault-secrets`, `commit-push-pr`, `mutation-runner`, `property-test-gen`, `red-team`), `diff` each pair, decide canonical, take that one.

**Step 4 — Skip `friday-meeting/skills/skills/` and `~/projects/.archive/`.** Both are stale snapshots. Confirm with `diff` that they're subsets of the merged set, then `mv ~/friday-meeting ~/archive/friday-meeting-2026-04`.

**Step 5 — Merge hooks.** Copy all 6 Codex hooks + 2 Claude hooks into `~/.dotfiles/hooks/`. Update the existing `~/.claude/hooks/*.sh` paths inside the scripts if they reference `~/.codex/skills/...` (the voice/visual triggers do).

**Step 6 — Replace originals with symlinks.** One platform at a time, with snapshot backup:
```
mv ~/.claude/hooks ~/.claude/hooks.bak && ln -s ~/.dotfiles/hooks ~/.claude/hooks
mv ~/.claude/bin   ~/.claude/bin.bak   && ln -s ~/.dotfiles/bin   ~/.claude/bin
ln -s ~/.dotfiles/skills ~/.claude/skills        # this dir didn't exist before
```
Test Claude Code launches cleanly. Then do Codex. Then `.agents/`. Don't delete the `.bak` dirs until you've used Claude for a full day with no breakage.

**Step 7 — Reconcile the 4 diverged project CLAUDE.md/AGENTS.md pairs.** One project at a time:
```
diff ~/projects/qc/CLAUDE.md ~/projects/qc/AGENTS.md
```
Decide canonical content, write to one file, symlink the other. Commit per project.

**Step 8 — Clean up orphans.**
- `~/projects/.claude/` (orphan parent dir) — investigate `settings.local.json`, then likely remove
- Empty `agents/` directories in projects you don't use them — remove
- `~/.codex/migrated-from-claude/CLAUDE.md` — move to `~/archive/`

**Step 9 — Document.** Write `~/.dotfiles/README.md` explaining the layout and the symlink topology. Add to the master plan as completed.

### Stop conditions / risks

- **The `.agents` CLI may not be active.** If you stopped using sketch.dev's agents CLI, those 52 skills are orphans — they need to land somewhere readable (Claude or Codex) or they're dead weight. Worth confirming what tool reads `~/.agents/skills/` before treating it as canonical.
- **Symlink across WSL boundaries.** WSL→Windows file events can break symlink sensing in some Windows-side tools (Obsidian indexers, VSCode-Windows). Test before committing to symlink everywhere.
- **Skills that hardcode paths.** Any skill that does `source ~/.codex/skills/foo` instead of relative paths will break after the move. Grep for hardcoded paths first.

---

## 7. What to do next

The user-facing question:

1. **Do you still use the `.agents` CLI** (sketch.dev / claude-agent / similar)? If no — the 52 skills there get migrated to `~/.dotfiles/skills/` and symlinked back; if yes — same thing, but `~/.agents/skills` stays as a symlink target so the CLI still works.
2. **Approve Step 0 (the tar snapshot)?** I'll do nothing else without OK on the next steps.
3. **Skill triage:** want to keep all 70 unique skills, or take this opportunity to delete unused ones (e.g. `meme-control`, `caveman`, `grill-me`, `heidegger-reflect` — judgment calls)?

I'm not moving anything until you confirm.
