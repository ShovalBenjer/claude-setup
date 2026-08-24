"""Read-only data providers for the control tower: Codex/a2a usage + intent-plane health.

Split note (2026-07-10): the standalone renderer and the `python -m ...dashboard` entry
were removed. tower.py is the live TUI and imports a2a_usage/intent_health plus the two
path constants from here, so this module is now a pure, tested data layer with no
presentation. The old renderer's scorecard panel read a hardcoded dated
`docs/project-scorecard-*.md`, which drifted out of date (the stale-cache bug); tower
computes the scorecard live via standards.score_projects instead, so nothing here reads a
frozen file any more.
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

A2A_AUDIT = Path.home() / ".claude" / "cache" / "a2a" / "audit.jsonl"
INTENT_DB = Path.home() / ".intent" / "intent.db"


def a2a_usage(path: Path = A2A_AUDIT) -> dict[str, Any]:
    """Codex call volume and reliability from the a2a audit ledger."""
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line:
                with contextlib.suppress(json.JSONDecodeError):
                    rows.append(json.loads(line))
    except OSError:
        return {"total": 0, "completed": 0, "failed": 0, "fail_rate": 0.0, "by_state": {}, "by_day": {}}
    state = Counter(str(r.get("state", "?")) for r in rows)
    day = Counter(str(r.get("ts", ""))[:10] for r in rows if r.get("ts"))
    total = len(rows)
    completed = state.get("completed", 0)
    failed = total - completed
    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "fail_rate": round(failed / total, 3) if total else 0.0,
        "by_state": dict(state.most_common()),
        "by_day": dict(sorted(day.items())),
    }


def intent_health(db: Path = INTENT_DB) -> dict[str, Any]:
    """Row counts from the intent plane (fast, read-only)."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return {}

    def count(table: str) -> int:
        try:
            return int(conn.execute(f"select count(*) from {table}").fetchone()[0])
        except sqlite3.Error:
            return 0

    out = {
        "events": count("events"),
        "intents": count("intent_cards"),
        "evidence": count("evidence"),
        "bead_refs": count("hive_bead_refs"),
        "bindings": count("hive_bindings"),
    }
    conn.close()
    return out
