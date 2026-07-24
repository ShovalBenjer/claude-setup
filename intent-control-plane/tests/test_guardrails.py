"""Tests for guardrails.py: anti-reward-hacking screen, scoped-diff, topology-fitness (P21).

Constraints 6-7 of the spec. reward_hacking_flags screens a proposed diff for the gaming patterns
the 2026 literature named (deleting a check, skipping a test, suppressing a gate); is_scoped_diff
rejects full-file rewrites and over-broad diffs (full-rewrite freedom increases hacking); and
topology_fitness decides whether to swarm (loosely-coupled, decomposable) or orchestrate (coupled)
before fanning out. Pure functions over real diff/text fixtures, no mocks.
"""
from __future__ import annotations

from intent_control_plane.guardrails import (
    is_scoped_diff,
    reward_hacking_flags,
    topology_fitness,
)

DIFF_CLEAN = (
    "diff --git a/mod.py b/mod.py\n"
    "@@ -1,3 +1,4 @@\n"
    " def foo():\n"
    "-    return 1\n"
    "+    if x:\n"
    "+        return 2\n"
    "+    return 1\n"
)

DIFF_REMOVED_ASSERT = (
    "diff --git a/test_x.py b/test_x.py\n"
    "@@ -1,3 +1,2 @@\n"
    " def test_thing():\n"
    "-    assert compute() == 42\n"
    "+    compute()\n"
)

DIFF_SUPPRESSION = (
    "diff --git a/mod.py b/mod.py\n"
    "@@ -1,1 +1,1 @@\n"
    "-value = compute()\n"
    "+value = compute()  # type: ignore\n"
)

DIFF_SKIP = (
    "diff --git a/test_y.py b/test_y.py\n"
    "@@ -1,2 +1,3 @@\n"
    '+@pytest.mark.skip(reason="flaky")\n'
    " def test_y():\n"
    "     pass\n"
)

DIFF_REMOVED_TEST = (
    "diff --git a/test_z.py b/test_z.py\n"
    "@@ -1,2 +1,0 @@\n"
    "-def test_z():\n"
    "-    assert True\n"
)


def test_reward_hacking_flags_detects_removed_assertion():
    assert "removed-assertion-or-raise" in reward_hacking_flags(DIFF_REMOVED_ASSERT)


def test_reward_hacking_flags_detects_added_suppression():
    assert "added-check-suppression" in reward_hacking_flags(DIFF_SUPPRESSION)


def test_reward_hacking_flags_detects_added_skip():
    assert "added-test-skip" in reward_hacking_flags(DIFF_SKIP)


def test_reward_hacking_flags_detects_removed_test():
    assert "removed-test-case" in reward_hacking_flags(DIFF_REMOVED_TEST)


def test_reward_hacking_flags_clean_diff_has_none():
    assert reward_hacking_flags(DIFF_CLEAN) == []


def test_is_scoped_diff_accepts_small():
    assert is_scoped_diff(DIFF_CLEAN) is True


def test_is_scoped_diff_rejects_full_file_rewrite():
    rewrite = "diff --git a/big.py b/big.py\n" + "\n".join(f"-old line {i}" for i in range(200))
    assert is_scoped_diff(rewrite) is False


def test_is_scoped_diff_rejects_too_many_files():
    many = "\n".join(f"diff --git a/f{i}.py b/f{i}.py\n+x = {i}" for i in range(4))
    assert is_scoped_diff(many, max_files=3) is False


def test_topology_fitness_swarm_vs_orchestrate():
    assert topology_fitness(local_passes=4, coupling=0.2) == "swarm"      # decomposable + loosely coupled
    assert topology_fitness(local_passes=4, coupling=0.8) == "orchestrate"  # highly coupled -> sequence it
    assert topology_fitness(local_passes=1, coupling=0.1) == "orchestrate"  # nothing to fan out
