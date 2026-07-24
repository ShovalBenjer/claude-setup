"""Tests for the concurrent-session guard (shared-HOME destructive op classifier)."""
from __future__ import annotations

import pytest

from intent_control_plane.session_guard import (
    _ancestor_pids,
    _count_other_sessions,
    _detection_result,
    _probe_failed,
    _process_parents,
    classify,
    decide,
    guard_decision,
)

DESTRUCTIVE_COMMANDS = [
    "git worktree prune",
    "git worktree add ../scratch feat/x",
    "git worktree remove scratch",
    "git worktree move scratch scratch2",
    "git branch -d feat/old",
    "git branch -D feat/old",
    "git clean -f",
    "git clean -fd",
    "git clean -fdx",
    "git reset --hard",
    "git reset --hard origin/main",
    "git checkout -- .",
    "rm -rf ~/.git",
    "mv ~/.git /tmp/backup-git",
    "git push --force",
    "git push -f",
    "git push origin main -f",
]

READ_ONLY_COMMANDS = [
    "git status",
    "git log",
    "ls",
]


@pytest.mark.parametrize("cmd", DESTRUCTIVE_COMMANDS)
def test_classify_true_for_destructive_commands(cmd: str) -> None:
    assert classify(cmd) is True


@pytest.mark.parametrize("cmd", READ_ONLY_COMMANDS)
def test_classify_false_for_read_only_commands(cmd: str) -> None:
    assert classify(cmd) is False


def test_guard_decision_allows_read_only_always() -> None:
    decision = guard_decision("git status", other_sessions=5, override=False)
    assert decision["allow"] is True


def test_guard_decision_denies_destructive_with_other_sessions_and_no_override() -> None:
    decision = guard_decision("git worktree prune", other_sessions=2, override=False)
    assert decision["allow"] is False
    assert "2" in decision["reason"]


def test_guard_decision_allows_destructive_with_override() -> None:
    decision = guard_decision("git worktree prune", other_sessions=2, override=True)
    assert decision["allow"] is True
    assert "override" in decision["reason"]


def test_guard_decision_allows_destructive_with_no_other_sessions() -> None:
    decision = guard_decision("git worktree prune", other_sessions=0, override=False)
    assert decision["allow"] is True


# caller's own pid (999) + its ancestor chain (998 shell, 997 claude main)
EXCLUDE = {999, 998, 997}


def test_count_other_sessions_counts_two_other_processes() -> None:
    entries = [(111, "node /usr/local/bin/claude"), (222, "python3 -m codex")]
    assert _count_other_sessions(entries, EXCLUDE) == 2


def test_count_other_sessions_excludes_own_lineage() -> None:
    # own pid + full ancestor chain (claude main + shells) never count.
    entries = [
        (999, "python -m intent_control_plane.session_guard"),
        (998, "bash"),
        (997, "node /usr/local/bin/claude (own main)"),
    ]
    assert _count_other_sessions(entries, EXCLUDE) == 0


def test_count_other_sessions_includes_sibling_in_same_posix_session() -> None:
    # flag-4 fix: a sibling session is NOT in the caller's lineage, so it is
    # counted even if it would share the caller's POSIX session id.
    entries = [(555, "node /usr/local/bin/claude")]
    assert _count_other_sessions(entries, EXCLUDE) == 1


def test_count_other_sessions_ignores_pgrep_invocation_line() -> None:
    entries = [(111, "node /usr/local/bin/claude"), (556, "pgrep -af claude")]
    assert _count_other_sessions(entries, EXCLUDE) == 1


def test_count_other_sessions_ignores_non_claude_processes() -> None:
    assert _count_other_sessions([(111, "node /usr/bin/other-app")], EXCLUDE) == 0


def test_count_other_sessions_case_insensitive_match() -> None:
    assert _count_other_sessions([(111, "NODE /usr/local/bin/CLAUDE")], EXCLUDE) == 1


def test_ancestor_pids_walks_the_chain() -> None:
    assert _ancestor_pids(100, {100: 50, 50: 10, 10: 1}) == {50, 10}


def test_ancestor_pids_guards_against_cycles() -> None:
    assert _ancestor_pids(5, {5: 6, 6: 5}) == {6}


def test_process_parents_parses_ps_output() -> None:
    lines = ["  100    50", "50 10", "garbage line", "10 1"]
    assert _process_parents(lines) == {100: 50, 50: 10, 10: 1}


def test_detection_result_none_when_a_probe_failed() -> None:
    # any probe failure means detection is incomplete; fail safe (None -> block).
    assert _detection_result([(111, "node claude")], set(), any_probe_failed=True) is None


def test_detection_result_counts_when_all_probes_ok() -> None:
    assert _detection_result([(111, "node claude")], set(), any_probe_failed=False) == 1


def test_probe_failed_only_for_error_returncodes() -> None:
    # 0 (found) and 1 (none found) are successful probes; 2/3 are errors.
    assert _probe_failed(0) is False
    assert _probe_failed(1) is False
    assert _probe_failed(2) is True
    assert _probe_failed(3) is True


def test_decide_blocks_destructive_when_detection_unavailable() -> None:
    # detected is None means session detection could not run at all; a
    # destructive op must fail SAFE (block), not fail open.
    d = decide("git worktree prune", detected=None, override=False)
    assert d["allow"] is False
    assert "detection unavailable" in d["reason"]


def test_decide_allows_destructive_when_detection_unavailable_but_override() -> None:
    d = decide("git worktree prune", detected=None, override=True)
    assert d["allow"] is True
    assert "override" in d["reason"]


def test_decide_delegates_to_guard_when_detection_succeeded() -> None:
    assert decide("git worktree prune", detected=3, override=False)["allow"] is False
    assert decide("git worktree prune", detected=0, override=False)["allow"] is True


def test_decide_allows_read_only_even_when_detection_unavailable() -> None:
    assert decide("git status", detected=None, override=False)["allow"] is True
