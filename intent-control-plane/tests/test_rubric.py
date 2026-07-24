"""Tests for rubric.py: the decomposed weighted rubric where deterministic checks DISPOSE.

Constraint 2 of the spec: a single holistic judge score is a reward-hacking surface, so each axis
is an independent weighted criterion, and where a deterministic check exists (tests/lint/types)
it DISPOSES the reward rather than being averaged in. A failing deterministic criterion sends the
whole score to 0, no matter how high the judge (craft) score is.
"""
from __future__ import annotations

from intent_control_plane.rubric import score_rubric

CRITERIA = [
    {"name": "tests_pass", "weight": 2.0, "kind": "deterministic"},
    {"name": "craft", "weight": 1.0, "kind": "judge"},
]


def test_weighted_mean_when_all_pass():
    result = score_rubric(CRITERIA, {"tests_pass": 1.0, "craft": 0.6})
    assert result["disposed"] is False
    assert result["overall"] == round((2.0 * 1.0 + 1.0 * 0.6) / 3.0, 4)


def test_deterministic_failure_disposes_reward():
    # craft is a near-perfect 0.99, but tests fail -> the whole reward is disposed to 0.
    result = score_rubric(CRITERIA, {"tests_pass": 0.0, "craft": 0.99})
    assert result["disposed"] is True
    assert result["overall"] == 0.0
    assert "tests_pass" in result["disposed_by"]


def test_missing_criterion_scores_zero():
    result = score_rubric(CRITERIA, {"tests_pass": 1.0})
    assert result["per_criterion"]["craft"] == 0.0
    assert result["disposed"] is False


def test_judge_only_rubric_is_plain_weighted_mean():
    criteria = [{"name": "a", "weight": 1.0, "kind": "judge"}, {"name": "b", "weight": 3.0, "kind": "judge"}]
    result = score_rubric(criteria, {"a": 1.0, "b": 0.0})
    assert result["overall"] == round(1.0 / 4.0, 4)
    assert result["disposed"] is False
