#!/usr/bin/env bash
# connector-usage-log.sh -- PostToolUse hook for MCP connector tools (mcp__*).
#
# Why this exists: measured 2026-08-17, the estate had ~24 connected MCP servers,
# 10 with a routing row, and ZERO usage records anywhere on disk (grep for a
# connector/mcp ledger returned nothing). Skills get state/skill-use.jsonl; MCP
# calls got nothing, so the registry's connector table floats free of behavior,
# the same defect class skill-usage-log.sh fixed for skills. Mirrors that hook.
#
# Contract: always exits 0, always emits valid JSON, never blocks.

set -uo pipefail
INPUT="$(cat 2>/dev/null || true)"

HOOK_INPUT="$INPUT" python <<'PYEOF' 2>/dev/null || true
import json, os, datetime, pathlib

try:
    payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
except Exception:
    payload = {}

tool = payload.get("tool_name", "") or ""
if not tool.startswith("mcp__"):
    raise SystemExit(0)

parts = tool.split("__")
server = parts[1] if len(parts) > 1 else "unknown"
method = parts[2] if len(parts) > 2 else ""

cwd = payload.get("cwd") or os.getcwd()
project = os.path.basename(str(cwd).rstrip("/\\")) or "unknown"

row = {
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "server": server,
    "tool": method,
    "session": payload.get("session_id", ""),
    "project": project,
    "outcome": "errored" if (
        isinstance(payload.get("tool_response"), dict)
        and (payload["tool_response"].get("is_error")
             or payload["tool_response"].get("error"))
    ) else "ran",
}

os_dir = os.environ.get("CLAUDE_OS_DIR") or str(pathlib.Path.home() / "claude-setup")
log = pathlib.Path(os_dir) / "state" / "connector-use.jsonl"
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
PYEOF

echo '{}'
exit 0
