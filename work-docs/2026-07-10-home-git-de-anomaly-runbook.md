# HOME git de-anomaly runbook (2026-07-10)

Read-only diagnosis + reversible, staged runbook to make `/home/shovalbe` (`~/.git`) its own
local-setup repo, DETACHED from the cs-agent (axia-seekapa) Azure remote, with the cs-agent
codebase no longer checked out into HOME root. Target chosen by operator 2026-07-10.

STATUS: PLAN ONLY. Nothing here has been executed. Execute ONLY when the coast is clear
(no parallel Claude/Codex session operating on the shared `~/.git`), step by step, verifying
and keeping the rollback for each step. This is high-blast-radius: it touches the operator's
HOME environment and a git object store shared by live worktrees.

---

## 1. Verified diagnosis (evidence, not assumption)

- `~/.git` origin = `https://dev.azure.com/Corp-domain/Corp-AI/_git/axia-seekapa-cs-agents`
  (the cs-agent Azure remote). Verified: `git -C /home/shovalbe remote -v`.
- HOME HEAD = `feat/v109-yasha-multilingual`; its history IS cs-agent commits
  ("harden yasha prompt", "CRM query allowlist"). Verified: `git -C /home/shovalbe log`.
- `~/.git` tracks **345 files, overwhelmingly the cs-agent codebase** checked out INTO HOME
  root: tests(73), azure-function-crm(52), agent-prompts(45), qa_reports(21),
  kb-snapshot(20), scripts(17), evals(14), kb-source(6), widget(3), plus cs-agent config
  (requirements, pyproject, azure-pipelines.yml, docker-compose, Seekapa_FAQ_KB.*). The
  `docs`(55) and `.claude`(20) tracked trees are a MIX of cs-agent docs and your setup work
  (needs categorization, see step 3).
- Your intent-control-plane / local-setup work sits as ~238 UNCOMMITTED changes (mostly
  `docs/`, `.claude/`) on top of the cs-agent checkout, plus untracked files.
- Shared worktrees on the SAME `~/.git`:
  - `~` -> feat/v109 (HOME itself)
  - `~/projects/axia-seekapa-cs-agents` -> fix/kb (my session worktree; hand-re-registered, flagged prunable)
  - `~/projects/axia-seekapa-cs-agents-pii-eval-before-enable` -> feat/pii-eval (a LIVE parallel session)
- `~/projects/.git` = a SECOND clone of the cs-agent remote, same branch, 0 tracked files (stray).
- Preserved already: my cs-agent session work in `/home/shovalbe/session-backup-20260710-cs-agents.tgz`
  (1.4M, verified). cs-agent commit `247aa3c4` reachable.

Root cause: the cs-agent repo was cloned/checked-out at `/home/shovalbe` itself (HOME-as-repo),
so HOME's git IS the cs-agent repo, and years of local-setup work accreted in the same tree.

## 2. Premortem (failure modes to design against)

1. **Lose uncommitted setup work.** The ~238 uncommitted HOME changes (intent-control-plane)
   are the whole point; a `reset --hard` / `checkout` / re-init without backing them up first
   destroys them. Mitigation: full working-tree backup before ANY git op (step 0).
2. **Break the live parallel worktree.** `pii-eval-before-enable` shares `~/.git`. Deleting
   or re-initing `~/.git`, or pruning worktrees, can corrupt its state mid-write. Mitigation:
   do NOT execute until that session is done; migrate it to a standalone clone first.
3. **Push garbage to the cs-agent Azure remote.** HOME's mixed tree is on a cs-agent branch
   with the cs-agent origin; an accidental `git push` sends HOME/setup files to prod repo.
   Mitigation: detach/rename origin EARLY (step 1) so no push can reach cs-agent by accident.
4. **Orphan the cs-agent history / lose the real repo.** Re-initing `~/.git` discards the
   cs-agent object store that the worktrees depend on. Mitigation: stand up an INDEPENDENT
   cs-agent clone (step 2) and migrate all worktrees off `~/.git` BEFORE touching `~/.git`.
5. **Misclassify files** (delete a setup file thinking it is cs-agent, or vice versa).
   Mitigation: explicit categorized inventory reviewed by operator before any move (step 3),
   and every move is `git mv` / copy, never `rm`, until verified.

## 3. Preconditions (coast-clear gate)

- [ ] No parallel session is mid-operation on `~/.git`. Confirm the `pii-eval-before-enable`
      session is idle/done: `git -C /home/shovalbe worktree list` and coordinate.
- [ ] Disk space for a full HOME backup (HOME working tree minus caches).
- [ ] Operator available to answer the categorization + new-remote decisions in step 3.

## 4. Runbook (staged, reversible)

