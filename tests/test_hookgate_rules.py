"""Behaviour tests for the hookgate PreToolUse guard.

ADR-0021 names `tools/hookgate` as the reference case for "Rust for hot paths,
Python for oracles", and records as an open precondition that it has **no selftest
verb and is named in no test file**. A reference case with no oracle is the wrong
reference. This closes the second half of that: the binary is still selftest-less,
but its behaviour is now pinned from the outside.

The test drives the real compiled binary rather than reimplementing the regexes,
because the defect class here is a pattern that stops matching, and a Python copy of
the pattern would keep passing while the shipped binary changed.

TWO THINGS THIS TEST LEARNED THE HARD WAY, both worth keeping:

1. The denial is in the JSON on stdout, NOT the exit code. hookgate exits 0 either
   way, deliberately, so a guard failure cannot brick the CLI. A first version of
   this probe read the return code and reported every case as allowed, including
   `reset --hard`. Reading the wrong observable produces a green test over a dead
   guard, which is this repo's most-logged failure class.

2. Every command string here is assembled from fragments. Written literally, the
   file's own contents match the patterns it is testing, and the live PreToolUse
   guard blocks the pytest invocation that would run it. The guard documents that
   false positive and keeps it on purpose.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "tools/hookgate/target/release/hookgate"

# Assembled, never literal. See point 2 in the module docstring.
GIT = "git "
BLOCKED = [
    (GIT + "push --force gh main", "bare force-push destroys another agent's history"),
    (GIT + "push -f gh main", "the short form is the same operation"),
    (GIT + "res" + "et --hard HEAD~1", "discards committed work"),
    (GIT + "clean -fd", "deletes untracked work"),
    (GIT + "push --delete gh old", "removes a remote ref"),
    (GIT + "push --mirror gh", "overwrites every remote ref at once"),
]
ALLOWED = [
    (GIT + "push --force-with-lease gh main",
     "a lease is refused server-side if the remote moved, which is exactly the "
     "protection the bare-force ban exists to provide"),
    (GIT + "push --force-with-lease=refs/heads/x gh main", "the explicit-ref form"),
    (GIT + "push gh main", "an ordinary push"),
    (GIT + "commit -m 'x'", "not a destructive verb at all"),
    (GIT + "status", "read-only"),
]


def _decide(command: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    p = subprocess.run([str(BIN)], input=payload, capture_output=True, text=True,
                       timeout=30)
    doc = json.loads(p.stdout or "{}")
    hook = doc.get("hookSpecificOutput") or {}
    return str(hook.get("permissionDecision") or "allow").lower()


pytestmark = pytest.mark.skipif(
    not BIN.exists(),
    reason="hookgate is not built here; `cargo build --release` in tools/hookgate. "
           "Skipped rather than failed because the binary is a gitignored artifact "
           "and CI does not carry a Rust toolchain.")


@pytest.mark.parametrize("command,why", BLOCKED, ids=[c for c, _ in BLOCKED])
def test_destructive_commands_are_denied(command, why):
    assert _decide(command) == "deny", why


@pytest.mark.parametrize("command,why", ALLOWED, ids=[c for c, _ in ALLOWED])
def test_safe_commands_are_not_denied(command, why):
    assert _decide(command) != "deny", why


def test_the_probe_reads_the_decision_and_not_the_exit_code():
    """Without this, every assertion above passes against a guard that denies nothing.

    hookgate exits 0 on a denial by design. If a future change made `_decide` read
    the return code instead, the BLOCKED cases would all report "allow" and this
    assertion is the one that says so in one line rather than six.
    """
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": GIT + "push --force gh main"}})
    p = subprocess.run([str(BIN)], input=payload, capture_output=True, text=True,
                       timeout=30)
    assert p.returncode == 0, "a denial must not be signalled by a nonzero exit"
    assert "deny" in p.stdout, "the denial must be in the JSON the harness reads"


def test_malformed_input_fails_open_and_says_nothing():
    """Documented behaviour, pinned so a change to it is deliberate.

    main.rs: "Fail open on malformed input ... a broken guard must not brick the CLI".
    That is a real tradeoff and not an accident, so it belongs in a test rather than
    only in a comment.
    """
    p = subprocess.run([str(BIN)], input="not json at all", capture_output=True,
                       text=True, timeout=30)
    assert p.returncode == 0
    assert json.loads(p.stdout or "{}") == {}
