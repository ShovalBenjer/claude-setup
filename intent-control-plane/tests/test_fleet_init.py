"""Tests for fleet_init.py: the read-only Phase-0 fleet-readiness scan.

Turns a messy ~/projects into a per-repo verdict (delegate-ready vs organize-first) plus the gap
list, so autonomous agents are never pointed at an unorganized repo. Pure classification/readiness
logic is unit-tested; scan_repo is a real read-only filesystem read tested against a tmp fixture
(no mocks). It never writes to any repo.
"""
from __future__ import annotations

from intent_control_plane.fleet_init import classify_dir, repo_readiness, scan_repo


def test_classify_dir_separates_active_from_clutter():
    assert classify_dir(".archive") == "retired"
    assert classify_dir("ORM-AGENT-widgora-gates-wt") == "worktree"
    assert classify_dir("sales-agents.pre-git-reconnect-backup-20260706") == "backup"
    assert classify_dir("campaign-analysis") == "active"


def test_repo_readiness_flags_nested_git():
    report = repo_readiness(
        {"has_nested_git": True, "nested_repos": ["social-media-agent"], "todo_files": ["TODO.md"],
         "has_docs": True, "has_tests": True, "has_pipeline": True}
    )
    assert report["verdict"] == "organize-first"
    assert any("repo-in-repo" in gap for gap in report["gaps"])


def test_repo_readiness_flags_fragmented_todos():
    report = repo_readiness(
        {"has_nested_git": False, "nested_repos": [],
         "todo_files": ["TODO.md", "MATURITY-TODO.md", "AI_NATIVE_CODE_TODO.md"],
         "has_docs": True, "has_tests": True, "has_pipeline": True}
    )
    assert report["verdict"] == "organize-first"
    assert any("TODO" in gap for gap in report["gaps"])


def test_repo_readiness_delegate_ready_when_clean():
    report = repo_readiness(
        {"has_nested_git": False, "nested_repos": [], "todo_files": ["TODO.md"],
         "has_docs": True, "has_tests": True, "has_pipeline": True}
    )
    assert report["verdict"] == "delegate-ready"
    assert report["gaps"] == []


def test_scan_repo_detects_nested_git_and_todos(tmp_path):
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "sub" / ".git").mkdir()  # nested = repo-in-repo defect
    (repo / "TODO.md").write_text("x")
    (repo / "MATURITY-TODO.md").write_text("y")
    (repo / "docs").mkdir()
    facts = scan_repo(repo)
    assert facts["has_nested_git"] is True
    assert "sub" in facts["nested_repos"]
    assert set(facts["todo_files"]) == {"TODO.md", "MATURITY-TODO.md"}
    assert facts["has_docs"] is True
