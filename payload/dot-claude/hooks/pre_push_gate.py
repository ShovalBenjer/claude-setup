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
# Ordinary ways to publish a feature branch. An ALLOW-LIST: anything this does not
# recognise still asks, so an unfamiliar shape is never silently permitted.
#
# Widened 2026-08-06. The previous pattern was `^\s*git\s+push\s*$`, which admitted a
# bare `git push` and nothing else, so every real push prompted. It was also redundant:
# `hookgate` runs first on the same event and DENIES force, --delete, --mirror, --prune
# and a leading `+` refspec outright, so this gate was re-asking about a class already
# refused and spending its signal on shapes that were unfamiliar rather than dangerous.
#
#   git push
#   git push [-q] [-u|--set-upstream] <remote> [<branch>|HEAD:<branch>]
#
# A remote is a bare name only. A URL or a path is not a known remote and still asks.
# Must NOT begin with a dash. Caught by the verification pass: with a leading dash
# allowed, `--all` and `--tags` parsed as remote NAMES and ran autonomously, so any
# unknown flag would have. An allow-list that admits arbitrary flags is a deny-list
# with extra steps.
_REMOTE = r"[A-Za-z0-9._][A-Za-z0-9._-]*"
_BRANCH = r"[A-Za-z0-9._/-]+"
SIMPLE_CURRENT_BRANCH_PUSH = re.compile(
    r"(?i)^\s*git\s+push"
    r"(?:\s+-q|\s+--quiet)?"
    r"(?:\s+(?:-u|--set-upstream))?"
    r"(?:\s+" + _REMOTE + r"(?:\s+(?:HEAD:)?" + _BRANCH + r")?)?"
    r"\s*$")

# The one target that must never be automatic. ADR-0012: work ships through a PR, so a
# direct push to the deploy branch is exactly the push a human should see. Matched on the
# END of the refspec, so `HEAD:main` and a bare `main` are both caught.
PROTECTED_TARGET = re.compile(r"(?i)\bgit\s+push\b[^\r\n]*?(?:^|\s|:)(?:main|master)\s*$")
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


SEPARATORS = re.compile(r"&&|\|\||[;\n|]")

# Redirections are noise to every question this file asks, and they actively break
# the split: `git push 2>&1 | tail -3` contains an `&`, so a separator set that
# includes a bare `&` cuts the redirect in half and leaves `git push 2>` as the
# segment, which matches no push form and asks. Stripped before segmenting rather
# than after, so the separator pass never sees them.
REDIRECT = re.compile(r"\s*\d?>>?\s*&?\s*[^\s;|&]+|\s*<\s*[^\s;|&]+")


def push_segment(command: str) -> str | None:
    """The one shell segment that pushes, or None if that is not what this is.

    Added 2026-08-08 because the operator was still being prompted after the
    proof branch was downgraded, and the cause was not the push at all. Every
    recognised-form check here is a `fullmatch` against the WHOLE command
    string, so `git push` alone passes and

        git add -A; git commit -q -m msg; git push -q -u gh HEAD; echo pushed
        git push 2>&1 | tail -3

    both fail to match and ask, on the grounds of being an unrecognised push
    form. They are not unrecognised pushes. They are recognised pushes inside a
    compound command, and the parser had no way to say so.

    Splitting on shell separators and returning the pushing segment lets the
    existing checks run against the thing they were written for. It deliberately
    does NOT widen what counts as safe: the segment still has to satisfy
    SIMPLE_CURRENT_BRANCH_PUSH, still asks on main or master, and a wrapper such
    as `sh -c 'git push'` still fails because the segment is the whole `sh -c`
    call, which is not a push form.

    Two or more pushing segments returns None, which falls back to matching the
    entire string and therefore asks. A command that pushes twice is exactly the
    shape worth a human read, and picking one of them would hide the other.

    This cannot parse shell. A `git push` inside a quoted string or a heredoc is
    seen as a segment and, failing to match the simple form, asks. That is the
    same false positive hookgate documents and keeps on purpose: the failure
    direction is a question nobody needed, not a push nobody saw.
    """
    segments = [s.strip() for s in SEPARATORS.split(REDIRECT.sub("", command))]
    pushing = [s for s in segments if PUSH.search(s)]
    return pushing[0] if len(pushing) == 1 else None


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


def note(reason: str) -> None:
    """Say it without stopping the push.

    Changed 2026-08-08 on the operator's instruction that git should not prompt
    him. This is deliberately not a removal: the reason still reaches stderr, it
    simply no longer converts every push into a decision.

    Why this particular check and not the others. The missing-proof branch fires
    on any push carrying an unpushed source file with no valid
    `.claude/proofs/current.json`. That file is real and `/prove-implementation`
    really does write it, but producing it is a manual per-push ritual that is
    not part of the flow, so in practice the branch fired on essentially every
    substantive push. A gate that asks every time is not a gate, it is the
    alarm-blindness failure the ledger already carries: the operator learns to
    approve without reading, and the one push that genuinely needed a second
    look is approved with the same reflex as the ninety before it.

    What stays an ask, and why each earns it: a push aimed at main or master,
    because ADR-0012 makes the deploy branch the one target that is never
    automatic and it is rare enough to be worth a stop; and a push whose form
    the parser does not recognise, because an unrecognised form is not a known
    quantity being waved through. Separately, the hookgate binary still DENIES
    bare force-push, remote ref deletion, mirror push and forced refspecs, and
    a deny is not affected by anything here.
    """
    print(json.dumps({}))
    print(reason, file=sys.stderr)


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
    command = push_segment(command) or command
    if PROTECTED_TARGET.search(command):
        ask(
            "This push targets main or master directly. ADR-0012 says work ships through "
            "a pull request, so the deploy branch is the one target that is never "
            "automatic. Push a feature branch and open a PR, or confirm explicitly."
        )
        return 0
    if not SIMPLE_CURRENT_BRANCH_PUSH.fullmatch(command):
        ask(
            "This push is not one of the recognised feature-branch forms "
            "(`git push`, `git push [-q] [-u] <remote> [<branch>|HEAD:<branch>]`). "
            "Wrappers, extra flags, URLs as remotes, and unfamiliar refspecs are "
            "reviewed explicitly rather than assumed safe."
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
        note("pre-push note: the implementation proof at .claude/proofs/current.json is "
             "invalid or incomplete. Pushing anyway; run /prove-implementation if this "
             "change deserves evidence bound to the commit.")
    elif source and proof is not True:
        note("pre-push note: this push changes behavior-affecting files and no valid, "
             "current-state-bound implementation proof covers them. Test-file presence "
             "alone is not execution evidence. Pushing anyway.")
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
