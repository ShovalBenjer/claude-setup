"""Oracle for the two gate checks added for the map and the prior-art audit.

Half of this file is about a defect in the gate that predates those checks. The
domain loop iterated the fixed DOMAINS list and looked each name up in the
contract, so a domain the contract declared but the list did not contain was read
from disk, ignored, and never reported. A contract that says

    "codemap": {"builtin": "dir_map"}

then reads as if the repository checks its own map while nothing runs it, which is
the exact failure the gate was built to stop, one level up: a check that exists
only as text. test_a_domain_declared_only_in_the_contract_still_runs pins the
fix, and the two required-by-default cases pin the half of it that matters, since
a declared domain whose failure does not block is a disabled check with better
manners.

The rest asserts the builtins report what the tool reports. They shell out to
tools/map/codemap.py rather than importing it, so the evidence in the gate report
is the output of the command a human would run, and there is one implementation of
the rule instead of two that drift.
"""

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "engine" / "tools" / "gate" / "gate.py"
CODEMAP_PATH = ROOT / "engine" / "tools" / "map" / "codemap.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("gate_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gate = _load(GATE_PATH)

FIXED = list(gate.DOMAINS)


def _rmtree_or_fail(path: str) -> None:
    """Delete a scratch repo and RAISE if it survives.

    Replaces `shutil.rmtree(path, ignore_errors=True)`, which measured on 2026-07-30 had
    leaked 1,879 directories into %LOCALAPPDATA%\\Temp. The mechanism: git marks pack
    files read-only, rmtree fails with PermissionError on Windows, and ignore_errors
    swallows it. So the cleanup ran on every test, always reported success, and could
    not fail. That is the same class as L-2026-07-27-d, here in test hygiene.

    The onexc/onerror handler chmods the offending path and retries once, which is the
    standard Windows fix. The final assertion is the part that matters: if the directory
    is still there, the test fails loudly instead of leaving litter behind.
    """
    def _retry(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=lambda f, p, e: _retry(f, p, e))
    else:  # pragma: no cover - depends on the interpreter running the suite
        shutil.rmtree(path, onerror=lambda f, p, e: _retry(f, p, e))
    if os.path.exists(path):
        raise AssertionError(
            "scratch repo survived cleanup: {}. Leaving it silently is how 1,879 of "
            "these accumulated.".format(path))


