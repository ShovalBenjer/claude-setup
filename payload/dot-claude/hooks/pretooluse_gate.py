#!/usr/bin/env python3
"""One PreToolUse process instead of two, without moving either guard's logic here.

Measured on this machine 2026-07-30, 25 warm reps each, stdin from a file:

    safety_gate.py                211 ms
    pre_push_gate.py              224 ms   -> 435 ms on EVERY Bash call
    this dispatcher, python -S -E 117 ms
    python -S -E -c pass          106 ms   <- the floor

So the two guards cost 435 ms per Bash tool call to do about 11 ms of regex work.
The rest was two Python interpreter cold starts. This file removes one of them and
`-S -E` in settings.json removes the site-import half of the other, leaving the
dispatcher 11 ms above the bare-interpreter floor. There is nothing further to win
here without leaving Python, and the two alternatives were measured and rejected:
Git Bash + grep is cheaper to start (130 ms) but would mean reimplementing the deny
rules in shell, and routing to WSL python3 costs 227 ms per call because the wsl.exe
boundary is more expensive than the interpreter it saves, even though python3 inside
the distro starts in 24 ms.

WHY THIS IS SAFE TO DO TO A SAFETY GUARD

Nothing here reimplements a rule. `safety_gate.RULES` is already module-level data, so
the deny patterns are used from their own module, and `pre_push_gate` is invoked
through its own `main()`. The structural fact that makes the fast path correct is that
`pre_push_gate.main()` returns without acting unless the command matches
`pre_push_gate.PUSH`; every non-push call spends a full interpreter start to answer
"no". This file asks that same regex, from that same module, before deciding to enter
it. If the guard's trigger condition ever widens beyond PUSH, this fast path becomes
wrong, and `tests/test_pretooluse_gate.py` is the differential oracle that catches it:
it runs a command corpus through this dispatcher and through the two hooks separately
and requires byte-identical decisions.

The hook protocol allows exactly one JSON object on stdout, which is the other reason
the two guards could not simply be chained in one shell command.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import types
from pathlib import Path
from typing import Any

HOOK_DIR = Path(__file__).resolve().parent


def _load(name: str):
    """Import a sibling hook by path.

    Not a plain `import`: these files live in ~/.claude/hooks, which is not a package
    and is not on sys.path when Claude Code spawns a hook with an absolute script path.
    """
    spec = importlib.util.spec_from_file_location(name, HOOK_DIR / (name + ".py"))
    if spec is None or spec.loader is None:
        raise ImportError(name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    # Read stdin once. Both guards want it, and it can only be consumed once.
    try:
        raw = sys.stdin.buffer.read()
        payload: Any = json.loads(raw.decode("utf-8"))
        command = str(payload.get("tool_input", {}).get("command", ""))
    except (AttributeError, json.JSONDecodeError, TypeError, UnicodeDecodeError):
        # Fail open, matching safety_gate's own contract: a broken guard must not
        # brick the CLI, and native permission rules are the first line of defence.
        print("{}")
        return 0

    # Deny rules first. A blocked command must not also be inspected for push
    # evidence, and this ordering is what the two-hook configuration produced too
    # (safety_gate was listed first and a deny short-circuits the call).
    try:
        safety_gate = _load("safety_gate")
    except Exception:  # noqa: BLE001 - a guard that cannot load must fail open
        safety_gate = None

    if safety_gate is not None:
        for pattern, reason in safety_gate.RULES:
            if pattern.search(command):
                safety_gate.emit_denial(reason)
                return 0

    # Push evidence gate. Only reached for commands that actually look like a push,
    # which is the entire latency win: the common path never imports subprocess,
    # never shells out to git, and never touches the filesystem.
    try:
        pre_push_gate = _load("pre_push_gate")
    except Exception:  # noqa: BLE001
        print("{}")
        return 0

    if not pre_push_gate.PUSH.search(command):
        print("{}")
        return 0

    # Hand the guard its own stdin back, unmodified, and let it decide. Only the
    # `.buffer.read()` surface is used by its main(), so a namespace with a BytesIO
    # is a complete stand-in; it is deliberately not a real file object because
    # nothing here should be able to reach the actual stdin a second time.
    sys.stdin = types.SimpleNamespace(  # type: ignore[assignment]
        buffer=io.BytesIO(raw),
        read=lambda *a: raw.decode("utf-8"),
    )
    return pre_push_gate.main()


if __name__ == "__main__":
    raise SystemExit(main())
