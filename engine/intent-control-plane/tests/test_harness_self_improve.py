"""Regression guards for the G1 self-improve decision logic.

These freeze the two fixes made on 2026-07-09: the reachability regex must see
uppercase skill names (LTMD), and the reflect prompt must name the concrete
verifier for the self-improve class.
"""
from __future__ import annotations

from intent_control_plane.harness.self_improve import (
    build_reflect_prompt,
    reflect_verifier,
    unreachable_skills,
)


def test_unreachable_skills_flags_only_unrouted():
    routed = {"LTMD", "decision-grade", "feature-investor"}
    inventory = ["LTMD", "decision-grade", "feature-investor", "meme-control"]
    assert unreachable_skills(inventory, routed) == ["meme-control"]


def test_unreachable_skills_empty_routed_marks_all():
    assert unreachable_skills(["a", "b"], set()) == ["a", "b"]


def test_reflect_verifier_names_self_improve_for_g1():
    assert reflect_verifier("Daily gastown self-improvement check (G1)") == (
        "python3 ~/.claude/bin/self-improve.py"
    )
    assert reflect_verifier("self-improve report tweak") == "python3 ~/.claude/bin/self-improve.py"


def test_reflect_verifier_generic_for_other_classes():
    v = reflect_verifier("fix the widget dashboard cold start")
    assert "self-improve.py" not in v


def test_build_reflect_prompt_forces_explicit_verification():
    p = build_reflect_prompt("Daily gastown self-improvement check (G1)", ["explicit_verification"])
    assert "explicit_verification" in p
    assert "python3 ~/.claude/bin/self-improve.py" in p
    assert "do not answer with only a proposal" in p
