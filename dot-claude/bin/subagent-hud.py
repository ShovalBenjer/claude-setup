#!/usr/bin/env python3
"""subagentStatusLine renderer: WoW-style party-card rows for the Claude Code agent panel.

Reads the agent-panel JSON on stdin (carries tasks[] with id/status/model/tokenCount/label)
and emits one {"id":..., "content":...} JSON line per row, rendering each teammate as a party
member in the Widgora palette: a status-colored sigil, the task name, and status/model/mana
(token cost). No emoji. ANSI truecolor. Fails silent (empty output) on any bad input.
"""
from __future__ import annotations

import json
import sys


def c(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


RESET = "\033[0m"
TEXT = c(237, 237, 242)
MUTED = c(139, 145, 163)
GREEN = c(46, 189, 133)
AMBER = c(224, 162, 58)
RED = c(240, 82, 106)

# status -> (color, label). Color is always paired with the word (colorblind-safe rule).
STATUS = {
    "working": (GREEN, "working"),
    "in_progress": (GREEN, "working"),
    "running": (GREEN, "working"),
    "idle": (MUTED, "idle"),
    "pending": (MUTED, "pending"),
    "blocked": (AMBER, "blocked"),
    "failed": (RED, "failed"),
    "error": (RED, "failed"),
    "completed": (GREEN, "done"),
    "done": (GREEN, "done"),
}


def mana(n: object) -> str:
    try:
        value = int(n or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{value / 1000:.1f}k" if value >= 1000 else str(value)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    for task in data.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id")
        if task_id is None:
            continue
        name = str(task.get("label") or task.get("name") or task.get("description") or "agent")[:32]
        color, word = STATUS.get(str(task.get("status", "")).lower(), (MUTED, str(task.get("status", "?"))))
        model = str(task.get("model") or "")
        tok = mana(task.get("tokenCount"))
        content = f"{color}◆{RESET} {TEXT}{name}{RESET}  {MUTED}{word} · {model} · {tok} mana{RESET}"
        print(json.dumps({"id": task_id, "content": content}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
