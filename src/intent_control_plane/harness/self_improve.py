"""Pure decision logic for the G1 self-improvement loop.

Extracted from ~/.claude/bin/self-improve.py so the two error-prone pieces, the
skill-reachability check and the Codex reflect prompt, are unit-tested. The
script keeps the I/O (intent CLI subprocess, Codex call, report write) and
imports these.
"""
from __future__ import annotations


def unreachable_skills(inventory: list[str], routed: set[str]) -> list[str]:
    """Installed skills the router cannot surface (wire a route or prune).

    `routed` is router.routed_skill_names(): the authoritative set the router can
    emit, not a regex scrape of a source file (which broke when the router logic
    moved out of the hook into the package).
    """
    return [s for s in inventory if s not in routed]


def reflect_verifier(goal: str) -> str:
    """The concrete verifier command to name for this intent class, or a generic hint."""
    g = (goal or "").lower()
    if "self-improve" in g or "gastown self-improvement" in g:
        return "python3 ~/.claude/bin/self-improve.py"
    return "the exact verifier command for this intent"


def build_reflect_prompt(goal: str, proof: list[str]) -> str:
    """Codex reflect prompt that forces an explicit_verification line, not just a proposal."""
    verifier = reflect_verifier(goal)
    return (
        f"You are improving a personal Claude+Codex agent setup. This intent finished WITHOUT its "
        f"required proof: goal={goal!r}, proof_required={proof}. Propose ONE concrete, minimal change "
        f"(to a specific hook, the prompt-router, or a skill) that would make this class of task attach "
        f"its proof automatically next time. One short paragraph, name the file to change. "
        f"Before finalizing, run {verifier} and include an explicit_verification line with the command, "
        f"exit status, and output path or snippet; do not answer with only a proposal when "
        f"proof_required includes explicit_verification."
    )
