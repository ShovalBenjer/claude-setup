"""Oracle for dot-claude/hooks/completion_gate.py, the Stop hook.

This hook runs at the end of every turn in every project, so its failure modes are
asymmetric and both are bad in different ways. A false negative wastes the operator's
time, which is the measured 940 minutes a week this check exists to recover. A false
positive nags a turn that was right to stop, and a hook that cries wolf gets deleted.

The loop-guard case is the one that would be catastrophic rather than annoying: a Stop
hook that blocks unconditionally traps a session with no way out, so `stop_hook_active`
is asserted directly rather than assumed.

The legitimate-stop cases are drawn from this repository's own authority rules: an
oracle edit, a destructive action, a credential operation, a publication. If those get
nagged, the hook is training the session to push past exactly the boundaries that exist
to be respected, which is worse than not having the check.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "dot-claude" / "hooks" / "completion_gate.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("completion_gate_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gate = _load(GATE_PATH)


def act(text: str) -> str:
    return gate.verdict(text)[0]


def why(text: str) -> str:
    return gate.verdict(text)[1]


class HandbackTests(unittest.TestCase):
    def test_a_turn_ending_in_an_offer_to_continue_is_blocked(self) -> None:
        self.assertEqual(act("I fixed the parser and ran the suite.\n\nWant me to?"),
                         "block")
        self.assertEqual(why("Report.\n\nShall I go ahead and wire it up?"),
                         "handback_without_reason")

    def test_a_bare_trailing_question_is_blocked(self) -> None:
        self.assertEqual(act("Here is the analysis.\n\nWhich one do you prefer?"), "block")

    def test_the_pattern_this_hook_was_written_for(self) -> None:
        """The literal shape measured 124 times in one week."""
        real = (
            "Two things are genuinely yours to call, because both are oracle edits:\n\n"
            "1. completion_gate.py: add the ask-back check.\n"
            "2. panel.py: fix it or retire it.\n\nWant me to?"
        )
        self.assertEqual(act(real), "block")

    def test_a_question_in_the_middle_does_not_fire(self) -> None:
        """Only the closing segment counts. A report that asks and then answers has
        not handed anything back, and nagging it would make reasoning aloud costly."""
        text = (
            "Is the append atomic on Windows? I measured it: 24 threads produced 18 "
            "lines.\n\nSo I added a lock and the selftest now covers it. 23 of 23 "
            "mutations caught."
        )
        self.assertEqual(act(text), "pass")

    def test_a_turn_that_just_reports_work_passes(self) -> None:
        text = "Gate is green. 435 tests passed, types clean, codemap regenerated."
        self.assertEqual(act(text), "pass")


class LegitimateStopTests(unittest.TestCase):
    def test_the_explicit_marker_passes(self) -> None:
        text = ("I have gone as far as I can.\n\n"
                "NEEDS OPERATOR: rotating this key changes credentials I must not "
                "handle. Do you want me to proceed?")
        self.assertEqual(act(text), "pass")
        self.assertEqual(why(text), "handback_with_marker")

    def test_authority_boundary_categories_pass_without_the_marker(self) -> None:
        """These are the stops this repository's rules require."""
        for phrase in (
            "This is a destructive action, so should I proceed?",
            "This requires your approval because it edits an oracle. Want me to?",
            "That would publish to a third party. Shall I?",
            "This would rotate the credential. Do you want that?",
        ):
            self.assertEqual(act(phrase), "pass", phrase)

    def test_a_marker_without_a_question_still_passes(self) -> None:
        self.assertEqual(act("NEEDS OPERATOR: only you can approve a production deploy."),
                         "pass")


