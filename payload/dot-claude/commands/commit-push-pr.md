---
description: Run quality gates, commit, push, open PR, and sweep merged local branches. Auto-detects stack and remote (GitHub or Azure DevOps).
argument-hint: [optional commit message]
---

You are running the `/commit-push-pr` skill. Read the canonical instructions from `~/.agents/skills/commit-push-pr/SKILL.md` and execute every step in order.

If `$ARGUMENTS` is non-empty, use it as the commit message; otherwise auto-generate one from the staged diff per the skill's Step 4.

Hard rules:

- **Stop on failure.** If the lint/test gate fails, stop and report exactly what failed. Do not stage, do not commit, do not push.
- **Detect remote before pushing.** GitHub uses `gh pr create`; Azure DevOps uses `az repos pr create`. Skill Step 5 has the detection snippet.
- **Always run the sweep step (Step 7).** It uses cherry-pick detection so it correctly handles squash-merged branches that `git branch -d` would reject. Never skip it.
- **Don't `--no-verify`.** Don't `--amend` a pushed commit. Don't push to `main`/`master` directly — auto-create a feature branch first.
- **Co-author line uses your actual model name** (e.g. `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`).

Final report (terse): PR URL, branch + remote, swept branches, any kept-with-reason.