### Step 0 - PRESERVE everything (no git writes)
- Full backup of the HOME working tree (setup work + uncommitted), excluding caches and the
  cs-agent codebase heavy dirs:
  ```
  tar czf /home/shovalbe/home-preflight-backup-20260710.tgz \
    --exclude='.venv' --exclude='__pycache__' --exclude='*.python_packages' \
    --exclude='.mypy_cache' --exclude='.ruff_cache' --exclude='.cache' --exclude='node_modules' \
    -C /home/shovalbe .claude .codex .agents docs bin .config \
    <any other intent-control-plane / setup dirs the operator names>
  ```
- Also snapshot git state: `git -C /home/shovalbe worktree list --porcelain > ~/worktrees-20260710.txt`,
  `git -C /home/shovalbe branch -vv > ~/branches-20260710.txt`, `git -C /home/shovalbe stash list`.
- ROLLBACK for the whole operation: restore from these backups.

### Step 1 - Neutralize the cs-agent remote on HOME (stops accidental push to prod)
- `git -C /home/shovalbe remote rename origin cs-agent-legacy` (keep it, do not delete yet, so
  nothing is lost and no auto-push targets it as "origin").
- VERIFY: `git -C /home/shovalbe remote -v` shows no `origin`. Fully reversible (rename back).

### Step 2 - Make the cs-agent repo INDEPENDENT (off `~/.git`)
- Decision: the canonical cs-agent working copy is `~/projects/axia-seekapa-cs-agents`. Convert
  it (and the pii-eval one) from a WORKTREE of `~/.git` into a STANDALONE clone:
  - Fresh clone: `git clone <cs-agent Azure URL> ~/projects/axia-seekapa-cs-agents.new`, then
    re-apply the uncommitted work by extracting the session tgz over it onto a branch.
  - OR `git worktree move` / detach if git supports it cleanly for this layout.
- Coordinate the pii-eval worktree the same way with that session.
- VERIFY: `git -C ~/projects/axia-seekapa-cs-agents rev-parse --git-dir` resolves to a LOCAL
  `.git` dir (not `~/.git/worktrees/...`); the app tests still run green there.
- ROLLBACK: the original worktrees + `~/.git` untouched until this is confirmed.

### Step 3 - Carve out local-setup vs cs-agent, categorize (operator review)
- Produce the inventory: for each tracked path in `~/.git`, label LOCAL-SETUP (keep in the new
  HOME repo) vs CS-AGENT (belongs only to the cs-agent clone). Obvious cs-agent: azure-function-crm,
  tests, agent-prompts, qa_reports, kb-snapshot, kb-source, evals, scripts, widget, the cs-agent
  configs, Seekapa_FAQ_KB.*. Needs review: `docs/`, `.claude/` (mixed).
- DECISION POINTS for operator:
  1. New remote for HOME's local-setup repo? (a personal remote, or none / local-only.)
  2. Keep cs-agent history in HOME's new repo (unlikely) or start fresh history for setup only?
  3. Exact fate of the mixed `docs/` and `.claude/` trees.

### Step 4 - Reset `~/.git` to a local-setup repo (only after steps 1-3 verified)
- With all worktrees migrated off `~/.git` and the cs-agent clone independent:
  - Remove the cs-agent codebase files from HOME root (they now live only in the clone). Use
    `git rm --cached` + move-to-archive first, never a blind `rm`, until verified.
  - Re-establish HOME history for setup only (fresh `git init` into a new gitdir, or a filtered
    branch), set the chosen remote (or none), commit the categorized setup files.
- VERIFY: HOME root has NO cs-agent codebase dirs; `git -C /home/shovalbe remote -v` is the new
  (or empty) remote; `git -C /home/shovalbe ls-files` lists only setup files; the cs-agent clone
  is healthy and independent; the pii-eval session is intact.

### Step 5 - Cleanup
- Remove the stray `~/projects/.git` (the 0-file second cs-agent clone) after confirming it holds
  nothing unique. Explicit per-action OK.
- `git worktree prune` on the cs-agent clone once worktrees are sane.

## 5. What NOT to do
- No `git reset --hard`, `git checkout .`, `git clean -f`, or `rm -rf` on HOME before step 0's
  backup is verified.
- No `git push` from HOME while origin still points at cs-agent.
- No execution while the `pii-eval-before-enable` session is live on `~/.git`.
- No blind `rm` of "cs-agent" files from HOME until the independent clone is confirmed to hold them.

## 6. Open decisions for the operator (blockers to executing)
1. New remote (or none) for HOME's local-setup repo?
2. Fresh history for setup, or preserve?
3. Categorization of `docs/` and `.claude/` (which subpaths are setup vs cs-agent)?
4. Green light that the parallel pii-eval session is idle so step 2/4 are safe.
