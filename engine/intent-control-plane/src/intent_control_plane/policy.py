"""Strategy bandit: which orchestration strategy (workflow/subagent/solo) wins, from telemetry.

Closes the /loop measurement intent (know which implementation strategies are better by
recording data over time). Each strategy outcome is logged as a telemetry row; strategy_stats
aggregates the rows into a Beta posterior over success; recommend_strategy Thompson-samples a
cost-aware pick so the harness biases toward what actually works, without upgrading the model.

Pure decision logic (strategy_stats, beta_posterior, recommend_strategy, telemetry_row) is
unit-tested; append_telemetry is the only I/O (one append to the jsonl ledger).
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from intent_control_plane.util import utc_now

TELEMETRY_LOG = Path.home() / ".claude" / "cache" / "orchestration" / "telemetry.jsonl"

# Strategies the router can choose between (the set the bandit explores).
STRATEGIES = ("workflow", "subagent", "solo", "parallel_agents")


def strategy_stats(lines: list[str], task_type: str | None = None) -> dict[str, dict[str, Any]]:
    """Per-strategy aggregates from telemetry.jsonl lines.

    Each bucket: n, wins (status == 'green'), pass_rate, avg_tokens, avg_ms (over rows carrying a
    numeric duration). Malformed or non-dict lines are skipped, not fatal. When task_type is set,
    only rows with that task_type (default 'general') are counted, so the comparison is per-kind.
    """
    agg: dict[str, dict[str, float]] = {}
    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if task_type is not None and str(row.get("task_type", "general")) != task_type:
            continue
        strat = str(row.get("strategy", "?"))
        bucket = agg.setdefault(
            strat, {"n": 0.0, "wins": 0.0, "tokens_sum": 0.0, "ms_sum": 0.0, "ms_n": 0.0}
        )
        bucket["n"] += 1
        if str(row.get("status", "")) == "green":
            bucket["wins"] += 1
        tokens = row.get("subagent_tokens")
        if isinstance(tokens, int | float):
            bucket["tokens_sum"] += tokens
        duration = row.get("duration_ms")
        if isinstance(duration, int | float):
            bucket["ms_sum"] += duration
            bucket["ms_n"] += 1
    out: dict[str, dict[str, Any]] = {}
    for strat, bucket in agg.items():
        n = bucket["n"]
        out[strat] = {
            "n": n,
            "wins": bucket["wins"],
            "pass_rate": round(bucket["wins"] / n, 3) if n else 0.0,
            "avg_tokens": round(bucket["tokens_sum"] / n, 1) if n else 0.0,
            "avg_ms": round(bucket["ms_sum"] / bucket["ms_n"], 1) if bucket["ms_n"] else None,
        }
    return out


def strategy_by_task_type(lines: list[str]) -> dict[str, dict[str, dict[str, Any]]]:
    """Cross-tab {task_type: {strategy: stats}}, the "which strategy wins for which kind of task" readout.

    Groups rows by task_type, then reuses strategy_stats per group so the per-strategy aggregation
    stays single-sourced. Rows without a task_type fall in the 'general' bucket.
    """
    grouped: dict[str, list[str]] = {}
    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        grouped.setdefault(str(row.get("task_type", "general")), []).append(text)
    return {ttype: strategy_stats(group) for ttype, group in grouped.items()}


def beta_posterior(wins: float, n: float) -> tuple[float, float]:
    """Beta(1+wins, 1+losses): a uniform prior, so an unseen strategy is still explored, not zeroed."""
    return (1.0 + wins, 1.0 + (n - wins))


def recommend_strategy(
    stats: dict[str, dict[str, Any]],
    rng: random.Random,
    candidates: list[str] | None = None,
    lam: float = 0.0,
    mu: float = 0.0,
) -> str:
    """Thompson-sample a strategy, cost- and latency-adjusted.

    For each candidate, sample its success rate from Beta(posterior), then subtract lam * (its
    token cost / max token cost) and mu * (its latency / max latency). The argmax wins. A
    candidate with no telemetry gets the uniform Beta(1, 1), so it is explored rather than
    ignored (cold start). rng is a seeded random.Random for determinism. Empty candidate set
    falls back to 'solo' (the reliable serial default).
    """
    cands = list(candidates) if candidates is not None else list(stats.keys())
    if not cands:
        return "solo"
    max_tokens = max((float(stats.get(c, {}).get("avg_tokens", 0.0)) for c in cands), default=0.0) or 1.0
    max_ms = max((float(stats.get(c, {}).get("avg_ms") or 0.0) for c in cands), default=0.0) or 1.0
    best = cands[0]
    best_score = float("-inf")
    for cand in cands:
        s = stats.get(cand, {})
        alpha, beta = beta_posterior(float(s.get("wins", 0.0)), float(s.get("n", 0.0)))
        sampled = rng.betavariate(alpha, beta)
        cost_penalty = lam * (float(s.get("avg_tokens", 0.0)) / max_tokens)
        latency_penalty = mu * (float(s.get("avg_ms") or 0.0) / max_ms)
        score = sampled - cost_penalty - latency_penalty
        if score > best_score:
            best, best_score = cand, score
    return best


def telemetry_row(
    strategy: str,
    status: str,
    task: str,
    subagent_tokens: int = 0,
    duration_ms: int | None = None,
    agent_count: int = 1,
    run_id: str | None = None,
    note: str = "",
    task_type: str = "general",
) -> dict[str, Any]:
    """Pure: build one telemetry row (matches the existing jsonl schema).

    task_type is the coarse category (refactor/bugfix/feature/docs/wiring/...) that turns the
    global strategy comparison into a per-kind one; it defaults to 'general' so old callers stay valid.
    """
    return {
        "ts": utc_now(),
        "strategy": strategy,
        "task_type": task_type,
        "task": task[:240],
        "agent_count": agent_count,
        "subagent_tokens": subagent_tokens,
        "duration_ms": duration_ms,
        "status": status,
        "run_id": run_id,
        "note": note,
    }


def append_telemetry(row: dict[str, Any], log_path: Path = TELEMETRY_LOG) -> None:
    """I/O: append one row to the telemetry ledger, creating the dir if fresh."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def record_dispatch(
    strategy: str,
    task_type: str,
    status: str,
    task: str,
    subagent_tokens: int = 0,
    duration_ms: int | None = None,
    agent_count: int = 1,
    run_id: str | None = None,
    note: str = "",
    log_path: Path = TELEMETRY_LOG,
) -> dict[str, Any]:
    """Auto-emit: build + append one dispatch outcome in a single call (the burn-down's call site).

    This is the wiring that makes "record the data over time" automatic: one call per dispatched
    unit of work, so the ledger fills as the harness runs instead of via a manual CLI step. Returns
    the row it wrote so the caller can log or inspect it.
    """
    row = telemetry_row(
        strategy,
        status,
        task,
        subagent_tokens=subagent_tokens,
        duration_ms=duration_ms,
        agent_count=agent_count,
        run_id=run_id,
        note=note,
        task_type=task_type,
    )
    append_telemetry(row, log_path)
    return row
