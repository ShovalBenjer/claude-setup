#!/usr/bin/env python3
"""Ask for review before pushing source changes without nearby test evidence."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PUSH = re.compile(r"(?i)\bgit\b[^\r\n;&|]{0,400}\bpush\b")
SIMPLE_CURRENT_BRANCH_PUSH = re.compile(r"(?i)^\s*git\s+push\s*$")
SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".hxx", ".cs", ".go",
    ".java", ".js", ".jsx", ".mjs", ".cjs", ".kt", ".php", ".py", ".r",
    ".rb", ".rs", ".scala", ".swift", ".ts", ".tsx", ".vue", ".svelte",
    ".sql", ".sh", ".ps1", ".tf", ".hcl", ".yaml", ".yml", ".proto",
    ".gradle", ".kts", ".csproj", ".fsproj", ".vbproj", ".ipynb", ".prisma",
    ".graphql", ".gql", ".toml", ".jsonc", ".bicep", ".dart", ".jl", ".lua",
}
BEHAVIOR_FILENAMES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "bun.lock", "bun.lockb", "pyproject.toml", "poetry.lock", "uv.lock",
    "cargo.toml", "cargo.lock", "go.mod", "go.sum", "gradlew",
    "gradle.properties", "pom.xml", "composer.json", "composer.lock",
    "gemfile", "gemfile.lock",
    "tsconfig.json", "jsconfig.json", "deno.json", "deno.jsonc",
}
CONFIG_PREFIXES = (
    "tsconfig.", "jsconfig.", "wrangler.", "next.config.", "vite.config.",
    "astro.config.", "svelte.config.", "nuxt.config.", "playwright.config.",
    "vitest.config.", "jest.config.", "eslint.config.", "rollup.config.",
    "webpack.config.", "tailwind.config.", "drizzle.config.",
)
TEST_MARKERS = (
    "/test/", "/tests/", "/spec/", "/specs/", "__tests__/",
    ".test.", ".tests.", ".spec.", "_test.",
)


def discover_repo_root(cwd: Path) -> Path | None:
    candidate = cwd.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for parent in (candidate, *candidate.parents):
        if (parent / ".git").exists():
            if parent.resolve() == Path.home().resolve() or parent.parent == parent:
                return None
            return parent
    return None


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )


def changed_files(cwd: Path) -> tuple[Path | None, list[str]]:
    root = discover_repo_root(cwd)
    if root is None:
        return None, []
    files: set[str] = set()
    cached = run_git(root, "diff", "--name-only", "--cached")
    if cached.returncode != 0:
        return root, ["__INSPECTION_FAILED__"]
    files.update(line.strip().replace("\\", "/") for line in cached.stdout.splitlines() if line.strip())
    branch = run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    upstream = run_git(root, "rev-parse", "--symbolic-full-name", "@{upstream}")
    push_target = run_git(root, "rev-parse", "--symbolic-full-name", "@{push}")
    if branch.returncode != 0 or upstream.returncode != 0 or push_target.returncode != 0:
        return root, sorted(files | {"__NO_UPSTREAM__"})
    push_default = run_git(root, "config", "--get", "push.default")
    if push_default.returncode not in {0, 1}:
        return root, ["__INSPECTION_FAILED__"]
    if push_default.returncode == 0 and push_default.stdout.strip() != "simple":
        return root, sorted(files | {"__AMBIGUOUS_PUSH__"})
    if upstream.stdout.strip() != push_target.stdout.strip():
        return root, sorted(files | {"__AMBIGUOUS_PUSH__"})
    branch_name = branch.stdout.strip()
    remote = run_git(root, "config", "--get", f"branch.{branch_name}.remote")
    if remote.returncode != 0 or not remote.stdout.strip():
        return root, sorted(files | {"__AMBIGUOUS_PUSH__"})
    remote_name = remote.stdout.strip()
    configured_refspec = run_git(root, "config", "--get-all", f"remote.{remote_name}.push")
    remote_mirror = run_git(root, "config", "--bool", "--get", f"remote.{remote_name}.mirror")
    follow_tags = run_git(root, "config", "--bool", "--get", "push.followTags")
    if configured_refspec.returncode == 0:
        return root, sorted(files | {"__AMBIGUOUS_PUSH__"})
    if remote_mirror.stdout.strip() == "true" or follow_tags.stdout.strip() == "true":
        return root, sorted(files | {"__AMBIGUOUS_PUSH__"})
    comparison = ("diff", "--name-only", "@{push}..HEAD")
    committed = run_git(root, *comparison)
    if committed.returncode != 0:
        return root, ["__INSPECTION_FAILED__"]
    files.update(line.strip().replace("\\", "/") for line in committed.stdout.splitlines() if line.strip())
    return root, sorted(files)


def is_test(path: str) -> bool:
    normalized = "/" + path.lower().lstrip("/")
    name = Path(path).name.lower()
    return name.startswith("test_") or any(marker in normalized for marker in TEST_MARKERS)


def is_source(path: str) -> bool:
    normalized = "/" + path.lower().lstrip("/")
    name = Path(path).name.lower()
    return (
        (
            Path(path).suffix.lower() in SOURCE_SUFFIXES
            or name in BEHAVIOR_FILENAMES
            or name.startswith(CONFIG_PREFIXES)
            or name.startswith("requirements")
            or name.startswith("dockerfile")
            or name in {"makefile", "justfile"}
            or "/.github/workflows/" in normalized
            or "/migrations/" in normalized
            or "/.claude/hooks/" in normalized
        )
        and not is_test(path)
    )


def current_repo_state(root: Path) -> dict[str, str | None]:
    validator = (
        Path.home()
        / ".claude"
        / "skills"
        / "prove-implementation"
        / "scripts"
        / "implementation_proof.py"
    )
    if not validator.is_file():
        return {"git_commit": None, "diff_sha256": None}
    result = subprocess.run(
        [sys.executable, str(validator), "state", "--cwd", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        return {"git_commit": None, "diff_sha256": None}
    try:
        state = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"git_commit": None, "diff_sha256": None}
    return {
        "git_commit": state.get("git_commit"),
        "diff_sha256": state.get("diff_sha256"),
    }


def proof_is_valid(root: Path, expected_state: dict[str, str | None]) -> bool | None:
    proof = root / ".claude" / "proofs" / "current.json"
    if not proof.exists():
        return None
    try:
        validator = (
            Path.home()
            / ".claude"
            / "skills"
            / "prove-implementation"
            / "scripts"
            / "implementation_proof.py"
        )
        if not validator.is_file():
            return False
        validated = subprocess.run(
            [sys.executable, str(validator), "validate", str(proof)],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if validated.returncode != 0:
            return False
        data = json.loads(proof.read_text(encoding="utf-8"))
        checks = data["verification"]["checks"]
        passing = [
            check for check in checks
            if check.get("status") == "pass"
            and check.get("exit_code") == 0
            and str(check.get("command", "")).strip()
            and str(check.get("output_sha256", "")).strip()
        ]
        states_match = bool(passing) and all(
            check.get("repo_state", {}).get("git_commit") == expected_state["git_commit"]
            and check.get("repo_state", {}).get("diff_sha256") == expected_state["diff_sha256"]
            for check in passing
        )
        return (
            data.get("schema_version") == "implementation-proof.v1" and states_match
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
        return False


def ask(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    try:
        payload: Any = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        command = str(payload.get("tool_input", {}).get("command", ""))
        raw_cwd = payload.get("cwd") or os.getcwd()
        cwd = Path(str(raw_cwd))
    except (AttributeError, json.JSONDecodeError, TypeError, OSError, UnicodeDecodeError):
        print("{}")
        return 0

    if not PUSH.search(command):
        print("{}")
        return 0
    if not SIMPLE_CURRENT_BRANCH_PUSH.fullmatch(command):
        ask(
            "Only a plain `git push` can be bound automatically to the current "
            "branch and its upstream. Review wrappers, refspecs, flags, and other repositories explicitly."
        )
        return 0

    try:
        root, files = changed_files(cwd)
        if root is None:
            ask(
                "The hook cannot safely identify a bounded repository for this push. "
                "Automatic proof is disabled for home/root repositories; review the target explicitly."
            )
            return 0
        if not files:
            print("{}")
            return 0
        if "__INSPECTION_FAILED__" in files:
            ask("Git push inspection failed after a repository was found. Review repository ownership and changed files before push.")
            return 0
        if "__NO_UPSTREAM__" in files:
            ask("This branch has no upstream, so the hook cannot prove which commits or refs will be pushed. Review the push target explicitly.")
            return 0
        if "__AMBIGUOUS_PUSH__" in files:
            ask(
                "Plain `git push` is not provably a single current-branch push to "
                "the upstream ref under this repository's push configuration. Review the destination and refs explicitly."
            )
            return 0
        source = [path for path in files if is_source(path)]
        state = current_repo_state(root) if source else None
        if source and (
            not state
            or not state.get("git_commit")
            or not state.get("diff_sha256")
        ):
            ask(
                "The hook could not bind evidence to the current commit and complete "
                "working-tree state. Review the repository state before push."
            )
            return 0
        proof = proof_is_valid(root, state) if source and state else None
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        ask("Git push inspection failed. Review the target, changed files, and implementation evidence before push.")
        return 0

    if source and proof is False:
        ask("The implementation proof at .claude/proofs/current.json is invalid or incomplete. Review it before push.")
    elif source and proof is not True:
        ask(
            "This push changes behavior-affecting files but no valid, current-state-bound "
            "implementation proof covers the change. Test-file presence alone is not execution evidence."
        )
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
