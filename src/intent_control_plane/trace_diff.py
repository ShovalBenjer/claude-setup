"""Deterministic trace-diff core: PRD T4.4 / mojuco sim2real rung 4.

We already log every a2a call and intent event as JSON. Deterministic trace
replay runs a recorded trace against a candidate model or prompt and diffs
the divergence, step by step. Volatile fields (timestamps, ids) are excluded
from comparison via ignore_keys, so the clock is virtualized and only real
behavioral divergence shows.

This is the pure diff core: comparing a recorded trace to a candidate trace
and reporting where they diverge. The actual replay-against-a-model wiring
(running the candidate to produce its trace) is separate, shared-HOME work;
this module is self-contained and unwired by design.
"""
from __future__ import annotations

import json
from typing import Any

_MISSING = object()


def _strip(obj: object, ignore_keys: tuple[str, ...]) -> object:
    """Recursively drop ignore_keys from dicts at every depth (and inside lists)."""
    if isinstance(obj, dict):
        return {k: _strip(v, ignore_keys) for k, v in obj.items() if k not in ignore_keys}
    if isinstance(obj, list):
        return [_strip(x, ignore_keys) for x in obj]
    return obj


def _canonical(step: object, ignore_keys: tuple[str, ...]) -> str:
    """Canonical string form of one trace step, for equality comparison.

    ignore_keys are dropped RECURSIVELY (every nested dict, and dicts inside
    lists), which virtualizes the clock at any depth: pass
    ignore_keys=("ts", "timestamp", "id") to ignore volatile fields wherever
    they sit, not just at the top level (a nested payload.ts or an id inside a
    list of tool calls no longer produces a false divergence).
    """
    return json.dumps(_strip(step, ignore_keys), sort_keys=True, default=str)


def diff_traces(
    recorded: list[Any], candidate: list[Any], ignore_keys: tuple[str, ...] = ()
) -> dict[str, Any]:
    """Compare recorded and candidate traces step by step, return the divergence summary."""
    n_recorded = len(recorded)
    n_candidate = len(candidate)
    n_steps = max(n_recorded, n_candidate)

    diverged_indices: list[int] = []
    for index in range(n_steps):
        recorded_step = recorded[index] if index < n_recorded else _MISSING
        candidate_step = candidate[index] if index < n_candidate else _MISSING
        if recorded_step is _MISSING or candidate_step is _MISSING:
            diverged_indices.append(index)
            continue
        if _canonical(recorded_step, ignore_keys) != _canonical(candidate_step, ignore_keys):
            diverged_indices.append(index)

    identical = not diverged_indices
    divergence_rate = 0.0 if n_steps == 0 else len(diverged_indices) / n_steps

    return {
        "n_recorded": n_recorded,
        "n_candidate": n_candidate,
        "first_divergence": diverged_indices[0] if diverged_indices else None,
        "diverged_indices": diverged_indices,
        "identical": identical,
        "divergence_rate": divergence_rate,
    }
