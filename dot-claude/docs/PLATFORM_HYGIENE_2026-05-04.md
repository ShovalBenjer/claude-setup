# Platform Hygiene Sweep - 2026-05-04

Automation id: `c01-platform-hygiene-sweep`
Run timestamp UTC: `20260504T062400Z`
Workspace root: `/home/shovalbe`
Mode: read + propose, no destructive changes

## MEMORY_PROPOSALS

### Scope and evidence

- Scanned last-7-day Claude surfaces requested by the task:
  - `/home/shovalbe/.claude/file-history/`
  - `/home/shovalbe/.claude/cache/`
  - `/home/shovalbe/.claude/projects/-home-shovalbe/`
- Evidence command:
  - `rtk proxy bash -lc 'find /home/shovalbe/.claude/file-history /home/shovalbe/.claude/cache /home/shovalbe/.claude/projects/-home-shovalbe -type f -mtime -7 2>/dev/null | wc -l; find /home/shovalbe/.claude/file-history /home/shovalbe/.claude/cache /home/shovalbe/.claude/projects/-home-shovalbe -type f -mtime -30 2>/dev/null | wc -l; find /home/shovalbe/.claude/file-history /home/shovalbe/.claude/cache /home/shovalbe/.claude/projects/-home-shovalbe -type f -mtime -90 2>/dev/null | wc -l'`
  - Output: `345`, `11425`, `11425`
- Current local Claude home memory index exists at `/home/shovalbe/.claude/projects/-home-shovalbe/memory/MEMORY.md` and lists 14 entries.
- Current memory files were last updated between `2026-04-30` and `2026-05-03`.

### Proposed new or updated memory

1. UPDATE: PST pipeline memory should be revised from "tooling exists under ~/.claude/bin" to "expected tooling is referenced by service/memory, but missing from ~/.claude/bin as of 2026-05-04."
   - Evidence: `pst-watch.service` exists and points to `/home/shovalbe/.claude/bin/pst-watch.sh`, but `/home/shovalbe/.claude/bin/pst-watch.sh`, `pst-to-memory.py`, `pst-to-db.py`, and `pst-to-knowledge.py` are missing.
   - Routing note: home-level runtime/PST pipeline.
   - Do not overwrite the older memory; preserve it as history and append the current contradiction.

2. NEW: Weekly Azure audit skill approval.
   - Evidence: recent home transcript created `/home/shovalbe/.claude/skills/azure-audit/SKILL.md` after the user asked for weekly Azure resources, dormant Azure DevOps repos, wikis, Foundry agents, and cost/activity audit coverage.
   - Proposed behavior memory: when the user asks for dormant Azure/resource cleanup, produce evidence-first audit reports and propose deletions rather than deleting autonomously.
   - Routing note: home-level Azure/ADO/Foundry operations.

3. NEW: Skill bridge compatibility fact.
   - Evidence: `/home/shovalbe/.claude/skills/` now contains two real local skills and six symlinks into `.codex` or `.agents` skill stores.
   - Proposed behavior memory: treat `.claude/skills` as a compatibility surface with symlinked active skills; when checking existence, follow symlinks instead of using `find -type f` only.
   - Routing note: home-level Claude/Codex compatibility.

4. SKIP: Several recent transcripts contain user corrections and operational nudges, but most are already covered by existing memory or global AGENTS rules:
   - root-cause inspection before patching
   - exact evidence and command output
   - no destructive actions without explicit approval
   - Codex as executor and Claude as orchestrator

### Stale or contradictory memory

- Stale candidate: older memory says PST scripts exist under `/home/shovalbe/.claude/bin`. Current evidence says those exact paths are absent.
- No removal proposed. This should be an UPDATE because the old memory may describe a prior valid state.

## HOOK_HEALTH

### Files audited

- `/home/shovalbe/.claude/hooks/visual-explainer-trigger.sh`
- `/home/shovalbe/.claude/hooks/voice-explainer-trigger.sh`

### Verification evidence

- Command:
  - `rtk proxy bash -lc 'for f in /home/shovalbe/.claude/hooks/*.sh; do [ -e "$f" ] || continue; printf "FILE %s\n" "$f"; grep -n "budget:" "$f" || true; head -n 5 "$f"; bash -n "$f" && echo "bash_n=PASS" || echo "bash_n=FAIL"; grep -nE "set -euo pipefail|/tmp|mktemp|trap |nc |curl |az |while true|for \(\(;;\)\)|until false" "$f" || true; done'`
- Output summary:
  - `visual-explainer-trigger.sh`: `bash_n=PASS`, has `set -euo pipefail`, uses `/tmp/.claude-visual-explainer-cooldown`.
  - `voice-explainer-trigger.sh`: `bash_n=PASS`, has `set -euo pipefail`, uses `/tmp/.claude-voice-explainer-cooldown`.

### Findings

1. LOW: Missing budget comments.
   - Neither hook contains a `# budget: ...ms` comment.
   - Proposed patch: add explicit budget comments near the header, for example `# budget: 50ms`.