class CompletionClaimTests(unittest.TestCase):
    def test_the_original_check_still_fires_as_a_nudge(self) -> None:
        """Demoted from block to nudge 2026-08-12 on operator instruction, with
        the measurement: 211 of 243 blocks in the prior week were this reason,
        while ship_gate_stop.py enforces the same property against the run
        ledger. The check must still FIRE and still name its reason: a silent
        pass would be the oracle going blind rather than going quiet."""
        self.assertEqual(act("All done, everything works."), "nudge")
        self.assertEqual(why("All done, everything works."),
                         "completion_without_evidence")

    def test_an_unevidenced_claim_that_also_hands_back_still_blocks(self) -> None:
        """The demotion must not silence the stronger sibling check."""
        self.assertEqual(act("All done.\n\nWant me to continue?"), "block")
        self.assertEqual(why("All done.\n\nWant me to continue?"),
                         "handback_without_reason")

    def test_a_claim_with_evidence_passes(self) -> None:
        self.assertEqual(act("Fixed. pytest exit code 0, 435 passed."), "pass")

    def test_an_evidenced_claim_that_also_hands_back_is_still_caught(self) -> None:
        """Evidence excuses the CLAIM, not the stop."""
        self.assertEqual(act("Fixed, 435 tests passed.\n\nWant me to deploy it?"),
                         "block")


class SlopDashTests(unittest.TestCase):
    """The response channel is held to the same writing rule as the files.

    Added 2026-07-29 after measuring the hook's own author: 33 spaced-dash connectors
    across 17 of 28 text turns in one session, while every markdown file that session
    produced passed tools/slop_lint.py. The false-positive cases below are the ones that
    matter most: a checker that cannot tell prose from quoted code is what bought
    panel.py its third waiver, and this check must not repeat it.
    """

    def test_a_spaced_em_dash_connector_is_blocked(self) -> None:
        self.assertEqual(act("The map is generated — a hand edit reads as drift."),
                         "block")
        self.assertEqual(why("The map is generated — a hand edit reads as drift."),
                         "slop_dash")

    def test_a_spaced_en_dash_connector_is_blocked(self) -> None:
        self.assertEqual(act("Ran the gate – it passed."), "block")

    def test_the_rule_matches_slop_lint_exactly(self) -> None:
        """Same regex as tools/slop_lint.py:21. Two spellings would drift apart."""
        import re as _re
        slop = ROOT / "tools" / "slop_lint.py"
        src = slop.read_text(encoding="utf-8")
        pattern = _re.search(r'DASH = re\.compile\(r"([^"]+)"\)', src).group(1)
        self.assertEqual(pattern, gate.DASH.pattern)

    def test_a_hyphen_is_not_a_dash(self) -> None:
        self.assertEqual(act("The read-only sweep found 261 dead paths."), "pass")

    def test_an_unspaced_dash_does_not_fire(self) -> None:
        """slop_lint only gates the CONNECTOR form, so this hook must not exceed it."""
        self.assertEqual(act("Pages 12—14 of the spec."), "pass")

    def test_a_dash_inside_a_fenced_block_does_not_fire(self) -> None:
        text = "Here is the command:\n\n```\ngit log --oneline — the tail\n```\n\nRan it."
        self.assertEqual(act(text), "pass")

    def test_a_dash_inside_an_inline_span_does_not_fire(self) -> None:
        self.assertEqual(act("Run `wrangler pages deploy — dist` now."), "pass")

    def test_a_dash_inside_a_url_does_not_fire(self) -> None:
        """Only a dash WITHIN the URL token is exempt. The first draft of this test
        asserted that a spaced dash following a URL passed too, and the check correctly
        refused: that dash is prose punctuation that happens to sit after a link."""
        self.assertEqual(act("See https://example.com/a%20—%20b for the ledger."), "pass")
        self.assertEqual(act("See https://example.com/x — it is the ledger."), "block")

    def test_a_fence_does_not_swallow_a_later_violation(self) -> None:
        """Stripping must not blind the check to prose AFTER quoted code."""
        text = "```\nx — y\n```\n\nThe gate passed — the tree is clean."
        self.assertEqual(act(text), "block")

    def test_the_handback_message_wins_when_a_turn_does_both(self) -> None:
        """Ordering is a claim about which failure costs the operator more."""
        text = "I ran the sweep — it found nine items.\n\nWant me to continue?"
        self.assertEqual(why(text), "handback_without_reason")


