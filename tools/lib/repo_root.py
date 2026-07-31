"""Which claude-setup checkout is a tool operating on?

Every tool here used to answer that with `Path.home() / "claude-setup"`. That is
right on Windows and quietly wrong from WSL, where `Path.home()` is `/home/shov`
and the migration left a second checkout there, two commits behind the one under
`/mnt/c`. The tools did not fail; they read a stale tree and wrote their output
into it. tests/test_repo_root.py carries the measurement.

The rule this module encodes: a tool belongs to the checkout it LIVES IN, not to
the checkout that happens to sit under the invoking user's home. Home is the last
resort, kept only for a caller with no positional evidence at all, and even then
the result must be a real checkout rather than a constructed path.

Order:
    1. CLAUDE_OS_DIR, if set to something non-blank. The operator's override wins
       outright and is not validated against git, because pointing it at a
       worktree or an export is a legitimate thing to do.
    2. The nearest ancestor of `start` containing `.git`. `start` defaults to this
       file, so any tool that imports this module gets its own checkout.
    3. `home/claude-setup`, if that is itself a checkout.
    4. RepoRootNotFound. Never a path that was assembled but not confirmed.
"""

from __future__ import annotations

import os
import pathlib


class RepoRootNotFound(RuntimeError):
    """No checkout could be identified, and guessing one is not an option."""


def _is_checkout(p: pathlib.Path) -> bool:
    # A worktree carries `.git` as a file rather than a directory, so test for
    # existence and not for is_dir().
    return (p / ".git").exists()


def find_upward(start: pathlib.Path) -> pathlib.Path | None:
    start = pathlib.Path(start).resolve()
    for candidate in (start, *start.parents):
        if _is_checkout(candidate):
            return candidate
    return None


def resolve(start: pathlib.Path | str | None = None,
            home: pathlib.Path | str | None = None,
            env: dict | None = None) -> pathlib.Path:
    """The harness repo root. `start`/`home`/`env` are injectable for the tests."""
    env = os.environ if env is None else env
    override = (env.get("CLAUDE_OS_DIR") or "").strip()
    if override:
        return pathlib.Path(override).resolve()

    start = pathlib.Path(__file__).resolve().parent if start is None else pathlib.Path(start)
    found = find_upward(start)
    if found is not None:
        return found

    home = pathlib.Path.home() if home is None else pathlib.Path(home)
    fallback = (home / "claude-setup").resolve()
    if _is_checkout(fallback):
        return fallback

    raise RepoRootNotFound(
        f"no claude-setup checkout found from {start} or under {home}; "
        "set CLAUDE_OS_DIR to name one explicitly"
    )
