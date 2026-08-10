"""The half of prompt capture that holds the actual words has to survive a bare interpreter.

`capture_turn.py` writes two records. The first, a hashed row in
`state/prompt-tickets.jsonl`, needs nothing but the standard library and has never
stopped working: 494 rows. The second writes the VERBATIM prompt into `~/.intent`, and
it stopped on the WSL move without anyone noticing for ten days.

The reason it was invisible is the design working as intended. `main()` wraps `enrich()`
in a bare except so a broken enrichment can never block the operator's prompt, which is
correct: a hook that raises on every turn is worse than a hook that records less. But a
swallowed failure reports nothing, and the live `settings.json` runs this hook under
plain `python3`, an interpreter with no venv and no `intent_control_plane` on its path.
So every prompt since 2026-07-31 wrote its hash and dropped its text.

Measured 2026-08-10: `/mnt/c/Users/shova/.intent/intent.db` holds 235 events with
verbatim text, last written 2026-07-31T04:15:07Z. `~/.intent` on this machine did not
exist at all.

These tests run the module the way the hook runs it, with the SYSTEM interpreter and a
scrubbed environment, because the defect was environmental and a test importing the
module inside the developer's own session would have passed throughout the outage. That
is the whole lesson: the check has to reproduce the caller, not the author.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "tools" / "intent" / "capture_turn.py"
SRC = ROOT / "intent-control-plane" / "src"

#: The interpreter the live hook actually uses. Not sys.executable, which in a test run
#: is whatever venv pytest was launched from and would hide the bug being guarded.
SYSTEM_PYTHON = "/usr/bin/python3"


def bare_env(home: Path) -> dict[str, str]:
    """The hook's environment, minus anything that would smuggle the package in."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    env["HOME"] = str(home)
    return env


def run_hook(home: Path, text: str) -> subprocess.CompletedProcess:
    payload = {"prompt": text, "cwd": str(ROOT), "session_id": "test-session"}
    return subprocess.run(
        [SYSTEM_PYTHON, str(HOOK)],
        input=json.dumps(payload), capture_output=True, text=True,
        env=bare_env(home), cwd=str(ROOT), timeout=60)


needs_system_python = pytest.mark.skipif(
    not Path(SYSTEM_PYTHON).exists(),
    reason="no {} on this host; the hook's interpreter cannot be reproduced".format(
        SYSTEM_PYTHON))


@needs_system_python
def test_the_package_is_importable_without_a_venv_once_the_module_has_run():
    """The direct oracle for the outage.

    Before the fix this raised ModuleNotFoundError, and `main()` swallowed it. Asserting
    on the import rather than on the hook's exit code matters, because the hook exits 0
    either way by design.
    """
    probe = ("import sys; sys.argv=['x']; "
             "sys.path.insert(0, {!r}); "
             "import intent_control_plane.cli, intent_control_plane.schema; "
             "print('ok')".format(str(SRC)))
    r = subprocess.run([SYSTEM_PYTHON, "-c", probe], capture_output=True, text=True,
                       env=bare_env(Path.home()), timeout=60)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


@needs_system_python
def test_the_hook_writes_the_verbatim_text_under_a_bare_interpreter(tmp_path):
    """End to end, the way the outage would have been caught.

    A hashed row proves nothing here: that half never broke. The assertion is that the
    typed words reach the store.
    """
    home = tmp_path / "home"
    home.mkdir()
    typed = "a sentence that exists only in this test, 8f31c2"

    r = run_hook(home, typed)
    assert r.returncode == 0, r.stderr

    db = home / ".intent" / "intent.db"
    assert db.is_file(), (
        "no store at {}. stderr was: {!r}".format(db, r.stderr[-500:]))

    con = sqlite3.connect(str(db))
    try:
        rows = con.execute("SELECT COUNT(*) FROM events WHERE model_text LIKE ?",
                           ("%8f31c2%",)).fetchone()
    finally:
        con.close()
    assert rows[0] == 1, "the verbatim text did not reach the events table"


@needs_system_python
def test_the_hook_stays_silent_and_exits_zero(tmp_path):
    """Two properties the docstring calls load-bearing, guarded so a fix cannot cost them.

    Anything printed on exit 0 from UserPromptSubmit is injected into the session's
    context, so a chatty hook taxes every turn. And a non-zero exit blocks the prompt.
    """
    home = tmp_path / "home"
    home.mkdir()
    r = run_hook(home, "silence check")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


@needs_system_python
def test_a_broken_enrichment_still_exits_zero(tmp_path, monkeypatch):
    """The swallow is deliberate and must survive the fix.

    Making the store unwritable is the cheapest real failure: the durable hashed row is
    already written by then, and the operator's prompt must not be blocked by the half
    that could not run.
    """
    home = tmp_path / "home"
    home.mkdir()
    (home / ".intent").write_text("not a directory", encoding="utf-8")

    r = run_hook(home, "enrichment cannot possibly work here")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""
