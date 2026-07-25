#!/usr/bin/env python3
"""Every registered hook actually EXECUTES without erroring.

Existence is not execution. On 2026-07-25 pre_push_gate.py existed, was readable
by PowerShell, and still failed on every single Bash call with

    python: can't open file 'C:\\Users\\shova\\.claude\\hooks\\pre_push_gate.py':
    [Errno 2] No such file or directory

A stat-based checker calls that green. This one launches each hook the way Claude
Code does (command + args, JSON payload on stdin) and looks at what comes back.

What counts as a failure here
-----------------------------
Hooks legitimately use exit codes to signal decisions: 0 = allow, 2 = block with
feedback on stderr. Neither is a defect. A defect is the hook failing to RUN:
a traceback, an interpreter that cannot find the script, a missing module, a
timeout. Those are detected by signature, not by exit code alone, so a blocking
hook is never reported as broken.

Read-only by design: it sends a harmless payload (a `git status` Bash call) so
nothing is mutated, and it never runs Stop/PreCompact hooks that write state.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SETTINGS = Path(os.path.expanduser("~")) / ".claude" / "settings.json"
TIMEOUT = 20

# Events whose hooks write handoff state or notify; running them would forge
# session artifacts, so they are resolved but not invoked.
NO_INVOKE = {"PreCompact", "Notification", "SessionEnd"}

# Substrings that mean "the hook could not run", as opposed to "the hook ran and
# decided to block". Matched case-insensitively against stdout+stderr.
BROKEN_SIGNS = (
    "can't open file",
    "cannot open file",
    "no such file or directory",
    "modulenotfounderror",
    "importerror",
    "traceback (most recent call last)",
    "is not recognized as",
    "command not found",
    "syntaxerror",
    "permission denied",
)


def payload_for(event: str) -> str:
    base = {
        "session_id": "refute-selftest",
        "transcript_path": "",
        "cwd": os.getcwd(),
        "hook_event_name": event,
    }
    if event == "PreToolUse":
        base |= {"tool_name": "Bash", "tool_input": {"command": "git status --short"}}
    elif event == "PostToolUse":
        base |= {"tool_name": "Bash", "tool_input": {"command": "git status --short"},
                 "tool_response": {"stdout": "", "stderr": "", "interrupted": False}}
    elif event == "UserPromptSubmit":
        base |= {"prompt": "refute.py self-test, ignore"}
    return json.dumps(base)


def argv_for(hook: dict) -> list[str] | None:
    cmd = hook.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return None
    argv = [cmd]
    args = hook.get("args")
    if isinstance(args, list):
        argv.extend(str(a) for a in args)
    return argv


def main() -> int:
    if not SETTINGS.exists():
        print(f"settings.json not found at {SETTINGS}")
        return 1
    try:
        cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"settings.json is not valid JSON: {e}")
        return 1

    broken: list[str] = []
    ran = 0
    skipped = 0

    for event, groups in (cfg.get("hooks") or {}).items():
        for group in groups or []:
            for hook in group.get("hooks") or []:
                argv = argv_for(hook)
                if argv is None:
                    broken.append(f"{event}: registration has no command")
                    continue
                if event in NO_INVOKE:
                    skipped += 1
                    continue

                label = f"{event}: {' '.join(argv[:2])}"
                try:
                    p = subprocess.run(
                        argv, input=payload_for(event), capture_output=True,
                        text=True, timeout=TIMEOUT, errors="replace",
                    )
                except subprocess.TimeoutExpired:
                    broken.append(f"{label} -> timed out after {TIMEOUT}s")
                    continue
                except OSError as e:
                    broken.append(f"{label} -> could not launch: {e}")
                    continue

                ran += 1
                blob = ((p.stdout or "") + (p.stderr or "")).lower()
                hit = next((s for s in BROKEN_SIGNS if s in blob), None)
                if hit:
                    first = next(
                        (ln.strip() for ln in
                         ((p.stderr or "") + "\n" + (p.stdout or "")).splitlines()
                         if ln.strip()),
                        "(no output)",
                    )
                    broken.append(f"{label} -> rc={p.returncode} [{hit}] {first[:160]}")
                elif p.returncode not in (0, 2):
                    broken.append(f"{label} -> unexpected rc={p.returncode} "
                                  f"(0=allow, 2=block are the defined codes)")

    if ran == 0 and not broken:
        print("no hooks were invoked; treat as UNKNOWN not pass")
        return 1

    if broken:
        print(f"{len(broken)} hook(s) do not execute cleanly "
              f"({ran} invoked, {skipped} skipped as state-writing):")
        for b in broken:
            print(f"  {b}")
        return 1

    print(f"{ran} hooks invoked, all execute cleanly ({skipped} skipped as state-writing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
