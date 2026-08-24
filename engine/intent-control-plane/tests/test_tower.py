"""Tests for the control-tower data layer (rendering is presentation, smoke-tested only)."""
from __future__ import annotations

import pytest

from intent_control_plane.tower import (
    context_budget_band,
    endpoints_panel_data,
    estimate_tokens,
    main,
    parse_deployment_names,
    parse_git_worktree_porcelain,
    sessions_panel_data,
    summarize_turns,
    telemetry_summary,
)

# --- worktree / session parser (real captured `git worktree list --porcelain` samples) ------

_SINGLE_WORKTREE_PORCELAIN = [
    "worktree /home/shovalbe/projects/intent-control-plane",
    "HEAD 40e0fcf2baf37e88d4003b8c2304b2efedf57595",
    "branch refs/heads/master",
]

_MULTI_WORKTREE_PORCELAIN = [
    "worktree /home/shovalbe/projects/ORM-AGENT",
    "HEAD da14922a6138cfd192253c23a0e93bdc3a2588bd",
    "branch refs/heads/feature/widgora-release",
    "",
    "worktree /home/shovalbe/projects/ORM-AGENT-ci-review-wt",
    "HEAD cd82799352732ee656434fd2697c935994944e0b",
    "branch refs/heads/ci/codex-review-rollout",
    "",
    "worktree /home/shovalbe/projects/ORM-AGENT-widgora-gates-wt",
    "HEAD 4cc605cbb10cb0069a8bb648239d94181b0ac6e7",
    "branch refs/heads/chore/widgora-pipeline-gates",
    "",
    "worktree /home/shovalbe/projects/ORM-AGENT-widgora-indicators-wt",
    "HEAD e65d1c2292ea1855f7c5a3122972053f611d5cc9",
    "branch refs/heads/feat/widgora-indicators-overlay",
]


def test_parse_worktree_porcelain_single_entry() -> None:
    entries = parse_git_worktree_porcelain(_SINGLE_WORKTREE_PORCELAIN)
    assert len(entries) == 1
    assert entries[0]["repo"] == "intent-control-plane"
    assert entries[0]["branch"] == "master"
    assert entries[0]["head"] == "40e0fcf2"
    assert entries[0]["worktree"] == "/home/shovalbe/projects/intent-control-plane"


def test_parse_worktree_porcelain_multi_entry_family() -> None:
    entries = parse_git_worktree_porcelain(_MULTI_WORKTREE_PORCELAIN)
    assert len(entries) == 4
    by_repo = {e["repo"]: e for e in entries}
    assert by_repo["ORM-AGENT"]["branch"] == "feature/widgora-release"
    assert by_repo["ORM-AGENT-ci-review-wt"]["branch"] == "ci/codex-review-rollout"
    assert by_repo["ORM-AGENT-widgora-gates-wt"]["branch"] == "chore/widgora-pipeline-gates"
    assert by_repo["ORM-AGENT-widgora-indicators-wt"]["branch"] == "feat/widgora-indicators-overlay"
    assert by_repo["ORM-AGENT"]["head"] == "da14922a"


def test_parse_worktree_porcelain_detached_head() -> None:
    lines = ["worktree /tmp/scratch", "HEAD abc123def456", "detached"]
    entries = parse_git_worktree_porcelain(lines)
    assert entries[0]["branch"] == "(detached)"


def test_parse_worktree_porcelain_bare_repo() -> None:
    lines = ["worktree /tmp/bare-repo.git", "bare"]
    entries = parse_git_worktree_porcelain(lines)
    assert entries[0]["branch"] == "(bare)"


def test_parse_worktree_porcelain_empty_input_is_empty() -> None:
    assert parse_git_worktree_porcelain([]) == []


def test_sessions_panel_data_shape() -> None:
    # real environment, no mocks: exercises the impure git/pgrep wrapper end-to-end.
    data = sessions_panel_data()
    assert "own_pid" in data
    assert "other_sessions" in data
    assert isinstance(data["worktrees"], list)
    if data["worktrees"]:
        assert {"worktree", "head", "branch", "repo"} <= set(data["worktrees"][0].keys())


# --- telemetry summary --------------------------------------------------------------------

_TELEMETRY_FIXTURE = [
    '{"strategy":"workflow","subagent_tokens":300000,"duration_ms":100000,"status":"green"}',
    '{"strategy":"workflow","subagent_tokens":200000,"duration_ms":200000,"status":"red"}',
    '{"strategy":"solo","subagent_tokens":0,"duration_ms":null,"status":"green"}',
]


def test_telemetry_summary_per_strategy_aggregation() -> None:
    summary = telemetry_summary(_TELEMETRY_FIXTURE)
    assert summary["workflow"]["count"] == 2
    assert summary["workflow"]["avg_subagent_tokens"] == 250000.0
    assert summary["workflow"]["avg_duration_ms"] == 150000.0
    assert summary["workflow"]["pass_rate"] == 0.5
    assert summary["solo"]["count"] == 1
    assert summary["solo"]["avg_subagent_tokens"] == 0.0
    assert summary["solo"]["avg_duration_ms"] is None
    assert summary["solo"]["pass_rate"] == 1.0