2. LOW: `/tmp` cooldown files have no cleanup path.
   - The cooldown files are intentionally persistent between invocations, but the scripts do not document lifecycle or cleanup.
   - Proposed patch: either document that these are intentionally self-refreshing cooldown sentinels or use a cache directory with a periodic cleanup policy.

3. PASS: Syntax.
   - `bash -n` passed for both hook scripts.

4. PASS: Strict mode.
   - Both scripts include `set -euo pipefail`.

5. PASS: Network/auth timeouts not applicable.
   - No `curl`, `nc`, or `az` calls were found in either hook.

6. PASS: Infinite-loop risk not found.
   - No `while true`, `for ((;;))`, or `until false` patterns were found.

7. HIGH: RTK hook integrity marker and target are missing from `~/.claude/hooks`.
   - Command:
     - `rtk proxy bash -lc 'if [ -f /home/shovalbe/.claude/hooks/.rtk-hook.sha256 ]; then echo expected=$(cat /home/shovalbe/.claude/hooks/.rtk-hook.sha256); else echo expected=MISSING; fi; if [ -f /home/shovalbe/.claude/hooks/rtk-rewrite.sh ]; then echo actual=$(sha256sum /home/shovalbe/.claude/hooks/rtk-rewrite.sh | awk "{print \$1}"); else echo actual_file=MISSING; fi'`
   - Output:
     - `expected=MISSING`
     - `actual_file=MISSING`
   - Proposed action: do not hand-edit RTK-managed hooks. Re-run the approved RTK initialization path for the intended runtime, then re-check the marker and hash.

8. MEDIUM: Stale `/tmp/.claude-*` files older than 72 hours.
   - Command:
     - `rtk proxy bash -lc 'find /tmp -maxdepth 1 -name ".claude-*" -type f -mmin +4320 -printf "%TY-%Tm-%Td %TH:%TM %s %p\n" 2>/dev/null | sort | sed -n "1,80p"; echo COUNT=$(find /tmp -maxdepth 1 -name ".claude-*" -type f -mmin +4320 2>/dev/null | wc -l)'`
   - Output:
     - `2026-04-30 09:55 115 /tmp/.claude-visual-log`
     - `2026-04-30 09:55 2 /tmp/.claude-visual-count`
     - `COUNT=2`
   - Proposed cleanup command only:
     - `find /tmp -maxdepth 1 -name '.claude-*' -type f -mmin +4320 -print`
     - After review: `find /tmp -maxdepth 1 -name '.claude-*' -type f -mmin +4320 -delete`

## SKILL_USAGE

### Inventory evidence

- Command:
  - `rtk proxy bash -lc 'ls -la /home/shovalbe/.claude/skills'`
- Output summary:
  - Real directories: `azure-audit`, `codex-call`
  - Symlinked skills: `commit-push-pr`, `deep-research`, `eval-runner`, `red-team-review`, `visual-explainer`, `voice-explainer`

### Invocation scan method

- Scanned 30-day and 90-day text hits across `/home/shovalbe/.claude/projects/-home-shovalbe` and `/home/shovalbe/.claude/cache`.
- Also verified `/home/shovalbe/.claude/history.jsonl` exists:
  - `2026-05-03 18:13 96646 /home/shovalbe/.claude/history.jsonl`
- Caveat: counts are text-hit evidence, not exact semantic invocations. Claude transcripts contain hook injected prompts, skill docs, generated files, and tool results, so counts are useful for cold/dead detection but can overcount hotness.

### Classification

| Skill | Type | 30d hits | 90d hits | Class | Archive candidate |
|---|---:|---:|---:|---|---|
| `azure-audit` | local dir | 38 | 38 | HOT | No |
| `codex-call` | local dir | 42 | 42 | HOT | No |
| `commit-push-pr` | symlink to `.codex` | 228 | 228 | HOT | No |
| `deep-research` | symlink to `.agents` | 119 | 119 | HOT | No |
| `eval-runner` | symlink to `.codex` | 137 | 137 | HOT | No |
| `red-team-review` | symlink to `.codex` | 121 | 121 | HOT | No |
| `visual-explainer` | symlink to `.codex` | 245 | 245 | HOT | No |
| `voice-explainer` | symlink to `.codex` | 233 | 233 | HOT | No |

### Findings

- No `COLD` or `DEAD` skills found under `/home/shovalbe/.claude/skills/` by the 30/90 day text-hit scan.
- No archive candidates proposed.
- Operational note: because most skills are symlinks, archive decisions should be made against the source skill store (`.codex` or `.agents`), not only the compatibility link.

## PST_PIPELINE_HEALTH

### PST source

- Command:
  - `rtk proxy bash -lc 'P=/home/shovalbe/shoval.be@i-sdd.com.pst; if [ -e "$P" ]; then stat -c "exists=YES size=%s mtime=%y path=%n" "$P"; else echo exists=NO path=$P; fi; command -v readpst || true; readpst -V 2>&1 | head -5 || true'`
