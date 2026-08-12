"""The prior-art schema's absorption fields, ABSORB-01 and ABSORB-09.

The root-cause row those two tickets share: all 41 prior-art records carried the
same 14 fields and not one of them named what was taken from the alternative it
evaluated. Absorption was unrepresentable, therefore unchecked, therefore it
never happened, and ABSORB-06 recorded the true rate as "unknown, not zero".

These pin the oracle rather than the data. The counts move every time a record is
written; what must not move is that a record cannot omit either field, that both
vocabularies stay closed, and that a status claiming a decision has to name it.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "map"))
sys.path.insert(0, os.path.join(ROOT, "tools", "audit"))

import absorption_backfill  # noqa: E402
import codemap  # noqa: E402

CLEAN = {"verdict_class": "keep-ours", "absorption_status": "unreviewed"}


def records():
    base = os.path.join(ROOT, "docs", "prior-art")
    for name in sorted(os.listdir(base)):
        if name.endswith(".json"):
            with open(os.path.join(base, name), encoding="utf-8") as fh:
                yield name, json.load(fh)


def test_a_clean_record_is_clean():
    assert codemap.absorption_problems("c", CLEAN) == []


@pytest.mark.parametrize("field,wording", [
    ("verdict_class", "no verdict_class"),
    ("absorption_status", "no absorption_status"),
])
def test_a_missing_field_is_reported_as_missing(field, wording):
    """Not merely reported. The missing branch and the invalid branch are
    adjacent, and a None value falls through from one to the other, so a test
    that only counted messages would pass with the missing check deleted."""
    rec = {k: v for k, v in CLEAN.items() if k != field}
    msgs = codemap.absorption_problems("c", rec)
    assert len(msgs) == 1
    assert wording in msgs[0]


@pytest.mark.parametrize("field,value", [
    ("verdict_class", "probably"),
    ("absorption_status", "probably"),
])
def test_both_vocabularies_are_closed(field, value):
    msgs = codemap.absorption_problems("c", dict(CLEAN, **{field: value}))
    assert len(msgs) == 1
    assert "probably" in msgs[0], "the message must quote the rejected value"


@pytest.mark.parametrize("status", codemap.ABSORPTION_NEEDS_DETAIL)
def test_a_status_claiming_a_decision_must_name_it(status):
    """An enum that groups perfectly and carries no detail is the free-text
    defect wearing a vocabulary, which is what ABSORB-09 diagnosed on the board
    and then found in this repo's own records."""
    bare = codemap.absorption_problems("c", dict(CLEAN, absorption_status=status))
    assert len(bare) == 1
    named = codemap.absorption_problems(
        "c", dict(CLEAN, absorption_status=status, absorbed="took the elision rule"))
    assert named == []


def test_whitespace_does_not_satisfy_absorbed():
    msgs = codemap.absorption_problems(
        "c", dict(CLEAN, absorption_status="absorbed", absorbed="   \n "))
    assert len(msgs) == 1


def test_unreviewed_does_not_require_detail():
    """`unreviewed` is a real value, not a hole. Requiring prose beside it would
    buy a sentence saying nobody has looked, and the recheck_after date is what
    bounds it."""
    assert codemap.absorption_problems("c", dict(CLEAN, absorbed="")) == []


def test_the_failure_message_names_the_command_that_fixes_it():
    msgs = codemap.absorption_problems("c", {})
    assert len(msgs) == 2
    assert all(codemap.BACKFILL_CMD in m for m in msgs)


def test_every_committed_record_carries_both_fields():
    bad = []
    for name, rec in records():
        bad.extend("{}: {}".format(name, m)
                   for m in codemap.absorption_problems(name, rec))
    assert bad == []


def test_the_backfill_never_overwrites_a_decided_status():
    """A rerun that reset a reviewed record to `unreviewed` would silently undo
    the review the field exists to force, and the rerun happens every time one of
    the open branches lands a new record."""
    decided = {"verdict_class": "absorb", "absorption_status": "adopted",
               "absorbed": "the whole library"}
    assert absorption_backfill.planned("tools-trycmd", decided) == {}


def test_the_backfill_guesses_no_verdict_class_for_an_unknown_component():
    """Deriving the enum from the free text by keyword would reintroduce the
    defect: four of the verdicts are whole sentences."""
    assert "verdict_class" not in absorption_backfill.planned("no-such-component", {})


def test_the_table_covers_every_committed_record():
    stems = {name[:-len(".json")] for name, _ in records()}
    missing = sorted(stems - set(absorption_backfill.VERDICT_CLASS))
    assert missing == [], (
        "these records have no assigned verdict_class and would fail the gate: "
        + ", ".join(missing))


def test_the_measured_absorption_rate_is_reported_not_hidden():
    """The count belongs on the PASS path. ABSORB-06 said the rate was unknown
    rather than zero; a number that only appears when something breaks goes back
    to unknown the moment it is fixed."""
    _found, detail = codemap.audit_prior_art(ROOT, __import__("datetime").date(2026, 1, 1))
    assert "unreviewed_absorption" in detail
    assert set(detail["unreviewed_absorption"]) <= set(detail["recorded"])
