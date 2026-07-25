#!/usr/bin/env python3
"""Every other checker FAILS when its inputs are absent (no fail-open verifiers).

A mutation test on the verification layer itself. It is the direct answer to the
worst bug this engine has produced so far: hooks_exist.py examined zero hooks and
returned 0. Green, having verified nothing. That is strictly worse than having no
checker, because it converts an unknown into a false assurance, and nothing in the
output hints that anything was skipped.

Method: run each sibling checker in a subprocess with HOME and USERPROFILE pointed
at an empty temporary directory, so every file it wants to read is missing. A
correct checker must exit nonzero. A checker that exits 0 with no inputs is
fail-open, and its green result carries no information.

This does not prove a checker is correct. It proves it is not vacuous, which is
the specific failure mode that already bit us.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKS_DIR = Path(__file__).resolve().parent
SELF = Path(__file__).resolve().name
TIMEOUT = 30


def main() -> int:
    peers = sorted(
        p for p in CHECKS_DIR.glob("*.py")
        if p.name != SELF and not p.name.startswith("_")
    )
    if not peers:
        print(f"found no sibling checkers in {CHECKS_DIR}; treat as UNKNOWN not pass")
        return 1

    fail_open: list[str] = []
    tested = 0

    with tempfile.TemporaryDirectory(prefix="refute-emptyhome-") as tmp:
        for peer in peers:
            env = dict(os.environ)
            env["HOME"] = tmp
            env["USERPROFILE"] = tmp
            env.pop("HOMEDRIVE", None)
            env.pop("HOMEPATH", None)

            try:
                p = subprocess.run(
                    [sys.executable, str(peer)],
                    capture_output=True, text=True, timeout=TIMEOUT,
                    env=env, cwd=str(CHECKS_DIR.parents[2]), errors="replace",
                )
            except subprocess.TimeoutExpired:
                fail_open.append(f"{peer.name}: timed out with empty inputs")
                continue

            tested += 1
            if p.returncode == 0:
                first = next((ln.strip() for ln in (p.stdout or "").splitlines()
                              if ln.strip()), "(no output)")
                fail_open.append(
                    f"{peer.name}: exited 0 with every input missing -> "
                    f"fail-open. Said: {first[:120]}")

    if tested == 0:
        print("ran zero checkers; treat as UNKNOWN not pass")
        return 1

    if fail_open:
        print(f"{len(fail_open)} of {tested} checkers pass without inspecting anything:")
        for f in fail_open:
            print(f"  {f}")
        return 1

    print(f"all {tested} sibling checkers fail closed when their inputs are absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