- Output:
  - `exists=YES size=143754240 mtime=2026-04-23 21:03:13.610510400 +0300 path=/home/shovalbe/shoval.be@i-sdd.com.pst`
  - `/usr/bin/readpst`
  - `ReadPST / LibPST v0.6.76`

### Service status

- Unit files exist:
  - `/home/shovalbe/.config/systemd/user/pst-watch.service`
  - `/home/shovalbe/.config/systemd/user/default.target.wants/pst-watch.service`
- Service content:
  - `ExecStart=/home/shovalbe/.claude/bin/pst-watch.sh /home/shovalbe/shoval.be@i-sdd.com.pst`
- Status command:
  - `rtk proxy bash -lc 'systemctl --user list-unit-files pst-watch.service --no-pager 2>&1 | sed -n "1,20p"; echo ---STATUS---; systemctl --user status pst-watch.service --no-pager 2>&1 | sed -n "1,25p"'`
- Output:
  - `Failed to connect to bus: Operation not permitted`
  - `---STATUS---`
  - `Failed to connect to bus: Operation not permitted`
- BLOCKED: systemd user bus is unavailable in this scheduled Codex sandbox, so live service status could not be read.

### Required scripts

- Command:
  - `rtk proxy bash -lc 'for f in /home/shovalbe/.claude/bin/pst-watch.sh /home/shovalbe/.claude/bin/pst-to-memory.py /home/shovalbe/.claude/bin/pst-to-db.py /home/shovalbe/.claude/bin/pst-to-knowledge.py; do if [ -e "$f" ]; then stat -c "EXISTS %a %s %y %n" "$f"; else echo MISSING $f; fi; done'`
- Output:
  - `MISSING /home/shovalbe/.claude/bin/pst-watch.sh`
  - `MISSING /home/shovalbe/.claude/bin/pst-to-memory.py`
  - `MISSING /home/shovalbe/.claude/bin/pst-to-db.py`
  - `MISSING /home/shovalbe/.claude/bin/pst-to-knowledge.py`
- BLOCKED: the service points at a missing watcher script, and all requested PST helper scripts are absent from `~/.claude/bin`.

### SQLite/cache health

- Command:
  - `rtk proxy bash -lc 'DB=/home/shovalbe/.claude/cache/sessions.db; if [ -e "$DB" ]; then stat -c "db_exists=YES size=%s mtime=%y" "$DB"; sqlite3 "$DB" ".tables" 2>&1 | tr " " "\n" | sed "/^$/d" | sort | sed -n "1,80p"; echo ---email_counts---; sqlite3 "$DB" "select count(*) from emails;" 2>&1; else echo db_exists=NO; fi'`
- Output:
  - `db_exists=NO`
- BLOCKED: `~/.claude/cache/sessions.db` is missing, so `emails` row count could not be verified.

### Email-body safety

- This sweep did not mine or print email bodies.
- PST verification was limited to file existence, mtime, installed parser, service wiring, script existence, and database/table existence.

## ACTIONABLE_NEXT_STEPS

1. Restore or intentionally retire the PST pipeline compatibility layer.
   - If restoring: recreate `/home/shovalbe/.claude/bin/pst-watch.sh`, `pst-to-memory.py`, `pst-to-db.py`, and `pst-to-knowledge.py`, then run:
     - `systemctl --user daemon-reload`
     - `systemctl --user restart pst-watch.service`
     - `systemctl --user status pst-watch.service --no-pager`
   - If retiring: disable the user unit after confirming there is a replacement path:
     - `systemctl --user disable --now pst-watch.service`
   - Do not run either path blindly; the current automation is read/propose only.

2. Update memory for the PST pipeline contradiction.
   - Proposed memory update: "PST tooling was expected under ~/.claude/bin, but as of 2026-05-04 the service unit exists while the target scripts and sessions.db are missing."

3. Re-establish RTK hook integrity only through RTK tooling.
   - Current evidence: `/home/shovalbe/.claude/hooks/.rtk-hook.sha256` and `/home/shovalbe/.claude/hooks/rtk-rewrite.sh` are missing.
   - Proposed verification after repair:
     - `sha256sum /home/shovalbe/.claude/hooks/rtk-rewrite.sh`
     - `cat /home/shovalbe/.claude/hooks/.rtk-hook.sha256`

4. Add explicit hook budgets.
   - Proposed patch targets:
     - `/home/shovalbe/.claude/hooks/visual-explainer-trigger.sh`
     - `/home/shovalbe/.claude/hooks/voice-explainer-trigger.sh`
   - Suggested comment: `# budget: 50ms`

5. Review stale temp files before cleanup.
   - Review:
     - `find /tmp -maxdepth 1 -name '.claude-*' -type f -mmin +4320 -print`
   - Cleanup after review:
     - `find /tmp -maxdepth 1 -name '.claude-*' -type f -mmin +4320 -delete`

6. Keep all `.claude/skills` entries for now.
   - No cold/dead skill archive candidates were found.
   - Future improvement: replace text-hit counts with structured invocation extraction from transcript event types to avoid overcounting generated docs and hook hints.
