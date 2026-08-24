# A3. Hook Health Audit

Schedule: Sundays 9:00 PM
Repo root: `/home/shovalbe/.claude/`
Mode: read + propose

Audit `~/.claude/hooks/*.sh`:

1. For each hook, parse the per-hook budget comment if present, for example `# budget: 50ms`. List hooks without a budget comment.
2. Check shell syntax with `bash -n <hook>`.
3. Grep for anti-patterns: missing `set -euo pipefail`, hardcoded absolute paths to `/tmp` without cleanup, calls to `nc` or `curl` without timeouts, calls to `az` without retry, infinite loops.
4. Inspect `/tmp/.claude-*` for stale state files older than 72 hours.
5. Check `~/.claude/hooks/.rtk-hook.sha256` against the actual hash of `rtk-rewrite.sh`; flag if mismatched.

Output `~/.claude/docs/HOOK_HEALTH_<DATE>.md` with:

- Per-hook table: name, LOC, has_budget_comment, syntax_ok, anti_patterns, last_modified.
- Stale-state list with suggested `rm` commands. Do not auto-remove anything.
- RTK integrity status.
- Top 3 hooks with no budget comment and suggested values.