class LoopGuardTests(unittest.TestCase):
    """The only failure here that could trap a session rather than annoy someone."""

    def _run(self, payload: dict) -> dict:
        """Run the hook as a real subprocess, with its ledger redirected to a temp dir.

        CLAUDE_OS_DIR is what the hook resolves its log path from, so overriding it is
        the supported way to keep a test out of the real ledger. The first version of
        this test omitted it and wrote six synthetic rows into
        state/handback-log.jsonl, which is the same defect as the gate selftest writing
        scratch-repo rows into state/gate-runs.jsonl: a measurement ledger that a test
        can reach is a ledger whose numbers are not measurements.
        """
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, CLAUDE_OS_DIR=tmp)
            proc = subprocess.run(
                [sys.executable, str(GATE_PATH)],
                input=json.dumps(payload).encode("utf-8"),
                capture_output=True, timeout=30, env=env,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
            return json.loads(proc.stdout.decode("utf-8") or "{}")

    def test_it_blocks_once(self) -> None:
        out = self._run({"last_assistant_message": "Done.\n\nWant me to continue?",
                         "stop_hook_active": False, "session_id": "test1234"})
        self.assertEqual(out.get("decision"), "block")

    def test_it_never_blocks_twice_in_one_turn(self) -> None:
        out = self._run({"last_assistant_message": "Done.\n\nWant me to continue?",
                         "stop_hook_active": True, "session_id": "test1234"})
        self.assertEqual(out, {})

    def test_malformed_input_never_blocks(self) -> None:
        proc = subprocess.run([sys.executable, str(GATE_PATH)],
                              input=b"not json at all", capture_output=True, timeout=30)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout.decode("utf-8") or "{}"), {})

    def test_an_empty_payload_never_blocks(self) -> None:
        self.assertEqual(self._run({}), {})


class RitualAcknowledgementTests(unittest.TestCase):
    """Added 2026-07-30. The operator's framing: an output style is a request, and this
    pattern sits below the prompt layer, so only a gate changes it.

    The false-positive risk here is sharper than for the other checks, because the
    corrections rule REQUIRES stating that a correction was correct and what it changed.
    A check that cannot tell "the hook was correct, so I ran the gate" from "you're
    absolutely right, my apologies" would make honest reporting impossible, so both
    directions are asserted.
    """

    def _v(self, text: str) -> tuple[str, str]:
        return gate.verdict(text)

    def test_second_person_praise_blocks(self) -> None:
        for phrase in (
            "You're right, that's my violation to fix.",
            "You are absolutely right about the floor.",
            "That's correct, the merge is superseded.",
            "Good catch on the em-dash.",
            "My apologies for the confusion.",
            "I apologize, the number was wrong.",
        ):
            action, reason = self._v("Ran the gate, exit 0. " + phrase)
            self.assertEqual(action, "block", phrase)
            self.assertEqual(reason, "ritual_acknowledgement", phrase)

    def test_evaluative_openers_block(self) -> None:
        for opener in ("Perfect.", "Great!", "Excellent,", "Absolutely.", "Exactly!"):
            action, reason = self._v(opener + " The tests pass, exit code 0.")
            self.assertEqual(action, "block", opener)
            self.assertEqual(reason, "ritual_acknowledgement", opener)

    def test_factual_correction_reporting_is_allowed(self) -> None:
        """The corrections rule requires this to stay possible."""
        for ok in (
            "The Stop hook fired because the tree had never been gated, so I ran it.",
            "My stated floor was wrong by 2.4x; the instrument was adding MSYS overhead.",
            "That measurement is superseded: the real figure is 44ms, tested via pytest.",
            "The gate is correct to block here. Exit code 0 after the fix.",
        ):
            action, reason = self._v(ok)
            self.assertEqual(action, "pass", "{} -> {}".format(ok, reason))

    def test_mid_sentence_adjectives_are_not_openers(self) -> None:
        """Anchored to line start, so ordinary English survives."""
        action, _ = self._v("The lto setting is perfect for this, verified by benchmark.")
        self.assertEqual(action, "pass")

    def test_a_dash_and_a_ritual_together_report_the_ritual(self) -> None:
        action, reason = self._v("Good catch. The value — as tested — is 44ms.")
        self.assertEqual(action, "block")
        self.assertEqual(reason, "ritual_acknowledgement")

    def test_code_and_quotes_are_stripped_before_matching(self) -> None:
        """Quoting a command or a log line containing the phrase must stay free."""
        action, _ = self._v(
            "Test output below, exit code 0.\n\n```\nassert msg == \"you're right\"\n```"
        )
        self.assertEqual(action, "pass")

    def test_hebrew_ritual_blocks(self) -> None:
        action, reason = self._v("אתה צודק. exit code 0, tested.")
        self.assertEqual(action, "block")
        self.assertEqual(reason, "ritual_acknowledgement")


