#!/usr/bin/env bash
# skill-usage-log.sh -- PostToolUse hook for the Skill tool.
#
# Recovered from state/retired-2026-07-25/hooks/meme-post-skill.sh, which already
# had the correct parse at its line 18 and spent it on playing a meme clip. The
# meme call is replaced by a JSONL append.
#
# Why this exists: as of 2026-07-27 no ledger in the estate carries a skill
# identifier. `refutations.jsonl` contains the string "skill" 119 times and
# `bus.jsonl` 21 times, every occurrence inside claim prose. There is no `skill`,
# `agent` or `subagent` field in any record, so every quality signal on disk
# floats free of what produced it. Nothing can be ranked until this fires.
#
# Contract: always exits 0, always emits valid JSON, never blocks. A logging hook
# that can fail the turn is worse than no logging.

set -uo pipefail
INPUT="$(cat 2>/dev/null || true)"

# The log path is computed inside Python, deliberately. Passing a POSIX path
# from Git Bash to a Windows Python depends on MSYS path conversion, which
# applies to `export`ed vars but not reliably to a command-prefix assignment.
# That difference silently produced zero rows on the first version of this hook.
HOOK_INPUT="$INPUT" python <<'PYEOF' 2>/dev/null || true
import json, os, sys, datetime, pathlib

try:
    payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
except Exception:
    payload = {}

skill = (payload.get("tool_input") or {}).get("skill", "")
if not skill:
    raise SystemExit(0)

# cwd decides the project, the same way Claude Code names its transcript dirs.
cwd = payload.get("cwd") or os.getcwd()
project = os.path.basename(str(cwd).rstrip("/\\")) or "unknown"

row = {
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "skill": skill,
    "args": ((payload.get("tool_input") or {}).get("args") or "")[:200],
    "session": payload.get("session_id", ""),
    "project": project,
    "cwd": str(cwd),
    # No quality judgement here (a hook scoring its own invocation is the
    # self-congratulation failure mode; quality joins from gate-runs.jsonl).
    # But the mechanical fact of the call is recordable: 2026-08-12, all 71
    # rows to date carried outcome None because the promised join never ran,
    # so "ran" vs "errored" was indistinguishable. This records only what the
    # harness itself reported about the tool call.
    "outcome": "errored" if (
        isinstance(payload.get("tool_response"), dict)
        and (payload["tool_response"].get("is_error")
             or payload["tool_response"].get("error"))
    ) else "ran",
}

os_dir = os.environ.get("CLAUDE_OS_DIR") or str(pathlib.Path.home() / "claude-setup")
log = pathlib.Path(os_dir) / "state" / "skill-use.jsonl"
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
PYEOF

echo '{}'
exit 0