def test_telemetry_summary_empty_lines_is_empty_dict() -> None:
    assert telemetry_summary([]) == {}


def test_telemetry_summary_skips_malformed_json_lines() -> None:
    lines = ['{"strategy":"workflow","status":"green"}', "not json", ""]
    summary = telemetry_summary(lines)
    assert summary["workflow"]["count"] == 1


def test_telemetry_summary_skips_valid_but_non_dict_json() -> None:
    # Valid JSON that is not an object (list/number/string) must be skipped, not crash
    # with AttributeError on row.get(...). Regression for the '[]' line case.
    lines = ["[]", "1", '"x"', '{"strategy":"solo","status":"green"}']
    summary = telemetry_summary(lines)
    assert summary["solo"]["count"] == 1
    assert "?" not in summary  # non-dict rows did not leak in as an unknown strategy


def test_main_watch_nonpositive_interval_is_rejected() -> None:
    # --watch 0 would busy-loop and --watch -1 would raise ValueError in time.sleep;
    # both must be rejected at the CLI boundary with a clean exit, not a crash.
    for bad in ["0", "-1"]:
        with pytest.raises(SystemExit):
            main(["--watch", bad])


# --- context-degradation meter --------------------------------------------------------------


def test_estimate_tokens_is_char_quarter() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 400) == 100


def test_context_budget_band_thresholds() -> None:
    assert context_budget_band(99_999) == "green"
    assert context_budget_band(100_000) == "amber"
    assert context_budget_band(159_999) == "amber"
    assert context_budget_band(160_000) == "red"


def test_summarize_turns_picks_latest_session_and_counts_prompts() -> None:
    rows = [
        {"session_id": "old", "timestamp_utc": "2026-07-10T09:00:00Z", "event_type": "user_prompt", "model_text": "x" * 40},
        {"session_id": "cur", "timestamp_utc": "2026-07-10T10:00:00Z", "event_type": "user_prompt", "model_text": "y" * 400},
        {"session_id": "cur", "timestamp_utc": "2026-07-10T10:05:00Z", "event_type": "assistant_final", "model_text": "z" * 400},
        {"session_id": "cur", "timestamp_utc": "2026-07-10T10:10:00Z", "event_type": "user_prompt", "model_text": "w" * 400},
    ]
    meter = summarize_turns(rows)
    assert meter["session"] == "cur"
    assert meter["turns"] == 2  # two user_prompt events in the latest session, not the old one
    assert meter["est_tokens"] == 300  # (400+400+400)//4 summed over the session's rows
    assert meter["band"] == "green"


def test_summarize_turns_empty_is_zeroed_green() -> None:
    assert summarize_turns([]) == {"session": None, "turns": 0, "est_tokens": 0, "band": "green"}


# --- deployed-endpoints panel ---------------------------------------------------------------


def test_parse_deployment_names_extracts_backtick_gpt_names_only() -> None:
    text = "Correct: `gpt-5.4-nano-cs-agent`, `gpt-5.4-mini-qc-api-telephony` and prose `not-a-model`."
    names = parse_deployment_names(text)
    assert "gpt-5.4-nano-cs-agent" in names
    assert "gpt-5.4-mini-qc-api-telephony" in names
    assert "not-a-model" not in names


def test_parse_deployment_names_dedupes_and_preserves_order() -> None:
    text = "`gpt-5.4-a` then `gpt-5.4-b` then `gpt-5.4-a` again"
    assert parse_deployment_names(text) == ["gpt-5.4-a", "gpt-5.4-b"]


def test_endpoints_panel_data_parses_deployment_names(tmp_path) -> None:
    rule = tmp_path / "foundry-deployment-per-project.md"
    rule.write_text(
        "Correct: `gpt-5.4-nano-cs-agent`, `gpt-5.4-mini-qc-api-telephony`,\n"
        "`gpt-5.4-mini-training`, `gpt-5.4-nano-call-analysis-agent`.\n"
    )
    audit = tmp_path / "audit.jsonl"
    audit.write_text('{"state": "completed"}\n{"state": "failed"}\n')

    data = endpoints_panel_data(rule_path=rule, audit_path=audit)
    assert data["deployments"] == [
        "gpt-5.4-nano-cs-agent",
        "gpt-5.4-mini-qc-api-telephony",
        "gpt-5.4-mini-training",
        "gpt-5.4-nano-call-analysis-agent",
    ]
    assert data["codex_a2a_calls"] == 2
    assert "grok-4-1-fast-reasoning-2-eval" in data["judges"]
    assert "DeepSeek-V3.2" in data["judges"]


def test_endpoints_panel_data_falls_back_to_default_deployments(tmp_path) -> None:
    missing_rule = tmp_path / "does-not-exist.md"
    audit = tmp_path / "audit.jsonl"
    audit.write_text("")
    data = endpoints_panel_data(rule_path=missing_rule, audit_path=audit)
    assert "gpt-5.4-nano-cs-agent" in data["deployments"]
    assert data["codex_a2a_calls"] == 0


# --- end-to-end smoke (real environment, no mocks) -------------------------------------------


def test_main_once_smoke(capsys) -> None:
    assert main(["--once"]) == 0
    out = capsys.readouterr().out
    assert out.strip() != ""
