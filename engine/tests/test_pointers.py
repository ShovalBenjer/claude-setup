"""Oracle for tools/audit/pointers.py's check() adapter and the extracted
defer_unanswerable() helper (item 2, docs/taste.md 2026-08-24 migration).

THE TRAP THIS FILE PINS

cmd_scan() applies two host-answerability filters INLINE, not inside scan():
a pointer into the live home (~/.claude/...) is unanswerable with no live
~/.claude on this host (the CI case: 304 false findings on a GitHub runner,
per this file's own comment), and a Windows drive-path pointer is
unanswerable on a POSIX host. A naive check() built on scan() alone would
reproduce exactly that false-positive class. defer_unanswerable() extracts
both filters so they can be tested directly, with the real host state
injectable rather than depending on where these tests happen to run.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "audit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "lib"))
import pointers as P  # noqa: E402


class DeferLiveHome(unittest.TestCase):
    def test_live_pointer_kept_when_live_home_present(self):
        findings = [{"kind": "doc-ref", "severity": "low", "file": "a.md:1",
                     "target": "~/.claude/bin/work-item.sh", "note": "x"}]
        kept, live_def, win_def = P.defer_unanswerable(
            findings, live_home=True, is_windows=False)
        self.assertEqual(kept, findings)
        self.assertEqual(live_def, [])

    def test_live_pointer_deferred_when_live_home_absent(self):
        findings = [{"kind": "doc-ref", "severity": "low", "file": "a.md:1",
                     "target": "~/.claude/bin/work-item.sh", "note": "x"}]
        kept, live_def, win_def = P.defer_unanswerable(
            findings, live_home=False, is_windows=False)
        self.assertEqual(kept, [])
        self.assertEqual(len(live_def), 1)

    def test_repo_internal_pointer_never_deferred(self):
        # A pointer inside the repo tree stays blocking regardless of live home.
        findings = [{"kind": "pointer", "severity": "medium", "file": "b.md",
                     "target": "payload/dot-claude/skills/x/SKILL.md", "note": "x"}]
        kept, live_def, win_def = P.defer_unanswerable(
            findings, live_home=False, is_windows=False)
        self.assertEqual(kept, findings)
        self.assertEqual(live_def, [])

    def test_absolute_home_prefix_also_deferred_not_only_tilde(self):
        # PR #37 residual red: /home/shov/.claude/... must defer the same as ~/.claude/...
        import os
        prefix = os.path.expanduser("~") + os.sep
        findings = [{"kind": "doc-ref", "severity": "low", "file": "a.md:1",
                     "target": prefix + ".claude/bin/work-item.sh", "note": "x"}]
        kept, live_def, win_def = P.defer_unanswerable(
            findings, live_home=False, is_windows=False)
        self.assertEqual(kept, [])
        self.assertEqual(len(live_def), 1)


class DeferWindows(unittest.TestCase):
    def test_windows_drive_path_kept_on_windows(self):
        findings = [{"kind": "wired-missing", "severity": "high", "file": "settings.json",
                     "target": r"C:\Program Files\Git\bin\bash.exe", "note": "x"}]
        kept, live_def, win_def = P.defer_unanswerable(
            findings, live_home=True, is_windows=True)
        self.assertEqual(kept, findings)
        self.assertEqual(win_def, [])

    def test_windows_drive_path_deferred_on_posix(self):
        findings = [{"kind": "wired-missing", "severity": "high", "file": "settings.json",
                     "target": r"C:\Program Files\Git\bin\bash.exe", "note": "x"}]
        kept, live_def, win_def = P.defer_unanswerable(
            findings, live_home=True, is_windows=False)
        self.assertEqual(kept, [])
        self.assertEqual(len(win_def), 1)

    def test_both_filters_compose(self):
        findings = [
            {"kind": "doc-ref", "severity": "low", "file": "a.md:1",
             "target": "~/.claude/x", "note": "x"},
            {"kind": "wired-missing", "severity": "high", "file": "settings.json",
             "target": r"C:\x.exe", "note": "x"},
            {"kind": "pointer", "severity": "medium", "file": "b.md",
             "target": "payload/dot-claude/skills/x/SKILL.md", "note": "x"},
        ]
        kept, live_def, win_def = P.defer_unanswerable(
            findings, live_home=False, is_windows=False)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["kind"], "pointer")
        self.assertEqual(len(live_def), 1)
        self.assertEqual(len(win_def), 1)


class CheckAdapter(unittest.TestCase):
    def test_check_returns_finding_list(self):
        findings = P.check()
        self.assertIsInstance(findings, list)
        for f in findings:
            self.assertIn(f.severity, ("high", "medium", "low"))
            self.assertTrue(f.checker.startswith("pointers."))

    def test_check_carries_target_in_meta(self):
        findings = P.check()
        for f in findings:
            self.assertIn("target", f.meta)


if __name__ == "__main__":
    unittest.main()
