"""Cost-aware per-pass model routing + advantage-conditioning (AC-D3).

Two mechanisms for the depth engine. select_model chooses which cheap-model arm runs the next
pass, cost-aware (reusing policy's Beta posterior, so a model with no history is still explored),
but only among arms the remaining budget can afford; when nothing is affordable it returns None,
and that None is the hard budget cap that stops the loop (Budget-Aware Agentic Routing). Advantage-
conditioning (RECAP) squeezes a second use out of the eval scores already paid for: kept variants
become positive exemplars that steer the next generation, and rejected ones are surfaced only as
'avoid' failure tags, never as content, so the model is pulled toward good passes without being
shown how to reproduce bad ones.

Pure decision logic, no I/O; the archive rows it reads come from archive.read_variants at the call
site.
"""
from __future__ import annotations

import math
import random
from typing import Any

from intent_control_plane.policy import beta_posterior


def affordable_arms(arms: list[dict[str, Any]], budget_remaining: float) -> list[dict[str, Any]]:
    """The arms whose average cost the remaining budget can still cover."""
    return [arm for arm in arms if float(arm.get("avg_cost", 0.0)) <= budget_remaining]


def select_model(
    arms: list[dict[str, Any]], rng: random.Random, budget_remaining: float, lam: float = 0.5
) -> str | None:
    """Cost-aware Thompson pick among affordable arms; None when the budget affords nothing (hard cap).

    arms: [{name, wins, n, avg_cost}]. Samples each arm's success rate from Beta(posterior), then
    subtracts lam * (its cost / max affordable cost). The argmax wins. Deterministic for a seeded rng.
    """
    pool = affordable_arms(arms, budget_remaining)
    if not pool:
        return None
    max_cost = max((float(arm.get("avg_cost", 0.0)) for arm in pool), default=0.0) or 1.0
    best: str | None = None
    best_score = -math.inf
    for arm in pool:
        alpha, beta = beta_posterior(float(arm.get("wins", 0.0)), float(arm.get("n", 0.0)))
        sampled = rng.betavariate(alpha, beta)
        score = sampled - lam * (float(arm.get("avg_cost", 0.0)) / max_cost)
        if score > best_score:
            best = str(arm["name"])
            best_score = score
    return best


def advantage_exemplars(variants: list[dict[str, Any]], k_pos: int = 3) -> dict[str, Any]:
    """RECAP: top-k KEPT variants as positive exemplars; aggregated failure_tags from REJECTED ones.

    The rejected variants contribute only their failure tags (an 'avoid' signal), never their
    content, so conditioning steers toward good passes without teaching the bad ones.
    """
    kept = [v for v in variants if v.get("verdict") == "kept"]
    rejected = [v for v in variants if v.get("verdict") == "rejected"]
    positives = sorted(kept, key=lambda v: float(v.get("score", 0.0)), reverse=True)[:k_pos]
    tag_counts: dict[str, int] = {}
    for variant in rejected:
        for tag in variant.get("failure_tags") or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    avoid = sorted(tag_counts, key=lambda tag: (-tag_counts[tag], tag))
    return {"positive": positives, "avoid_tags": avoid}


def condition_prompt(task: str, exemplars: dict[str, Any]) -> str:
    """Compose the next-pass prompt: the task, positive exemplars (force-positive), and avoid tags."""
    lines = [task]
    positives = exemplars.get("positive") or []
    if positives:
        lines.append("Build on these high-scoring passes and match their quality:")
        lines.extend(
            f"- [{exemplar.get('score')}] {str(exemplar.get('content', ''))[:200]}" for exemplar in positives
        )
    avoid = exemplars.get("avoid_tags") or []
    if avoid:
        lines.append("Avoid these failure modes: " + ", ".join(str(tag) for tag in avoid))
    return "\n".join(lines)
