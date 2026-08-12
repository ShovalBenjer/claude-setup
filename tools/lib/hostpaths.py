#!/usr/bin/env python3
"""Resolve a path written for one host while running on the other.

This repository is authored on Windows and also run from WSL, and the two see the
same files through different names. `dot-claude/` is the committed copy of a Windows
`~/.claude`, so its absolute paths are CORRECT for the machine it deploys to and
meaningless to a Linux `os.path.exists`. A checker that resolves them against the
Linux filesystem is asking the wrong question rather than finding an answer.

Three tools got that wrong on 2026-07-31, in one repository, in one morning:

  - `tools/selfimprove/scan.py` called every bash hook missing, because Git Bash
    writes `/c/Users/...` and that is a RELATIVE path on Linux. Its three
    highest-ranked proposals were phantom.
  - `tools/refute/refute.py` reported 26 of 26 verifiers broken; two of them also
    verified the wrong clone.
  - `tools/audit/pointers.py` reported 12 HIGH wired-missing hooks in
    `dot-claude/settings.json`. All twelve files exist under `/mnt/c`.

The third is the most damaging, because a missing hook is a real and common defect,
so twelve of them is believable, `pointers scan` exits FAIL on it, and the genuinely
dead pointers in the same report are buried underneath.

THE SAFETY PROPERTY, and it is the reason `mounts` is a parameter rather than a
constant: translation happens only where a drive is ACTUALLY MOUNTED. On bare Linux
with no `/mnt/c`, `C:\\Users\\x` is genuinely unreachable and stays unreachable. A
translator that rewrites unconditionally is a machine for making absent paths look
present, which is a worse failure than the one it replaces: this repo's whole
verification stance is that a checker must be able to say no.

Deliberately not a path-manipulation library. Two spellings in, one question
answered, and `exists()` is the only thing callers should need.

Scope this does NOT cover, stated so nobody reads more into it: UNC paths other
than \\wsl.localhost\<distro> and \\wsl$\<distro> (added 2026-08-12 with a failing
test, when the live Notification hook's notify-toast.ps1 appeared through that
spelling), drive letters mapped to network shares, `%USERPROFILE%` and `$env:`
expansion, and the reverse direction (Linux paths read from Windows). None has
appeared in this repo's traffic; add them with a failing test when one does.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

#: `C:\x`, `c:/x`. The separator after the colon may be either slash.
_DRIVE = re.compile(r"^([A-Za-z]):[\\/](.*)$", re.S)

#: `/c/x`, the MSYS form Git Bash writes. Exactly ONE letter between the slashes:
#: `/home/...` and `/cc/...` must not match, and a bare `/c` is a real Linux path.
_MSYS = re.compile(r"^/([A-Za-z])/(.+)$")


def wsl_mounts(root: str = "/mnt") -> dict[str, Path]:
    """Drive letters that are actually reachable, lowercased.

    Reads the filesystem rather than trusting `/proc/version`, because "this kernel
    says microsoft" and "the C drive is mounted" are different facts, and only the
    second one licenses a translation.
    """
    base = Path(root)
    if os.name == "nt" or not base.is_dir():
        return {}
    out = {}
    try:
        for entry in base.iterdir():
            if len(entry.name) == 1 and entry.name.isalpha() and entry.is_dir():
                out[entry.name.lower()] = entry
    except OSError:
        return {}
    return out


_UNC_WSL = re.compile(r"^\\\\wsl(?:\.localhost|\$)\\([^\\]+)\\(.*)$")
_ENV_SENTINEL = object()


def translate(raw: str, mounts: dict[str, Path] | None = None,
              distro: object = _ENV_SENTINEL) -> Path:
    """The path as this host can reach it, or unchanged when it cannot.

    Unchanged is the honest answer for an unmounted drive; see the module docstring.
    A \\\\wsl.localhost\\<distro>\\ UNC name (or the legacy \\\\wsl$\\ spelling) is
    this filesystem's own root, but only when we ARE that distro: the same
    only-where-mounted safety property, with WSL_DISTRO_NAME as the mount witness.
    """
    m = _UNC_WSL.match(raw)
    if m:
        here = os.environ.get("WSL_DISTRO_NAME") if distro is _ENV_SENTINEL else distro
        if here == m.group(1):
            return Path("/" + m.group(2).replace("\\", "/"))
        return Path(raw)
    if mounts is None:
        mounts = wsl_mounts()
    if not mounts:
        return Path(raw)

    m = _DRIVE.match(raw)
    if m:
        drive, rest = m.group(1).lower(), m.group(2)
        mount = mounts.get(drive)
        # Only the separators are rewritten. Splitting on whitespace would lose
        # `C:\Program Files\Git\bin\bash.exe`, which is one of the twelve.
        return mount / rest.replace("\\", "/") if mount else Path(raw)

    m = _MSYS.match(raw)
    if m:
        drive, rest = m.group(1).lower(), m.group(2)
        mount = mounts.get(drive)
        if mount:
            return mount / rest
    return Path(raw)


def exists(raw: str, mounts: dict[str, Path] | None = None) -> bool:
    """Is the file there, asked in whichever name space can answer."""
    try:
        return translate(raw, mounts).exists()
    except OSError:
        return False


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print("%-6s %s -> %s" % ("ok" if exists(arg) else "ABSENT", arg, translate(arg)))
