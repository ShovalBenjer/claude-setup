# C1. Platform Hygiene and Hive Parity Sweep

Schedule: Sundays 6:00-8:00 PM Asia/Jerusalem
Mode: read + propose + local Hive beads, no destructive changes

This compact automation replaces the standalone A1, A3, and A12 timers.

Run one platform hygiene pass covering memory, hook health, skill usage, PST pipeline status, and Claude/Codex Hive parity.

Use `gpt-5.5` with medium reasoning. Treat `~/.codex` as the source of truth and `~/.claude` as a compatibility layer.

Hive scope:

- Rig config: `~/.hive/rigs.yaml`
- Active project manifests: `<project>/.codex/hive.yaml`
- Claude compatibility pointers: `<project>/.claude/hive.yaml`
- Bead commands: `bead-create`, `bead-list`, `bead-claim`, `bead-close`
- You may create local beads for platform parity issues. Do not edit files, delete files, comment on PRs, or create ADO work items.

## 1. Memory Curator

Scan the last 7 days of Claude Code session transcripts under:

- `~/.claude/file-history/`
- `~/.claude/cache/`
- `~/.claude/projects/-home-shovalbe/`

Identify:

- Corrections the user made that should become feedback memory.
- Approaches the user explicitly approved.
- New project facts not yet in memory.
- Stale memories that contradict latest sessions.

Do not modify memory files. Propose only.

## 2. Hook Health

Audit `~/.claude/hooks/*.sh`:

- budget comments, for example `# budget: 50ms`
- `bash -n` syntax result
- missing `set -euo pipefail`
- `/tmp` usage without cleanup
- `nc` or `curl` calls without timeouts
- `az` calls without retry or clear auth failure handling
- infinite-loop risks
- stale `/tmp/.claude-*` files older than 72 hours
- `~/.claude/hooks/.rtk-hook.sha256` vs the actual hash of `rtk-rewrite.sh`

Do not remove stale files. Propose cleanup commands only.

## 3. Skill Usage

Scan the last 30 days of session transcripts and `history.jsonl` for skill invocations. For each skill under `~/.claude/skills/`, classify:

- `HOT`: at least 10 invocations
- `WARM`: 1 to 9 invocations
- `COLD`: 0 invocations in 30 days
- `DEAD`: 0 invocations in 90 days

Suggest archive candidates only. Do not move or delete skills.

## 4. PST Pipeline Health

The user email/PST source is:

`/home/shovalbe/shoval.be@i-sdd.com.pst`

This is the Linux path behind the Windows UNC path:

`\\wsl.localhost\Ubuntu-24.04\home\shovalbe\shoval.be@i-sdd.com.pst`

Do not mine email bodies in this automation. Only verify pipeline health:

- PST file exists and mtime.
- `readpst` is installed.
- `pst-watch.service` exists and status if systemd user access is available.
- `~/.claude/bin/pst-watch.sh`, `pst-to-memory.py`, `pst-to-db.py`, and `pst-to-knowledge.py` exist.
- `~/.claude/cache/sessions.db` has `emails` rows if SQLite access works.

Never print full email bodies.

## 5. Hive and Claude/Codex Parity

Verify:

- `~/.hive/beads.db`, `~/.hive/rigs.yaml`, `~/.hive/audit.jsonl`, and `~/.hive/bin/bead-*` exist.
- `bead-list --json --limit 5` works.
- each active project in `~/.hive/rigs.yaml` has a real `.codex/` directory, `.codex/hive.yaml`, `AGENTS.md`, and `.claude/hive.yaml` when `.claude/` exists.
- Codex config has `model = "gpt-5.5"` and medium reasoning.
- Codex automation runner defaults to `CODEX_MODEL=gpt-5.5` and `CODEX_REASONING_EFFORT=medium`.
- Claude settings route Bash through the RTK compatibility hook.
- Claude `/cdp` documentation points to Obscura on port 9222 and Edge on port 9223.
- `~/.codex/bin/obscura-cdp status` works or reports a clear blocker.

Create a `P1` bead if Claude Bash RTK enforcement is missing. Create a `P2` bead if Obscura is documented but not smoke-testable.

## Output

Write one report:

`~/.claude/docs/PLATFORM_HYGIENE_<DATE>.md`

The report must contain:

- `MEMORY_PROPOSALS`
- `HOOK_HEALTH`
- `SKILL_USAGE`
- `PST_PIPELINE_HEALTH`
- `HIVE_PARITY`
- `HIVE_BEADS_CREATED`
- `ACTIONABLE_NEXT_STEPS`

If a finding is project-specific, add a short routing note naming the affected project, but do not edit project files.