class GateCase(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.mkdtemp(prefix="gate-extra-")
        self.addCleanup(_rmtree_or_fail, self.td)
        self.root = Path(self.td)
        for cmd in ("git init -q .",
                    "git config user.email t@t",
                    "git config user.name t"):
            subprocess.run(cmd.split(), cwd=self.td, check=True, capture_output=True)
        self.write("README.md", "# fixture\n\nA repository used by the gate oracle.\n")

    def write(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def install_codemap(self) -> None:
        (self.root / "engine" / "tools" / "map").mkdir(parents=True, exist_ok=True)
        shutil.copy(CODEMAP_PATH, self.root / "engine" / "tools" / "map" / "codemap.py")

    def write_map(self) -> None:
        subprocess.run([sys.executable, "engine/tools/map/codemap.py", "write",
                        "--project", self.td],
                       cwd=self.td, check=True, capture_output=True)

    def commit(self) -> None:
        subprocess.run(["git", "add", "-A"], cwd=self.td, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=self.td,
                       check=True, capture_output=True)

    def contract(self, **extra: dict) -> None:
        """Every fixed domain waived so the verdict turns on the extra domains only."""
        domains = {d: {"waived": {"reason": "oracle fixture", "until": "2099-01-01"}}
                   for d in FIXED}
        domains.update(extra)
        self.write(gate.CONTRACT_NAME,
                   json.dumps({"project": "fixture", "domains": domains}, indent=1))

    def run_gate(self, domain: str | None = None) -> tuple[int, dict]:
        out = self.root / "gate.json"
        cmd = [sys.executable, str(GATE_PATH), "run", "--project", self.td,
               "--json", str(out)]
        if domain:
            cmd += ["--domain", domain]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        self.assertTrue(out.exists(), "gate wrote no json report:\n" + proc.stdout + proc.stderr)
        return proc.returncode, json.loads(out.read_text(encoding="utf-8"))

    def run_gate_raw(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(GATE_PATH), "run", "--project", self.td, *argv],
            capture_output=True, text=True, encoding="utf-8", errors="replace")

    def status_of(self, report: dict, domain: str) -> str:
        for r in report["results"]:
            if r["domain"] == domain:
                return r["status"]
        self.fail("the gate never evaluated the {} domain. Domains reported: {}".format(
            domain, [r["domain"] for r in report["results"]]))

    def evidence_of(self, report: dict, domain: str) -> str:
        for r in report["results"]:
            if r["domain"] == domain:
                return r["evidence"]
        return ""


class TestExtraDomains(GateCase):
    def test_a_domain_declared_only_in_the_contract_still_runs(self):
        self.contract(house_rule={"cmd": sys.executable + " -c \"pass\""})
        self.commit()
        _, report = self.run_gate()
        self.assertEqual(gate.PASS, self.status_of(report, "house_rule"))

    def test_an_extra_domain_that_fails_blocks_the_verdict(self):
        self.contract(house_rule={"cmd": sys.executable + " -c \"raise SystemExit(3)\""})
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.FAIL, self.status_of(report, "house_rule"))
        self.assertIn("house_rule", report["record"]["blocking"],
                      "a domain the contract declares must block by default, or declaring "
                      "it is decoration")
        self.assertEqual(1, rc)

    def test_an_extra_domain_can_be_declared_not_required(self):
        self.contract(house_rule={"required": False,
                                  "cmd": sys.executable + " -c \"raise SystemExit(3)\""})
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.FAIL, self.status_of(report, "house_rule"))
        self.assertNotIn("house_rule", report["record"]["blocking"])
        self.assertEqual(0, rc, "an explicit required:false is the visible way to opt out")

    def test_an_extra_domain_with_no_check_is_uncovered_not_absent(self):
        self.contract(house_rule={"note": "we mean to do this"})
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.UNCOVERED, self.status_of(report, "house_rule"))
        self.assertEqual(1, rc)

    def test_an_extra_domain_can_be_run_on_its_own(self):
        # The other half of the same defect. Widening the loop is not enough while
        # --domain is validated against the fixed list, because then the one
        # command a person reaches for to debug a failing extra domain is the one
        # command that refuses to run it.
        self.contract(house_rule={"cmd": sys.executable + " -c \"pass\""})
        self.commit()
        _, report = self.run_gate(domain="house_rule")
        self.assertEqual([r["domain"] for r in report["results"]], ["house_rule"])
        self.assertEqual(gate.PASS, self.status_of(report, "house_rule"))

    def test_an_unknown_domain_name_is_refused_and_lists_the_real_ones(self):
        # Dropping argparse's choices= must not turn a typo into a silent
        # UNCOVERED for a domain nobody ever declared.
        self.contract(house_rule={"cmd": sys.executable + " -c \"pass\""})
        self.commit()
        proc = self.run_gate_raw("--domain", "hosue_rule")
        self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
        out = proc.stdout + proc.stderr
        self.assertIn("hosue_rule", out)
        self.assertIn("house_rule", out, "the error has to name what is available")

    def test_the_report_lists_every_declared_domain(self):
        self.contract(house_rule={"cmd": sys.executable + " -c \"pass\""},
                      second_rule={"cmd": sys.executable + " -c \"pass\""})
        self.commit()
        _, report = self.run_gate()
        names = [r["domain"] for r in report["results"]]
        self.assertEqual(len(FIXED) + 2, len(names))
        self.assertEqual(len(names), len(set(names)), "a domain was evaluated twice")


class TestBuiltinsRegistered(unittest.TestCase):
    def test_both_new_builtins_are_registered(self):
        for name in ("dir_map", "prior_art"):
            self.assertIn(name, gate.BUILTINS)

    def test_an_unknown_builtin_is_a_failure_not_a_skip(self):
        self.assertNotIn("no_such_builtin", gate.BUILTINS)


