---
name: reground
description: "Full context reload for Shoval's workstation. Use for /reground, /insights, context drift, stale assumptions, or when asked to reread rules/tools/skills and summarize project state from git, remote commits, Jira reminders, docs, plans, and recent artifacts."
---

# Reground

Use when:
- The user says `/reground`, `/insights`, "reground", "reread all the tools/skills/rules", "what changed", or "where are we?"
- Context drift, compaction, conflicting assumptions, or stale project state might affect the next action.
- The user wants a current project snapshot before planning or executing.
- Before any substantive plan/build when the current project state is unclear, the branch may be wrong, the repo is dirty, the PRD/spec may have moved, or recent artifacts/data files may change the answer.

## Default Outcome

Return a compact status report grounded in live local evidence. Do not start implementation work after reground unless the user explicitly asks. When reground is invoked automatically as a preflight for implementation, keep the report short and continue into the requested work after surfacing blockers.

## Inputs

- Active cwd and nearest git repo.
- Global rules: `/home/shovalbe/AGENTS.md`, `/home/shovalbe/.codex/RTK.md`, `/home/shovalbe/.codex/config.toml`, `/home/shovalbe/.claude/settings.json`, `/home/shovalbe/.claude/settings.local.json`.
- Global knowledge docs under `/home/shovalbe/docs/`, especially core setup, testing, research, pipeline, and architecture files. Start with the docs index when present, then read the task-relevant files.
- Project rules/docs if inside a project: nearest `AGENTS.md`, `.codex/hive.yaml`, `.claude/hive.yaml`, `README.md`, `CLAUDE.md`, `docs/**`.
- Project tree and artifact surface: top-level dirs/files, recent `.png`, `.xlsx`, `.csv`, `.parquet`, `.json`, `.txt`, `.md`, `.html`, and obvious build/output/artifact folders.
- Open work from plans/specs: unchecked checklist items, TODO/FIXME/BLOCKED markers, and acceptance criteria in `/home/shovalbe/docs/**`, project `docs/**`, `.claude/plans/**`, and task-shaped `.codex/**/SPEC.md` files.
- Skills metadata: `/home/shovalbe/.agents/skills/*/SKILL.md`, `/home/shovalbe/.codex/skills/*/SKILL.md`, and plugin skills under `/home/shovalbe/.codex/plugins/cache/**/skills/*/SKILL.md` when relevant.
- Memory quick pass: `/home/shovalbe/.codex/memories/memory_summary.md` is already injected; search `/home/shovalbe/.codex/memories/MEMORY.md` for cwd/project/Jira keys only when relevant.
- Jira reminders: local cache at `/home/shovalbe/.claude/jira/reminders.json`; do not refresh or write Jira unless separately requested.

## Evidence Modes

Use the smallest evidence pass that makes the next action safe.

### Lite reground

Use for routine context refresh, small edits, or when the branch/spec/artifact
state is already mostly known. Compose the commands dynamically from the task,
rather than running a full scan by habit:

```bash
rtk git status --short
rtk git branch --show-current
rtk git log --oneline --decorate -5
rtk git remote -v
rtk rg -n "<task keyword>" README.md docs .  # targeted, not broad
rtk proxy find "$PWD" -maxdepth 2 -type f \( -name 'AGENTS.md' -o -name 'CLAUDE.md' -o -name '*.md' \)
```

### Full reground

Use for platform, production, data, UI, deploy, cleanup, cross-repo work, dirty
trees, wrong-branch suspicion, PRD drift, or artifact-dependent tasks. You may
run the bundled collector as a shortcut:

```bash
rtk /home/shovalbe/.agents/skills/reground/scripts/reground-snapshot.sh "$PWD"
```

Or dynamically compose equivalent Linux probes when they fit better:

```bash
rtk git status --short
rtk git log --oneline --decorate -8
rtk git remote -v
rtk proxy find "$PWD" -maxdepth 3 -type d \( -name artifacts -o -name outputs -o -name dist -o -name build -o -name logs \)
rtk proxy find "$PWD" -type f \( -name '*.png' -o -name '*.xlsx' -o -name '*.csv' -o -name '*.parquet' -o -name '*.json' \) -printf '%T@ %p\n'
rtk proxy du -h --max-depth=1 "$PWD"
rtk rg -n "TODO|FIXME|mock|monkeypatch|jest.mock|vi.mock|placeholder|stub" tests src admin generator docs
```

Use evidence from whichever commands you run as the spine of the report. If one
probe fails, continue manually with the next useful `rtk` or `rtk proxy` command.

## What To Collect

1. **Rules and tools**
   - Re-read the root `AGENTS.md` instructions and RTK contract.
   - Note active command discipline: prefer `rtk`, `bun`/`bunx`, `uv`, TDD, no mocks, PRD control plane, Ponytail simplification, verification evidence.
   - List only the skill/tool surfaces relevant to the next task; do not dump the whole skill catalog unless the user asks.
