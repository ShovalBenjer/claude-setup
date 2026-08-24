"""Layer 4 - the company: grade personas, then PIP or bench, from archived variants.

The virtual company runs the self-evolving-agent population loop as HR: each persona is graded on
the variants it produced (archive.py), and the roster status decides who is active, on a PIP, or
benched. Two guardrails are load-bearing. Failure costs more trust than success earns (asymmetric
earned trust, the +5/-15 pattern), so a persona cannot coast on a few wins after repeated misses.
And a persona is never demoted on noise: below a minimum sample count it stays active regardless
of a bad streak (statistical-significance guard). A benched persona is not deleted; the archive
keeps its failure-tagged history so it can be reflectively rehired later (a stepping stone, per
Darwin-Godel-Machine). Reflective rehire and grow-on-gap (AC-C3/C4) are later slices.

Pure decision logic over a list of variant rows; no I/O of its own (it reads via
archive.read_variants at the call site).
"""
from __future__ import annotations

from typing import Any


def trust_score(
    verdicts: list[str],
    start: float = 50.0,
    up: float = 5.0,
    down: float = 15.0,
    floor: float = 0.0,
    ceil: float = 100.0,
) -> float:
    """Asymmetric earned trust: +up on 'kept', -down on a 'rejected'* failure, neutral otherwise, clamped.

    Failure is penalized harder than success is rewarded, so trust reflects reliability, not a lucky
    recent win. A neutral verdict like 'scored' (a live spawn screened but not judged) carries no
    trust signal and must not move the score, or every un-judged spawn would silently tank a persona
    (audit #11). Clamped to [floor, ceil] so it reads as a stable 0-100 trust level.
    """
    value = start
    for verdict in verdicts:
        if verdict == "kept":
            value += up
        elif verdict.startswith("rejected"):
            value -= down
        value = max(floor, min(ceil, value))
    return round(value, 3)


def persona_scorecard(variants: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-persona grade from archived variants: n, kept, keep_rate, avg_score, cost, trust."""
    order: dict[str, list[str]] = {}
    agg: dict[str, dict[str, float]] = {}
    for row in variants:
        persona = str(row.get("persona", "?"))
        verdict = str(row.get("verdict", ""))
        bucket = agg.setdefault(persona, {"n": 0.0, "kept": 0.0, "score_sum": 0.0, "cost_sum": 0.0})
        bucket["n"] += 1
        if verdict == "kept":
            bucket["kept"] += 1
        score = row.get("score")
        if isinstance(score, int | float):
            bucket["score_sum"] += float(score)
        cost = row.get("cost_tokens")
        if isinstance(cost, int | float):
            bucket["cost_sum"] += float(cost)
        order.setdefault(persona, []).append(verdict)
    out: dict[str, dict[str, Any]] = {}
    for persona, bucket in agg.items():
        n = bucket["n"]
        out[persona] = {
            "n": int(n),
            "kept": int(bucket["kept"]),
            "keep_rate": round(bucket["kept"] / n, 3) if n else 0.0,
            "avg_score": round(bucket["score_sum"] / n, 3) if n else 0.0,
            "cost_sum": int(bucket["cost_sum"]),
            "trust": trust_score(order[persona]),
        }
    return out


def roster_status(
    scorecard: dict[str, dict[str, Any]],
    min_samples: int = 5,
    pip_below: float = 0.5,
    fire_below: float = 0.25,
) -> dict[str, str]:
    """Map each persona to active / pip / benched from its keep_rate, with a significance guard.

    Below min_samples the persona stays active: too little evidence to demote, so noise never
    fires a good agent (the #1 way an automated HR loop goes wrong). At or above the threshold,
    keep_rate < fire_below benches (fired-but-archived), keep_rate < pip_below is a PIP.
    """
    status: dict[str, str] = {}
    for persona, card in scorecard.items():
        n = int(card.get("n", 0))
        keep_rate = float(card.get("keep_rate", 0.0))
        if n < min_samples:
            status[persona] = "active"
        elif keep_rate < fire_below:
            status[persona] = "benched"
        elif keep_rate < pip_below:
            status[persona] = "pip"
        else:
            status[persona] = "active"
    return status
