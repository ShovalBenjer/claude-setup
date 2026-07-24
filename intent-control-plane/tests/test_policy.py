"""Tests for the strategy bandit: aggregation, Beta posterior, cost-aware Thompson, telemetry IO."""
from __future__ import annotations

import json
import random

import pytest

from intent_control_plane.cli import main
from intent_control_plane.policy import (
    append_telemetry,
    beta_posterior,
    recommend_strategy,
    record_dispatch,
    strategy_by_task_type,
    strategy_stats,
    telemetry_row,
)


def test_telemetry_record_rejects_negative_counts():
    # Codex review: negative tokens/ms/agents would corrupt the bandit stats; reject at the CLI.
    for bad in (["--tokens", "-1"], ["--ms", "-5"], ["--agents", "-2"]):
        with pytest.raises(SystemExit):
            main(["telemetry", "record", "--strategy", "solo", "--status", "green", "--task", "t", *bad])

# real-schema rows (see ~/.claude/cache/orchestration/telemetry.jsonl)
_FIXTURE = [
    json.dumps({"strategy": "workflow", "status": "green", "subagent_tokens": 300000, "duration_ms": 400000}),
    json.dumps({"strategy": "subagent", "status": "green", "subagent_tokens": 66000, "duration_ms": 106000}),
    json.dumps({"strategy": "subagent", "status": "red", "subagent_tokens": 0, "duration_ms": 193000}),
    json.dumps({"strategy": "solo", "status": "green", "subagent_tokens": 0, "duration_ms": None}),
]


def test_strategy_stats_aggregates_wins_and_costs():
    stats = strategy_stats(_FIXTURE)
    assert stats["subagent"]["n"] == 2
    assert stats["subagent"]["wins"] == 1
    assert stats["subagent"]["pass_rate"] == 0.5
    assert stats["subagent"]["avg_tokens"] == 33000.0
    assert stats["workflow"]["pass_rate"] == 1.0
    assert stats["solo"]["avg_ms"] is None  # null duration excluded from the average


def test_strategy_stats_skips_malformed_and_non_dict():
    stats = strategy_stats(["not json", "", "[]", '{"strategy":"solo","status":"green"}'])
    assert stats["solo"]["n"] == 1
    assert "?" not in stats


def test_beta_posterior_uniform_prior():
    assert beta_posterior(0, 0) == (1.0, 1.0)  # unseen -> uniform, gets explored
    assert beta_posterior(9, 10) == (10.0, 2.0)


def test_recommend_prefers_the_evidenced_winner():
    # A wins 9/10, B wins 1/10: over many seeds Thompson should pick A the large majority
    stats = {
        "A": {"n": 10, "wins": 9, "avg_tokens": 0.0, "avg_ms": 0.0},
        "B": {"n": 10, "wins": 1, "avg_tokens": 0.0, "avg_ms": 0.0},
    }
    picks = [recommend_strategy(stats, random.Random(seed)) for seed in range(200)]
    assert picks.count("A") > 160  # dominant, not exclusive (it still explores)


def test_recommend_cold_start_explores_unseen_candidate():
    # 'new' has no stats -> uniform Beta(1,1); over many seeds it must be picked at least sometimes
    stats = {"A": {"n": 10, "wins": 6, "avg_tokens": 0.0, "avg_ms": 0.0}}
    picks = [recommend_strategy(stats, random.Random(seed), candidates=["A", "new"]) for seed in range(100)]
    assert "new" in picks
    assert "A" in picks


def test_recommend_cost_penalty_breaks_ties_toward_cheaper():
    # equal evidence, A is 10x cheaper; with a strong cost weight A should dominate
    stats = {
        "A": {"n": 10, "wins": 5, "avg_tokens": 10000.0, "avg_ms": 0.0},
        "B": {"n": 10, "wins": 5, "avg_tokens": 100000.0, "avg_ms": 0.0},
    }
    picks = [recommend_strategy(stats, random.Random(seed), lam=0.5) for seed in range(200)]
    assert picks.count("A") > picks.count("B")


def test_recommend_empty_candidates_is_safe_default():
    assert recommend_strategy({}, random.Random(0)) == "solo"


def test_telemetry_row_matches_schema():
    row = telemetry_row("subagent", "green", "build the bandit", subagent_tokens=66000, duration_ms=106000)
    assert row["strategy"] == "subagent"
    assert row["status"] == "green"
    assert row["subagent_tokens"] == 66000
    assert set(row) >= {"ts", "strategy", "task", "status", "subagent_tokens", "duration_ms"}


def test_append_then_aggregate_roundtrip(tmp_path):
    log = tmp_path / "telemetry.jsonl"
    append_telemetry(telemetry_row("solo", "green", "t1"), log)
    append_telemetry(telemetry_row("solo", "red", "t2"), log)
    stats = strategy_stats(log.read_text().splitlines())
    assert stats["solo"]["n"] == 2
    assert stats["solo"]["pass_rate"] == 0.5


# --- Track 0: per-task-type strategy comparison + auto-emit ---

_TYPED_FIXTURE = [
    json.dumps({"strategy": "workflow", "status": "green", "task_type": "refactor", "subagent_tokens": 300000}),
    json.dumps({"strategy": "workflow", "status": "red", "task_type": "bugfix", "subagent_tokens": 250000}),
    json.dumps({"strategy": "subagent", "status": "green", "task_type": "bugfix", "subagent_tokens": 60000}),
    json.dumps({"strategy": "subagent", "status": "green", "task_type": "bugfix", "subagent_tokens": 64000}),
    json.dumps({"strategy": "solo", "status": "green", "task_type": "refactor", "subagent_tokens": 0}),
]


def test_telemetry_row_carries_task_type():
    row = telemetry_row("subagent", "green", "fix the TOCTOU race", task_type="bugfix")
    assert row["task_type"] == "bugfix"


def test_telemetry_row_task_type_defaults_general():
    # backward compatible: existing callers that omit task_type still produce a valid row
    assert telemetry_row("solo", "green", "t")["task_type"] == "general"


def test_strategy_stats_filters_by_task_type():
    # global stats mix task types; the filtered view isolates one so the comparison is fair
    bugfix = strategy_stats(_TYPED_FIXTURE, task_type="bugfix")
    assert "solo" not in bugfix  # solo only appears in refactor rows
    assert bugfix["subagent"]["n"] == 2
    assert bugfix["subagent"]["pass_rate"] == 1.0
    assert bugfix["workflow"]["pass_rate"] == 0.0


def test_strategy_by_task_type_cross_tab():
    # the analysis-over-time readout: which strategy wins for which kind of task
    table = strategy_by_task_type(_TYPED_FIXTURE)
    assert set(table) == {"refactor", "bugfix"}
    assert table["bugfix"]["subagent"]["pass_rate"] == 1.0
    assert table["bugfix"]["workflow"]["pass_rate"] == 0.0
    assert table["refactor"]["workflow"]["n"] == 1


def test_record_dispatch_is_the_auto_emit_call_site(tmp_path):
    # one call per dispatched unit closes the data loop without a manual CLI step
    log = tmp_path / "telemetry.jsonl"
    record_dispatch("workflow", "refactor", "green", "burn down the audit highs", subagent_tokens=120000, log_path=log)
    record_dispatch("subagent", "bugfix", "red", "fix swarm order-dependence", log_path=log)
    table = strategy_by_task_type(log.read_text().splitlines())
    assert table["refactor"]["workflow"]["wins"] == 1.0
    assert table["bugfix"]["subagent"]["pass_rate"] == 0.0
