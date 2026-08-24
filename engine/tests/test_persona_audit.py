"""Oracle for tools/audit/persona_audit.py's check() adapter (item 2,
docs/taste.md 2026-08-24 migration).

No host-answerability trap here, unlike rules_sync.py and pointers.py:
audit() takes explicit registry/trees/live/agents paths with no CI-vs-real-
machine branching to preserve. check() is a straightforward Finding adapter
over audit()'s verdict field, verified against the same synthetic-registry
fixture shape cmd_selftest() already uses in persona_audit.py itself, so
this test's fixtures are recognizable as siblings of the tool's own oracle
rather than an independently invented shape that could silently diverge.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "audit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "lib"))
import persona_audit as PA  # noqa: E402


class CheckAdapter(unittest.TestCase):
    def _build_fixture(self, root: Path):
        reg = root / "registry.md"
        reg.write_text(
            "### Alpha Office\n\n- `writes-things`\n- `ghost-skill`\n\n"
            "### Beta Desk\n\n- `writes-things`\n\n"
            "### Gamma Lab\n\n- `reads-only`\n\n")
        repo, live = root / "repo", root / "live"
        for s in ("writes-things", "reads-only"):
            (repo / s).mkdir(parents=True)
        (live / "writes-things").mkdir(parents=True)
        (live / "reads-only").mkdir(parents=True)
        agents = root / "agents"
        agents.mkdir()
        (agents / "alpha-office.md").write_text("---\ntools: Read, Bash\n---\n")
        (agents / "beta-desk.md").write_text("---\ntools: Read, Bash, Write\n---\n")
        (agents / "gamma-lab.md").write_text("---\ntools: Read, Bash\n---\n")
        return reg, repo, live, agents

    def test_write_blocked_persona_reported_medium(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, repo, live, agents = self._build_fixture(root)
            PA.PRODUCERS.add("writes-things")
            try:
                findings = PA.check(registry=str(reg), trees=[str(repo)],
                                     live=str(live), agents=str(agents))
            finally:
                PA.PRODUCERS.discard("writes-things")
            wb = [f for f in findings if f.checker == "persona_audit.write-blocked"]
            self.assertEqual(len(wb), 1)
            self.assertEqual(wb[0].file, "Alpha Office")
            self.assertEqual(wb[0].severity, "medium")

    def test_operational_persona_not_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, repo, live, agents = self._build_fixture(root)
            PA.PRODUCERS.add("writes-things")
            try:
                findings = PA.check(registry=str(reg), trees=[str(repo)],
                                     live=str(live), agents=str(agents))
            finally:
                PA.PRODUCERS.discard("writes-things")
            names = [f.file for f in findings]
            self.assertNotIn("Beta Desk", names)
            self.assertNotIn("Gamma Lab", names)

    def test_routed_dead_persona_reported_high(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, repo, live, agents = self._build_fixture(root)
            (repo / "repo-only").mkdir()
            reg.write_text(reg.read_text() + "\n### Delta Wing\n\n- `repo-only`\n")
            PA.PRODUCERS.add("writes-things")
            try:
                findings = PA.check(registry=str(reg), trees=[str(repo)],
                                     live=str(live), agents=str(agents))
            finally:
                PA.PRODUCERS.discard("writes-things")
            dead = [f for f in findings if f.checker == "persona_audit.routed-dead"]
            self.assertEqual(len(dead), 1)
            self.assertEqual(dead[0].file, "Delta Wing")
            self.assertEqual(dead[0].severity, "high")

    def test_missing_registry_reported_as_finding_not_exception(self):
        findings = PA.check(registry="/definitely/does/not/exist.md")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].checker, "persona_audit.registry-missing")

    def test_unresolved_skill_carried_in_meta(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reg, repo, live, agents = self._build_fixture(root)
            PA.PRODUCERS.add("writes-things")
            try:
                findings = PA.check(registry=str(reg), trees=[str(repo)],
                                     live=str(live), agents=str(agents))
            finally:
                PA.PRODUCERS.discard("writes-things")
            wb = [f for f in findings if f.file == "Alpha Office"][0]
            self.assertIn("ghost-skill", wb.meta["unresolved"])


if __name__ == "__main__":
    unittest.main()
