"""Tests for the evolve tracker: verdict, score, baseline read, and the record/compare loop."""
from __future__ import annotations

from intent_control_plane.evolution import (
    evolution_verdict,
    golden_score,
    last_evolve_score,
    run_evolution,
)
from intent_control_plane.schema import connect, initialize


def test_evolution_verdict():
    assert evolution_verdict(0.9, None) == "baseline-set"
    assert evolution_verdict(0.9, 0.8) == "improved"
    assert evolution_verdict(0.7, 0.8) == "regressed"
    assert evolution_verdict(0.8, 0.8) == "same"


def test_golden_score():
    assert golden_score({"passed": 1, "failed": 1}) == 0.5
    assert golden_score({"passed": 3, "failed": 0}) == 1.0
    assert golden_score({"passed": 0, "failed": 0}) == 0.0  # no fixtures -> 0.0, no div-by-zero


def test_last_evolve_score_none_before_any_run(tmp_path):
    base = tmp_path / ".intent"
    initialize(base)
    assert last_evolve_score(base) is None


def test_run_evolution_baseline_then_regression_records_rows(tmp_path):
    base = tmp_path / ".intent"
    initialize(base)
    first = run_evolution(base, {"passed": 2, "failed": 0, "fixture_count": 2})
    assert first["verdict"] == "baseline-set"
    assert first["score"] == 1.0
    assert first["baseline"] is None

    second = run_evolution(base, {"passed": 1, "failed": 1, "fixture_count": 2})
    assert second["verdict"] == "regressed"
    assert second["baseline"] == 1.0
    assert second["score"] == 0.5

    with connect(base) as conn:
        rows = [tuple(r) for r in conn.execute(
            "select eval_type, status from eval_results where eval_type = 'evolve' order by rowid"
        ).fetchall()]
    assert rows == [("evolve", "pass"), ("evolve", "fail")]  # regression recorded as fail