class ChannelParityTests(unittest.TestCase):
    """The file channel and the response channel must correct the operator identically.

    tools/slop_lint.py gates prose FILES; completion_gate.py gates the RESPONSE. Lesson
    L-2026-07-29-g is precisely the case where an oracle covered the cheap surface and
    not the high-traffic one. Two spellings of one rule would drift, and the operator
    would be corrected by one and not the other, so the patterns are pinned equal here.
    """

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "slop_lint_under_test", ROOT / "tools" / "slop_lint.py"
        )
        self.sl = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.sl
        spec.loader.exec_module(self.sl)

    def test_dash_pattern_is_identical(self) -> None:
        self.assertEqual(self.sl.DASH.pattern, gate.DASH.pattern)

    def test_ritual_opener_pattern_is_identical(self) -> None:
        self.assertEqual(self.sl.RITUAL_OPENER.pattern, gate.RITUAL_OPENER.pattern)

    def test_ritual_pattern_agrees_on_shared_phrases(self) -> None:
        """slop_lint omits the Hebrew and 'sorry' arms on purpose (file prose quotes
        them legitimately), so equality is asserted on BEHAVIOUR for the shared set
        rather than on the pattern string."""
        shared = [
            "you're right", "you are absolutely right", "that's correct",
            "good catch", "my apologies", "I apologize",
            "thanks for the correction", "Great question",
        ]
        for phrase in shared:
            self.assertTrue(gate.RITUAL.search(phrase), "hook missed: " + phrase)
            self.assertTrue(
                self.sl.RITUAL.search(phrase) or self.sl.RITUAL_OPENER.search(phrase),
                "slop_lint missed: " + phrase,
            )

    def test_neither_flags_legitimate_prose(self) -> None:
        for ok in (
            "The lto setting is perfect for this.",
            "The gate is correct to block here.",
            "Exactly which domains are waived is recorded in the ledger.",
        ):
            self.assertIsNone(gate.RITUAL.search(ok), ok)
            self.assertIsNone(self.sl.RITUAL.search(ok), ok)


class LedgerTests(unittest.TestCase):
    def test_every_stop_is_logged_including_the_clean_ones(self) -> None:
        """A false-positive rate cannot be computed from the fires alone."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "state" / "handback-log.jsonl"
            original, gate.LOG = gate.LOG, log
            try:
                gate.record("clean", "pass", "sess1234")
                gate.record("handback_without_reason", "block", "sess1234")
            finally:
                gate.LOG = original

            rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual({r["action"] for r in rows}, {"pass", "block"})
            self.assertTrue(all(r["ts"] and r["session"] == "sess1234" for r in rows))

    def test_an_unwritable_ledger_does_not_raise(self) -> None:
        """A hook that dies on a full disk must not take the session with it."""
        original, gate.LOG = gate.LOG, Path("\x00invalid") / "x.jsonl"
        try:
            gate.record("clean", "pass", "s")
        finally:
            gate.LOG = original


if __name__ == "__main__":
    unittest.main()
