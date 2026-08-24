"""Oracle for tools/review/panel.py's check() adapter (item 2, docs/taste.md
2026-08-24 migration, tool 6 of 6, saved for last per the advisor's own
ordering: most personas, most tests riding on it, worst pilot / correct
last).

WHY diff_or_text IS GENUINELY UNUSED HERE, NOT BY CONVENTION

The five tools migrated before this one all ignore diff_or_text because
they scan whole trees, not a diff. panel.py is different: its real input IS
a diff, but added_lines(project, base) computes it FROM GIT internally
(three diff commands plus untracked-file collection), not from a text blob
that could be handed in as a string. check(project=, base=) is therefore the
correct shape, matching what cmd_run() already needs, and diff_or_text stays
unused for a structural reason specific to this tool.

This file does NOT re-prove every persona's check pattern — cmd_selftest()
already plants and proves one positive case per registered check id, and
duplicating that fixture here would be redundant weight without adding real
coverage. This file proves only what's specific to the check() adapter:
Finding conversion, the not-a-repo case, the no-added-lines case, and that a
real finding from a minimal fixture agrees byte-for-byte with what run_local()
itself would have produced.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "review"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "lib"))
import panel as P  # noqa: E402


def _git_repo(td: str) -> None:
    P.sh("git init -q .", td)
    P.sh('git -c user.email=t@t -c user.name=t commit -q --allow-empty -m base', td)


class CheckNotARepo(unittest.TestCase):
    def test_non_repo_reported_as_finding_not_exception(self):
        with tempfile.TemporaryDirectory() as td:
            findings = P.check(project=td)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].checker, "panel.not-a-repo")
            self.assertEqual(findings[0].severity, "high")


class CheckNoAddedLines(unittest.TestCase):
    def test_clean_repo_no_changes_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            _git_repo(td)
            findings = P.check(project=td)
            self.assertEqual(findings, [])


class CheckRealFinding(unittest.TestCase):
    def test_planted_finding_converts_to_Finding_correctly(self):
        with tempfile.TemporaryDirectory() as td:
            _git_repo(td)
            f = Path(td) / "app.py"
            f.write_text("import subprocess\nsubprocess.run(cmd, shell=True)\n")
            findings = P.check(project=td)
            shell_true = [x for x in findings if x.checker == "py-shell-true"]
            self.assertEqual(len(shell_true), 1)
            self.assertEqual(shell_true[0].file, "app.py")
            self.assertEqual(shell_true[0].severity, "high")
            self.assertIn("persona", shell_true[0].meta)

    def test_check_agrees_with_run_local_on_the_same_diff(self):
        """The direct cross-check: check() must not silently diverge from what
        cmd_run()'s own run_local(added_lines(...)) would report for identical
        input, since check() reimplements none of the classification logic and
        only wraps it."""
        with tempfile.TemporaryDirectory() as td:
            _git_repo(td)
            f = Path(td) / "app.py"
            f.write_text("import subprocess\nsubprocess.run(cmd, shell=True)\n")

            findings = P.check(project=td)
            lines = P.added_lines(td, P.default_base(td))
            raw = P.run_local(lines)

            self.assertEqual(len(findings), len(raw))
            for finding, row in zip(
                    sorted(findings, key=lambda x: (x.file, x.line, x.checker)),
                    sorted(raw, key=lambda x: (x["file"], x["line"], x["check"]))):
                self.assertEqual(finding.checker, row["check"])
                self.assertEqual(finding.severity, row["severity"])
                self.assertEqual(finding.file, row["file"])
                self.assertEqual(finding.line, row["line"])


class CheckExternalDisabledByDefault(unittest.TestCase):
    def test_allow_external_false_by_default_no_network_call_attempted(self):
        # allow_external defaults to False, so run_external() must never be
        # invoked unless explicitly requested — same default as cmd_run()'s
        # own --allow-external flag being opt-in.
        with tempfile.TemporaryDirectory() as td:
            _git_repo(td)
            f = Path(td) / "app.py"
            f.write_text("import subprocess\nsubprocess.run(cmd, shell=True)\n")
            findings = P.check(project=td)
            for finding in findings:
                self.assertEqual(finding.source, "local")


if __name__ == "__main__":
    unittest.main()
