#!/usr/bin/env python3
"""Stop-boundary drift sentinel, NOTIFY-ONLY payload (not wired by default).

Reads the Stop payload (session_id, transcript_path), the lane from
$CLAUDE_LANE, and asks tools/drift/drift.py whether this session's edits left
the lane's owned tree. On drift it emits a systemMessage naming the offending
paths and asking for /reground, and records a strike in state/drift/.

It NEVER blocks and never exits 2. The escalation policy (strike 2 closes the
session via a hookgate deny) stays unarmed until a week of state/drift/ ledger
shows the false-positive rate: the follow-through hook's threshold cost a
measured 66 operator turns before it was softened, and this hook does not get
to repeat that on hope. A missing lane, charter, or drift.py reports OFF as a
systemMessage rather than passing silently (ship_gate_stop.py's rule: a guard
that cannot run must announce it).

Wire (operator decision) as a Stop hook:
  python3 ~/.claude/hooks/drift_notify_stop.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys


def out(msg: str) -> int:
    sys.stdout.write(json.dumps({"systemMessage": msg}))
    return 0


def load_drift():
    candidates = []
    env = os.environ.get("CLAUDE_SETUP_ROOT")
    if env:
        candidates.append(os.path.join(env, "tools", "drift", "drift.py"))
    candidates.append(os.path.join(os.path.expanduser("~"),
                                   "claude-setup", "tools", "drift", "drift.py"))
    for cand in candidates:
        if os.path.exists(cand):
            spec = importlib.util.spec_from_file_location("_drift", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return out("drift sentinel OFF: unreadable Stop payload")
    lane = os.environ.get("CLAUDE_LANE", "").strip()
    if not lane:
        return 0  # no lane claimed; nothing to measure, and boot already nags
    transcript = payload.get("transcript_path") or ""
    session = payload.get("session_id") or "unknown"
    mod = load_drift()
    if mod is None:
        return out("drift sentinel OFF: drift.py not found (set CLAUDE_SETUP_ROOT)")
    from pathlib import Path
    verdict = mod.check(Path(transcript), lane, session)
    if verdict["verdict"] == "OFF":
        return out("drift sentinel OFF: " + verdict.get("why", ""))
    if verdict["verdict"] == "CLEAN":
        return 0
    return out(
        "DRIFT strike {n} for lane {lane}: edits outside the lane's tree: "
        "{paths}. Run /reground and either re-claim the right lane or stop "
        "this work. (notify-only; strike 2 close is not armed)".format(
            n=verdict["strike"], lane=lane,
            paths=", ".join(verdict["offending"][:5])))


if __name__ == "__main__":
    raise SystemExit(main())
