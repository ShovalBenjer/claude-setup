"""A waiver describes a measurement, and the gate must check that it still does.

Measured 2026-08-07 on this repository. The `skills` domain carried a live waiver
whose reason ended with its own falsifier in prose: "CONFIRM BY RUNNING: python
tools/audit/skills_sync.py check -- expect 'DRIFT: 51'. If it prints a different
number this waiver is stale." A gate run printed that sentence verbatim as the
domain's evidence, reported WAIVED, and returned VERDICT: PASS. Run by hand
ninety seconds later, the checker printed DRIFT: 29 and exited 1.

Nothing in the run was false. The output simply asserted more than the run had
measured: `until` was checked, the confirmation was not, and 22 items had been
resolved by a session that deployed skills on 2026-08-06 without anyone
restating the waiver they invalidated. An expiry date catches a waiver that ran
out. It cannot catch one that stopped being true.

These tests run `check_domain` directly against a throwaway directory, so they
never touch the real contract. The last two exist to stop the fix from
over-correcting into a check that fails every waiver, or into one that any
output satisfies.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "gate"))
import gate  # noqa: E402

LIVE = "2099-01-01"


def domain(cmd=None, confirm=None, until=LIVE, reason="measured 51 items"):
    spec = {"required": True}
    if cmd is not None:
        spec["cmd"] = cmd
        spec["timeout"] = 60
    waived = {"reason": reason, "until": until}
    if confirm is not None:
        waived["confirm"] = confirm
    spec["waived"] = waived
    return spec


def check(tmp_path, spec):
    return gate.eval_domain("skills", spec, str(tmp_path), {}, False)


class TestAWaiverIsCheckedAgainstItsOwnMeasurement:

    def test_a_stale_confirm_string_fails_the_domain(self, tmp_path):
        """The measured 2026-08-07 case: the waiver says 51, the checker says 29."""
        out = check(tmp_path, domain(cmd="echo DRIFT: 29; exit 1", confirm="DRIFT: 51"))
        assert out["status"] == gate.FAIL
        assert "STALE" in out["evidence"]
        assert "DRIFT: 29" in out["evidence"], "the current measurement belongs in the evidence"

    def test_a_confirmed_waiver_still_passes(self, tmp_path):
        """Otherwise this is not a confirmation, it is a ban on waivers."""
        out = check(tmp_path, domain(cmd="echo DRIFT: 29; exit 1", confirm="DRIFT: 29"))
        assert out["status"] == gate.WAIVED
        assert "confirmed" in out["evidence"]

    def test_the_commands_exit_code_is_not_the_signal(self, tmp_path):
        """A waived domain's command is expected to fail; that is usually why it
        was waived. What is being tested is the waiver's description of it."""
        failing = check(tmp_path, domain(cmd="echo DRIFT: 29; exit 1", confirm="DRIFT: 29"))
        passing = check(tmp_path, domain(cmd="echo DRIFT: 29; exit 0", confirm="DRIFT: 29"))
        assert failing["status"] == passing["status"] == gate.WAIVED

    def test_a_confirm_string_with_no_command_fails(self, tmp_path):
        """Otherwise deleting the domain's cmd is the cheapest way to make the
        confirmation unrunnable, and an unrunnable confirmation would pass."""
        out = check(tmp_path, domain(cmd=None, confirm="DRIFT: 51"))
        assert out["status"] == gate.FAIL
        assert "never run" in out["evidence"]


class TestTheOlderWaiverRulesStillHold:
    """The confirmation is an addition. If it swallowed the expiry check or the
    plain-waiver path, these go red rather than the ones above."""

    def test_a_waiver_with_no_confirm_is_untouched(self, tmp_path):
        out = check(tmp_path, domain(cmd="exit 1"))
        assert out["status"] == gate.WAIVED
        assert out["cmd"] is None, "a plain waiver must not start running commands"

    def test_an_expired_waiver_fails_before_any_confirmation_runs(self, tmp_path):
        out = check(tmp_path, domain(cmd="echo DRIFT: 29", confirm="DRIFT: 29",
                                     until="2020-01-01"))
        assert out["status"] == gate.FAIL
        assert "expired" in out["evidence"]
        assert "confirmed" not in out["evidence"]


@pytest.mark.parametrize("bad", ["", "soon", "2026-13-45"])
def test_an_unparseable_date_is_not_rescued_by_a_passing_confirmation(tmp_path, bad):
    """A malformed date already reads as expired. A confirmation that holds must
    not turn that back into a live waiver, or `until: soon` becomes permanent
    again through the new field."""
    out = check(tmp_path, domain(cmd="echo DRIFT: 29", confirm="DRIFT: 29", until=bad))
    assert out["status"] == gate.FAIL
