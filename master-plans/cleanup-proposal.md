# $HOME Cleanup Proposal — 2026-04-30

Generated overnight while you were asleep. **Nothing was deleted.** Every action below requires your sign-off in the morning.

## TL;DR

You have a structural anomaly: `$HOME` (`/home/shovalbe`) is itself a git working tree of `dev.azure.com/.../axia-seekapa-cs-agents`. Every loose file at $HOME (138MB Outlook .pst, WhatsApp images, .ssh keys, research markdown dumps, claude.json backups) is "untracked" in *that* repo. One stray `git add -A` at $HOME and you'd commit/push private email archives or SSH state to Azure DevOps.

I added defensive ignore patterns (local-only, never pushed) tonight — see "Already done" below. The rest needs your approval.

---

## Already done tonight (safe, reversible, no deletions)

1. **Fixed `.npmrc` nvm conflict.**
   - `prefix=/home/shovalbe/.local` removed (caused "globalconfig and/or prefix incompatible with nvm" warning on every `claude` launch).
   - Backup at `~/.npmrc.backup-2026-04-30`.
   - Verified: `npm config get prefix` → `/home/shovalbe/.nvm/versions/node/v22.22.2`. Clean.

2. **Repaired `.git/info/exclude`** (local-only file, NOT committed to the repo).
   - Was 899 lines: same 18-line "claude-code scrub-mode stubs" block duplicated ~40 times. Likely a bug in some scrub feature appending without dedup.
   - Now ~80 lines, deduped, plus added safety patterns for: `.ssh/`, `*.pst`, `WhatsApp Image *.jpeg`, `.aws/`, `.azure/`, `.docker/config.json`, `.npm/`, `.cache/`, claude session/cache state, and stray version-string artifacts (`=2.0.0`, `11.12.1`).
   - Backup at `.git/info/exclude.backup-2026-04-30`.
   - Untracked count dropped from 100+ to 61.

3. **Hooks audit — clean.** Both `voice-explainer-trigger.sh` and `visual-explainer-trigger.sh` work; helpers at `~/.claude/bin/generate-voice.py` + `generate-visual.py` are present and reference the right skill paths. One regex gap noted: voice hook fires on `i'm tired` / `im tired` but NOT `i am tired` (regex requires no-space form). Tiny fix if you want it.

---

## Needs your approval — high priority (security / data risk)

### A. Decide what `$HOME` should be

**Option A1 — `$HOME` should NOT be the worktree root** (recommended).
- Move the seekapa repo to `~/projects/axia-seekapa-cs-agents/`.
- Re-init `$HOME` as either no git repo or a small dotfiles repo.
- Risk: moderate — must update any `.claude/settings.json` paths, CI references, and the working agents. Plan needed.

**Option A2 — Keep $HOME-as-repo, but harden.**
- Trust `.git/info/exclude` (already hardened tonight).
- Add a pre-commit hook on this repo that blocks staging anything matching `*.pst`, `.ssh/**`, `.aws/**` even if user runs `git add -f`.
- Add a `.gitattributes` rule. (Lower friction; ~30 min work.)

I recommend **A2 tonight, A1 next week** because A1 is a bigger surgical move.

### B. The 138MB `shoval.be@i-sdd.com.pst`

- It's at `$HOME` root, currently excluded, but still occupies 138MB.
- Should be moved to `~/Documents/email-archive/` or out of $HOME entirely.
- Action: `mv ~/shoval.be@i-sdd.com.pst ~/Documents/email-archive/` (creates dir if needed).
- **Awaiting your OK.**

### C. `.claude.json.backup.*` (5 files, ~210 KB total, all from 2026-04-15)
- These are auto-snapshots of `.claude.json`. Multiple from a single afternoon = bug or noise.
- Recommendation: `mv ~/.claude.json.backup.* ~/.claude/backups/` (keep, but out of $HOME root).
- Or delete if you don't need them.

---

## Needs your approval — medium priority (clutter)

### D. Research markdown dumps at $HOME root (15 files, ~600KB)
Either keep them out of $HOME (move to `~/research/`) or delete after archiving:
- `2026 Mathematics & Statistics Frontier — What Hasn't Reached AI Yet and Why.md`
- `AI Engineering 2030–2035  Scientific Frontiers...md`
- `Autonomous Agentic Coding Systems with Semantic Self-Awareness  2025–2030 Deep Dive.md` (and `(1).md` duplicate)
- `Claude Code  Complete Issue Map & User Fixes.md`
- `Claude Code bwrap Bash Tool Failure on WSL2  Root Cause & Fixes.md`
- `From 2028  Looking Back on 2026 Agentic Coding...md`
- `Futuristic Learning Stack for an AI Engineer — April 2026 Edition.md`
- `Q-Learning, Deep RL & March 2026 Research...md`
- `RTK.md`
- `compass_artifact_wf-...text_markdown.md`
- `deep-research-bwrap-wsl-error.md`
- `azure-wiki-onepager-skill.md` (49KB — looks like a draft skill spec)
- `agent_prompt_v38_mind.md` (12KB)

