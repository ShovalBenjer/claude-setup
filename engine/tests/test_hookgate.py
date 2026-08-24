"""Oracle for tools/hookgate, the compiled PreToolUse gate.

Three distinct things can rot, and only one of them is caught by the Rust compiler:

1. `src/rules.rs` drifting from `safety_gate.py::RULES`. Caught by regen --check.
2. The two regex engines disagreeing on byte-identical patterns. Only the differential
   oracle catches this, and it is the reason a generated file is not sufficient evidence.
3. The corpus decaying into something that exercises nothing. A corpus where Python
   blocks zero commands would make the oracle pass trivially, so a floor is asserted.

The binary is a build artifact and is gitignored, so tests that need it SKIP when it is
absent rather than fail. A skip is honest; a pass with no binary would be a lie, which is
the failure class where an accountability check is required but never actually verified.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CRATE = ROOT / "engine" / "tools" / "hookgate"
CORPUS = CRATE / "corpus.txt"
BINARIES = [
    CRATE / "target" / "release" / "hookgate.exe",
    CRATE / "target" / "release" / "hookgate",
    CRATE / "target" / "x86_64-unknown-linux-gnu" / "release" / "hookgate",
]


def find_binary() -> Path | None:
    return next((b for b in BINARIES if b.exists()), None)


def load_safety_gate():
    for candidate in (
        Path.home() / ".claude" / "hooks" / "safety_gate.py",
        ROOT / "payload" / "dot-claude" / "hooks" / "safety_gate.py",
    ):
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("_sg_for_test", candidate)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            return mod
    return None


class GeneratedRulesTests(unittest.TestCase):
    def test_rules_rs_matches_safety_gate(self) -> None:
        """A hand-edited or stale rules.rs means the compiled gate enforces old rules."""
        proc = subprocess.run(
            [sys.executable, str(CRATE / "regen_rules.py"), "--check"],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(
            proc.returncode, 0,
            "src/rules.rs is stale or hand-edited.\n" + proc.stdout + proc.stderr,
        )

    def test_rules_rs_is_marked_generated(self) -> None:
        text = (CRATE / "src" / "rules.rs").read_text(encoding="utf-8")
        self.assertIn("GENERATED", text)
        self.assertIn("Do not hand-edit", text)


class CorpusTests(unittest.TestCase):
    """A corpus that exercises nothing would make the differential oracle vacuous."""

    def setUp(self) -> None:
        self.sg = load_safety_gate()
        if self.sg is None:
            self.skipTest("no safety_gate.py found")
        self.commands = [
            c for c in CORPUS.read_text(encoding="utf-8").splitlines() if c.strip()
        ]

    def test_corpus_is_substantial(self) -> None:
        self.assertGreaterEqual(len(self.commands), 100)

    def test_corpus_triggers_a_majority_of_rules(self) -> None:
        """Every rule the compiled gate carries should be reachable by the corpus.

        A rule no command exercises is a rule the oracle says nothing about.
        """
        fired = set()
        for cmd in self.commands:
            for i, (pat, _r) in enumerate(self.sg.RULES):
                if pat.search(cmd):
                    fired.add(i)
                    break
        unexercised = sorted(set(range(len(self.sg.RULES))) - fired)
        self.assertEqual(
            unexercised, [],
            "rules never exercised by corpus.txt, so the oracle proves nothing about "
            "them: {}".format(unexercised),
        )

    def test_corpus_contains_negatives(self) -> None:
        """Blocking everything would also make agreement trivial."""
        blocked = sum(
            1 for c in self.commands
            if any(p.search(c) for p, _ in self.sg.RULES)
        )
        self.assertGreater(blocked, 0, "corpus blocks nothing")
        self.assertLess(blocked, len(self.commands), "corpus blocks everything")


class PrescanSoundnessTests(unittest.TestCase):
    """The prescan skips compiling patterns that cannot match. Verified, not trusted.

    Over-approximating a literal group costs a wasted compile. UNDER-approximating skips a
    rule on a command it should block and reports nothing, so this is the one optimisation in
    the crate that can create a security hole while every test still passes and every
    benchmark improves. The check therefore runs in the suite, not only in the generator.
    """

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "_regen_for_test", CRATE / "regen_rules.py"
        )
        self.rg = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.rg
        spec.loader.exec_module(self.rg)
        _path, self.rules = self.rg.load_rules()

    def test_every_literal_group_is_sound(self) -> None:
        failures = self.rg.verify_literals(self.rules)
        self.assertEqual(failures, [], "\n".join(failures))

    def test_the_verifier_can_actually_fail(self) -> None:
        """A soundness check that cannot fail proves nothing.

        Plants a group that is not a real precondition of the rule and requires detection.
        This is the mutation test for the verifier itself.
        """
        original = dict(self.rg.LITERAL_GROUPS)
        try:
            self.rg.LITERAL_GROUPS[3] = (("git",), ("reset",), ("definitely-not-present",))
            failures = self.rg.verify_literals(self.rules)
            self.assertTrue(
                failures, "verifier accepted a bogus group, so it is not checking anything"
            )
            self.assertIn("UNSOUND", failures[0])
        finally:
            self.rg.LITERAL_GROUPS.clear()
            self.rg.LITERAL_GROUPS.update(original)

    def test_weakening_a_group_set_is_not_reported_as_unsound(self) -> None:
        """Dropping a group only causes extra compiles, never a missed block."""
        original = dict(self.rg.LITERAL_GROUPS)
        try:
            self.rg.LITERAL_GROUPS[3] = (("git",),)
            self.assertEqual(self.rg.verify_literals(self.rules), [])
        finally:
            self.rg.LITERAL_GROUPS.clear()
            self.rg.LITERAL_GROUPS.update(original)

    def test_generated_file_carries_the_groups(self) -> None:
        text = (CRATE / "src" / "rules.rs").read_text(encoding="utf-8")
        self.assertIn("literal_groups", text)
        # Spot-check a conjunction actually made it through codegen.
        self.assertIn('r#"reset"#', text)


class GuidanceParityTests(unittest.TestCase):
    """The refusal message must be identical in both implementations.

    Added 2026-07-30 with the guidance itself. A guard that gives different advice depending
    on which build happens to be deployed teaches the caller two different things about the
    same refusal, and the drift would be invisible because both still block correctly.
    """

    @staticmethod
    def _rust_guidance() -> str:
        import re
        text = (CRATE / "src" / "main.rs").read_text(encoding="utf-8")
        m = re.search(r'const GUIDANCE: &str = "(.*?)";', text, re.DOTALL)
        assert m, "GUIDANCE not found in main.rs"
        # rustc: a trailing backslash consumes the newline and the following indentation.
        return re.sub(r"\\\n\s*", "", m.group(1))

    def test_guidance_is_byte_identical(self) -> None:
        sg = load_safety_gate()
        if sg is None:
            self.skipTest("no safety_gate.py found")
        self.assertTrue(hasattr(sg, "GUIDANCE"), "safety_gate.py lost GUIDANCE")
        self.assertEqual(sg.GUIDANCE, self._rust_guidance())

    def test_guidance_names_the_escape_hatch(self) -> None:
        """The whole point is that the caller learns the workaround at refusal time."""
        sg = load_safety_gate()
        if sg is None:
            self.skipTest("no safety_gate.py found")
        self.assertIn("Write tool", sg.GUIDANCE)

    def test_guidance_did_not_become_a_rule(self) -> None:
        """It is appended to the message. If it leaks into RULES, matching changed."""
        sg = load_safety_gate()
        if sg is None:
            self.skipTest("no safety_gate.py found")
        for pattern, reason in sg.RULES:
            self.assertNotIn("Write tool", reason)
            self.assertNotIn("Write tool", pattern.pattern)


class DifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.binary = find_binary()
        if self.binary is None:
            self.skipTest(
                "hookgate binary absent; build with: cd tools/hookgate "
                "&& cargo build --release"
            )
        self.sg = load_safety_gate()
        if self.sg is None:
            self.skipTest("no safety_gate.py found")

    def test_rust_and_python_agree_exactly(self) -> None:
        commands = [
            c for c in CORPUS.read_text(encoding="utf-8").splitlines() if c.strip()
        ]
        expected = []
        for cmd in commands:
            idx = -1
            for i, (pat, _r) in enumerate(self.sg.RULES):
                if pat.search(cmd):
                    idx = i
                    break
            expected.append(idx)

        proc = subprocess.run(
            [str(self.binary), "--diff-mode"],
            input="\n".join(commands).encode("utf-8"),
            capture_output=True, timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        got = [int(x) for x in proc.stdout.decode("utf-8").split()]
        self.assertEqual(len(got), len(expected))

        regressions = [
            (c, p, r) for c, p, r in zip(commands, expected, got) if p >= 0 and r < 0
        ]
        self.assertEqual(
            regressions, [],
            "SECURITY REGRESSION: python blocks these, the compiled gate allows them",
        )
        self.assertEqual(
            got, expected,
            "the two engines disagree on byte-identical patterns",
        )

    def test_malformed_input_fails_open(self) -> None:
        proc = subprocess.run(
            [str(self.binary)], input=b"not json", capture_output=True, timeout=60
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.decode("utf-8").strip(), "{}")

    def test_a_denied_command_emits_the_platform_shape(self) -> None:
        import json
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "git reset --hard"}}
        ).encode("utf-8")
        proc = subprocess.run(
            [str(self.binary)], input=payload, capture_output=True, timeout=60
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.decode("utf-8"))
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertIn("reset", hso["permissionDecisionReason"].lower())

    def test_an_ordinary_command_is_allowed(self) -> None:
        import json
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "echo hello"}}
        ).encode("utf-8")
        proc = subprocess.run(
            [str(self.binary)], input=payload, capture_output=True, timeout=60
        )
        self.assertEqual(proc.stdout.decode("utf-8").strip(), "{}")


if __name__ == "__main__":
    unittest.main()
