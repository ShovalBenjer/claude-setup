"""A ~/.claude that is a directory is not a ~/.claude that is a deployment.

Measured 2026-08-10 on a Claude Code container. `~/.claude/skills` existed and
held the container's own skills, so skills_sync's guard (which keyed on the
DIRECTORY) passed, the survey compared this repository against a tree that was
never synced from it, and the domain reported `DRIFT: 87` against the 28 the
contract records. That number also drove the waiver's `confirm` string STALE and
failed the whole gate, for a reason with nothing to do with drift.

`pointers.py` hit the identical defect on 2026-08-05 and was fixed by keying its
guard on `settings.json` rather than the directory, because a runner creates the
empty directory. The same guard was never brought to this tool. Lesson class
L-2026-07-31-g, a host-shaped oracle answering the wrong question on a host it
was not written for.

Both directions are pinned. A guard that only ever says "cannot measure" is as
useless as one that never does, and it would silently disable the domain on the
operator's own machine.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "audit"))

import skills_sync  # noqa: E402


@pytest.fixture
def live_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude" / "skills").mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_LIVE_HOME", str(home))
    return home / ".claude"


def test_a_skills_directory_without_settings_is_not_a_deployment(live_home):
    assert live_home.is_dir()
    assert (live_home / "skills").is_dir()
    assert not skills_sync.is_deployed_home()


def test_the_same_tree_is_a_deployment_once_settings_exists(live_home):
    (live_home / "settings.json").write_text(json.dumps({"hooks": {}}) + "\n")
    assert skills_sync.is_deployed_home()


def test_an_absent_home_is_also_not_a_deployment(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_LIVE_HOME", str(tmp_path / "nothing-here"))
    assert not skills_sync.is_deployed_home()


def test_check_returns_cannot_measure_rather_than_a_drift_number(live_home, capsys):
    """Exit 2, not 1. gate.py already reads 2 as cannot-measure and records the
    domain under waivers_unconfirmed, so the verdict stays honest about what it
    did not check instead of failing or silently passing."""
    class Args:
        strict = False

    rc = skills_sync.cmd_check(Args())
    out = capsys.readouterr().out
    assert rc == 2, out
    assert "DRIFT" not in out, "a foreign tree must not produce a drift count"
    assert "settings.json" in out, "the message must name the discriminator"


def test_the_directory_guard_still_fires_when_there_is_no_skills_tree(tmp_path, monkeypatch,
                                                                     capsys):
    """The older guard is not replaced by the new one. Its message is distinct,
    because 'no tree at all' and 'a tree that is not ours' are different facts
    and a checker that prints one word for both cannot be acted on."""
    monkeypatch.setenv("CLAUDE_LIVE_HOME", str(tmp_path / "empty"))

    class Args:
        strict = False

    rc = skills_sync.cmd_check(Args())
    out = capsys.readouterr().out
    assert rc == 2
    assert "no live skills tree" in out
