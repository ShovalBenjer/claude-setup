"""Phase-0 fleet-readiness scan: turn a messy ~/projects into a per-repo delegate verdict.

Read-only. Before any autonomous agent touches a repo, this inventories it and returns a verdict
(delegate-ready vs organize-first) plus the concrete gaps: repo-in-repo defects (the topology rule),
fragmented TODO files (unify them first), a missing docs/ spine, missing tests. It never writes to
any repo. classify_dir filters real project dirs from archive/worktree/backup clutter.

Pure logic (classify_dir, repo_readiness) is unit-tested; scan_repo / fleet_report are read-only
filesystem walks (bounded depth, heavy dirs pruned).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_PRUNE = {"node_modules", ".venv", "venv", "__pycache__", ".git", ".mypy_cache", ".pytest_cache", "dist", "build"}


def classify_dir(name: str) -> str:
    """Classify a top-level dir: active project vs retired/worktree/backup/archive clutter."""
    low = name.lower()
    if name.startswith("."):
        return "retired"
    if name.endswith("-wt") or "-wt-" in name:
        return "worktree"
    if "backup" in low or ".pre-git" in low or "retired" in low:
        return "backup"
    if "archive" in low:
        return "archive"
    return "active"


def repo_readiness(facts: dict[str, Any]) -> dict[str, Any]:
    """A verdict + gap list from a repo's scan facts. A blocking gap forces organize-first."""
    gaps: list[str] = []
    blocking = False
    if facts.get("has_nested_git"):
        nested = ", ".join(facts.get("nested_repos", [])) or "nested .git"
        gaps.append(f"repo-in-repo defect: {nested}")
        blocking = True
    todos = facts.get("todo_files", [])
    if len(todos) > 1:
        gaps.append(f"fragmented TODOs ({len(todos)}): {', '.join(todos)}")
        blocking = True
    if not facts.get("has_docs"):
        gaps.append("no docs/ spine")
        blocking = True
    if not facts.get("has_tests"):
        gaps.append("no tests")
        blocking = True
    if not facts.get("has_pipeline"):
        gaps.append("no pipeline (advisory)")
    return {"verdict": "organize-first" if blocking else "delegate-ready", "gaps": gaps}


def _find_nested_git(root: Path, max_depth: int = 3) -> list[str]:
    """Sub-directories (not root) that contain their own .git: the repo-in-repo defect."""
    nested: list[str] = []
    for dirpath, dirnames, _ in os.walk(root):
        current = Path(dirpath)
        depth = len(current.relative_to(root).parts)
        if current != root and (current / ".git").exists():
            nested.append(str(current.relative_to(root)))
        dirnames[:] = [] if depth >= max_depth else [d for d in dirnames if d not in _PRUNE]
    return nested


def scan_repo(path: Path) -> dict[str, Any]:
    """Read-only inventory of one repo dir. Never writes."""
    repo = Path(path)
    nested = _find_nested_git(repo)
    todo_files = sorted(f.name for f in repo.glob("*") if "todo" in f.name.lower())
    has_tests = (repo / "tests").is_dir() or any(repo.glob("test_*.py")) or any(repo.glob("*_test.py"))
    has_pipeline = (repo / "azure-pipelines.yml").exists() or (repo / ".github").is_dir()
    return {
        "path": str(repo),
        "name": repo.name,
        "has_git": (repo / ".git").exists(),
        "has_nested_git": bool(nested),
        "nested_repos": nested,
        "todo_files": todo_files,
        "has_docs": (repo / "docs").is_dir(),
        "has_tests": has_tests,
        "has_pipeline": has_pipeline,
    }


def fleet_report(root: Path) -> list[dict[str, Any]]:
    """Read-only readiness report for every top-level dir under root (active repos get a verdict)."""
    reports: list[dict[str, Any]] = []
    for child in sorted(Path(root).iterdir()):
        if not child.is_dir():
            continue
        kind = classify_dir(child.name)
        if kind != "active":
            reports.append({"name": child.name, "kind": kind, "verdict": "skipped", "gaps": []})
            continue
        facts = scan_repo(child)
        if not facts["has_git"]:
            reports.append({"name": child.name, "kind": "active", "verdict": "not-git-init", "gaps": ["no .git"]})
            continue
        readiness = repo_readiness(facts)
        reports.append(
            {
                "name": child.name,
                "kind": "active",
                "verdict": readiness["verdict"],
                "gaps": readiness["gaps"],
                "nested_repos": facts["nested_repos"],
                "todo_files": facts["todo_files"],
            }
        )
    return reports
