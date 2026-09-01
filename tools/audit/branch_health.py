#!/usr/bin/env python3
"""Check git branch and worktree health.

Stale branches (merged into main but not deleted) and orphaned worktrees are
the two shapes of git debris that have caused gate failures in this repo.
The codemap domain excludes .claude/worktrees from compileall because a sibling
worktree carried live conflict markers; the types domain failed on the same
markers. This tool catches the debris before it causes a downstream failure.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, timeout=30, cwd=cwd, check=False,
    )


def _default_branch(cwd: str) -> str:
    r = _git(["symbolic-ref", "refs/remotes/origin/HEAD", "--short"], cwd)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().replace("origin/", "", 1)
    for name in ("main", "master"):
        r2 = _git(["rev-parse", "--verify", name], cwd)
        if r2.returncode == 0:
            return name
    return "main"


def check(project: str) -> tuple[int, list[str]]:
    """Return (exit_code, findings) for branch and worktree health."""
    findings: list[str] = []

    default = _default_branch(project)

    # Collect worktree info first so we can skip branches checked out in a worktree.
    worktrees: list[dict[str, str]] = []
    worktree_branches: set[str] = set()
    r = _git(["worktree", "list", "--porcelain"], project)
    if r.returncode == 0:
        current_wt: dict[str, str] = {}
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                if current_wt:
                    worktrees.append(current_wt)
                current_wt = {"path": line[len("worktree "):]}
            elif line == "bare":
                current_wt["bare"] = "true"
            elif line.startswith("branch "):
                current_wt["branch"] = line[len("branch "):]
            elif line == "prunable":
                current_wt["prunable"] = "true"
            elif not line:
                pass
        if current_wt:
            worktrees.append(current_wt)
        for wt in worktrees:
            b = wt.get("branch", "")
            if b:
                worktree_branches.add(b.replace("refs/heads/", "", 1))

    r = _git(["branch", "--merged", default, "--format=%(refname:short)"], project)
    if r.returncode == 0:
        for branch in r.stdout.strip().splitlines():
            branch = branch.strip()
            if not branch or branch == default:
                continue
            if branch.startswith("(HEAD detached"):
                continue
            if branch in worktree_branches:
                continue
            findings.append(f"STALE BRANCH: {branch} is fully merged into {default}")

    main_wt = None
    for wt in worktrees:
        path = wt.get("path", "")
        if wt.get("bare") == "true":
            continue
        if main_wt is None:
            main_wt = path
            continue
        if wt.get("prunable") == "true":
            findings.append(f"ORPHANED WORKTREE: {path} (prunable)")
        elif not os.path.isdir(path):
            findings.append(f"MISSING WORKTREE DIR: {path}")

    r = _git(["worktree", "prune", "--dry-run"], project)
    if r.returncode == 0 and r.stdout.strip():
        for line in r.stdout.strip().splitlines():
            msg = line.strip()
            if msg and not any(msg in f for f in findings):
                findings.append(f"PRUNABLE: {msg}")

    if findings:
        for f in findings:
            print(f)
        print(f"\n{len(findings)} issue(s) found")
        return 1, findings

    print("branch and worktree health clean")
    return 0, findings


def selftest() -> int:
    """Prove the checker catches stale branches and orphaned worktrees."""
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        os.makedirs(repo)
        _git(["init", "-b", "main", repo])
        _git(["commit", "--allow-empty", "-m", "initial"], repo)

        code, found = check(repo)
        if code != 0:
            failures.append(f"a clean repo returned {code}, expected 0")

        _git(["checkout", "-b", "feature-done"], repo)
        _git(["commit", "--allow-empty", "-m", "feature work"], repo)
        _git(["checkout", "main"], repo)
        _git(["merge", "--no-ff", "feature-done", "-m", "merge feature"], repo)

        code, found = check(repo)
        if code != 1:
            failures.append(f"a repo with a stale branch returned {code}, expected 1")
        if not any("STALE BRANCH" in f and "feature-done" in f for f in found):
            failures.append("the stale branch was not named in findings")

        _git(["branch", "-d", "feature-done"], repo)
        code, found = check(repo)
        if code != 0:
            failures.append(f"after deleting the stale branch, returned {code}, expected 0")

        wt_path = os.path.join(tmp, "worktree-test")
        _git(["worktree", "add", wt_path, "-b", "wt-branch"], repo)
        code, found = check(repo)
        if code != 0:
            failures.append(f"a valid worktree returned {code}, expected 0")

        import shutil
        shutil.rmtree(wt_path)
        code, found = check(repo)
        if code != 1:
            failures.append(f"an orphaned worktree returned {code}, expected 1")
        if not any("ORPHANED" in f or "PRUNABLE" in f or "MISSING" in f for f in found):
            failures.append("the orphaned worktree was not named in findings")

        _git(["worktree", "prune"], repo)
        code, found = check(repo)
        stale_from_wt = any("STALE" in f and "wt-branch" in f for f in found)
        if stale_from_wt:
            _git(["branch", "-D", "wt-branch"], repo)
            code, found = check(repo)
        if code != 0:
            failures.append(f"after pruning the worktree, returned {code}, expected 0")

    for line in failures:
        print(f"FAIL {line}")
    if not failures:
        print(f"PASS branch_health selftest ({6 + (1 if stale_from_wt else 0)} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("check", "selftest"), default="check", nargs="?")
    parser.add_argument("--project", default=os.getcwd())
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    code, _ = check(args.project)
    return code


if __name__ == "__main__":
    sys.exit(main())
