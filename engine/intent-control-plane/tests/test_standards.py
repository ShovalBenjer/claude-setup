"""Tests for the per-project compliance scorer."""
from __future__ import annotations

from intent_control_plane.standards import (
    has_lint_config,
    has_type_config,
    nested_git_count,
    score_repo,
    supply_chain_checks,
)


def test_lint_and_type_config_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")
    assert has_lint_config(tmp_path)
    assert has_type_config(tmp_path)


def test_no_config_when_absent(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    assert not has_lint_config(tmp_path)
    assert not has_type_config(tmp_path)


def test_nested_git_is_flagged(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / ".git").mkdir()
    assert nested_git_count(tmp_path) == 1


def test_no_nested_git(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    assert nested_git_count(tmp_path) == 0


def test_score_repo_covers_all_dimensions(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text("# x\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "adr").mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n[tool.pytest.ini_options]\n")
    (tmp_path / "test_a.py").write_text("def test_x():\n    assert True\n")
    rec = score_repo(tmp_path)
    assert set(rec["dimensions"]) == {"repo_org", "code_health", "docs", "testing", "cicd", "supply_chain"}
    assert rec["dimensions"]["code_health"]["passed"] == 2
    assert rec["dimensions"]["repo_org"]["passed"] >= 3
    assert "/" in rec["score"]


def test_supply_chain_checks_detects_pinned_sast_secret(tmp_path):
    (tmp_path / "uv.lock").write_text("")
    (tmp_path / "azure-pipelines.yml").write_text(
        "steps:\n  - script: bandit -r .\n  - script: detect-secrets scan\n"
    )
    c = supply_chain_checks(tmp_path)
    assert c["pinned_deps"] is True
    assert c["sast_in_ci"] is True
    assert c["secret_scan"] is True


def test_supply_chain_checks_empty(tmp_path):
    c = supply_chain_checks(tmp_path)
    assert c["pinned_deps"] is False
    assert c["sast_in_ci"] is False
    assert c["secret_scan"] is False
