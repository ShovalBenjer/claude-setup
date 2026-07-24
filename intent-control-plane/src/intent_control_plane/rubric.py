"""Decomposed weighted rubric: deterministic checks DISPOSE the reward, judges only propose.

Constraint 2 of the depth-harness spec. A single holistic LLM-judge score is a documented
reward-hacking surface, so the rubric is a list of independent weighted criteria. A criterion is
either 'deterministic' (a test/lint/type/schema check: pass is 1.0, anything less fails) or
'judge' (a model rating in [0, 1]). If ANY deterministic criterion fails, the whole reward is
disposed to 0 regardless of the judge scores, so a swarm worker cannot buy a high score by
pleasing the judge while breaking the build. Otherwise the overall is the weighted mean.

Pure function, no I/O.
"""
from __future__ import annotations

from typing import Any


def score_rubric(criteria: list[dict[str, Any]], results: dict[str, float]) -> dict[str, Any]:
    """Score one candidate against the decomposed rubric.

    criteria: [{name, weight, kind: 'deterministic'|'judge'}]. results: criterion name -> score in
    [0, 1] (a missing criterion scores 0). Returns overall, per_criterion, disposed, disposed_by.
    """
    per_criterion: dict[str, float] = {}
    disposed_by: list[str] = []
    total_weight = 0.0
    weighted_sum = 0.0
    for criterion in criteria:
        name = str(criterion["name"])
        weight = float(criterion.get("weight", 1.0))
        kind = str(criterion.get("kind", "judge"))
        score = float(results.get(name, 0.0))
        per_criterion[name] = score
        if kind == "deterministic" and score < 1.0:
            disposed_by.append(name)
        total_weight += weight
        weighted_sum += weight * score
    disposed = bool(disposed_by)
    overall = 0.0 if disposed else (round(weighted_sum / total_weight, 4) if total_weight else 0.0)
    return {
        "overall": overall,
        "per_criterion": per_criterion,
        "disposed": disposed,
        "disposed_by": disposed_by,
    }
