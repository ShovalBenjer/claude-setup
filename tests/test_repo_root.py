"""Oracle for tools/lib/repo_root.py: which claude-setup does a tool operate on?

THE DEFECT, MEASURED 2026-07-31

Four tools resolve the harness repo as `Path.home() / "claude-setup"` when
`CLAUDE_OS_DIR` is unset:

    tools/selfimprove/scan.py:20      tools/digest/build_digest.py:10
    tools/local/reflex_router.py:14   tools/audit_claude_setup.py:189

On Windows that is `C:\\Users\\shova\\claude-setup` and is correct. Run the same
tool from WSL and `Path.home()` is `/home/shov`, where the migration left a
CLONE of this repo:

    git -C /mnt/c/Users/shova/claude-setup rev-parse HEAD -> 3f23458
    git -C /home/shov/claude-setup        rev-parse HEAD -> 8a4217b   (2 behind)

So the tools do not fail. They succeed, against a stale repository, and write
their output there. `scan.py` calls `OUT.mkdir(parents=True, exist_ok=True)` and
writes `proposals.jsonl`; a ranked work list computed from a two-commit-old tree
and deposited where nobody reads it is a worse outcome than a crash, because a
crash is attributable.

WHAT THIS PINS

  - An explicit `CLAUDE_OS_DIR` always wins. It is the operator's override and
    nothing may second-guess it.
  - With no override, the answer comes from where the TOOL lives, not from where
    the user's home is. A tool inside a checkout belongs to that checkout.
  - The home fallback survives only for the case it was written for: a tool
    invoked with no positional evidence at all.
  - The resolver never silently returns a directory that is not a checkout.

Deliberately NOT pinned here: which of the two checkouts is authoritative. That
is an operator decision (see the cross-repo duplicate note in
~/.claude/rules/hidden-trees.md, same class of finding). This module only
guarantees a tool stops picking one by accident.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from lib import repo_root  # noqa: E402


def _git_init(d: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=d, check=True,
                   capture_output=True)


@pytest.fixture
def two_checkouts(tmp_path: Path):
    """A 'real' checkout holding the tool, and a decoy under a fake home."""
    real = tmp_path / "real" / "claude-setup"
    (real / "tools" / "lib").mkdir(parents=True)
    _git_init(real)

    fake_home = tmp_path / "home"
    decoy = fake_home / "claude-setup"
    decoy.mkdir(parents=True)
    _git_init(decoy)
    return real, fake_home, decoy


class TestOverrideWins:
    def test_explicit_env_beats_everything(self, two_checkouts, monkeypatch):
        real, fake_home, decoy = two_checkouts
        chosen = real.parent / "elsewhere"
        chosen.mkdir()
        monkeypatch.setenv("CLAUDE_OS_DIR", str(chosen))
        assert repo_root.resolve(start=decoy, home=fake_home) == chosen

    def test_blank_env_is_not_an_override(self, two_checkouts, monkeypatch):
        real, fake_home, _ = two_checkouts
        monkeypatch.setenv("CLAUDE_OS_DIR", "   ")
        assert repo_root.resolve(start=real / "tools" / "lib",
                                 home=fake_home) == real


class TestLocationBeatsHome:
    def test_a_tool_inside_a_checkout_gets_that_checkout(self, two_checkouts,
                                                        monkeypatch):
        """The whole defect in one assertion: the decoy under home must lose."""
        real, fake_home, decoy = two_checkouts
        monkeypatch.delenv("CLAUDE_OS_DIR", raising=False)
        got = repo_root.resolve(start=real / "tools" / "lib", home=fake_home)
        assert got == real
        assert got != decoy

    def test_walks_up_from_a_nested_tool(self, two_checkouts, monkeypatch):
        real, fake_home, _ = two_checkouts
        deep = real / "tools" / "lib" / "a" / "b"
        deep.mkdir(parents=True)
        monkeypatch.delenv("CLAUDE_OS_DIR", raising=False)
        assert repo_root.resolve(start=deep, home=fake_home) == real


class TestHomeFallback:
    def test_used_only_when_the_start_point_is_in_no_checkout(self, two_checkouts,
                                                              monkeypatch, tmp_path):
        _, fake_home, decoy = two_checkouts
        orphan = tmp_path / "orphan"
        orphan.mkdir()
        monkeypatch.delenv("CLAUDE_OS_DIR", raising=False)
        assert repo_root.resolve(start=orphan, home=fake_home) == decoy

    def test_absent_everywhere_raises_rather_than_inventing_a_path(
            self, monkeypatch, tmp_path):
        monkeypatch.delenv("CLAUDE_OS_DIR", raising=False)
        empty = tmp_path / "nothing"
        empty.mkdir()
        with pytest.raises(repo_root.RepoRootNotFound):
            repo_root.resolve(start=empty, home=empty)


class TestTheLiveCallers:
    """The four modules named in the docstring must not reintroduce the pattern."""

    OFFENDERS = [
        "tools/selfimprove/scan.py",
        "tools/digest/build_digest.py",
        "tools/local/reflex_router.py",
        "tools/audit_claude_setup.py",
    ]

    @pytest.mark.parametrize("rel", OFFENDERS)
    def test_no_bare_home_claude_setup_default(self, rel):
        raw = (Path(__file__).resolve().parents[1] / rel).read_text(
            encoding="utf-8", errors="replace")
        # Comment lines are stripped before matching. A fix that documents the
        # pattern it removed must not read as the pattern still being there;
        # that is L-2026-07-29-d, an oracle that cannot tell code from prose
        # about code, and it is the reason this test nearly failed its own fix.
        src = "\n".join(ln for ln in raw.splitlines()
                        if not ln.lstrip().startswith("#"))
        assert 'home() / "claude-setup"' not in src, (
            f"{rel} still defaults the harness repo to the user's home; under WSL "
            "that is the stale clone at /home/shov/claude-setup")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
