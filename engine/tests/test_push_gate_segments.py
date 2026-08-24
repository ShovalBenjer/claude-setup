"""A recognised push inside a compound command is still a recognised push.

The operator was prompted twice on 2026-08-08 after the proof branch had already
been downgraded to a note, and the cause was not the push. Every recognised-form
check in `pre_push_gate.py` is a `fullmatch` against the WHOLE command string, so
a bare `git push` passed and the same push inside a `;` chain or behind a pipe
did not, and asked on the grounds of being an unrecognised form. It was not an
unrecognised push. It was a recognised push with other commands around it.

The first two cases here are the exact strings he was asked to approve. The rest
exist because the fix is a widening, and a widening needs its boundary pinned:
main and master still ask, wrappers still ask, unknown flags still ask, and a
command containing two pushes asks rather than silently judging one of them.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "payload", "dot-claude", "hooks"))

import pre_push_gate as gate  # noqa: E402

CHAIN = 'git status; git add -A; git commit -q -m "x"; git push -q -u gh HEAD; echo pushed'


@pytest.mark.parametrize("command, expected", [
    (CHAIN, "git push -q -u gh HEAD"),
    ("git push 2>&1 | tail -3", "git push"),
    ("git push", "git push"),
    ("git push -q gh HEAD && echo done", "git push -q gh HEAD"),
    ("git status && git log --oneline -1", None),
])
def test_the_pushing_segment_is_isolated(command, expected):
    assert gate.push_segment(command) == expected


def test_two_pushes_return_none_so_the_whole_command_is_judged():
    """Picking one would hide the other, and a double push is worth a human read."""
    assert gate.push_segment("git push gh HEAD; git push other HEAD") is None


def test_a_redirect_does_not_survive_into_the_segment():
    """`2>&1` contains an ampersand and broke the split before it was stripped.

    The separator set cut the redirect in half and left `git push 2>` as the
    segment, which matches no push form, so the fix for a prompt produced a
    prompt.
    """
    assert "2>" not in (gate.push_segment("git push 2>&1 | tail -3") or "")


def test_the_isolated_segment_still_has_to_be_a_recognised_form():
    """The widening is about WHERE the push sits, not about what counts as safe."""
    assert gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch(gate.push_segment(CHAIN))
    assert not gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch(
        gate.push_segment("git add -A; git push --all"))


def test_a_protected_target_is_still_caught_inside_a_chain():
    """ADR-0012 is the one stop worth keeping, and a chain must not launder it."""
    assert gate.PROTECTED_TARGET.search(gate.push_segment("git add -A; git push gh main"))
    assert gate.PROTECTED_TARGET.search(
        gate.push_segment("echo hi && git push origin master"))


def test_a_wrapper_is_not_a_push_form_even_though_it_contains_one():
    """`sh -c 'git push'` isolates to the whole sh call, which matches nothing."""
    segment = gate.push_segment("cd /tmp; sh -c 'git push'")
    assert not gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch(segment)
