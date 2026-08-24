#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-prompt}"
INPUT="$(cat)"

# AI_AGENT gate removed: Claude Code always sets AI_AGENT=claude-code_*, so gating on it
# disabled intent capture in EVERY interactive session (why intent.db only had smoke data).
# Real automation still skips via CLAUDE_LOOP_MODE / CODEX_AUTOMATION_ID.
if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; then
  echo '{}'
  exit 0
fi

HOOK_INPUT="$INPUT" PYTHONPATH="$HOME/projects/intent-control-plane/src${PYTHONPATH:+:$PYTHONPATH}" python3 - "$MODE" <<'PYEOF'
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from intent_control_plane.cli import capture, context_pack, extract_intent


mode = sys.argv[1] if len(sys.argv) > 1 else "prompt"
try:
    payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
except Exception:
    payload = {}


def get_cwd(data: dict) -> str:
    workspace = data.get("workspace") or {}
    return (
        workspace.get("current_dir")
        or workspace.get("project_dir")
        or data.get("cwd")
        or os.environ.get("PWD")
        or str(Path.home())
    )


def get_prompt(data: dict) -> str:
    for key in ("prompt", "user_prompt", "message", "text"):
        value = data.get(key)
        if isinstance(value, str):
            return value
    return ""


def get_final_text(data: dict) -> str:
    for key in ("response", "assistant_response", "final_answer", "answer", "message", "text"):
        value = data.get(key)
        if isinstance(value, str):
            return value[:8000]
    result = data.get("result")
    if isinstance(result, dict):
        for key in ("response", "final_answer", "message", "text"):
            value = result.get(key)
            if isinstance(value, str):
                return value[:8000]
    return ""


def git_branch(cwd: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=1.5,
        )
    except Exception:
        return None
    branch = result.stdout.strip()
    return branch or None


cwd = get_cwd(payload)
branch = git_branch(cwd)
session = payload.get("session_id") or payload.get("sessionId") or "claude-hook"

if mode == "stop":
    final_text = get_final_text(payload).strip()
    if final_text:
        try:
            capture(
                SimpleNamespace(
                    base_dir=Path.home() / ".intent",
                    event_type="assistant_final",
                    session=session,
                    repo=cwd,
                    branch=branch,
                    bead=None,
                    workflow=None,
                    actor="claude",
                    authority="assistant_summary",
                    text=final_text,
                )
            )
        except Exception:
            pass
    print("{}")
    raise SystemExit(0)

prompt = get_prompt(payload).strip()
if mode != "prompt" or not prompt:
    print("{}")
    raise SystemExit(0)

try:
    captured = capture(
        SimpleNamespace(
            base_dir=Path.home() / ".intent",
            event_type="user_prompt",
            session=session,
            repo=cwd,
            branch=branch,
            bead=None,
            workflow=None,
            actor="shoval",
            authority="raw_user_prompt",
            text=prompt,
        )
    )
    intent = extract_intent(
        SimpleNamespace(base_dir=Path.home() / ".intent", event=captured["event_id"])
    )
    pack = context_pack(
        SimpleNamespace(
            base_dir=Path.home() / ".intent",
            repo=cwd,
            task=prompt[:240],
            format="json",
            top_k=8,
        )
    )
except Exception as exc:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": f"INTENT CAPTURE WARNING: local intent capture failed: {type(exc).__name__}: {exc}",
        }
    }))
    raise SystemExit(0)

constraints = intent.get("constraints") or []
proof = intent.get("proof_required") or []
constraint_text = "; ".join(item.get("text", "") for item in constraints[:3]) or "none inferred"
proof_text = ", ".join(item.get("type", "") for item in proof[:5]) or "explicit_verification"

recall_items = pack.get("included_items", [])[:8] if isinstance(pack, dict) else []
recall_lines = []
_self_id = captured.get("event_id")
for _it in recall_items:
    if _it.get("source_event_id") == _self_id:
        continue  # skip the just-captured current prompt (self-match ranks itself #1)
    _ex = (_it.get("excerpt") or "").replace("\n", " ").strip()
    if _ex.startswith("<"):
        continue  # skip tool/system notification blobs; not real prior intent
    _ex = _ex.replace("—", ", ").replace("–", ", ")[:160]
    if _ex:
        recall_lines.append(f"    - {_ex}")
    if len(recall_lines) >= 3:
        break

message_lines = [
    "INTENT CONTROL PLANE:",
    f"- captured_event: `{captured['event_id']}`",
    f"- intent: `{intent['intent_id']}`",
    f"- context_pack: `{pack['context_pack_id']}`",
    f"- constraints: {constraint_text}",
    f"- proof_required: {proof_text}",
]
if recall_lines:
    message_lines.append("- recalled context (top ranked prior events):")
    message_lines.extend(recall_lines)
message_lines.append(
    "Before claiming completion, attach evidence with `intent evidence attach` or clearly state the blocker."
)
message = "\n".join(message_lines)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": message,
    }
}))
PYEOF
