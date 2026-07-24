"""Tests for transitions.py: the depth-pass lifecycle as a guarded durable state machine.

AC-O1/O2: a pass moves drafted -> rubric-scored -> {kept|rejected} -> regression-tested ->
shipped, and reaching a later state without its predecessor is structurally impossible (an
allow-list graph, not the generic deny-list in cli.py). advance_pass reads the current state
(checkpoint-before), fails closed on an illegal jump, and persists to the state_transitions
table; undo is a compensating transition to 'reverted', never a literal state reversal. Real
sqlite via a tmp base_dir, no mocks.
"""
from __future__ import annotations

import sqlite3
import threading

import pytest
from hypothesis import given
from hypothesis import strategies as st

from intent_control_plane.schema import connect, initialize
from intent_control_plane.transitions import (
    GENESIS,
    PASS_LIFECYCLE,
    advance_pass,
    current_pass_state,
    is_allowed,
    revert_pass,
    transition_record,
)


def test_is_allowed_legal_lifecycle():
    assert is_allowed(None, GENESIS) is True
    assert is_allowed("drafted", "rubric-scored") is True
    assert is_allowed("rubric-scored", "kept") is True
    assert is_allowed("rubric-scored", "rejected") is True
    assert is_allowed("kept", "regression-tested") is True
    assert is_allowed("regression-tested", "shipped") is True


def test_is_allowed_blocks_predecessor_skips():
    assert is_allowed(None, "rubric-scored") is False  # first state must be the genesis
    assert is_allowed("drafted", "shipped") is False
    assert is_allowed("rubric-scored", "shipped") is False
    assert is_allowed("drafted", "kept") is False


def test_transition_record_sets_allowed_by_contract():
    legal = transition_record("subj-1", "drafted", "rubric-scored", "worker")
    assert legal["allowed_by_contract"] == 1
    assert legal["to_state"] == "rubric-scored"
    illegal = transition_record("subj-1", "drafted", "shipped", "worker")
    assert illegal["allowed_by_contract"] == 0
    for col in ("transition_id", "subject_id", "from_state", "to_state", "actor", "created_at_utc"):
        assert col in legal


def test_advance_pass_full_path_and_current_state(tmp_path):
    subj = "artifact-42"
    for state in ("drafted", "rubric-scored", "kept", "regression-tested", "shipped"):
        advance_pass(tmp_path, subj, state, "worker")
    assert current_pass_state(tmp_path, subj) == "shipped"


def test_advance_pass_fails_closed_on_illegal_jump(tmp_path):
    subj = "artifact-43"
    advance_pass(tmp_path, subj, "drafted", "worker")
    with pytest.raises(ValueError):
        advance_pass(tmp_path, subj, "shipped", "worker")  # skips predecessors
    assert current_pass_state(tmp_path, subj) == "drafted"  # illegal jump was not persisted


def test_revert_is_a_compensating_transition(tmp_path):
    subj = "artifact-44"
    for state in ("drafted", "rubric-scored", "kept", "regression-tested", "shipped"):
        advance_pass(tmp_path, subj, state, "worker")
    revert_pass(tmp_path, subj, "operator", reason="held-out regressed post-ship")
    assert current_pass_state(tmp_path, subj) == "reverted"


_STATES = [*PASS_LIFECYCLE.keys(), None]


@given(
    from_state=st.sampled_from(_STATES),
    to_state=st.sampled_from(list(PASS_LIFECYCLE.keys())),
)
def test_is_allowed_matches_the_graph(from_state, to_state):
    expected = (to_state == GENESIS) if from_state is None else (to_state in PASS_LIFECYCLE[from_state])
    assert is_allowed(from_state, to_state) is expected


def test_advance_pass_is_atomic_under_concurrency(tmp_path):
    # audit #14: check-then-insert across two unsynchronized connections let concurrent advances from
    # the same state both commit. The atomic BEGIN IMMEDIATE transaction must let exactly one of N
    # racing genesis advances persist; the losers re-read the updated state and fail closed.
    initialize(tmp_path)
    subj = "artifact-race"
    n = 12
    barrier = threading.Barrier(n)
    successes: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        try:
            advance_pass(tmp_path, subj, "drafted", "worker")
        except (ValueError, sqlite3.OperationalError):
            return
        with lock:
            successes.append("ok")

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with connect(tmp_path) as conn:
        count = conn.execute(
            "select count(*) as c from state_transitions where subject_id = ?", (subj,)
        ).fetchone()["c"]
    assert count == 1  # exactly one genesis transition persisted, not a race of duplicates
    assert len(successes) == 1
    assert current_pass_state(tmp_path, subj) == "drafted"
