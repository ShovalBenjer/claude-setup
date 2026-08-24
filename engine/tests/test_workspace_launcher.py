"""Oracle for tools/workspace/: the launcher must not answer the lane question for you.

THE DEFECT

`Claude new-recruit (Admin).lnk`, pinned to the taskbar, ran

    wt.exe -d "C:\\Users\\shova\\Downloads\\new-recruit" pwsh -NoExit -Command claude

so every session started in one repo with CLAUDE_LANE unset. docs/charters.md
assigns a lane per working directory, so sessions doing pure harness work reported
Lane C because a shortcut chose their cwd. The 2026-07-27 fix was two-part: a
chooser (Start-Claude.ps1) and a pin that opens it (repoint_taskbar_pin.ps1).

WHAT THESE CHECKS PIN, AND WHY EACH ONE CAN FAIL

  - A declared lane resolves to that lane's directory, and the four lanes are not
    all the same directory. A launcher that collapses back to one repo is the
    original defect wearing a menu.
  - `-Path` NEVER infers a lane, not even when the path IS a lane's directory.
    Inference is what produced the wrong answer in the first place; an unknown
    lane is recoverable, a confidently wrong one is not. (The interactive project
    picker does map a known directory back to its lane. That is a different
    input: the operator chose from a list of lanes, rather than the script
    guessing from a path some launcher set.)
  - With no arguments the script prompts instead of defaulting. A default is how
    a chooser silently becomes a hardcoded shortcut again.
  - A missing directory exits nonzero rather than launching somewhere else.
  - The live taskbar pin does not still carry the old hardcoded form. This is the
    check that would have caught the real gap: the chooser and the lane shortcuts
    both existed and worked for ~11 hours while every actual session still opened
    through the old pin, because the fix was installed next to the habit instead
    of inside it. Skipped where the pin does not exist.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools" / "workspace" / "Start-Claude.ps1"
PWSH = shutil.which("pwsh")

HOME = Path(os.environ.get("USERPROFILE") or Path.home())
PIN = (HOME / "AppData" / "Roaming" / "Microsoft" / "Internet Explorer"
       / "Quick Launch" / "User Pinned" / "TaskBar"
       / "Claude new-recruit (Admin).lnk")

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _run(*args: str, stdin: str | None = None) -> tuple[int, str]:
    """Drive the launcher in -NoLaunch mode. It must never start claude here."""
    p = subprocess.run(
        [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(LAUNCHER),
         *args, "-NoLaunch"],
        input=stdin, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120,
    )
    return p.returncode, _ANSI.sub("", (p.stdout or "") + (p.stderr or ""))


def _resolved(out: str) -> tuple[str | None, str | None]:
    """The two lines the script prints once it has decided: cwd and lane."""
    cwd = lane = None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("cwd "):
            cwd = s[4:].strip()
        elif s.startswith("lane "):
            rest = s[5:].strip()
            lane = None if rest.startswith("UNDECLARED") else rest.split()[0]
    return cwd, lane


@unittest.skipIf(PWSH is None, "pwsh not installed")
class LaneResolution(unittest.TestCase):
    def test_declared_lane_resolves_to_that_lane(self):
        for letter in ("B", "C", "D", "E"):
            with self.subTest(lane=letter):
                rc, out = _run("-Lane", letter)
                cwd, lane = _resolved(out)
                if cwd is None and "missing directory" in out:
                    self.skipTest(f"lane {letter} directory absent on this machine")
                self.assertEqual(rc, 0, out)
                self.assertEqual(lane, letter, out)
                self.assertIsNotNone(cwd, out)
                self.assertTrue(Path(cwd).is_dir(), f"lane {letter} cwd missing: {cwd}")

    def test_retired_lane_a_is_rejected(self):
        """Lane A was retired 2026-07-29 (operator decision, docs/charters.md).
        ValidateSet must refuse it, or the retirement is prose."""
        rc, out = _run("-Lane", "A")
        self.assertNotEqual(rc, 0, out)

    def test_lanes_are_not_one_directory(self):
        """B is the harness repo and C is the resume engine. If a change ever made
        every lane resolve to the same place, the menu would be decoration."""
        _, out_b = _run("-Lane", "B")
        _, out_c = _run("-Lane", "C")
        cwd_b, _ = _resolved(out_b)
        cwd_c, _ = _resolved(out_c)
        if cwd_b is None or cwd_c is None:
            self.skipTest("lane B or C directory absent on this machine")
        self.assertNotEqual(Path(cwd_b), Path(cwd_c))


@unittest.skipIf(PWSH is None, "pwsh not installed")
class LaneIsNeverInferred(unittest.TestCase):
    def test_path_without_lane_is_undeclared(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = _run("-Path", tmp)
            cwd, lane = _resolved(out)
            self.assertEqual(rc, 0, out)
            self.assertEqual(Path(cwd), Path(tmp).resolve())
            self.assertIsNone(lane, "an arbitrary path must not acquire a lane")

    def test_path_at_a_lane_directory_is_still_undeclared(self):
        """The regression that started all of this: cwd equal to a lane's repo is
        not evidence the session is doing that lane's work."""
        _, out = _run("-Lane", "C")
        lane_c_dir, _ = _resolved(out)
        if lane_c_dir is None:
            self.skipTest("lane C directory absent on this machine")
        rc, out = _run("-Path", lane_c_dir)
        cwd, lane = _resolved(out)
        self.assertEqual(rc, 0, out)
        self.assertEqual(Path(cwd), Path(lane_c_dir))
        self.assertIsNone(lane, "a path must never be read back as a lane")


@unittest.skipIf(PWSH is None, "pwsh not installed")
class NoSilentDefault(unittest.TestCase):
    def test_no_arguments_prompts_and_resolves_nothing(self):
        rc, out = _run(stdin="q\n")
        self.assertEqual(rc, 0, out)
        for expected in ("CLAUDE WORKSPACE", "global", "project", "new"):
            self.assertIn(expected, out)
        cwd, lane = _resolved(out)
        self.assertIsNone(cwd, "quitting the menu must not resolve a workspace")
        self.assertIsNone(lane)

    def test_missing_directory_fails_loudly(self):
        rc, out = _run("-Path", str(HOME / "no-such-directory-a7f3c1"))
        self.assertNotEqual(rc, 0, out)
        cwd, _ = _resolved(out)
        self.assertIsNone(cwd)


class TaskbarPin(unittest.TestCase):
    @unittest.skipUnless(PIN.exists(), "taskbar pin not present on this machine")
    def test_pin_opens_the_chooser_not_a_hardcoded_repo(self):
        raw = PIN.read_bytes().decode("utf-16-le", errors="ignore") + \
            PIN.read_bytes().decode("latin-1", errors="ignore")
        self.assertIn("Start-Claude.ps1", raw,
                      "the pinned shortcut does not launch the chooser")
        self.assertNotIn('-Command claude', raw,
                         "the pin still runs claude directly with a fixed -d")


if __name__ == "__main__":
    unittest.main()
