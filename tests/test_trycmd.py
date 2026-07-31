"""Oracle for tools/trycmd/trycmd.py: the CLI-surface snapshot harness.

The mechanism is a port of `trycmd` v1.2.1 and `snapbox` v0.6.21 (Rust), so the
checks here are split in two, and the split matters:

  - PORT FIDELITY. Cases lifted from the upstream `#[test]` blocks in
    trycmd-1.2.1/src/schema.rs:906-1120 and snapbox-0.6.21/src/filter/pattern.rs:610.
    If the port drifts from the grammar it claims to implement, the `.trycmd`
    files in this tree stop meaning what their format documents say they mean.
  - THE HARNESS CANNOT PASS VACUOUSLY. A snapshot runner has one dominant
    failure mode, which is reporting green because it ran nothing or because it
    swallowed what it could not read. test_empty_suite_fails and
    test_malformed_case_is_a_failure_not_a_skip exist only for that, and they
    are the two this file would keep if it had to lose the rest.

The real cases live in tests/cmd/*.trycmd and are executed here by
test_repo_cases_pass, so a broken CLI contract fails the pytest run and not only
a separate command nobody remembers to type.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRYCMD_PATH = ROOT / "tools" / "trycmd" / "trycmd.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("trycmd_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


trycmd = _load(TRYCMD_PATH)


def _cli(*args: str, project: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TRYCMD_PATH), *args,
                           "--project", str(project)],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


class TestGrammar(unittest.TestCase):
    """Port fidelity against trycmd-1.2.1/src/schema.rs:186 `parse_trycmd`."""

    def test_empty_input_yields_no_steps(self):
        self.assertEqual(trycmd.parse(""), [])

    def test_prose_outside_a_fence_is_ignored(self):
        steps = trycmd.parse("# heading\n\nsome prose\n\n```\n$ echo hi\n```\n")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].bin, "echo")

    def test_continuation_lines_append_to_the_same_command(self):
        step = trycmd.parse("```\n$ tool one\n> two three\n```\n")[0]
        self.assertEqual(step.args, ["one", "two", "three"])

    def test_quoted_argument_survives_shlex(self):
        step = trycmd.parse('```\n$ tool "a b" c\n```\n')[0]
        self.assertEqual(step.args, ["a b", "c"])

    def test_env_prefix_is_stripped_from_the_command(self):
        step = trycmd.parse("```\n$ A=1 B=2 tool\n```\n")[0]
        self.assertEqual(step.env, {"A": "1", "B": "2"})
        self.assertEqual(step.bin, "tool")

    def test_default_status_is_success(self):
        self.assertEqual(trycmd.parse("```\n$ tool\n```\n")[0].status, 0)

    def test_explicit_status_code_is_parsed(self):
        self.assertEqual(trycmd.parse("```\n$ tool\n? 2\n```\n")[0].status, 2)

    def test_failed_means_any_nonzero_not_a_specific_code(self):
        """`? failed` must not silently pin one code, or it over-asserts."""
        step = trycmd.parse("```\n$ tool\n? failed\n```\n")[0]
        self.assertIsNone(step.status)

    def test_unsupported_fence_language_is_skipped(self):
        self.assertEqual(trycmd.parse("```python\n$ tool\n```\n"), [])

    def test_ignore_attribute_is_honored(self):
        self.assertEqual(trycmd.parse("```console,ignore\n$ tool\n```\n"), [])

    def test_multiple_blocks_each_contribute_steps(self):
        self.assertEqual(len(trycmd.parse("```\n$ a\n```\nx\n```\n$ b\n```\n")), 2)

    def test_multiple_commands_in_one_block(self):
        steps = trycmd.parse("```\n$ a\nout\n$ b\n```\n")
        self.assertEqual([s.bin for s in steps], ["a", "b"])
        self.assertEqual(steps[0].expected, "out")

    def test_crlf_input_parses_identically_to_lf(self):
        """Three CRLF false results are already on this repo's record."""
        self.assertEqual(trycmd.parse("```\r\n$ tool a\r\n```\r\n")[0].args,
                         trycmd.parse("```\n$ tool a\n```\n")[0].args)

    def test_a_fenced_line_that_is_not_a_command_is_a_parse_error(self):
        with self.assertRaises(trycmd.ParseError):
            trycmd.parse("```\nnot a command\n```\n")

    def test_a_bare_status_word_that_is_not_a_code_is_a_parse_error(self):
        with self.assertRaises(trycmd.ParseError):
            trycmd.parse("```\n$ tool\n? sideways\n```\n")


