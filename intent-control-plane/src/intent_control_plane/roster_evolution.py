"""Reflective rehire + grow-on-gap for the virtual company, HUMAN-GATED (Layer 4, AC-C3/C4).

The company grades personas (company.py) and benches the weak ones. This module is how a benched
persona earns its way back and how the roster grows a new sub-persona for an uncovered task class,
but it deliberately does NOT act on its own. Every proposal carries requires_approval=True and
active=False, and apply_roster_change (the only path that would activate anything) refuses unless a
human explicitly approves. Rehire additionally passes a held-out non-regression gate before it is
even offered, so an overfit "improvement" cannot get promoted. This encodes the guardrail that
self-modification of the roster is proposed autonomously but applied only by a human.

Pure decision logic; no I/O.
"""
from __future__ import annotations

from typing import Any

from intent_control_plane.archive import keep_verdict

MODEL_LADDER = ["haiku", "sonnet", "opus"]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def propose_rehire(
    persona: str, card: dict[str, Any], current_model: str, current_principles: list[str]
) -> dict[str, Any]:
    """Propose a reflective rehire: escalate the model tier if possible, else sharpen the contract.

    Returns a proposal that REQUIRES human approval and is inactive; it is never applied here.
    """
    index = MODEL_LADDER.index(current_model) if current_model in MODEL_LADDER else 0
    next_model = MODEL_LADDER[min(index + 1, len(MODEL_LADDER) - 1)]
    change_type = "escalate-model" if next_model != current_model else "sharpen-principles"
    return {
        "persona": persona,
        "change_type": change_type,
        "from_model": current_model,
        "to_model": next_model,
        "proposed_principles": list(current_principles),
        "rationale": (
            f"{persona} underperforming (keep_rate {card.get('keep_rate')}, trust {card.get('trust')}); "
            f"{change_type}"
        ),
        "requires_approval": True,
        "active": False,
    }


def validate_rehire(
    proposal: dict[str, Any], held_out: list[float], held_out_baselines: list[float]
) -> str:
    """Gate a rehire on held-out non-regression before offering it to the human.

    approved-pending-human only if the mutated persona beats the mean baseline and regresses no
    individual held-out case (reuses the archive's keep_verdict); rejected otherwise. Fails closed
    when either held-out list is empty: no evidence never approves (audit #6).
    """
    if not held_out or not held_out_baselines:
        return "rejected"
    baseline = _mean(held_out_baselines)
    verdict = keep_verdict(_mean(held_out), baseline, held_out=held_out, held_out_baselines=held_out_baselines)
    return "approved-pending-human" if verdict == "kept" else "rejected"


def detect_coverage_gap(needed_classes: list[str], roster: dict[str, dict[str, Any]]) -> list[str]:
    """Task classes no ACTIVE persona covers (a benched persona's coverage does not count).

    This is the topology-fitness check: rather than fan a swarm into an uncovered class, grow a
    persona for it (grow-on-gap).
    """
    covered: set[str] = set()
    for info in roster.values():
        if str(info.get("status", "active")) == "active":
            covered.update(info.get("covers", []))
    return [task_class for task_class in needed_classes if task_class not in covered]


def propose_new_persona(gap_class: str, seed_principles: list[str]) -> dict[str, Any]:
    """Propose a new sub-persona for a coverage gap. Gated: requires approval and starts inactive."""
    return {
        "persona": f"{gap_class}-specialist",
        "change_type": "spawn",
        "covers": [gap_class],
        "proposed_principles": list(seed_principles),
        "rationale": f"roster has no active persona covering '{gap_class}'",
        "requires_approval": True,
        "active": False,
    }


def apply_roster_change(proposal: dict[str, Any], human_approved: bool) -> dict[str, Any]:
    """The ONLY path that would activate a rehire or spawn: refuses unless a human approves.

    This is the hard human-gate. Nothing in the harness calls it with human_approved=True
    automatically, so roster evolution proposes on its own but never acts on its own.
    """
    if not human_approved:
        return {"applied": False, "reason": "awaiting human approval", "proposal": proposal}
    return {"applied": True, "persona": proposal["persona"], "active": True, "proposal": proposal}
