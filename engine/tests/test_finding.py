"""Oracle for tools/lib/finding.py: the shared Finding contract every rule
checker migrated under item 2 (docs/taste.md, 2026-08-24) must return.

WHAT THIS PINS

  - severity is restricted to SEVERITIES; a checker that passes anything else
    gets a ValueError immediately, not a value that silently reaches a caller
    doing case-insensitive or fallback matching on it. panel.py's own
    validate_findings already falls back unrecognized severities to MED for
    an external judge's untrusted output; Finding is stricter on purpose,
    because a first-party checker inventing a new severity string is a bug
    in the checker, not untrusted input to be tolerated.
  - as_dict() maps onto panel.py's existing dict keys, so a checker's caller
    (cmd_run, emit_github_annotations) can consume a migrated checker's
    output with zero changes to the caller. This is what makes the migration
    additive, one checker at a time, gate green after each, instead of a
    flag-day rewrite of every caller in one commit.
  - file/line default to "" and 0 for checkers with no file locator (a
    transcript or response-text check), never a placeholder string that
    could be mistaken for a real path.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "lib"))
import finding as F  # noqa: E402


class FindingSeverity(unittest.TestCase):
    def test_recognized_severities_construct_cleanly(self):
        for sev in F.SEVERITIES:
            f = F.Finding(checker="x", severity=sev, file="a.py", line=1, why="test")
            self.assertEqual(f.severity, sev)

    def test_unrecognized_severity_raises_immediately(self):
        with self.assertRaises(ValueError):
            F.Finding(checker="x", severity="critical", file="a.py", line=1, why="test")

    def test_error_message_names_the_offending_checker(self):
        try:
            F.Finding(checker="my-checker", severity="bogus", file="a.py", line=1, why="t")
            self.fail("expected ValueError")
        except ValueError as e:
            self.assertIn("my-checker", str(e))
            self.assertIn("bogus", str(e))


class FindingTextScoped(unittest.TestCase):
    def test_file_and_line_default_for_non_file_checks(self):
        f = F.Finding(checker="discipline.calibrated-claims", severity="high",
                      file="", line=0, why="no VERIFIED/STAGED/ASSUMED tag")
        self.assertEqual(f.file, "")
        self.assertEqual(f.line, 0)


class FindingAsDict(unittest.TestCase):
    def test_as_dict_matches_panel_py_key_shape(self):
        f = F.Finding(checker="stack-lint.polars-not-pandas", severity="medium",
                      file="src/x.py", line=42, why="pandas import", snippet="import pandas as pd")
        d = f.as_dict()
        for key in ("persona", "check", "severity", "file", "line", "why", "snippet", "source"):
            self.assertIn(key, d)
        self.assertEqual(d["persona"], "stack-lint.polars-not-pandas")
        self.assertEqual(d["check"], "stack-lint.polars-not-pandas")
        self.assertEqual(d["severity"], "medium")
        self.assertEqual(d["line"], 42)

    def test_as_dict_default_source_is_local(self):
        f = F.Finding(checker="x", severity="low", file="a.py", line=1, why="t")
        self.assertEqual(f.as_dict()["source"], "local")


class FindingImmutable(unittest.TestCase):
    def test_finding_is_frozen(self):
        f = F.Finding(checker="x", severity="low", file="a.py", line=1, why="t")
        with self.assertRaises(Exception):
            f.severity = "high"  # frozen dataclass must reject mutation


if __name__ == "__main__":
    unittest.main()
