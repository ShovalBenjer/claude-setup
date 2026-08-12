#!/usr/bin/env python3
"""Every hook registered in live settings.json resolves to a file that exists.

Checker for the failure observed 2026-07-25: a PreToolUse hook was registered,
the target file was present and readable by PowerShell, and yet the hook errored
on every Bash call with "No such file or directory". A registration that does not
resolve is a hook that silently does nothing, and Claude Code does not say which.

HISTORY OF THIS FILE'S OWN BUG (kept deliberately, it is the point):
the first version read only hook["command"] and regex-hunted a script path in it.
The live settings use the two-field shape

    {"command": "python", "args": ["C:\\Users\\shova\\.claude\\hooks\\x.py"]}
    {"command": "C:\\Program Files\\Git\\bin\\bash.exe", "args": ["/c/Users/.../x.sh"]}

so "python" and "bash.exe" contained no script path, every hook was skipped, and
the checker reported success having examined ZERO hooks. A verifier that passes
without checking anything is worse than no verifier: it converts an unknown into
a false green. Hence the explicit "checked 0 hooks" failure below.

Two path dialects must both resolve, because the harness is Windows but shells
out to Git Bash: native C:\\Users\\... and POSIX /c/Users/....

SECOND BUG IN THIS FILE, found 2026-08-03 and fixed here. The rules above gated a
target on its FILE EXTENSION, so the live PreToolUse entry

    {"command": "/home/shov/claude-setup/tools/hookgate/target/release/hookgate"}

reported "no script path found" and C-003 read REFUTED, while the binary was on
disk at 2,131,576 bytes and perfectly runnable. A hook target does not have to be
a script: hookgate is compiled Rust and has no extension at all. The property this
file exists to protect is that a registered hook RESOLVES, not that it is spelled
like a script, so an extensionless absolute path is now a target in its own right.
That is the L-2026-07-31-b class, a gate checking the ruled form instead of the
property, and it is the second instance in three days.

The same edit fixes a Linux blind spot of the same origin: PATH_RE only accepted
C:\\... and the Git Bash /c/... dialect, so a plain POSIX /home/... path embedded
in a longer command string was invisible on this host. That is L-2026-07-31-g, a
host-shaped default that answers the wrong question on the other machine.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SETTINGS = Path(os.path.expanduser("~")) / ".claude" / "settings.json"

SCRIPT_EXT = (".py", ".sh", ".ps1", ".js", ".mjs", ".cmd", ".bat")
# A token that looks like a filesystem path: Windows native, Git Bash /c/..., or
# a plain POSIX absolute path. The last alternative is what this host actually
# uses and what the pre-2026-08-03 pattern could not see.
PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|/)[^\"';|\s]+")


def is_path_shaped(part: str) -> bool:
    """True if this token is an absolute path in any dialect we accept.

    Deliberately NOT extension-gated. An interpreter name like `python` or `node`
    is not path-shaped and stays excluded, which is what keeps the two-field
    {"command": "python", "args": [script]} case resolving against the script
    rather than against the interpreter.
    """
    return part.startswith("/") or bool(re.match(r"^[A-Za-z]:[\\/]", part))


def to_native(p: str) -> Path:
    """Normalize a Git Bash /c/Users/... path to C:\\Users\\... on Windows."""
    m = re.match(r"^/([A-Za-z])/(.*)$", p)
    if m and os.name == "nt":
        return Path(f"{m.group(1).upper()}:\\{m.group(2).replace('/', os.sep)}")
    return Path(p)


def script_targets(hook: dict) -> list[str]:
    """Every script-looking path this hook registration points at.

    Handles both shapes: the script inline in `command`, and the interpreter in
    `command` with the script in `args` (which is what the live config uses).
    """
    out: list[str] = []
    parts: list[str] = []

    cmd = hook.get("command")
    if isinstance(cmd, str):
        parts.append(cmd)
    args = hook.get("args")
    if isinstance(args, list):
        parts.extend(a for a in args if isinstance(a, str))

    for part in parts:
        # A bare token that is already an absolute path. Covers both the script
        # args entries and a compiled binary given directly as `command`, which
        # has no extension to match on.
        if is_path_shaped(part):
            out.append(part)
            continue
        # A path embedded in a longer command string, e.g. `python /x/y.py --flag`.
        # Here the extension IS the right filter: inside a shell string it is what
        # separates the target from its arguments.
        for m in PATH_RE.findall(part):
            tok = m.strip()
            if tok.lower().endswith(SCRIPT_EXT):
                out.append(tok)
    return out


def main() -> int:
    if not SETTINGS.exists():
        print(f"settings.json not found at {SETTINGS}")
        return 1

    try:
        cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"settings.json is not valid JSON: {e}")
        return 1

    missing: list[str] = []
    registrations = 0
    checked = 0

    for event, groups in (cfg.get("hooks") or {}).items():
        for group in groups or []:
            for hook in group.get("hooks") or []:
                registrations += 1
                targets = script_targets(hook)
                if not targets:
                    # An interpreter with no script arg is a real defect too.
                    missing.append(f"{event}: no resolvable target found in {hook.get('command')!r}")
                    continue
                for t in targets:
                    checked += 1
                    if not to_native(t).exists():
                        missing.append(f"{event}: {t}")

    if registrations == 0:
        print("no hooks registered at all in settings.json")
        return 1
    if checked == 0:
        print(f"checked 0 targets across {registrations} registrations: "
              f"the parser is not seeing this config shape, treat as UNKNOWN not pass")
        return 1

    if missing:
        print(f"{len(missing)} problem(s) across {registrations} registrations "
              f"({checked} targets resolved):")
        for m in missing:
            print(f"  {m}")
        return 1

    print(f"{checked} hook targets across {registrations} registrations all resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
