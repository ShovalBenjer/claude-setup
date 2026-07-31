"""Oracle for the interpreter name the gate shells out to.

THE DEFECT, MEASURED 2026-07-31 ON THIS WSL DISTRO

`quality-contract.json` spells every domain command with a bare `python`:

    unit    python -m pytest tests/ -q && python tools/gate/gate.py selftest && ...
    types   python -m compileall -q . && cd intent-control-plane && uv run ruff ...
    docmap  python tools/docmap/docmap.py check

Ubuntu ships `python3` and no `python`. The first run of the gate from WSL:

    docmap FAIL   exit 127 from `python tools/docmap/docmap.py check`
                      /bin/sh: 1: python: not found
    VERDICT: FAIL   blocking: unit FAIL, types FAIL, docmap FAIL

Three blocking domains, no failing test behind any of them, and a FAIL row
appended to state/gate-runs.jsonl against commit 3f23458. That row is the real
damage: the ledger is the artifact other tools read to decide whether this commit
is shippable, and it now carries a verdict that describes the host rather than
the code. The root suite passed 367 tests on the same tree, in the same minute.

WHY THE FIX IS A SHIM AND NOT A CONTRACT EDIT

`python` in the contract is the INTENT: run this with the interpreter the gate is
running under. Rewriting the JSON to `python3` moves the breakage to Windows,
where `python3` is a Store stub that opens a web page and exits 9009. Rewriting it
to `sys.executable` at string level breaks the `pipeline` domain, which greps the
workflow files for a literal `gate.py run`. So the interpreter is supplied on
PATH, where a shell already looks for it, and the contract text stays honest.

WHAT THIS PINS

  - A bare `python` command resolves, and resolves to the interpreter running the
    gate rather than to some other one on PATH.
  - An existing real `python` is never shadowed. On Windows the shim must not
    exist at all, or the gate would silently switch interpreters mid-migration.
  - The shim is only ever prepended for the subprocess, not exported into the
    parent environment.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "gate"))
import gate  # noqa: E402


class TestShimCreation:
    @pytest.mark.skipif(os.name == "nt", reason="posix shim; Windows has python")
    def test_absent_python_gets_a_shim(self, tmp_path):
        d = gate.python_shim_dir(which=lambda name: None, tmpdir=tmp_path)
        assert d is not None
        assert (Path(d) / gate.PYTHON_SHIM_NAME).exists()

    def test_present_python_gets_no_shim(self, tmp_path):
        d = gate.python_shim_dir(which=lambda name: "/usr/bin/python",
                                 tmpdir=tmp_path)
        assert d is None, "a real python on PATH must never be shadowed"

    def test_the_shim_is_executable(self, tmp_path):
        if os.name == "nt":
            pytest.skip("the executable bit is a posix concept")
        d = gate.python_shim_dir(which=lambda name: None, tmpdir=tmp_path)
        assert os.access(Path(d) / gate.PYTHON_SHIM_NAME, os.X_OK)


class TestTheShimActuallyRuns:
    """Not a mock: the shim is invoked through a real shell, as the gate does."""

    @pytest.mark.skipif(os.name == "nt", reason="posix shim; Windows has python")
    def test_shim_dispatches_to_this_interpreter(self, tmp_path):
        d = gate.python_shim_dir(which=lambda name: None, tmpdir=tmp_path)
        env = dict(os.environ, PATH=str(d) + os.pathsep + os.environ["PATH"])
        p = subprocess.run("python -c \"import sys; print(sys.executable)\"",
                           shell=True, capture_output=True, text=True, env=env,
                           timeout=60)
        assert p.returncode == 0, p.stderr
        assert p.stdout.strip() == sys.executable

    def test_shim_forwards_a_nonzero_exit(self, tmp_path):
        if os.name == "nt":
            pytest.skip("posix shim")
        d = gate.python_shim_dir(which=lambda name: None, tmpdir=tmp_path)
        env = dict(os.environ, PATH=str(d) + os.pathsep + os.environ["PATH"])
        p = subprocess.run("python -c \"import sys; sys.exit(3)\"", shell=True,
                           capture_output=True, text=True, env=env, timeout=60)
        assert p.returncode == 3, "a shim that swallows exit codes is worse than none"


class TestGateRunUsesIt:
    """The end of the chain: gate.run() is what every domain goes through."""

    def test_a_bare_python_command_succeeds(self, tmp_path):
        rc, out = gate.run("python -c \"print('shimmed')\"", str(tmp_path))
        assert rc == 0, out
        assert "shimmed" in out

    def test_the_parent_environment_is_not_mutated(self, tmp_path):
        before = os.environ.get("PATH")
        gate.run("python -c \"pass\"", str(tmp_path))
        assert os.environ.get("PATH") == before


class TestTheVirtualenvIsPerPlatform:
    """Second host-shaped collision in the same three domain commands.

    `intent-control-plane/.venv` was built by Windows uv: it holds `Lib/`,
    `Scripts/` and a pyvenv.cfg naming `C:\\Users\\shova\\...\\Python313`. From
    WSL, `uv sync --frozen` tries to replace it and dies on the DrvFs mount:

        error: failed to remove directory `.../.venv/Lib`: Directory not empty
               (os error 39)

    which is the `build` domain's entire failure, and it cascades into `unit` and
    `types` because both chain `uv run` after it. Deleting the venv would fix this
    run and break the operator's next Windows session, so the two hosts get two
    directories instead. Same reasoning as the python shim: the difference is
    supplied through the environment, not written into the contract.
    """

    def test_posix_gets_a_distinct_project_environment(self):
        """Same return-shape trap as the override test below, with a nastier trigger.

        This one only fires when the GATE runs the suite, which is the one context
        that matters and the one a bare `pytest tests/` never reproduces. The gate
        sets UV_PROJECT_ENVIRONMENT for the unit domain, pytest inherits it, and the
        nested `_domain_env()` call then sees the variable already present, adds no
        overlay entry for it, finds `python` already on PATH, and returns None for an
        empty overlay. Measured 2026-07-31: four legs of the unit domain green run
        one at a time, red under `gate.py run`, with .venv-linux correctly in force
        the whole time. Assert the effective value, which is the thing uv reads.
        """
        if os.name == "nt":
            pytest.skip("Windows keeps the default .venv")
        env = gate._domain_env()
        effective = (os.environ if env is None else env).get("UV_PROJECT_ENVIRONMENT")
        assert effective == gate.POSIX_VENV_NAME
        assert gate.POSIX_VENV_NAME != ".venv", (
            "sharing one directory is what collided in the first place")

    def test_an_operator_override_is_not_clobbered(self, monkeypatch):
        """The contract is the value a domain ends up running under, not the shape
        of the return.

        `_domain_env()` returns None to mean "inherit os.environ unchanged", which
        preserves the override perfectly, so asserting `env.get(...)` on the return
        only worked while something ELSE forced a non-empty overlay. On a host that
        already provides `python`, python_shim_dir() correctly returns None, the
        override suppresses the venv entry, the overlay is empty, and the old
        assertion died with AttributeError on None. Measured 2026-07-31 on WSL after
        tools/wsl/bootstrap.sh supplied `python`: green before the shim existed, red
        after, with the production code correct throughout. Resolve the effective
        value instead, which is what the domain actually sees.
        """
        if os.name == "nt":
            pytest.skip("posix-only injection")
        monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "/tmp/my-own-venv")
        env = gate._domain_env()
        effective = (os.environ if env is None else env).get("UV_PROJECT_ENVIRONMENT")
        assert effective == "/tmp/my-own-venv"

    def test_the_posix_venv_is_gitignored(self):
        """Asked of git, not of a .gitignore file: the rule that matters lives in
        intent-control-plane/.gitignore, and reading only the root one would pass
        this test by looking in the wrong place."""
        target = "intent-control-plane/" + gate.POSIX_VENV_NAME + "/x"
        p = subprocess.run(["git", "check-ignore", "-q", target],
                           cwd=ROOT, capture_output=True)
        assert p.returncode == 0, (
            f"{target} is not ignored; an unignored venv shows up as thousands of "
            "?? rows and hides real drift in git status")


class TestTheContractStillReadsAsPython:
    def test_domains_are_not_rewritten_to_python3(self):
        """If a later session 'fixes' this by editing the JSON, the Windows host
        breaks instead and this test says so at the point of the edit."""
        import json
        contract = json.loads((ROOT / "quality-contract.json").read_text(
            encoding="utf-8"))
        cmds = [d.get("cmd") or "" for d in contract["domains"].values()]
        assert any("python " in c for c in cmds)
        assert not any("python3 " in c for c in cmds), (
            "python3 is a Store stub on Windows that exits 9009; the interpreter "
            "belongs on PATH, not in the contract text")


@pytest.mark.skipif(shutil.which("python") is not None,
                    reason="this host has a real python; nothing to regress")
class TestTheOriginalFailure:
    def test_docmap_command_runs_on_a_host_without_python(self):
        """The literal command that returned 127 and blocked the gate."""
        rc, out = gate.run("python tools/docmap/docmap.py check", str(ROOT))
        assert "python: not found" not in out, out
        assert rc != 127, out


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
