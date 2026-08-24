"""Tests for observe.py: pure aggregation over telemetry rows and Foundry cost rows.

No mocks: rows are plain dicts shaped like policy.telemetry_row output (see
test_policy.py's _FIXTURE) and like a Foundry usage ledger row. All functions here
are pure (no I/O), so real dicts in-memory are the correct fixture, not a recording.
"""
from __future__ import annotations

from intent_control_plane.observe import cost_summary, summarize

# Known set: 10 rows with durations 100..1000ms in steps of 100, 8 green / 2 red,
# split across two strategies so both the overall and by_strategy math are checkable.
_ROWS = [
    {"strategy": "solo", "status": "green", "subagent_tokens": 100, "duration_ms": 100},
    {"strategy": "solo", "status": "green", "subagent_tokens": 200, "duration_ms": 200},
    {"strategy": "solo", "status": "green", "subagent_tokens": 300, "duration_ms": 300},
    {"strategy": "solo", "status": "red", "subagent_tokens": 400, "duration_ms": 400},
    {"strategy": "solo", "status": "green", "subagent_tokens": 500, "duration_ms": 500},
    {"strategy": "workflow", "status": "green", "subagent_tokens": 600, "duration_ms": 600},
    {"strategy": "workflow", "status": "green", "subagent_tokens": 700, "duration_ms": 700},
    {"strategy": "workflow", "status": "red", "subagent_tokens": 800, "duration_ms": 800},
    {"strategy": "workflow", "status": "green", "subagent_tokens": 900, "duration_ms": 900},
    {"strategy": "workflow", "status": "green", "subagent_tokens": 1000, "duration_ms": 1000},
]


def test_summarize_overall_counts_and_rate():
    out = summarize(_ROWS)
    assert out["n"] == 10
    assert out["success_rate"] == 0.8
    assert out["avg_tokens"] == 550.0


def test_summarize_percentiles_on_known_set():
    # durations are exactly 100..1000 step 100 -> p50 is the 5th/6th value, p95 near the top.
    out = summarize(_ROWS)
    assert out["p50_ms"] == 500
    assert out["p95_ms"] == 1000


def test_summarize_by_strategy_grouping():
    out = summarize(_ROWS)
    by = out["by_strategy"]
    assert by["solo"]["n"] == 5
    assert by["solo"]["success_rate"] == 0.8
    assert by["solo"]["avg_tokens"] == 300.0
    assert by["workflow"]["n"] == 5
    assert by["workflow"]["success_rate"] == 0.8
    assert by["workflow"]["avg_tokens"] == 800.0


def test_summarize_empty_input_is_safe():
    out = summarize([])
    assert out["n"] == 0
    assert out["success_rate"] == 0.0
    assert out["avg_tokens"] == 0.0
    assert out["p50_ms"] == 0.0
    assert out["p95_ms"] == 0.0
    assert out["by_strategy"] == {}


def test_summarize_single_row_percentiles():
    out = summarize([{"strategy": "solo", "status": "green", "subagent_tokens": 10, "duration_ms": 250}])
    assert out["p50_ms"] == 250
    assert out["p95_ms"] == 250


def test_summarize_skips_non_numeric_and_missing_duration():
    rows = [
        {"strategy": "solo", "status": "green", "subagent_tokens": "oops", "duration_ms": "nope"},
        {"strategy": "solo", "status": "green", "subagent_tokens": 100, "duration_ms": None},
        {"strategy": "solo", "status": "green", "subagent_tokens": 200, "duration_ms": 200},
    ]
    out = summarize(rows)
    assert out["n"] == 3
    assert out["avg_tokens"] == 100.0  # (0 + 100 + 200) / 3, non-numeric token treated as absent
    assert out["p50_ms"] == 200  # only the one real duration counted
    assert out["p95_ms"] == 200


def test_summarize_malformed_rows_are_skipped_not_fatal():
    rows = [
        "not a dict",
        [],
        {"strategy": "solo", "status": "green", "duration_ms": 50},
        {"strategy": "solo", "status": "red", "duration_ms": 60},
    ]
    out = summarize(rows)  # type: ignore[arg-type]
    assert out["n"] == 2  # only the two real dict rows count


_FOUNDRY_ROWS = [
    {"token_input": 1000, "token_output": 200},
    {"token_input": 2000, "token_output": 400},
    {"token_input": 500, "token_output": 100},
]


def test_cost_summary_sums_tokens():
    out = cost_summary(_FOUNDRY_ROWS)
    assert out["total_input"] == 3500
    assert out["total_output"] == 700
    assert out["calls"] == 3


def test_cost_summary_empty_is_safe():
    out = cost_summary([])
    assert out["total_input"] == 0
    assert out["total_output"] == 0
    assert out["calls"] == 0


def test_cost_summary_skips_non_numeric_fields():
    rows = [
        {"token_input": "oops", "token_output": 100},
        {"token_input": 300, "token_output": "nope"},
        {"token_input": 50, "token_output": 10},
    ]
    out = cost_summary(rows)
    assert out["total_input"] == 350  # non-numeric input treated as 0
    assert out["total_output"] == 110  # non-numeric output treated as 0
    assert out["calls"] == 3