class TestDirMapBuiltin(GateCase):
    def documented(self) -> None:
        self.write("knowledge/docs/dir-purpose.txt", "\n".join([
            "knowledge | fixture knowledge root",
            "knowledge/docs | fixture documentation",
            "engine | fixture engine root",
            "engine/tools | fixture tooling",
            "engine/tools/map | the map generator under test",
        ]) + "\n")

    def test_fails_when_a_directory_has_no_stated_purpose(self):
        self.install_codemap()
        self.contract(codemap={"builtin": "dir_map"})
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.FAIL, self.status_of(report, "codemap"))
        self.assertIn("engine/tools/map", self.evidence_of(report, "codemap"))
        self.assertEqual(1, rc)

    def test_passes_when_every_directory_is_documented_and_the_map_is_current(self):
        self.install_codemap()
        self.documented()
        self.contract(codemap={"builtin": "dir_map"})
        # Commit first. The inventory comes from git ls-files, so a map written
        # over an uncommitted tree is a map of nothing.
        self.commit()
        self.write_map()
        rc, report = self.run_gate()
        self.assertEqual(gate.PASS, self.status_of(report, "codemap"),
                         self.evidence_of(report, "codemap"))
        self.assertEqual(0, rc)

    def test_fails_when_the_map_is_stale(self):
        self.install_codemap()
        self.documented()
        self.contract(codemap={"builtin": "dir_map"})
        self.commit()
        self.write_map()
        self.write("extra/thing.txt", "new\n")
        self.write("knowledge/docs/dir-purpose.txt",
                   (self.root / "knowledge" / "docs" / "dir-purpose.txt").read_text(encoding="utf-8")
                   + "extra | a directory added after the map was written\n")
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.FAIL, self.status_of(report, "codemap"))
        self.assertIn("extra", self.evidence_of(report, "codemap"))
        self.assertEqual(1, rc)

    def test_a_missing_tool_fails_and_names_itself(self):
        # The check must not pass because its own implementation is absent. A
        # deleted tool is the cheapest way to disable a gate domain and it has to
        # read as a failure of the domain, not an absence of one.
        self.documented()
        self.contract(codemap={"builtin": "dir_map"})
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.FAIL, self.status_of(report, "codemap"))
        self.assertIn("codemap.py", self.evidence_of(report, "codemap"))
        self.assertEqual(1, rc)


class TestPriorArtBuiltin(GateCase):
    """A component big enough to owe a build-vs-buy record, and the record."""

    def big_component(self) -> int:
        body = "\n".join("VALUE_{} = {}".format(i, i) for i in range(340))
        self.write("engine/core.py", body + "\n")
        return body.count("\n") + 1

    def documented(self) -> None:
        self.write("knowledge/docs/dir-purpose.txt", "\n".join([
            "knowledge | fixture knowledge root",
            "knowledge/docs | fixture documentation",
            "knowledge/docs/prior-art | build-vs-buy records",
            "engine | the fixture component that owes a record",
            "engine/tools | fixture tooling",
            "engine/tools/map | the map generator under test",
        ]) + "\n")
        self.write("knowledge/docs/prior-art/out-of-scope.txt",
                   "engine/tools/map | a copy of the tool under test, not fixture code\n")

    def record(self, **over: object) -> None:
        rec = {
            "component": "engine",
            "reviewed": "2026-07-25",
            "recheck_after": "2099-01-01",
            "verdict": "keep-ours",
            # Required since ABSORB-01/09. Without them this fixture exercises
            # the absorption checks rather than the expiry behaviour these
            # domain tests are about.
            "verdict_class": "keep-ours",
            "absorption_status": "unreviewed",
            "why": "no library covers the fixture's job",
            "alternatives": [{"name": "some-lib", "gap": "does not run offline"}],
            "evidence": "read the fixture source",
            "recheck": "python engine/tools/map/codemap.py prior-art",
        }
        rec.update(over)
        self.write("knowledge/docs/prior-art/engine.json", json.dumps(rec, indent=1))

    def test_fails_when_a_big_component_has_no_record(self):
        self.install_codemap()
        self.big_component()
        self.documented()
        self.contract(prior_art={"builtin": "prior_art"})
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.FAIL, self.status_of(report, "prior_art"))
        self.assertIn("engine", self.evidence_of(report, "prior_art"))
        self.assertEqual(1, rc)

    def test_passes_with_a_current_record(self):
        self.install_codemap()
        self.big_component()
        self.documented()
        self.record()
        self.contract(prior_art={"builtin": "prior_art"})
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.PASS, self.status_of(report, "prior_art"),
                         self.evidence_of(report, "prior_art"))
        self.assertEqual(0, rc)

    def test_the_gate_shows_what_the_audit_excluded_even_when_it_fails(self):
        # An exclusion the report only prints on the pass path is a suppression
        # nobody reads at the moment they are deciding whether to trust the audit.
        self.install_codemap()
        self.big_component()
        self.documented()
        self.contract(prior_art={"builtin": "prior_art"})
        self.commit()
        _, report = self.run_gate()
        evidence = self.evidence_of(report, "prior_art")
        self.assertIn("out of scope engine/tools/map", evidence)
        self.assertIn("not fixture code", evidence)

    def test_an_expired_record_fails_like_an_expired_waiver(self):
        self.install_codemap()
        self.big_component()
        self.documented()
        self.record(recheck_after="2020-01-01")
        self.contract(prior_art={"builtin": "prior_art"})
        self.commit()
        rc, report = self.run_gate()
        self.assertEqual(gate.FAIL, self.status_of(report, "prior_art"))
        self.assertIn("expired", self.evidence_of(report, "prior_art").lower())
        self.assertEqual(1, rc)


if __name__ == "__main__":
    unittest.main()
