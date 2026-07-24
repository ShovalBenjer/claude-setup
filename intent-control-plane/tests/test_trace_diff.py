"""Tests for the deterministic trace-diff core module."""
from __future__ import annotations

from intent_control_plane.trace_diff import diff_traces


def test_identical_traces_report_identical():
    recorded = [{"step": 1}, {"step": 2}, {"step": 3}]
    candidate = [{"step": 1}, {"step": 2}, {"step": 3}]
    result = diff_traces(recorded, candidate)
    assert result["identical"] is True
    assert result["first_divergence"] is None
    assert result["diverged_indices"] == []
    assert result["divergence_rate"] == 0.0


def test_one_differing_step_in_the_middle_is_found():
    recorded = [{"step": 1}, {"step": 2}, {"step": 3}]
    candidate = [{"step": 1}, {"step": "DIFFERENT"}, {"step": 3}]
    result = diff_traces(recorded, candidate)
    assert result["identical"] is False
    assert result["diverged_indices"] == [1]
    assert result["first_divergence"] == 1


def test_candidate_shorter_than_recorded_marks_missing_tail_diverged():
    recorded = [{"step": 1}, {"step": 2}, {"step": 3}]
    candidate = [{"step": 1}]
    result = diff_traces(recorded, candidate)
    assert result["identical"] is False
    assert result["diverged_indices"] == [1, 2]
    assert result["first_divergence"] == 1
    assert result["n_recorded"] == 3
    assert result["n_candidate"] == 1


def test_candidate_longer_than_recorded_marks_extra_tail_diverged():
    recorded = [{"step": 1}]
    candidate = [{"step": 1}, {"step": 2}, {"step": 3}]
    result = diff_traces(recorded, candidate)
    assert result["identical"] is False
    assert result["diverged_indices"] == [1, 2]
    assert result["first_divergence"] == 1
    assert result["n_recorded"] == 1
    assert result["n_candidate"] == 3


def test_ignore_keys_virtualizes_the_clock():
    recorded = [{"v": 1, "ts": "a"}]
    candidate = [{"v": 1, "ts": "b"}]
    result = diff_traces(recorded, candidate, ignore_keys=("ts",))
    assert result["identical"] is True
    assert result["diverged_indices"] == []


def test_ignore_keys_strips_nested_and_listed_fields():
    # the clock is virtualized at every depth, not just the top level
    recorded = [{"op": "call", "payload": {"v": 1, "ts": "a"}, "items": [{"id": "x", "n": 1}]}]
    candidate = [{"op": "call", "payload": {"v": 1, "ts": "b"}, "items": [{"id": "y", "n": 1}]}]
    assert diff_traces(recorded, candidate, ignore_keys=("ts", "id"))["identical"] is True
    # a real nested change (payload.v) still diverges even with ignore_keys set
    candidate2 = [{"op": "call", "payload": {"v": 2, "ts": "b"}, "items": [{"id": "y", "n": 1}]}]
    assert diff_traces(recorded, candidate2, ignore_keys=("ts", "id"))["identical"] is False


def test_without_ignore_keys_same_traces_diverge():
    recorded = [{"v": 1, "ts": "a"}]
    candidate = [{"v": 1, "ts": "b"}]
    result = diff_traces(recorded, candidate)
    assert result["identical"] is False
    assert result["diverged_indices"] == [0]


def test_both_empty_traces_are_identical_no_zero_division():
    result = diff_traces([], [])
    assert result["identical"] is True
    assert result["divergence_rate"] == 0.0
    assert result["n_recorded"] == 0
    assert result["n_candidate"] == 0
    assert result["first_divergence"] is None


def test_divergence_rate_math_one_of_four():
    recorded = [{"step": 1}, {"step": 2}, {"step": 3}, {"step": 4}]
    candidate = [{"step": 1}, {"step": "X"}, {"step": 3}, {"step": 4}]
    result = diff_traces(recorded, candidate)
    assert result["divergence_rate"] == 0.25
