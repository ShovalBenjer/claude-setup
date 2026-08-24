#!/usr/bin/env python3
"""The A2A inbox is wired into LIVE settings.json, on the event that matters,
pointing at a file that exists, and the tool behind it is green.

Replaces C-001's original verifier, which was

    Select-String -Path $env:USERPROFILE\\.claude\\settings.json -Pattern 'bus-inbox'

Two things were wrong with that, and only one of them is about my rename.

The small one: the implementation is now `python bus.py inbox` registered
directly, with no bus-inbox.sh wrapper, so the literal string is gone. Retargeting
the pattern to 'bus.py' would have made the claim pass again while leaving the
real weakness in place.

The real one: a substring grep passes on wirings that do not work. It passes when
the hook names a file that does not exist, which is precisely the wired-missing
class tools/audit/pointers.py exists to find. It passes when the hook is wired to
SessionStart only, which means a message sent to a lane mid-session is not
delivered until that lane starts a NEW session, and "arrives eventually, maybe
tomorrow" is not what an A2A bus claims. And it passes when the tool behind the
hook is broken, which is the wired-hollow class: a registration that fails open
and reports nothing.

So this checks four things instead of one substring:

  1. some live hook registration invokes an A2A inbox
  2. the script it names exists on this filesystem
  3. it is registered on UserPromptSubmit, not SessionStart alone
  4. the tool's own selftest exits 0

Deliberately accepts EITHER shape, `bus-inbox.sh` or `bus.py inbox`. The claim is
that the capability is wired, not that it is spelled the way I happened to spell
it, and a verifier pinned to one author's implementation detail refutes on a
refactor that broke nothing. What it will not accept is a bus.py registered with
some other subcommand, or with none: `bus.py send` on UserPromptSubmit is not an
inbox.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SETTINGS = Path(os.path.expanduser("~")) / ".claude" / "settings.json"

# Delivery must happen on the operator's turn boundary. SessionStart alone leaves
# a mid-session message undelivered until the next session start.
REQUIRED_EVENT = "UserPromptSubmit"


def to_native(p: str) -> Path:
    """Normalize Git Bash /c/Users/... to C:\\Users\\... . Same dialect problem
    as hooks_exist.py: the harness is Windows and shells out to Git Bash."""
    m = re.match(r"^/([A-Za-z])/(.*)$", p)
    if m and os.name == "nt":
        return Path(f"{m.group(1).upper()}:\\{m.group(2).replace('/', os.sep)}")
    return Path(p)


def inbox_target(hook: dict) -> str | None:
    """The inbox script this registration points at, or None.

    Accepts bus-inbox.sh (the wrapper shape) and bus.py with an `inbox` argument
    (the python-direct shape). bus.py WITHOUT `inbox` is rejected: it is some
    other subcommand and does not deliver anything.
    """
    parts: list[str] = []
    cmd = hook.get("command")
    if isinstance(cmd, str):
        parts.append(cmd)
    args = hook.get("args")
    if isinstance(args, list):
        parts.extend(a for a in args if isinstance(a, str))

    joined = " ".join(parts)
    for part in parts:
        low = part.lower().replace("\\", "/")
        if low.endswith("bus-inbox.sh"):
            return part
        if low.endswith("/bus.py") or low.endswith("bus.py"):
            # The subcommand has to actually be inbox.
            if re.search(r"(^|\s)inbox(\s|$)", joined):
                return part
            return None
    return None


def main() -> int:
    if not SETTINGS.exists():
        print(f"live settings.json not found at {SETTINGS}")
        return 1
    try:
        cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"live settings.json is not valid JSON: {e}")
        return 1

    found: list[tuple[str, str]] = []  # (event, target)
    for event, groups in (cfg.get("hooks") or {}).items():
        for group in groups or []:
            for hook in group.get("hooks") or []:
                t = inbox_target(hook)
                if t:
                    found.append((event, t))

    if not found:
        print("no A2A inbox hook registered in live settings.json; "
              f"events present: {sorted((cfg.get('hooks') or {}).keys())}")
        print("the tool and its canonical wiring can both be perfect and this "
              "still refutes: nothing delivers until the LIVE config carries it")
        return 1

    problems: list[str] = []

    for event, target in found:
        if not to_native(target).exists():
            problems.append(f"{event}: registered target does not exist: {target}")

    events = {e for e, _ in found}
    if REQUIRED_EVENT not in events:
        problems.append(
            f"registered on {sorted(events)} but not {REQUIRED_EVENT}: a message "
            f"sent to a lane mid-session would not be delivered until that lane "
            f"starts a new session")

    # A green wiring around a red tool is the wired-hollow class.
    bus_py = None
    for _, target in found:
        nat = to_native(target)
        if nat.name.lower() == "bus.py":
            bus_py = nat
            break
        if nat.name.lower() == "bus-inbox.sh":
            guess = Path(os.path.expanduser("~")) / "claude-setup" / "tools" / "bus" / "bus.py"
            if guess.exists():
                bus_py = guess

    if bus_py is None:
        problems.append("cannot locate bus.py behind the wiring to run its selftest")
    else:
        r = subprocess.run([sys.executable, str(bus_py), "selftest"],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            tail = (r.stdout or "")[-800:]
            problems.append(f"bus.py selftest exits {r.returncode}, so the wiring "
                            f"is hollow:\n{tail}")

    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1

    print(f"A2A inbox wired on {sorted(events)}, target exists, selftest exits 0")
    return 0


def selftest() -> int:
    """Prove this checker discriminates, by planting configs with known answers.

    Written because the version of this check that shipped first could only ever
    report REFUTED on this machine, and a verifier that cannot pass is as useless
    as one that cannot fail: neither carries information. hooks_exist.py failed
    the other way, reporting success having examined zero hooks, and its docstring
    keeps that bug on purpose. This is the same lesson pointed the other
    direction.

    The wired-correctly case has to pass for the right reason, so it points at
    the REAL bus.py and really runs its selftest. If bus.py breaks, this fails
    here rather than silently downgrading to a weaker assertion.
    """
    global SETTINGS
    real = SETTINGS
    tmp = Path(tempfile.mkdtemp(prefix="bus-wired-selftest-"))
    bus_py = Path(__file__).resolve().parents[2] / "bus" / "bus.py"
    failures: list[str] = []

    def check(name: str, got: int, want: int, why: str) -> None:
        ok = got == want
        print(f"[{'ok' if ok else 'FAIL'}] {name}")
        if not ok:
            print(f"       expected exit {want}, got {got}: {why}")
            failures.append(name)

    def plant(cfg: dict) -> int:
        p = tmp / "settings.json"
        p.write_text(json.dumps(cfg), encoding="utf-8")
        globals()["SETTINGS"] = p
        return main()

    entry = {"type": "command", "command": "python",
             "args": [str(bus_py), "inbox"], "timeout": 10}

    try:
        if not bus_py.exists():
            print(f"cannot selftest: bus.py absent at {bus_py}")
            return 1

        print("-- cases that must REFUTE --")
        check("no hooks at all", plant({"hooks": {}}), 1,
              "an empty config must not read as wired")

        check("unrelated hooks only",
              plant({"hooks": {"Stop": [{"hooks": [
                  {"type": "command", "command": "python",
                   "args": ["C:\\x\\completion_gate.py"]}]}]}}), 1,
              "some other hook is not the bus")

        check("SessionStart only, no UserPromptSubmit",
              plant({"hooks": {"SessionStart": [{"hooks": [dict(entry)]}]}}), 1,
              "mid-session sends would wait for the next session start")

        check("bus.py wired with the wrong subcommand",
              plant({"hooks": {"UserPromptSubmit": [{"hooks": [
                  {"type": "command", "command": "python",
                   "args": [str(bus_py), "send"]}]}]}}), 1,
              "`bus.py send` delivers nothing; it is not an inbox")

        check("bus.py wired with no subcommand",
              plant({"hooks": {"UserPromptSubmit": [{"hooks": [
                  {"type": "command", "command": "python",
                   "args": [str(bus_py)]}]}]}}), 1,
              "no subcommand is not an inbox either")

        check("wired to a target that does not exist",
              plant({"hooks": {
                  "SessionStart": [{"hooks": [
                      {"type": "command", "command": "python",
                       "args": ["C:\\nope\\bus.py", "inbox"]}]}],
                  "UserPromptSubmit": [{"hooks": [
                      {"type": "command", "command": "python",
                       "args": ["C:\\nope\\bus.py", "inbox"]}]}]}}), 1,
              "this is the wired-missing class: registered, resolves to nothing")

        print("-- case that must PASS --")
        check("wired on both events, target exists, selftest green",
              plant({"hooks": {
                  "SessionStart": [{"hooks": [dict(entry)]}],
                  "UserPromptSubmit": [{"hooks": [dict(entry)]}]}}), 0,
              "the checker cannot distinguish a correct wiring, so a REFUTED "
              "verdict from it carries no information")
    finally:
        globals()["SETTINGS"] = real

    print()
    if failures:
        print(f"{len(failures)} selftest case(s) failed: {failures}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
