"""Oracle for tools/map/codemap.py: the directory map has to be generated.

The instruction was "every dir mapped and documented". This repository has 351
tracked directories and 19 READMEs, so a hand-written map is a document that is
wrong the week after it is written. The rule these checks pin is therefore not
"a map exists" but "the map on disk equals the map the repository implies, and
no directory is without a stated purpose".

Two failure modes get their own checks because both have already happened here:

  - A purpose string copied into a registry when the directory already carries a
    SKILL.md description is a second source of truth, and the copy is the one
    that goes stale. `check` rejects a registry row that merely repeats the file.
  - A generated file whose own content feeds the next generation never settles.
    quality-contract.json embedded its measured status in comments and was wrong
    in four domains within days; a map that counted itself would flip from clean
    to drifted the moment it was committed. test_map_survives_its_own_commit
    fails on that specific mistake.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEMAP_PATH = ROOT / "tools" / "map" / "codemap.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("codemap_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


codemap = _load(CODEMAP_PATH)


def _git(cwd: Path, *args: str) -> str:
    p = subprocess.run(("git",) + args, cwd=str(cwd), check=True,
                       capture_output=True, text=True, encoding="utf-8")
    return p.stdout


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def _cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CODEMAP_PATH), *args, "--project", str(root)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


class MapCase(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "oracle@test")
        _git(self.root, "config", "user.name", "oracle")
        _write(self.root, "README.md", "# root\n\nThe repository under test.\n")

    def tearDown(self) -> None:
        self._td.cleanup()

    def commit(self, message: str = "c") -> None:
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", message)

    def registry(self, *lines: str) -> None:
        _write(self.root, "docs/dir-purpose.txt", "\n".join(lines) + "\n")

    def purposes(self) -> dict:
        return {d.path: d for d in codemap.inventory(str(self.root))}


class TestPurposeResolution(MapCase):
    def test_skill_frontmatter_description_is_the_purpose(self):
        # The folded scalar is how all 151 SKILL.md files in this repo are
        # written, so a resolver that only handles `description: one line` would
        # resolve almost nothing.
        _write(self.root, "skills/ship-gate/SKILL.md",
               "---\nname: ship-gate\ndescription: >-\n"
               "  The mandatory procedure before calling any\n"
               "  implementation done.\n---\n\n# Ship gate\n")
        self.commit()
        got = self.purposes()["skills/ship-gate"]
        self.assertEqual(got.source, "SKILL.md")
        self.assertEqual(got.purpose,
                         "The mandatory procedure before calling any implementation done.")

    def test_plain_frontmatter_description_is_the_purpose(self):
        _write(self.root, "skills/plain/SKILL.md",
               "---\nname: plain\ndescription: Does one thing.\n---\n\nbody\n")
        self.commit()
        self.assertEqual(self.purposes()["skills/plain"].purpose, "Does one thing.")

    def test_readme_first_prose_line_is_the_purpose(self):
        _write(self.root, "tools/bus/README.md",
               "# bus\n\n<!-- generated -->\n\nAppends events to the ledger.\n\nMore prose.\n")
        _write(self.root, "tools/bus/bus.py", "x = 1\n")
        self.commit()
        got = self.purposes()["tools/bus"]
        self.assertEqual(got.source, "README.md")
        self.assertEqual(got.purpose, "Appends events to the ledger.")

    def test_skill_wins_over_readme_when_both_exist(self):
        _write(self.root, "both/SKILL.md",
               "---\nname: both\ndescription: From the skill.\n---\n")
        _write(self.root, "both/README.md", "# both\n\nFrom the readme.\n")
        self.commit()
        got = self.purposes()["both"]
        self.assertEqual((got.source, got.purpose), ("SKILL.md", "From the skill."))

    def test_agents_md_is_a_fallback(self):
        _write(self.root, "dot-agents/AGENTS.md", "# agents\n\nWhat the codex tree carries.\n")
        self.commit()
        got = self.purposes()["dot-agents"]
        self.assertEqual((got.source, got.purpose), ("AGENTS.md", "What the codex tree carries."))

    def test_registry_row_documents_a_dir_that_has_no_file(self):
        _write(self.root, "tools/lib/envload.py", "x = 1\n")
        self.registry("tools/lib | Shared helpers imported by the other tools.")
        self.commit()
        got = self.purposes()["tools/lib"]
        self.assertEqual(got.source, "registry")
        self.assertEqual(got.purpose, "Shared helpers imported by the other tools.")

    def test_a_dir_with_nothing_resolves_to_undocumented(self):
        _write(self.root, "tools/orphan/thing.py", "x = 1\n")
        self.commit()
        self.assertEqual(self.purposes()["tools/orphan"].source, "none")
        self.assertEqual(self.purposes()["tools/orphan"].purpose, codemap.UNDOCUMENTED)

    def test_purpose_is_one_line_with_table_characters_escaped(self):
        # A pipe in a purpose string would otherwise split the row into extra
        # columns and the rendered map would be silently wrong.
        _write(self.root, "piped/SKILL.md",
               "---\nname: piped\ndescription: Reads a | b and reports.\n---\n")
        self.commit()
        self.assertEqual(self.purposes()["piped"].purpose, "Reads a | b and reports.")
        _cli(self.root, "write")
        row = [l for l in (self.root / "docs" / "CODEBASE-MAP.md").read_text(
            encoding="utf-8").splitlines() if l.startswith("| `piped`")][0]
        self.assertEqual(row.count("|"), 5, "escaped pipe leaked an extra column: " + row)

    def test_a_non_ascii_directory_name_is_read_as_itself(self):
        # git ls-files C-quotes any path outside ASCII, so a Hebrew directory
        # comes back as "\327\236..." wrapped in literal double quotes. Taken at
        # face value that is a directory whose name begins with a quote
        # character: it matches no row, can never be documented, and asking for a
        # registry row for it writes the quoting bug down as a fact. Measured on
        # the real repository: 5 of 194 undocumented directories were this.
        name = "מסמכים"
        _write(self.root, name + "/note.md", "hebrew\n")
        self.registry("docs | fixture documentation",
                      name + " | A directory named in Hebrew.")
        self.commit()
        got = self.purposes()
        self.assertIn(name, got, "quoted path leaked instead of the real name: "
                      + repr(sorted(k for k in got if k not in ("docs",))))
        self.assertEqual(got[name].purpose, "A directory named in Hebrew.")
        for k in got:
            self.assertFalse(k.startswith('"'), "a C-quoted path became a directory: " + k)
        _cli(self.root, "write")
        self.commit()
        r = _cli(self.root, "check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_untracked_directories_are_not_in_the_map(self):
        _write(self.root, "kept/f.py", "x = 1\n")
        self.commit()
        _write(self.root, "scratch/f.py", "x = 1\n")
        got = self.purposes()
        self.assertIn("kept", got)
        self.assertNotIn("scratch", got, "an uncommitted directory is not part of the repository")


class TestCheck(MapCase):
    def test_check_names_every_undocumented_dir_and_exits_nonzero(self):
        _write(self.root, "tools/a/x.py", "x = 1\n")
        _write(self.root, "tools/b/y.py", "y = 1\n")
        self.registry("tools | The tool tree.")
        self.commit()
        r = _cli(self.root, "check")
        self.assertNotEqual(r.returncode, 0, "undocumented directories passed the check")
        self.assertIn("tools/a", r.stdout + r.stderr)
        self.assertIn("tools/b", r.stdout + r.stderr)

    def test_check_passes_once_every_dir_resolves(self):
        _write(self.root, "tools/a/x.py", "x = 1\n")
        self.registry("tools | The tool tree.", "tools/a | Does a.", "docs | Documentation.")
        self.commit()
        _cli(self.root, "write")
        self.commit("map")
        r = _cli(self.root, "check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_registry_row_for_a_path_that_is_gone_fails(self):
        # Rot in the other direction: the row outlives the directory and the map
        # keeps asserting a purpose for something nobody can open.
        _write(self.root, "tools/a/x.py", "x = 1\n")
        self.registry("tools | The tool tree.", "tools/a | Does a.",
                      "docs | Documentation.", "tools/deleted | Did something once.")
        self.commit()
        _cli(self.root, "write")
        self.commit("map")
        r = _cli(self.root, "check")
        self.assertNotEqual(r.returncode, 0, "a registry row with no directory passed")
        self.assertIn("tools/deleted", r.stdout + r.stderr)

    def test_a_registry_row_that_repeats_the_dirs_own_file_fails(self):
        # The design rule, made executable: the directory's own SKILL.md is the
        # source of truth, so a row restating it is a copy that will drift.
        _write(self.root, "skills/dup/SKILL.md",
               "---\nname: dup\ndescription: Says one thing.\n---\n")
        self.registry("skills | Skill tree.", "docs | Documentation.",
                      "skills/dup | Says one thing.")
        self.commit()
        r = _cli(self.root, "check")
        self.assertNotEqual(r.returncode, 0, "a duplicated purpose string passed")
        out = r.stdout + r.stderr
        self.assertIn("skills/dup", out)

    def test_check_fails_when_the_map_on_disk_is_stale(self):
        _write(self.root, "tools/a/x.py", "x = 1\n")
        self.registry("tools | The tool tree.", "tools/a | Does a.", "docs | Documentation.")
        self.commit()
        _cli(self.root, "write")
        self.commit("map")
        self.assertEqual(_cli(self.root, "check").returncode, 0)
        _write(self.root, "tools/c/z.py", "z = 1\n")
        self.registry("tools | The tool tree.", "tools/a | Does a.",
                      "docs | Documentation.", "tools/c | Does c.")
        self.commit("added c")
        r = _cli(self.root, "check")
        self.assertNotEqual(r.returncode, 0, "a map missing a whole directory passed")
        self.assertIn("tools/c", r.stdout + r.stderr)

    def test_check_fails_when_the_map_was_edited_by_hand(self):
        _write(self.root, "tools/a/x.py", "x = 1\n")
        self.registry("tools | The tool tree.", "tools/a | Does a.", "docs | Documentation.")
        self.commit()
        _cli(self.root, "write")
        self.commit("map")
        m = self.root / "docs" / "CODEBASE-MAP.md"
        m.write_text(m.read_text(encoding="utf-8").replace("Does a.", "Does something else."),
                     encoding="utf-8")
        self.assertNotEqual(_cli(self.root, "check").returncode, 0,
                            "a hand-edited map passed; edits belong in the registry")

    def test_map_survives_its_own_commit(self):
        # The generated file is itself a tracked file in docs/. If the inventory
        # counted it, generating would be clean before the commit and drifted
        # after it, forever. Same shape as a fingerprint stamp that changes the
        # fingerprint, which is why this is pinned rather than assumed.
        _write(self.root, "tools/a/x.py", "x = 1\n")
        self.registry("tools | The tool tree.", "tools/a | Does a.", "docs | Documentation.")
        self.commit()
        _cli(self.root, "write")
        before = (self.root / "docs" / "CODEBASE-MAP.md").read_text(encoding="utf-8")
        self.commit("map")
        self.assertEqual(_cli(self.root, "check").returncode, 0,
                         "committing the map broke the check that generated it")
        _cli(self.root, "write")
        self.assertEqual(before, (self.root / "docs" / "CODEBASE-MAP.md").read_text(
            encoding="utf-8"), "the map does not converge across its own commit")

    def test_write_is_idempotent(self):
        _write(self.root, "tools/a/x.py", "x = 1\n")
        self.registry("tools | The tool tree.", "tools/a | Does a.", "docs | Documentation.")
        self.commit()
        _cli(self.root, "write")
        once = (self.root / "docs" / "CODEBASE-MAP.md").read_text(encoding="utf-8")
        _cli(self.root, "write")
        self.assertEqual(once, (self.root / "docs" / "CODEBASE-MAP.md").read_text(
            encoding="utf-8"))

    def test_json_output_is_machine_readable(self):
        _write(self.root, "tools/a/x.py", "x = 1\n")
        self.registry("tools | The tool tree.", "tools/a | Does a.", "docs | Documentation.")
        self.commit()
        r = _cli(self.root, "check", "--json")
        payload = json.loads(r.stdout)
        self.assertIn("undocumented", payload)
        self.assertIn("dirs", payload)


class TestPriorArt(MapCase):
    """The standing better-library audit, enforced the way waivers are.

    "constantly audit yourself if there is a better lib" cannot be a report,
    because a report is true on the day it is written. It is a per-component
    record with a review date and an expiry, and an expired record fails exactly
    like an expired waiver.
    """

    def component(self, name: str, loc: int = 400) -> None:
        _write(self.root, "tools/{}/{}.py".format(name, name), "\n".join(
            "x = {}".format(i) for i in range(loc)) + "\n")

    def record(self, name: str, recheck_after: str, alternatives=None) -> None:
        _write(self.root, "docs/prior-art/{}.json".format(name), json.dumps({
            "component": "tools/" + name,
            "reviewed": "2026-07-25",
            "recheck_after": recheck_after,
            "verdict": "keep-ours",
            "why": "nothing off the shelf gives tree-bound verdicts",
            "alternatives": alternatives if alternatives is not None else [
                {"name": "pre-commit", "gap": "no expiring waivers"}],
            "evidence": "read pre-commit's docs on 2026-07-25",
            "recheck": "python tools/map/codemap.py prior-art --project .",
        }, indent=2) + "\n")

    def test_a_big_component_with_no_record_fails(self):
        self.component("gate")
        self.commit()
        r = _cli(self.root, "prior-art")
        self.assertNotEqual(r.returncode, 0, "a 400-line component with no audit passed")
        self.assertIn("tools/gate", r.stdout + r.stderr)

    def test_a_current_record_passes(self):
        self.component("gate")
        self.record("gate", "2099-01-01")
        self.commit()
        r = _cli(self.root, "prior-art")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_an_expired_record_fails(self):
        self.component("gate")
        self.record("gate", "2020-01-01")
        self.commit()
        r = _cli(self.root, "prior-art")
        self.assertNotEqual(r.returncode, 0, "an expired prior-art record passed")
        self.assertIn("expired", (r.stdout + r.stderr).lower())

    def test_a_record_naming_no_alternative_fails(self):
        # "I looked and there is nothing" is the answer that requires the most
        # evidence and is the cheapest to type, so it does not count.
        self.component("gate")
        self.record("gate", "2099-01-01", alternatives=[])
        self.commit()
        r = _cli(self.root, "prior-art")
        self.assertNotEqual(r.returncode, 0, "a record with no alternatives considered passed")

    def test_a_declared_out_of_scope_prefix_removes_the_obligation(self):
        # Third-party code we did not write cannot be audited for whether
        # something better exists: we already chose it off the shelf.
        self.component("vendored")
        _write(self.root, "docs/prior-art/out-of-scope.txt",
               "tools/vendored | third-party skill installed from the marketplace\n")
        self.commit()
        r = _cli(self.root, "prior-art")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_an_exclusion_is_printed_and_never_silent(self):
        self.component("vendored")
        _write(self.root, "docs/prior-art/out-of-scope.txt",
               "tools/vendored | third-party skill installed from the marketplace\n")
        self.commit()
        out = _cli(self.root, "prior-art").stdout
        self.assertIn("tools/vendored", out)
        self.assertIn("marketplace", out, "the reason for the exclusion was not shown")

    def test_an_exclusion_with_no_reason_does_not_count(self):
        self.component("vendored")
        _write(self.root, "docs/prior-art/out-of-scope.txt", "tools/vendored\n")
        self.commit()
        self.assertNotEqual(_cli(self.root, "prior-art").returncode, 0,
                            "a bare prefix with no reason silently dropped a component")

    def test_a_small_component_needs_no_record(self):
        self.component("tiny", loc=20)
        self.commit()
        self.assertEqual(_cli(self.root, "prior-art").returncode, 0)

    def test_the_obligation_set_grows_with_the_code(self):
        # No hand-maintained list of components: crossing the threshold is what
        # creates the obligation, so new code cannot be born exempt.
        self.component("small", loc=20)
        self.commit()
        self.assertEqual(_cli(self.root, "prior-art").returncode, 0)
        self.component("small", loc=400)
        self.commit("grew")
        self.assertNotEqual(_cli(self.root, "prior-art").returncode, 0,
                            "a component that grew past the threshold stayed exempt")


if __name__ == "__main__":
    unittest.main()
