"""Tests for routing.py: cost-aware per-pass model routing + advantage-conditioning (AC-D3).

Two mechanisms. select_model picks the next cheap-model arm cost-aware (reuses policy's Beta
posterior) but only among arms the remaining budget can afford, returning None when nothing is
affordable, that None is the hard budget cap that stops the depth loop. advantage_exemplars +
condition_prompt are RECAP: reuse the archive's kept variants as positive exemplars to steer the
next generation and surface rejected ones only as 'avoid' failure tags, never as content.
"""
from __future__ import annotations

import random

from intent_control_plane.routing import (
    advantage_exemplars,
    affordable_arms,
    condition_prompt,
    select_model,
)

ARMS = [
    {"name": "haiku", "wins": 6.0, "n": 10.0, "avg_cost": 100.0},
    {"name": "sonnet", "wins": 8.0, "n": 10.0, "avg_cost": 400.0},
    {"name": "opus", "wins": 9.0, "n": 10.0, "avg_cost": 1500.0},
]


def test_affordable_arms_filters_by_budget():
    assert [a["name"] for a in affordable_arms(ARMS, 400.0)] == ["haiku", "sonnet"]


def test_select_model_respects_hard_budget_cap():
    assert select_model(ARMS, random.Random(0), budget_remaining=150.0) == "haiku"  # only haiku affordable


def test_select_model_none_when_nothing_affordable():
    assert select_model(ARMS, random.Random(0), budget_remaining=50.0) is None  # hard cap -> stop


def test_select_model_deterministic_with_seed():
    first = select_model(ARMS, random.Random(3), budget_remaining=5000.0)
    second = select_model(ARMS, random.Random(3), budget_remaining=5000.0)
    assert first == second and first in {"haiku", "sonnet", "opus"}


def test_select_model_prefers_dominant_arm():
    arms = [
        {"name": "A", "wins": 9.0, "n": 10.0, "avg_cost": 100.0},   # better and cheaper
        {"name": "B", "wins": 1.0, "n": 10.0, "avg_cost": 500.0},
    ]
    for seed in range(5):
        assert select_model(arms, random.Random(seed), budget_remaining=5000.0) == "A"


def test_advantage_exemplars_positives_and_avoid_tags():
    variants = [
        {"verdict": "kept", "score": 0.9, "content": "great pass", "failure_tags": []},
        {"verdict": "kept", "score": 0.7, "content": "ok pass", "failure_tags": []},
        {"verdict": "rejected", "score": 0.0, "content": "broke tests", "failure_tags": ["tests_pass"]},
        {"verdict": "rejected", "score": 0.0, "content": "broke tests again", "failure_tags": ["tests_pass"]},
    ]
    exemplars = advantage_exemplars(variants, k_pos=1)
    assert [p["content"] for p in exemplars["positive"]] == ["great pass"]  # top kept only
    assert exemplars["avoid_tags"] == ["tests_pass"]


def test_condition_prompt_forces_positive_hides_negative_content():
    exemplars = {"positive": [{"score": 0.9, "content": "the good exemplar"}], "avoid_tags": ["tests_pass"]}
    prompt = condition_prompt("do the task", exemplars)
    assert "do the task" in prompt
    assert "the good exemplar" in prompt  # positive shown as content
    assert "tests_pass" in prompt  # negative surfaced only as an avoid-tag
