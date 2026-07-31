"""Oracle for tools/selfimprove/scan.py's hook-health check.

The project CLAUDE.md names this scanner as how a session decides what to pick up
next, which makes a false positive here more expensive than a missing feature: it
does not merely fail to help, it actively spends a session on work that does not
exist. Measured on 2026-07-29, its three highest-ranked proposals (score 8) claimed
the SessionStart, PostToolUse and PreCompact hooks were missing while all three
existed live and one of them had run minutes earlier.

Per L017, a check with no positive test is indistinguishable from a check that can
never fire, so both directions are asserted here: a real file must NOT be reported,
and an absent one MUST be.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "tools" / "selfimprove" / "scan.py"


def _load():
    spec = importlib.util.spec_from_file_location("selfimprove_scan_under_test", SCAN_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


scan = _load()


class HookTargetResolution(unittest.TestCase):
    """The MSYS form has TWO correct answers, and which one depends on the host.

    These two cases asserted the Windows form unconditionally until 2026-07-31,
    which was right while every session started from a Windows shell. From WSL
    the same `/c/...` entry names a file at `/mnt/c/...`, and `C:/...` is not
    reachable at all, so an unconditional assertion here would force the fix to
    be wrong on one host or the other. The Windows arm is unchanged; the WSL arm
    is new. Neither is weakened: each host still gets an exact expected path.
    """

    WSL = scan._under_wsl()

    def test_an_msys_path_resolves_to_the_hosts_form(self) -> None:
        got = scan.resolve_hook_target("/c/Users/shova/.claude/hooks/session-recall.sh")
        want = ("/mnt/c/Users/shova/.claude/hooks/session-recall.sh" if self.WSL
                else "C:/Users/shova/.claude/hooks/session-recall.sh")
        self.assertEqual(got, Path(want))

    def test_the_drive_letter_case_matches_the_hosts_convention(self) -> None:
        want = "/mnt/d/tmp/x.sh" if self.WSL else "D:/tmp/x.sh"
        self.assertEqual(scan.resolve_hook_target("/d/tmp/x.sh"), Path(want))

    def test_a_windows_path_passes_through_unchanged(self) -> None:
        raw = r"C:\Users\shova\.claude\hooks\safety_gate.py"
        self.assertEqual(scan.resolve_hook_target(raw), Path(raw))

    def test_a_real_live_hook_is_not_reported_missing(self) -> None:
        """The exact regression: the live SessionStart hook, wired in MSYS form."""
        live = Path.home() / ".claude" / "hooks" / "session-recall.sh"
        if not live.is_file():
            self.skipTest("live session-recall.sh absent on this machine")
        wired = "/c/Users/shova/.claude/hooks/session-recall.sh"
        self.assertTrue(scan.resolve_hook_target(wired).exists())

    def test_an_absent_hook_is_still_detected(self) -> None:
        """The check must not be fixed by making it unable to fire."""
        with tempfile.TemporaryDirectory() as td:
            ghost = Path(td) / "not-there.sh"
            self.assertFalse(scan.resolve_hook_target(str(ghost)).exists())
        self.assertFalse(
            scan.resolve_hook_target("/c/Users/shova/.claude/hooks/no-such-hook.sh").exists()
        )

    def test_python_hooks_are_in_scope(self) -> None:
        """`.py` was missing from the suffix tuple, so python hooks were never checked."""
        self.assertIn(".py", scan.HOOK_SUFFIXES)
        self.assertIn(".sh", scan.HOOK_SUFFIXES)
        self.assertIn(".ps1", scan.HOOK_SUFFIXES)


if __name__ == "__main__":
    unittest.main()