Each has a `.Zone.Identifier` sidecar (Windows download metadata) that's pure noise.

Recommendation: `mkdir ~/research && mv ~/*.md ~/research/` then handle exceptions (`AGENTS.md`, `README.md`, `FIX-BWRAP-WSL.md` stay).

### E. WhatsApp image dump (4 files, ~520KB, all dated 2026-03-18)
`WhatsApp Image 2026-03-18 at 15.07.51.jpeg` and 3 siblings. Move to `~/Pictures/whatsapp-2026-03/` or delete.

### F. HTML msc-* files (3 files)
`msc-minimal-exams-strategy.html`, `msc-realistic-path.html`, `msc-research-plan.html` — academic planning. Probably belongs in `~/Documents/msc/`.

### G. Stray npm/pip artifacts
- `=2.0.0` (0 bytes) — created by mistyped `pip install >=2.0.0` or similar.
- `11.12.1` (84 bytes) — same flavor of mistake.
- Safe to delete.

### H. Empty stub files (likely from `claude-code scrub-mode`)
0-byte files: `.bash_aliases`, `.bash_login`, `.bash_logout`, `.bunfig.toml`, `.env.development`, `.env.development.local`, `.env.local`, `.env.production`, `.env.production.local`, `.env.test`, `.env.test.local`, `.github`, `.gitmodules`, `.netrc`, `.sudo_as_admin_successful`, `.yarnrc`, `.yarnrc.yml`, `.zlogin`, `.zlogout`, `.zprofile`, `.zshenv`, `.zshrc`, `bunfig.toml`, `package-lock.json`, `package.json`, `pnpm-lock.yaml`, `runners`, `actions-runner`, `yarn.lock`.

These are scrub-mode placeholders that mask real files inside Claude's sandbox — they should not exist in your interactive shell. If they're not interfering with anything, leave them. If they cause confusion (e.g. opening an empty `.zshrc` in your editor), `rm` them.

### I. Loose code drafts
- `linkedin_github_optimizer.jsx` (17KB) + Zone.Identifier
- `shoval_benjer_job_analysis.jsx` (23KB)
- `doc-design.md` (10KB)
- `friday-meeting.zip` (242KB)

Belong somewhere project-organized, not at $HOME.

---

## Needs your approval — low priority

### J. Git branch hygiene (per last session's "3 branches max" comment)
Local branches in this repo: `main`, `master`, `stage`, `tmp/stage-align-pr97`, `feat/v109-yasha-multilingual` (current), `backup/feat-callanalyzer-before-stage-align`, `feat/align-test-connector-to-production`, `feat/callanalyzer-mcp-integration`, `feat/chatwoot-webhook-handler`, `fix/codex-ci-endpoint`, `fix/codex-foundry-agent`, `fix/escalation-perf-v39`.

Many look stale. **Do not touch without explicit per-branch confirmation** — I won't be deleting these tonight.

Suggest a morning audit pass: for each branch, check `git log {branch} --not master` to see if it has unmerged work; delete cleanly merged ones with `git branch -d` (refuses if there's loss); confirm before `git branch -D`.

### K. `.claude/` directory at $HOME — what should be tracked?

Currently tracked in repo: `settings.json`, status reports, handover-* files.
Currently untracked: `assets/`, `bin/`, `docs/`, `hooks/`, `mcp-servers/`, `plugins/`, `cache/`, `sessions/`, `projects/`, etc.

Question for the morning: should `~/.claude/hooks/` and `~/.claude/bin/` (your custom helpers) be tracked in *some* repo (a personal dotfiles repo)? They currently exist nowhere version-controlled. Loss of disk = loss of those scripts.

---

## Suggested morning workflow

1. Read this file. Pick which sections you OK.
2. I'll execute item by item with confirmation.
3. After cleanup, we revisit the bigger structural question (A1 vs A2).

---

## Files I produced tonight (so you know what to review)

- `~/.npmrc` (rewritten — backup at `~/.npmrc.backup-2026-04-30`)
- `~/.git/info/exclude` (deduped + safety patterns — backup at `~/.git/info/exclude.backup-2026-04-30`)
- `~/cleanup-proposal.md` (this file)
- `~/.claude/projects/-home-shovalbe/memory/MEMORY.md` + seed memory files (next task)
- `~/claude-code-experimental-features.md` (research punch list, written when the background research agent finishes)

---

## Open question for the user

The scope you mentioned ("git health 3 branches at most master pulled from remote, stage and all of the local branches must be merged/aba[ndoned]") is destructive — I won't do it without you awake. Same with the "files, hygeine, readme.md, .gitignore + root file clean professional grade" — proposed above, awaiting OK.
