#!/usr/bin/env python3
"""Statusline: one honest line per terminal, and a state tap for the operator's own UI.

Two jobs, deliberately coupled:
1. Render `lane · repo · model · $cost · ctx%` for Claude Code's statusline bar,
   so every terminal names its lane and project (operator pick 2026-07-29: Rich).
2. Tee a compact per-session snapshot to state/sessions/<session_id>.json in the
   harness repo. That registry, not this bar, is the substrate for the
   operator's own UI (FleetView v0): the operator wants out of Claude's UI, and
   whatever stack that UI lands on reads these files, so the bar and the UI can
   never disagree about what a session is doing.

Lane honesty (same contract as session-recall.sh): a DECLARED lane (CLAUDE_LANE
from a lane launcher) renders plain, e.g. `B`. A lane inferred from cwd renders
`?>B`, because the desktop-shortcut era proved inferred lanes are confidently
wrong. No signal at all renders `?`.

Fields the harness does not provide are omitted, never invented. The snapshot
write is best-effort and must never break the bar: the bar is the contract,
the tap is a bonus.
"""
import json
import os
import sys
import time
from pathlib import Path

LANE_BY_DIR = {
    "claude-setup": "B",
    "new-recruit": "C",
    "daily-deep-learning": "D",
}


def lane_of(cwd: str) -> str:
    declared = (os.environ.get("CLAUDE_LANE") or "").strip().upper()
    if declared:
        return declared
    base = Path(cwd).name if cwd else ""
    inferred = LANE_BY_DIR.get(base)
    return "?>{}".format(inferred) if inferred else "?"


def main() -> int:
    # The bar renders in Claude Code's UI, which is UTF-8; a Windows console
    # default of cp1252 would mangle the separator.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    ws = payload.get("workspace") or {}
    cwd = ws.get("current_dir") or ws.get("project_dir") or os.getcwd()
    repo = Path(cwd).name or cwd
    model = (payload.get("model") or {}).get("display_name") or ""
    lane = lane_of(cwd)

    parts = [lane, repo]
    if model:
        parts.append(model)

    cost = (payload.get("cost") or {}).get("total_cost_usd")
    if isinstance(cost, (int, float)):
        parts.append("${:.2f}".format(cost))

    # Context pressure: the harness has exposed this under different names
    # across versions; take the first one present, omit when none is.
    ctx = None
    cw = payload.get("context_window") or {}
    for candidate in (cw.get("used_percentage"), payload.get("context_used_pct")):
        if isinstance(candidate, (int, float)):
            ctx = candidate
            break
    if ctx is not None:
        parts.append("ctx {:.0f}%".format(ctx))
    elif payload.get("exceeds_200k_tokens"):
        parts.append("ctx>200k")

    print(" · ".join(str(p) for p in parts))

    # --- the tap (best-effort, never fatal) ---
    try:
        sid = payload.get("session_id") or "unknown"
        reg = Path.home() / "claude-setup" / "state" / "sessions"
        reg.mkdir(parents=True, exist_ok=True)
        snap = {
            "ts": round(time.time(), 3),
            "session_id": sid,
            "lane": lane,
            "cwd": cwd,
            "repo": repo,
            "model": model,
            "cost_usd": cost,
            "ctx_pct": ctx,
            "version": payload.get("version"),
            "pid": os.getppid(),
        }
        tmp = reg / (sid + ".json.tmp")
        tmp.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, reg / (sid + ".json"))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
