"""Tests for durable.py: the A-seam DurableBackend Protocol and its InMemoryBackend.

Proves transitions.py is swappable behind a narrow interface without a rewrite: InMemoryBackend
enforces the exact same allow-list as transitions.PASS_LIFECYCLE (by importing is_allowed, not
re-deriving the graph), fails closed on an illegal jump, tracks the latest state per subject, and
supports a compensating revert. No sqlite, no mocks: InMemoryBackend is a real in-process
implementation, and the Protocol conformance check is isinstance-free (it just calls the methods
through a DurableBackend-typed reference, which is also what makes mypy check it structurally).
"""
from __future__ import annotations

import pytest

from intent_control_plane.durable import DurableBackend, InMemoryBackend


def test_in_memory_backend_advances_the_legal_lifecycle():
    backend = InMemoryBackend()
    subj = "artifact-1"
    for state in ("drafted", "rubric-scored", "kept", "regression-tested", "shipped"):
        record = backend.advance(subj, state)
        assert record["to_state"] == state
        assert record["allowed_by_contract"] == 1
    assert backend.current_state(subj) == "shipped"


def test_in_memory_backend_fails_closed_on_illegal_jump():
    backend = InMemoryBackend()
    subj = "artifact-2"
    backend.advance(subj, "drafted")
    with pytest.raises(ValueError):
        backend.advance(subj, "shipped")  # skips rubric-scored/kept/regression-tested
    # the illegal jump must not have been persisted
    assert backend.current_state(subj) == "drafted"


def test_current_state_tracks_the_latest_transition():
    backend = InMemoryBackend()
    subj = "artifact-3"
    assert backend.current_state(subj) is None  # no history yet
    backend.advance(subj, "drafted")
    assert backend.current_state(subj) == "drafted"
    backend.advance(subj, "rubric-scored")
    assert backend.current_state(subj) == "rubric-scored"
    backend.advance(subj, "kept")
    assert backend.current_state(subj) == "kept"


def test_compensate_moves_to_reverted():
    backend = InMemoryBackend()
    subj = "artifact-4"
    for state in ("drafted", "rubric-scored", "kept"):
        backend.advance(subj, state)
    record = backend.compensate(subj, "operator")
    assert record["to_state"] == "reverted"
    assert record["actor"] == "operator"
    assert backend.current_state(subj) == "reverted"


def test_compensate_fails_closed_when_reverted_is_not_a_legal_edge():
    backend = InMemoryBackend()
    subj = "artifact-5"
    backend.advance(subj, "drafted")
    with pytest.raises(ValueError):
        backend.compensate(subj, "operator")  # 'reverted' is only legal from kept/shipped
    assert backend.current_state(subj) == "drafted"


def test_in_memory_backend_satisfies_the_durable_backend_protocol_structurally():
    # Isinstance-free: assign to a DurableBackend-typed reference and drive it purely through
    # the Protocol's three methods. mypy structurally checks this assignment at type-check time;
    # at runtime this proves the object actually behaves like the seam, not merely looks like it.
    backend: DurableBackend = InMemoryBackend(actor="swarm-worker")
    subj = "artifact-6"
    assert backend.current_state(subj) is None
    first = backend.advance(subj, "drafted")
    assert first["actor"] == "swarm-worker"
    backend.advance(subj, "rubric-scored")
    backend.advance(subj, "kept")
    reverted = backend.compensate(subj, "operator")
    assert reverted["to_state"] == "reverted"
    assert backend.current_state(subj) == "reverted"
