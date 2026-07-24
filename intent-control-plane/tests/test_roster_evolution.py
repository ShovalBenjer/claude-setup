"""Tests for roster_evolution.py: reflective rehire + grow-on-gap, HUMAN-GATED (AC-C3/C4).

The company can propose to rehire a benched persona (escalate its model tier, sharpen its
contract) or spawn a new sub-persona for a coverage gap, but it never acts on those proposals
itself: apply_roster_change is the only activation path and it refuses unless a human explicitly
approves. Every proposal carries requires_approval=True and active=False. Rehire must also pass a
held-out non-regression gate before it is even offered to the human.
"""
from __future__ import annotations

from intent_control_plane.roster_evolution import (
    apply_roster_change,
    detect_coverage_gap,
    propose_new_persona,
    propose_rehire,
    validate_rehire,
)


def test_propose_rehire_escalates_model_tier():
    proposal = propose_rehire("Weak", {"keep_rate": 0.1, "trust": 20.0}, current_model="haiku", current_principles=["p1"])
    assert proposal["change_type"] == "escalate-model"
    assert proposal["to_model"] == "sonnet"
    assert proposal["requires_approval"] is True
    assert proposal["active"] is False


def test_propose_rehire_top_tier_sharpens_instead():
    proposal = propose_rehire("Weak", {"keep_rate": 0.1, "trust": 20.0}, current_model="opus", current_principles=["p1"])
    assert proposal["change_type"] == "sharpen-principles"
    assert proposal["to_model"] == "opus"  # already top tier, cannot escalate


def test_validate_rehire_held_out_gate():
    proposal = propose_rehire("Weak", {"keep_rate": 0.1}, current_model="haiku", current_principles=[])
    assert validate_rehire(proposal, held_out=[0.8, 0.9], held_out_baselines=[0.7, 0.7]) == "approved-pending-human"
    assert validate_rehire(proposal, held_out=[0.5, 0.9], held_out_baselines=[0.8, 0.7]) == "rejected"  # regressed a neighbor


def test_validate_rehire_fails_closed_without_held_out_evidence():
    # audit #6: an empty held-out set is no evidence; the gate must reject, never approve on absence.
    proposal = propose_rehire("Weak", {"keep_rate": 0.1}, current_model="haiku", current_principles=[])
    assert validate_rehire(proposal, held_out=[], held_out_baselines=[]) == "rejected"
    assert validate_rehire(proposal, held_out=[0.9], held_out_baselines=[]) == "rejected"


def test_detect_coverage_gap_only_counts_active_personas():
    roster = {
        "Engineering Firm": {"covers": ["code"], "status": "active"},
        "Product Studio": {"covers": ["ui"], "status": "benched"},  # benched -> its coverage does not count
    }
    gaps = detect_coverage_gap(["code", "ui", "data"], roster)
    assert set(gaps) == {"ui", "data"}


def test_propose_new_persona_is_gated():
    proposal = propose_new_persona("data", seed_principles=["own the data boundary"])
    assert proposal["change_type"] == "spawn"
    assert proposal["covers"] == ["data"]
    assert proposal["requires_approval"] is True
    assert proposal["active"] is False


def test_apply_roster_change_refuses_without_human_approval():
    proposal = propose_new_persona("data", seed_principles=[])
    blocked = apply_roster_change(proposal, human_approved=False)
    assert blocked["applied"] is False
    approved = apply_roster_change(proposal, human_approved=True)
    assert approved["applied"] is True
    assert approved["active"] is True