2. **Git and remote**
   - Current repo root, branch, upstream, dirty summary, untracked count.
   - Last local commits and upstream status.
   - Remote URL and last remote commit if discoverable without network escalation.
   - Branch hygiene: warn if at `$HOME` as repo root, no upstream, detached HEAD, huge dirty tree, many untracked scaffold files, or branch name obviously mismatches the requested project.
3. **Jira**
   - Summarize open/flagged reminders from local cache.
   - Include time pointer and stale-cache age.
   - Never create, move, or comment on Jira from reground.
4. **Project docs**
   - For home/setup work, read `/home/shovalbe/docs/README.md` first when it exists, then the relevant files under `/home/shovalbe/docs/specs/`, `/home/shovalbe/docs/research/`, `/home/shovalbe/docs/pipelines/`, and `/home/shovalbe/docs/core/`.
   - Surface recent/important project docs: `AGENTS.md`, `README.md`, `CLAUDE.md`, `docs/**/*.md`, `.codex/hive.yaml`, `.claude/hive.yaml`, plans/specs/runbooks.
   - Prefer modified time plus path; only read files whose names clearly matter to the active ask.
5. **Open plan/spec items**
   - Scan home/project docs and local plan folders for unchecked checklist items plus `TODO`, `FIXME`, `BLOCKED`, `remaining`, `not started`, `partial`, and acceptance-criteria markers.
   - Treat scan results as candidate open work, not proof. To close an item, reconcile it against code, tests, runtime/deploy state, or a newer superseding spec.
   - When a PRD/spec/task list exists for the requested surface, classify relevant items as `done`, `partial`, `not started`, `contradicted`, or `superseded`; cite the source file and line.
   - If the candidate list is too large, report the top files by density and inspect the task-relevant file first.
6. **Recent artifacts**
   - Last `.png`, `.xlsx`, `.csv`, `.parquet`, `.json`, `.txt`, `.md`, and `.html` files created/modified under the project root.
   - Last plans from `.claude/plans`, project `docs/**/plans`, `.codex/plan*`, and related local task/handoff folders.
7. **Tree and cleanup signal**
   - Summarize the top-level tree, obvious generated-output folders, large loose files, root clutter, and whether the project root looks production-clean enough to work in.
   - Do not delete or move anything during reground. Flag cleanup candidates only.
8. **AI coding risk scan**
   - Apply the platform-engineering lens: product intent, architecture, runtime/deploy, data contracts, security, observability, change impact, and rollback.
   - Apply the Ponytail lens: delete before adding, avoid one-off abstractions, avoid speculative scaffolding, prefer native/stdlib/already-installed tools.
   - Flag likely AI-coding failure smells when visible from the tree/status: monofiles, duplicate builders, frontend-only polish with missing backend state, generated scaffold leftovers, test gaps, mock-heavy tests, unverified data artifacts, or route/API drift.
9. **Insights mode**
   - If triggered as `/insights`, add a short "Likely Next Moves" section with 3-5 evidence-backed observations.
   - Keep it actionable: owner, date/age, blocker, next command or document to inspect.

## Output Format

Use this shape:

```text
REGROUND
Project: <path or home>
Branch: <branch>  Upstream: <remote/ref or none>
State: <dirty summary>

Rules Reloaded:
- <top 3-6 constraints that matter now>

Recent Git:
- local: <last 3 commits>
- remote/upstream: <status or unavailable>

Jira:
- <flagged reminders/time pointer/cache age, or none>

Docs And Plans:
- <important recent docs/plans with path + age>

Open Plan/Spec Items:
- <unchecked checklist/TODO/BLOCKED candidates, or "none found in scanned files">

Recent Artifacts:
- .png: <paths>
- data: <recent .xlsx/.csv/.parquet/.json paths>
- .txt: <paths>
- .md: <paths>

Tree And Hygiene:
- <top-level tree, root clutter, branch warnings, generated/scaffold clues>

AI Coding Risk:
- <platform-engineering and Ponytail risks to address before build>

Active Context:
- <what this means for the next turn>

Next Action:
- <one concrete recommended next step, or "waiting for user instruction">
```

For `/insights`, append:

```text
Likely Next Moves:
- <evidence-backed observation/action>
```

## Rules

- Read-only by default. Do not edit files, refresh Jira, call cloud APIs, kill processes, commit, or start servers during reground.
- Use local evidence over memory; if memory is used and not re-verified, say it may be stale.
- Keep secrets redacted. Never print tokens, `.env` values, auth headers, or full Claude provider tokens.
- Keep output concise. Reground is a state reset, not a full audit.
- Use full-depth collection only when the user asks for it, a repo is messy, data artifacts matter, or the next task is platform/production work. Otherwise run lite reground with dynamic commands.
- The bundled collector is a convenience, not the only valid reground path. Prefer task-shaped Bash probes when they produce less noise.
- If the user asks to "have it back" or update the skill, edit this skill and verify the script/syntax.
