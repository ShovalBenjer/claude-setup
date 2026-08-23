"""Pin which git pushes run autonomously and which still ask.

`dot-claude/hooks/pre_push_gate.py` is a LIVE PreToolUse hook. On 2026-08-06 its
allow-pattern was widened from `^\\s*git\\s+push\\s*$`, which admitted a bare push and
nothing else, to an allow-list of the ordinary feature-branch forms.

That widening was verified by a script in a temp directory, which is not verification at
all: nothing in the repository would catch a future edit to the regex, and this file is a
security control. Same shape as the finding this session spent a day on, that an
instrument without an oracle is decorative, arriving in the work that fixed it.

TWO PROPERTIES, and the second is the one that bites.

  ALLOW must stay narrow. It is an allow-list, so an unrecognised shape asks. The first
  version of the widened pattern let a remote name begin with a dash, so `--all` and
  `--tags` parsed as REMOTE NAMES and ran autonomously; any unknown flag would have. An
  allow-list that admits arbitrary flags is a deny-list with extra steps.

  ASK must keep main. ADR-0012 says work ships through a pull request, so a DIRECT push
  to the deploy branch is the one push a human should always see. This is about `git push
  origin main`, not about merging a PR into main, which is a different operation and is
  deliberately unaffected.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "dot-claude" / "hooks" / "pre_push_gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("_pre_push_gate_under_test", GATE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def gate():
    return _load()


def decides(mod, command: str) -> str:
    """"auto" when the hook would stay silent, "ask" when it would prompt."""
    if mod.PROTECTED_TARGET.search(command):
        return "ask"
    return "auto" if mod.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch(command) else "ask"


AUTONOMOUS = [
    "git push",
    "git push gh",
    "git push gh lane-a/foo",
    "git push -u gh lane-a/foo",
    "git push -q -u gh lane-a/foo",
    "git push --set-upstream origin HEAD:lane-a/session-corpus-extractor",
    "git push origin HEAD:lane-a/foo",
]

MUST_ASK = [
    ("git push origin main", "a direct push to the deploy branch, ADR-0012"),
    ("git push gh HEAD:main", "same, via a refspec"),
    ("git push origin master", "the other deploy-branch spelling"),
    ("git push --all gh", "a flag must never parse as a remote NAME"),
    ("git push --tags gh", "same class; this one shipped broken for one iteration"),
    ("git push https://github.com/x/y.git foo", "a URL is not a known remote"),
    ("git push gh foo && echo done", "a second command rides along"),
    ("git push gh foo | tee log", "a pipe rides along"),
    ("git push gh +refs/heads/x:refs/heads/y", "a forced refspec"),
]


@pytest.mark.parametrize("command", AUTONOMOUS, ids=AUTONOMOUS)
def test_ordinary_feature_branch_pushes_are_autonomous(gate, command):
    assert decides(gate, command) == "auto"


@pytest.mark.parametrize("command,why", MUST_ASK, ids=[c for c, _ in MUST_ASK])
def test_dangerous_or_unrecognised_pushes_still_ask(gate, command, why):
    assert decides(gate, command) == "ask", why


def test_a_remote_name_may_not_begin_with_a_dash(gate):
    """The hole the first widening shipped with, pinned directly at the pattern.

    Asserted against the regex rather than only through `decides`, because the
    parametrised case above would still pass if the flag were rejected for some unrelated
    reason, and the property being defended is specifically that a flag cannot be read as
    a remote.
    """
    assert gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch("git push --all gh") is None
    assert gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch("git push -x gh") is None
    assert gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch("git push gh") is not None


def test_the_allow_list_is_not_vacuous(gate):
    """Guard against a future edit that makes the pattern match everything.

    Without this, a regex broadened to `.*` would pass every AUTONOMOUS case above and
    fail nothing, since those tests only assert that the allowed set is allowed.
    """
    assert gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch("rm -rf /") is None
    assert gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch("git status") is None
    assert gate.SIMPLE_CURRENT_BRANCH_PUSH.fullmatch("") is None


def test_protected_target_does_not_over_match(gate):
    """`main` must be caught as a TARGET, not anywhere in the string.

    A pattern matching `main` loosely would gate a branch merely named
    `lane-a/domain-model`, which contains the substring, and the gate would be back to
    asking about ordinary work.
    """
    assert gate.PROTECTED_TARGET.search("git push gh lane-a/domain-model") is None
    assert gate.PROTECTED_TARGET.search("git push gh lane-a/maintenance") is None
    assert gate.PROTECTED_TARGET.search("git push gh main") is not None
