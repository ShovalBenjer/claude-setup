"""Regression for the C-003 checker, which reported REFUTED on a live hook that ran fine.

WHY THIS FILE EXISTS. On 2026-08-03 `refute.py run` reported C-003 REFUTED with

    PreToolUse: no script path found in '.../tools/hookgate/target/release/hookgate'

and the binary was on disk, executable, 2,131,576 bytes. The checker gated a hook
target on its file EXTENSION, and hookgate is compiled Rust with no extension, so a
working guard read as a dead pointer. That is L-2026-07-31-b: the gate checks the
ruled form of a rule instead of the property the rule exists to protect.

The four cases below are chosen so the file can go red in both directions. Two would
fail against the pre-fix checker (extensionless binary, POSIX path inside a command
string). Two would fail against a "fix" that simply stopped checking, which is the
tempting way to make a noisy verifier quiet and is the bug this checker's own
docstring already records once.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / "tools" / "refute" / "checks" / "hooks_exist.py"


def load_checker():
    """Import hooks_exist as a module object so SETTINGS can be repointed."""
    spec = importlib.util.spec_from_file_location("hooks_exist_under_test", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def run_against(tmp_path: Path, hooks: dict) -> int:
    """Write a settings.json containing `hooks` and return the checker's exit code."""
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": hooks}), encoding="utf-8")
    mod = load_checker()
    mod.SETTINGS = settings
    return mod.main()


def make_binary(tmp_path: Path, name: str = "hookgate") -> Path:
    """An executable file with no extension, standing in for the Rust binary."""
    p = tmp_path / name
    p.write_bytes(b"\x7fELF fake")
    p.chmod(0o755)
    return p


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX path dialect")
def test_extensionless_binary_resolves(tmp_path):
    """THE REGRESSION. A compiled hook target with no extension must pass.

    Against the pre-2026-08-03 checker this returns 1 with 'no script path found'.
    """
    binary = make_binary(tmp_path)
    rc = run_against(tmp_path, {"PreToolUse": [{"hooks": [{"command": str(binary)}]}]})
    assert rc == 0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX path dialect")
def test_absent_target_still_fails(tmp_path):
    """The property itself. Widening what counts as a target must not stop it failing."""
    rc = run_against(
        tmp_path,
        {"PreToolUse": [{"hooks": [{"command": str(tmp_path / "not-here")}]}]},
    )
    assert rc == 1


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX path dialect")
def test_interpreter_plus_script_arg_resolves_against_the_script(tmp_path):
    """`python /x/y.py` must check y.py, not the word python.

    This is the shape the live config actually uses, and getting it wrong is the
    first bug recorded in the checker's docstring.
    """
    script = tmp_path / "hook.py"
    script.write_text("print()\n", encoding="utf-8")
    rc = run_against(
        tmp_path,
        {"Stop": [{"hooks": [{"command": "python", "args": [str(script)]}]}]},
    )
    assert rc == 0

    script.unlink()
    rc = run_against(
        tmp_path,
        {"Stop": [{"hooks": [{"command": "python", "args": [str(script)]}]}]},
    )
    assert rc == 1, "an absent script arg must fail even though 'python' resolves"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX path dialect")
def test_interpreter_with_no_target_is_a_defect_not_a_pass(tmp_path):
    """A registration naming only an interpreter examines nothing, and unknown is not green.

    Guards the direction a lazy fix would take: making the checker quiet by treating
    'found no target' as success.
    """
    rc = run_against(tmp_path, {"Stop": [{"hooks": [{"command": "python"}]}]})
    assert rc == 1
