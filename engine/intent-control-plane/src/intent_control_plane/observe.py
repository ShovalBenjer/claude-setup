"""Observability aggregation: the dashboard DATA layer, not a GUI (A4).

Pure aggregation over telemetry-like rows (the shape policy.telemetry_row emits:
strategy, status, subagent_tokens, duration_ms) and over Foundry usage-ledger rows
(token_input, token_output). No I/O, no rendering: callers (a CLI command, tower.py,
or a future dashboard panel) read a jsonl ledger and hand the parsed rows here.
"""
from __future__ import annotations

import math
from typing import Any


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile: the ceil(pct/100 * n)-th smallest value (1-indexed).

    Stdlib-only (math.ceil), no interpolation. Empty input returns 0.0.
    """
    n = len(sorted_values)
    if n == 0:
        return 0.0
    rank = min(n, max(1, math.ceil(pct / 100.0 * n)))
    return sorted_values[rank - 1]


def _row_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Shared aggregation core for one bucket of rows (overall or one strategy)."""
    n = len(rows)
    if n == 0:
        return {"n": 0, "success_rate": 0.0, "avg_tokens": 0.0, "durations": []}
    wins = 0
    tokens_sum = 0.0
    durations: list[float] = []
    for row in rows:
        if str(row.get("status", "")) == "green":
            wins += 1
        tokens = row.get("subagent_tokens")
        if isinstance(tokens, int | float) and not isinstance(tokens, bool):
            tokens_sum += tokens
        duration = row.get("duration_ms")
        if isinstance(duration, int | float) and not isinstance(duration, bool):
            durations.append(duration)
    return {
        "n": n,
        "success_rate": round(wins / n, 3),
        "avg_tokens": round(tokens_sum / n, 1),
        "durations": durations,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate telemetry rows into overall + per-strategy stats.

    Returns {n, success_rate, avg_tokens, p50_ms, p95_ms, by_strategy}. Non-dict rows
    are skipped, not fatal. Missing/non-numeric subagent_tokens or duration_ms are
    treated as absent (tokens contribute 0 to the average, durations are excluded
    from the percentile set). Empty input is safe (all-zero result).
    """
    clean = [row for row in rows if isinstance(row, dict)]
    overall = _row_stats(clean)
    durations = sorted(overall.pop("durations"))
    overall["p50_ms"] = _percentile(durations, 50)
    overall["p95_ms"] = _percentile(durations, 95)

    by_strategy: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in clean:
        strat = str(row.get("strategy", "?"))
        grouped.setdefault(strat, []).append(row)
    for strat, strat_rows in grouped.items():
        stats = _row_stats(strat_rows)
        stats.pop("durations")
        by_strategy[strat] = stats

    overall["by_strategy"] = by_strategy
    return overall


def cost_summary(foundry_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum token_input/token_output across Foundry usage-ledger rows.

    Returns {total_input, total_output, calls}. Non-dict rows are skipped entirely
    (not counted as a call); non-numeric token fields on a real row contribute 0 but
    the row still counts as a call.
    """
    total_input = 0.0
    total_output = 0.0
    calls = 0
    for row in foundry_rows:
        if not isinstance(row, dict):
            continue
        calls += 1
        token_in = row.get("token_input")
        if isinstance(token_in, int | float) and not isinstance(token_in, bool):
            total_input += token_in
        token_out = row.get("token_output")
        if isinstance(token_out, int | float) and not isinstance(token_out, bool):
            total_output += token_out
    return {"total_input": total_input, "total_output": total_output, "calls": calls}
