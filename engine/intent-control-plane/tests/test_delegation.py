"""Tests for the delegation flywheel: executor choice, queue ranking, verify gate."""
from __future__ import annotations

from intent_control_plane.delegation import (
    build_queue,
    choose_executor,
    main,
    render_queue,
    verify_gate,
)


def test_main_returns_error_on_missing_path(tmp_path, capsys) -> None:
    # a CLI is a boundary: a bad path must return a controlled error, not a raw
    # FileNotFoundError traceback from iterdir().
    missing = tmp_path / "does-not-exist"
    assert main([str(missing)]) == 2
    assert "not a directory" in capsys.readouterr().out


def test_choose_executor_completed_is_codex():
    assert choose_executor({"state": "completed"}) == "codex"


def test_choose_executor_rate_limited_is_haiku():
    assert choose_executor({"state": "rate_limited"}) == "haiku"


def test_choose_executor_auth_failed_is_haiku():
    assert choose_executor({"state": "auth_failed"}) == "haiku"


def test_choose_executor_timeout_falls_back_to_haiku():
    assert choose_executor({"state": "timeout"}) == "haiku"


def test_choose_executor_failed_falls_back_to_haiku():
    assert choose_executor({"state": "failed"}) == "haiku"


def test_choose_executor_unknown_state_falls_back_to_haiku():
    assert choose_executor({"state": "some_new_state"}) == "haiku"


def test_choose_executor_missing_state_key_falls_back_to_haiku():
    assert choose_executor({}) == "haiku"


def _scorecard_fixture() -> list[dict]:
    return [
        {
            "name": "repo-a",
            "class": "flat",
            "score": "3/6",
            "dimensions": {
                "repo_org": {"passed": 4, "total": 4, "gaps": []},
                "code_health": {"passed": 0, "total": 2, "gaps": ["lint_config", "type_config"]},
                "testing": {"passed": 1, "total": 3, "gaps": ["runner", "gated_in_ci"]},
            },
        },
        {
            "name": "repo-b",
            "class": "flat",
            "score": "2/4",
            "dimensions": {
                "repo_org": {"passed": 2, "total": 4, "gaps": ["docs_dir", "adr"]},
                "cicd": {"passed": 1, "total": 2, "gaps": ["blocking_gates"]},
            },
        },
    ]


def test_build_queue_ranks_biggest_gap_first():
    queue = build_queue(_scorecard_fixture())
    # repo-a code_health gap = 2 (biggest), should sort first
    assert queue[0]["repo"] == "repo-a"
    assert queue[0]["dimension"] == "code_health"
    assert queue[0]["priority"] == 2


def test_build_queue_only_emits_failing_dimensions():
    queue = build_queue(_scorecard_fixture())
    dims_by_repo = {(item["repo"], item["dimension"]) for item in queue}
    # repo-a repo_org is passing (4/4), must not appear
    assert ("repo-a", "repo_org") not in dims_by_repo
    # repo-b repo_org (2/4) and cicd (1/2) are failing, must appear
    assert ("repo-b", "repo_org") in dims_by_repo
    assert ("repo-b", "cicd") in dims_by_repo


def test_build_queue_carries_gaps_as_failing_checks():
    queue = build_queue(_scorecard_fixture())
    item = next(i for i in queue if i["repo"] == "repo-a" and i["dimension"] == "code_health")
    assert item["failing_checks"] == ["lint_config", "type_config"]


def test_build_queue_stable_by_repo_then_dimension_on_tied_priority():
    scorecard = [
        {
            "name": "repo-z",
            "class": "flat",
            "score": "1/2",
            "dimensions": {"docs": {"passed": 1, "total": 2, "gaps": ["adr"]}},
        },
        {
            "name": "repo-a",
            "class": "flat",
            "score": "1/2",
            "dimensions": {"docs": {"passed": 1, "total": 2, "gaps": ["adr"]}},
        },
    ]
    queue = build_queue(scorecard)
    # Both have priority 1, tie broken by repo name ascending.
    assert [item["repo"] for item in queue] == ["repo-a", "repo-z"]


def test_build_queue_empty_scorecard_is_empty_queue():
    assert build_queue([]) == []


def _score(passed: int, total: int) -> dict:
    return {"name": "r", "class": "flat", "score": f"{passed}/{total}", "dimensions": {}}


def test_verify_gate_counts_false_when_tests_fail_even_if_score_rose():
    result = verify_gate(_score(2, 6), _score(4, 6), tests_passed=False)
    assert result["counts"] is False
    assert result["delta"] == 2


def test_verify_gate_counts_false_when_score_flat():
    result = verify_gate(_score(3, 6), _score(3, 6), tests_passed=True)
    assert result["counts"] is False
    assert result["delta"] == 0


def test_verify_gate_counts_true_when_score_rose_and_tests_pass():
    result = verify_gate(_score(2, 6), _score(3, 6), tests_passed=True)
    assert result["counts"] is True
    assert result["delta"] == 1


def test_verify_gate_counts_false_when_score_dropped():
    result = verify_gate(_score(4, 6), _score(3, 6), tests_passed=True)
    assert result["counts"] is False
    assert result["delta"] == -1


def test_verify_gate_reason_field_present():
    result = verify_gate(_score(2, 6), _score(3, 6), tests_passed=True)
    assert isinstance(result["reason"], str) and result["reason"]


def _queue_fixture() -> list[dict]:
    return [
        {"repo": "repo-a", "dimension": "code_health", "failing_checks": ["lint_config", "type_config"], "priority": 2},
        {"repo": "repo-b", "dimension": "repo_org", "failing_checks": ["docs_dir", "adr"], "priority": 2},
    ]


def test_render_queue_produces_markdown_table():
    table = render_queue(_queue_fixture())
    lines = table.splitlines()
    assert lines[0] == "| Repo | Dimension | Priority | Failing checks |"
    assert lines[1] == "|---|---|---|---|"
    assert "repo-a" in table
    assert "repo-b" in table
    assert "code_health" in table
    assert "repo_org" in table
    assert "lint_config, type_config" in table
    assert "docs_dir, adr" in table


def test_render_queue_empty_queue_is_header_only():
    table = render_queue([])
    lines = table.splitlines()
    assert lines[0] == "| Repo | Dimension | Priority | Failing checks |"
    assert lines[1] == "|---|---|---|---|"
    assert len(lines) == 2


def test_main_returns_zero_on_empty_dir(tmp_path):
    assert main([str(tmp_path)]) == 0
