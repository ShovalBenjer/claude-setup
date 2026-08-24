"""Oracle for tools/audit/skills_sync.py's check() adapter (item 2, docs/taste.md
2026-08-24 migration). Heaviest of the six migrated tools: 876 lines, 9 survey
categories, and TWO distinct unmeasurable states, not one.

THE TWO TRAPS THIS FILE PINS

1. No live tree at all (CI): cmd_check() prints SKIP and returns 0 (clean). A
   naive check() built on survey() alone would either crash (survey() assumes
   both trees exist) or, worse, silently report zero findings that reads
   identically to "checked, nothing wrong" instead of "could not check".
   check() must return [] here too, matching cmd_check()'s 0-exit meaning.

2. Live tree PRESENT but foreign (is_deployed_home() false — a directory
   named ~/.claude with no settings.json beside it, the remote-container case
   measured 2026-08-10: DRIFT 87 against a contract recording 28). This is
   UNMEASURABLE, distinct from both "clean" (empty findings) and "drift found"
   (real findings) — check() must return exactly one finding saying so, not
   the raw drift numbers from comparing against a tree nobody deployed.

Real bug caught while building this file, not shipped: is_deployed_home()
reads a hardcoded live_settings() path (~/.claude/settings.json via
live_home()), which cannot be overridden by a repo_base/live_base parameter
the way survey() can. check() therefore cannot be fully host-independent for
the foreign-home branch without also monkeypatching is_deployed_home() in
tests — the real function is used directly rather than faked, so this file's
foreign-home coverage patches the module-level function, not just the paths.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "audit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "lib"))
import skills_sync as SS  # noqa: E402


def real_body(tag="x"):
    """A body long enough to classify() as 'real', not 'pointer'/'hollow'.
    classify() counts non-empty lines against POINTER_MAX_LINES=3 and
    THIN_MAX_LINES=40, so a single long repeated line (1 line regardless of
    length) misclassifies as hollow — this needs actual newlines."""
    return "\n".join("real procedure line {} for {}".format(i, tag) for i in range(50))


class CheckNoLiveTree(unittest.TestCase):
    def test_no_live_tree_returns_empty_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            SS.write_skill(str(repo), "some-skill", real_body())
            findings = SS.check(repo_base=str(repo),
                                 live_base=str(Path(td) / "nonexistent-live"))
            self.assertEqual(findings, [])


class CheckNoRepoTree(unittest.TestCase):
    def test_no_repo_tree_reported_as_finding(self):
        with tempfile.TemporaryDirectory() as td:
            findings = SS.check(repo_base=str(Path(td) / "nonexistent-repo"),
                                 live_base=str(Path(td) / "also-nonexistent"))
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].checker, "skills_sync.no-repo-tree")


class CheckForeignHome(unittest.TestCase):
    def test_foreign_home_reported_as_one_finding_not_raw_drift(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            live = Path(td) / "live"
            repo.mkdir()
            live.mkdir()
            SS.write_skill(str(repo), "a-skill", real_body("a"))
            SS.write_skill(str(live), "totally-different-skill", real_body("b"))
            with mock.patch.object(SS, "is_deployed_home", return_value=False):
                findings = SS.check(repo_base=str(repo), live_base=str(live))
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].checker, "skills_sync.foreign-home")
            self.assertEqual(findings[0].severity, "medium")


class CheckRealDrift(unittest.TestCase):
    def _fixture(self, td):
        repo = Path(td) / "repo"
        live = Path(td) / "live"
        repo.mkdir()
        live.mkdir()
        return repo, live

    def test_repo_only_skill_reported_high(self):
        with tempfile.TemporaryDirectory() as td:
            repo, live = self._fixture(td)
            SS.write_skill(str(repo), "only-in-repo", real_body())
            with mock.patch.object(SS, "is_deployed_home", return_value=True):
                findings = SS.check(repo_base=str(repo), live_base=str(live))
            names = {f.file: f.checker for f in findings}
            self.assertEqual(names.get("only-in-repo"), "skills_sync.repo-only")

    def test_live_only_skill_reported_high(self):
        with tempfile.TemporaryDirectory() as td:
            repo, live = self._fixture(td)
            SS.write_skill(str(live), "only-in-live", real_body())
            with mock.patch.object(SS, "is_deployed_home", return_value=True):
                findings = SS.check(repo_base=str(repo), live_base=str(live))
            names = {f.file: f.checker for f in findings}
            self.assertEqual(names.get("only-in-live"), "skills_sync.live-only")

    def test_drifted_skill_carries_byte_counts_in_meta(self):
        with tempfile.TemporaryDirectory() as td:
            repo, live = self._fixture(td)
            SS.write_skill(str(repo), "shared", real_body("repo-version"))
            SS.write_skill(str(live), "shared", real_body("live-version"))
            with mock.patch.object(SS, "is_deployed_home", return_value=True):
                findings = SS.check(repo_base=str(repo), live_base=str(live))
            drift = [f for f in findings if f.checker == "skills_sync.drift"]
            self.assertEqual(len(drift), 1)
            self.assertIn("repo_bytes", drift[0].meta)
            self.assertIn("live_bytes", drift[0].meta)

    def test_identical_skill_not_reported(self):
        with tempfile.TemporaryDirectory() as td:
            repo, live = self._fixture(td)
            body = real_body("identical")
            SS.write_skill(str(repo), "same-skill", body)
            SS.write_skill(str(live), "same-skill", body)
            with mock.patch.object(SS, "is_deployed_home", return_value=True):
                findings = SS.check(repo_base=str(repo), live_base=str(live))
            names = [f.file for f in findings]
            self.assertNotIn("same-skill", names)

    def test_hollow_only_reported_when_strict(self):
        with tempfile.TemporaryDirectory() as td:
            repo, live = self._fixture(td)
            SS.write_skill(str(repo), "hollow-one", "x")  # pointer-length body
            SS.write_skill(str(live), "hollow-one", "x")
            with mock.patch.object(SS, "is_deployed_home", return_value=True):
                loose = SS.check(repo_base=str(repo), live_base=str(live), strict=False)
                strict = SS.check(repo_base=str(repo), live_base=str(live), strict=True)
            self.assertEqual(loose, [])


class CheckAgainstRealRepoScan(unittest.TestCase):
    def test_check_runs_against_real_repo_without_raising(self):
        findings = SS.check()
        self.assertIsInstance(findings, list)
        for f in findings:
            self.assertIn(f.severity, ("high", "medium", "low"))


if __name__ == "__main__":
    unittest.main()
