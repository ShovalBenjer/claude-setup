#!/usr/bin/env python3
"""Stop hook: compute active-engagement time for the session and append it to a
local worklog ledger, attributed to the current ticket pointer.

Active-engagement = sum of gaps between consecutive transcript events, with each
gap capped at IDLE_CAP_SEC (so AFK stretches don't inflate the number). This is a
proxy for real work time, not wall-clock.

Nothing is posted to Jira here. Entries accumulate in worklog-pending.jsonl and
are posted only when Shoval confirms ("log my time").

Reads the hook payload (JSON) from stdin: needs `transcript_path`, `session_id`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

IDLE_CAP_SEC = 300  # 5-min cap per gap
STATE_DIR = Path.home() / ".claude" / "jira"
POINTER = STATE_DIR / "current-ticket"
REMINDERS = STATE_DIR / "reminders.json"
PENDING = STATE_DIR / "worklog-pending.jsonl"


def parse_ts(line: str):
    try:
        obj = json.loads(line)
    except Exception:
        return None
    ts = obj.get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def active_seconds(transcript_path: str) -> float:
    p = Path(transcript_path)
    if not p.exists():
        return 0.0
    stamps = []
    with p.open() as f:
        for line in f:
            t = parse_ts(line)
            if t:
                stamps.append(t)
    if len(stamps) < 2:
        return 0.0
    stamps.sort()
    total = 0.0
    for a, b in zip(stamps, stamps[1:]):
        gap = (b - a).total_seconds()
        total += min(max(gap, 0.0), IDLE_CAP_SEC)
    return total


def ticket_relation(cwd: str, session_id: str, ticket: str) -> dict:
    if not ticket or not REMINDERS.exists():
        return {"related": False, "reason": "no_ticket_or_digest"}
    env = os.environ.copy()
    root = str(Path.home() / "projects" / "intent-control-plane" / "src")
    env["PYTHONPATH"] = root if not env.get("PYTHONPATH") else f"{root}:{env['PYTHONPATH']}"
    try:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "intent_control_plane.cli",
                "jira",
                "assess",
                "--digest",
                str(REMINDERS),
                "--pointer",
                str(POINTER),
                "--cwd",
                cwd,
                "--session",
                session_id,
                "--task",
                cwd,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2.5,
            env=env,
        )
    except Exception as exc:
        return {"related": False, "reason": f"assessment_error:{type(exc).__name__}"}
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"related": False, "reason": "assessment_failed"}
    try:
        report = json.loads(proc.stdout)
    except Exception:
        return {"related": False, "reason": "assessment_parse_failed"}
    return report.get("current_ticket_relation") or {
        "key": ticket,
        "related": False,
        "reason": "pointer_not_assessed",
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never break the Stop chain

    transcript = payload.get("transcript_path", "")
    session_id = payload.get("session_id", "")
    secs = active_seconds(transcript)
    if secs <= 0:
        return 0

    pointer_ticket = POINTER.read_text().strip() if POINTER.exists() else ""
    cwd = payload.get("cwd", "")
    relation = ticket_relation(cwd, session_id, pointer_ticket)
    ticket = pointer_ticket if relation.get("related") else ""
    minutes = secs / 60.0
    rounded_15 = int(round(minutes / 15.0) * 15)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "session_id": session_id,
        "ticket": ticket,            # may be "" — surfaced as "unattributed"
        "ticket_pointer": pointer_ticket,
        "ticket_relation": relation,
        "active_seconds": round(secs),
        "active_minutes": round(minutes, 1),
        "rounded_minutes": rounded_15,
        "cwd": cwd,
        "stopped_at": datetime.now(timezone.utc).isoformat(),
    }
    with PENDING.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
