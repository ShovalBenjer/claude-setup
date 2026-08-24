"""Prove tests/test_workspace_launcher.py can fail, by reintroducing the two defects.

A green suite is evidence only if red is reachable. Both mutations below are the
actual historical bugs, not synthetic ones:

  infer   `-Path` reads a lane back out of the directory, which is how a session
          doing harness work reported Lane C for hours.
  default no-argument runs silently pick lane C instead of prompting, which is the
          hardcoded shortcut with extra steps.

The file is restored from a byte copy and the restore is verified by hash, so a
crash mid-run cannot leave the launcher mutated. All I/O is binary on purpose:
text mode rewrote this LF file with CRLF endings, which is a silent 184-byte diff
the hash check caught and a reviewer would not have.

    python mutate_launcher_check.py
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "tools" / "workspace" / "Start-Claude.ps1"
TESTS = ROOT / "tests" / "test_workspace_launcher.py"

MUTATIONS = [
    (
        "infer: -Path resolves a lane from the directory",
        "    $lane = if ($Lane) { $Lane } else { '' }",
        "    $lane = if ($Lane) { $Lane } else { $k = ''; foreach ($n in $Lanes.Keys) "
        "{ if ($Lanes[$n].Dir -eq $dir) { $k = $n; break } }; $k }",
        "LaneIsNeverInferred",
    ),
    (
        "default: no arguments silently pick lane C",
        "} else {\n    Write-Host ''\n    Write-Host '  CLAUDE WORKSPACE'",
        "} elseif ($true) {\n    $dir = $Lanes['C'].Dir; $lane = 'C'\n} else {\n"
        "    Write-Host ''\n    Write-Host '  CLAUDE WORKSPACE'",
        "NoSilentDefault",
    ),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _pytest(node: str) -> int:
    return subprocess.run(
        [sys.executable, "-m", "pytest", f"{TESTS}::{node}", "-q"],
        cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).returncode


def main() -> int:
    original = LAUNCHER.read_bytes()
    before = _sha(LAUNCHER)
    backup = LAUNCHER.with_suffix(".ps1.mutbak")
    shutil.copy2(LAUNCHER, backup)

    rc = 0
    try:
        for name, old, new, node in MUTATIONS:
            old_b, new_b = old.encode(), new.encode()
            if old_b not in original.replace(b"\r\n", b"\n"):
                print(f"  SKIP {name}: anchor text not found, mutation is stale")
                rc = 1
                continue
            LAUNCHER.write_bytes(original.replace(b"\r\n", b"\n").replace(old_b, new_b, 1))
            caught = _pytest(node) != 0
            LAUNCHER.write_bytes(original)
            print(f"  {'CAUGHT ' if caught else 'SURVIVED'} {node:<20} {name}")
            if not caught:
                rc = 1
    finally:
        LAUNCHER.write_bytes(original)
        after = _sha(LAUNCHER)
        if after == before:
            backup.unlink(missing_ok=True)
            print(f"\n  launcher restored, sha256 unchanged {before[:12]}")
        else:
            print(f"\n  RESTORE FAILED. original preserved at {backup}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