class TestMatcher(unittest.TestCase):
    """Port fidelity against snapbox-0.6.21/src/filter/pattern.rs:582."""

    def test_exact_line(self):
        self.assertTrue(trycmd.line_matches("hello", "hello"))

    def test_wildcard_matches_anything_including_empty(self):
        self.assertTrue(trycmd.line_matches("anything at all", "[..]"))
        self.assertTrue(trycmd.line_matches("", "[..]"))

    def test_wildcard_as_prefix_suffix_and_infix(self):
        self.assertTrue(trycmd.line_matches("hello world", "hello [..]"))
        self.assertTrue(trycmd.line_matches("hello world", "[..] world"))
        self.assertTrue(trycmd.line_matches("abcde", "a[..]e"))

    def test_a_wildcard_does_not_make_everything_match(self):
        """The failure that would make this harness worthless."""
        self.assertFalse(trycmd.line_matches("goodbye", "hello [..]"))
        self.assertFalse(trycmd.line_matches("hello", "hell[..]x"))

    def test_normalize_collapses_only_a_genuine_match(self):
        self.assertEqual(trycmd.normalize("exit code 37", "exit code [..]"),
                         "exit code [..]")
        self.assertEqual(trycmd.normalize("boom", "exit code [..]"), "boom")

    def test_elide_swallows_intervening_lines_and_stops_at_the_anchor(self):
        self.assertEqual(trycmd.normalize("a\nx\ny\nz", "a\n...\nz"), "a\n...\nz")

    def test_elide_that_finds_no_anchor_does_not_pass(self):
        self.assertNotEqual(trycmd.normalize("a\nx\ny", "a\n...\nz"), "a\n...\nz")

    def test_a_pattern_free_expectation_is_left_untouched(self):
        self.assertEqual(trycmd.normalize("a\nb", "x\ny"), "a\nb")


class TestRunner(unittest.TestCase):
    def test_exit_code_is_reported_verbatim(self):
        step = trycmd.parse('```\n$ python -c "raise SystemExit(3)"\n```\n')[0]
        self.assertEqual(trycmd.run_step(step, ROOT)[0], 3)

    def test_stderr_is_merged_into_the_compared_stream(self):
        step = trycmd.parse(
            '```\n$ python -c "import sys; sys.stderr.write(\'e\')"\n```\n')[0]
        self.assertEqual(trycmd.run_step(step, ROOT)[1], "e")

    def test_a_missing_binary_is_a_failure_not_an_exception(self):
        step = trycmd.parse("```\n$ no-such-binary-anywhere\n```\n")[0]
        code, out = trycmd.run_step(step, ROOT)
        self.assertEqual(code, 127)
        self.assertIn("not found", out)

    def test_project_root_is_redacted_out_of_output(self):
        """An absolute path in a snapshot makes it pass only on one machine."""
        step = trycmd.parse('```\n$ python -c "import os; print(os.getcwd())"\n```\n')[0]
        self.assertEqual(trycmd.run_step(step, ROOT)[1], "[ROOT]")

    def test_env_prefix_reaches_the_process(self):
        step = trycmd.parse(
            '```\n$ TRYCMD_PROBE=zzz python -c "import os; print(os.environ[\'TRYCMD_PROBE\'])"\n```\n'
        )[0]
        self.assertEqual(trycmd.run_step(step, ROOT)[1], "zzz")


class TestHarnessCannotPassVacuously(unittest.TestCase):
    """The two checks this file exists for."""

    def test_empty_suite_fails(self):
        with tempfile.TemporaryDirectory() as td:
            r = _cli("check", project=Path(td))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("no cases found", r.stdout)

    def test_malformed_case_is_a_failure_not_a_skip(self):
        r = _cli("check", "tests/cmd/fixtures/malformed.trycmd")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("1 failed", r.stdout)

    def test_a_wrong_expectation_actually_fails(self):
        """Mutation control: if this passes, the comparison is not happening."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tests" / "cmd").mkdir(parents=True)
            (root / "tests" / "cmd" / "x.trycmd").write_text(
                '```\n$ python -c "print(\'real\')"\nWRONG\n```\n', encoding="utf-8")
            r = _cli("check", project=root)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("output mismatch", r.stdout)

    def test_a_wrong_exit_code_actually_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tests" / "cmd").mkdir(parents=True)
            (root / "tests" / "cmd" / "x.trycmd").write_text(
                '```\n$ python -c "pass"\n? 9\n```\n', encoding="utf-8")
            r = _cli("check", project=root)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("expected exit 9", r.stdout)


class TestOverwrite(unittest.TestCase):
    def test_overwrite_makes_a_failing_case_pass_and_records_the_real_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tests" / "cmd").mkdir(parents=True)
            case = root / "tests" / "cmd" / "x.trycmd"
            case.write_text('```\n$ python -c "print(\'real\')"\nWRONG\n```\n',
                            encoding="utf-8")
            self.assertEqual(_cli("check", project=root).returncode, 1)
            self.assertEqual(_cli("overwrite", project=root).returncode, 0)
            self.assertIn("real", case.read_text(encoding="utf-8"))
            self.assertEqual(_cli("check", project=root).returncode, 0)

    def test_overwrite_records_a_nonzero_status_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tests" / "cmd").mkdir(parents=True)
            case = root / "tests" / "cmd" / "x.trycmd"
            case.write_text('```\n$ python -c "raise SystemExit(4)"\n```\n',
                            encoding="utf-8")
            _cli("overwrite", project=root)
            self.assertIn("? 4", case.read_text(encoding="utf-8"))
            self.assertEqual(_cli("check", project=root).returncode, 0)


class TestRepoIntegration(unittest.TestCase):
    def test_selftest_passes_and_reports_its_count(self):
        r = _cli("selftest")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 checks failed", r.stdout)

    def test_repo_cases_pass(self):
        """The real CLI contracts in tests/cmd/*.trycmd."""
        r = _cli("check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_the_repo_suite_is_not_empty(self):
        cases = list((ROOT / "tests" / "cmd").glob("*.trycmd"))
        self.assertTrue(cases)
        steps = sum(len(trycmd.parse(c.read_text(encoding="utf-8"))) for c in cases)
        self.assertGreaterEqual(steps, 5, "the suite exists but asserts almost nothing")


if __name__ == "__main__":
    unittest.main()
