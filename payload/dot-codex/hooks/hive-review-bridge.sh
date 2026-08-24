#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-pickup}"
INPUT="$(cat)"

if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ] || [ -n "${AI_AGENT:-}" ]; then
  echo '{}'
  exit 0
fi

HOOK_INPUT="$INPUT" python3 - "$MODE" <<'PYEOF'
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


mode = sys.argv[1] if len(sys.argv) > 1 else "pickup"
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


def rig_for_path(cwd: str) -> str | None:
    path = Path(cwd).resolve()
    parts = set(path.parts)
    text = str(path)
    if "axia-seekapa-cs-agents" in parts or "cs-agent" in parts:
        return "cs-agent"
    if "qc-telephony-api" in parts or "/projects/qc/qc-telephony-api" in text:
        return "qc-telephony-api"
    if "video-understanding" in parts:
        return "video-understanding"
    if "campaign-analysis" in parts:
        return "campaign-analysis"
    if "seekapa-training-platform" in parts:
        return "seekapa-training-platform"
    if "ORM-AGENT" in parts:
        return "ORM-AGENT"
    return None


def serious_prompt(prompt: str) -> bool:
    if not prompt.strip():
        return True
    return bool(
        re.search(
            r"\b(fix|implement|build|review|ship|deploy|merge|prd|plan|reground|pickup|bead|hive|bug|feature|commit|push|test|refactor)\b",
            prompt,
            flags=re.IGNORECASE,
        )
    )


def latest_review() -> str | None:
    docs = Path.home() / ".claude" / "docs"
    candidates = sorted(docs.glob("ENGINEERING_REVIEW_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else None


def query_beads(rig: str | None, status: str) -> list[sqlite3.Row]:
    db_path = Path(os.environ.get("HIVE_DB", str(Path.home() / ".hive" / "beads.db")))
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    params: list[object] = [status]
    where = ["status = ?"]
    if rig:
        where.append("rig = ?")
        params.append(rig)
    priority_sql = f"""
      SELECT id, priority, rig, owner_role, title, claimed_by, created_at
      FROM beads
      WHERE {' AND '.join(where)}
      ORDER BY
        CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END,
        updated_at DESC,
        id DESC
      LIMIT 5
    """
    newest_sql = f"""
      SELECT id, priority, rig, owner_role, title, claimed_by, created_at
      FROM beads
      WHERE {' AND '.join(where)}
      ORDER BY created_at DESC, id DESC
      LIMIT 5
    """
    try:
        rows = []
        seen = set()
        for row in conn.execute(priority_sql, params).fetchall() + conn.execute(newest_sql, params).fetchall():
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            rows.append(row)
            if len(rows) >= 8:
                break
        return rows
    finally:
        conn.close()


def claim_first(rig: str, row: sqlite3.Row, prompt: str) -> sqlite3.Row:
    db_path = Path(os.environ.get("HIVE_DB", str(Path.home() / ".hive" / "beads.db")))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    claimed_by = "claude:auto"
    if prompt.strip():
        slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")[:48]
        if slug:
            claimed_by = f"claude:auto:{slug}"
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE beads SET status = 'claimed', claimed_by = ?, updated_at = datetime('now') WHERE id = ? AND status = 'open'",
            (claimed_by, row["id"]),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT id, priority, rig, owner_role, title, claimed_by, created_at FROM beads WHERE id = ?",
            (row["id"],),
        ).fetchone()
        audit_path = Path(os.environ.get("HIVE_AUDIT", str(Path.home() / ".hive" / "audit.jsonl")))
        event = {
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "event": "bead.claimed",
            "id": row["id"],
            "rig": rig,
            "claimed_by": claimed_by,
            "source": "claude-hook-user-prompt-submit",
        }
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
        return updated
    finally:
        conn.close()


cwd = get_cwd(payload)
prompt = get_prompt(payload)
rig = rig_for_path(cwd)

if mode == "pickup" and not serious_prompt(prompt):
    print("{}")
    raise SystemExit(0)

claimed_rows = query_beads(rig, "claimed")
open_rows = query_beads(rig, "open")
auto_claimed = None

if mode == "pickup" and rig and not claimed_rows and open_rows:
    auto_claimed = claim_first(rig, open_rows[0], prompt)
    claimed_rows = [auto_claimed]
    open_rows = [row for row in open_rows if row["id"] != auto_claimed["id"]]

rows = claimed_rows + open_rows
if not rows:
    print("{}")
    raise SystemExit(0)

review = latest_review()
scope = f"for rig `{rig}`" if rig else "globally"
lines = [
    f"CODEX REVIEW PICKUP: open Hive review beads exist {scope}. Before new implementation/planning, pick one up or explicitly defer with a reason.",
]
if review:
    lines.append(f"Latest scheduled Codex review: `{review}`.")
if auto_claimed:
    lines.append(f"AUTO-CLAIMED: #{auto_claimed['id']} for this Claude task. Do not switch tasks without closing or explicitly deferring it.")
elif claimed_rows:
    lines.append("Already claimed beads:")
else:
    lines.append("Open beads:")
for row in rows:
    suffix = f" | claimed_by={row['claimed_by']}" if row["claimed_by"] else ""
    lines.append(f"- #{row['id']} | {row['priority']} | {row['rig']} | {row['owner_role']} | {row['title']}{suffix}")

if mode == "post-tool":
    lines.append("After edits, close the claimed bead only with evidence: `~/.hive/bin/bead-close <id> --evidence-url <commit-or-report-or-test-log>`. Empty close is blocked.")
else:
    if not auto_claimed and not claimed_rows:
        lines.append("If this task touches one of these findings, claim it first: `~/.hive/bin/bead-claim --rig <rig> --claimed-by claude:<task>`.")
    lines.append("When resolved, close with evidence: `~/.hive/bin/bead-close <id> --evidence-url <commit-or-report-or-test-log>`. Empty close is blocked.")

message = "\n".join(lines)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart" if mode == "session" else ("UserPromptSubmit" if mode == "pickup" else "PostToolUse"),
        "additionalContext": message,
    }
}))
PYEOF
