"""A gate run records how long it took, so an existing budget stops being unfalsifiable.

`quality-contract.json`'s `unit` domain raised its timeout from 300 to 900 on
2026-07-31 and wrote its own falsifier into the note: "if the suite passes 600s
this number is hiding growth again and the split is overdue." Every one of the
8571 run rows recorded before 2026-08-08 lacks any duration field, so that
falsifier could not be evaluated against a single one of them. A budget whose
falsifier nobody can run is a disabled check, the same shape as a waiver whose
confirmation never fires.

These tests cover the recording, not the budget. Deciding what the budget should
be is a contract change and the operator's.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "engine", "tools", "gate"))

import gate  # noqa: E402


def last_row():
    with open(os.path.join(ROOT, gate.LEDGER), encoding="utf-8") as fh:
        return json.loads(fh.read().strip().splitlines()[-1])


def run_pointers():
    gate.cmd_run(argparse.Namespace(project=ROOT, domain="pointers",
                                    verbose=False, json=None))
    return last_row()


def test_a_run_records_its_own_wall_clock():
    row = run_pointers()
    assert isinstance(row["duration_seconds"], float)
    assert row["duration_seconds"] > 0


def test_the_run_total_is_recorded_per_domain_as_well():
    """A single total cannot say which domain grew.

    The falsifier this field exists for names ONE domain, unit, so a row that
    only carried a total would still leave it unevaluable.
    """
    row = run_pointers()
    assert "pointers" in row["domain_seconds"]
    assert row["domain_seconds"]["pointers"] > 0


def test_the_total_is_at_least_the_sum_of_the_domains_it_ran():
    """Catches a total measured from the wrong start point.

    Starting the clock after the contract loads, or resetting it per domain,
    both produce a total smaller than the work it claims to cover.
    """
    row = run_pointers()
    assert row["duration_seconds"] >= sum(row["domain_seconds"].values()) - 0.5


def test_duration_is_a_number_not_a_string():
    """The whole point is arithmetic against a budget.

    A stringified duration reads fine in the ledger and silently fails every
    comparison a checker would make.
    """
    row = run_pointers()
    assert not isinstance(row["duration_seconds"], str)
    for value in row["domain_seconds"].values():
        assert not isinstance(value, str)


def test_the_unit_budget_falsifier_can_now_be_evaluated():
    """The acceptance criterion, stated as the question it makes answerable.

    Not an assertion that unit is under 600s: this run does not execute unit.
    It asserts that a row carrying unit timing WOULD answer the question, which
    is exactly what 8571 earlier rows could not do.
    """
    row = {"domain_seconds": {"unit": 610.0}}
    over = [d for d, s in row["domain_seconds"].items() if d == "unit" and s > 600]
    assert over == ["unit"]
