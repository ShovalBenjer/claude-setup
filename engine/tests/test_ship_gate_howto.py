"""Oracle for the command dot-claude/hooks/ship_gate_stop.py tells a session to run.

The hook's whole output when a gate is red is one instruction. If that instruction is
wrong, the block is worse than useless: it stops the turn AND sends the session down a
path that does not work, which costs a round trip to discover.

Measured 2026-07-31 on this machine. `~/claude-setup` is a symlink to
`~/work/repos/claude-setup`, so the gate resolves through the symlink while the project
is the real path, and os.path.relpath compares the two as unrelated strings:

    setup_root : /home/shov/claude-setup
    project    : /home/shov/work/repos/claude-setup
    printed    : python ../../../claude-setup/tools/gate/gate.py run --project .
    correct    : python tools/gate/gate.py run --project .

Both spellings happen to reach the same file here, so this was invisible for as long as
nobody looked at it. It stops being harmless the moment the symlink is somewhere the
climb does not survive, and the operator quoted the ugly form back as the thing he was
being told to run. A hook that instructs is judged on the instruction.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = ROOT / "payload" / "dot-claude" / "hooks" / "ship_gate_stop.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("ship_gate_stop_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


hook = _load(HOOK_PATH)


class HowtoPath(unittest.TestCase):
    def test_a_symlinked_setup_root_does_not_produce_a_climbing_path(self):
        """The exact regression, built from scratch so it does not depend on this
        machine's own symlink surviving."""
        with tempfile.TemporaryDirectory() as td:
            real = Path(td) / "work" / "repos" / "claude-setup"
            (real / "engine" / "tools" / "gate").mkdir(parents=True)
            (real / "engine" / "tools" / "gate" / "gate.py").write_text("", encoding="utf-8")
            link = Path(td) / "claude-setup"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this host")

            got = hook.howto_command(str(link), str(real))
            self.assertEqual(got, "python engine/tools/gate/gate.py run --project .")
            self.assertNotIn("..", got)

    def test_a_genuinely_separate_setup_root_still_gets_a_relative_path(self):
        """The fix must not collapse every path to the project-local spelling: a gate
        that really does live elsewhere still has to be reachable."""
        with tempfile.TemporaryDirectory() as td:
            setup = Path(td) / "setup"
            (setup / "engine" / "tools" / "gate").mkdir(parents=True)
            (setup / "engine" / "tools" / "gate" / "gate.py").write_text("", encoding="utf-8")
            project = Path(td) / "someproject"
            project.mkdir()

            got = hook.howto_command(str(setup), str(project))
            self.assertEqual(got, "python ../setup/engine/tools/gate/gate.py run --project .")

    def test_the_separator_is_always_a_forward_slash(self):
        """The string is pasted into a shell, and the hook already normalised this on
        Windows. Keep that property through the fix."""
        with tempfile.TemporaryDirectory() as td:
            setup = Path(td) / "setup"
            (setup / "engine" / "tools" / "gate").mkdir(parents=True)
            (setup / "engine" / "tools" / "gate" / "gate.py").write_text("", encoding="utf-8")
            project = Path(td) / "p"
            project.mkdir()
            self.assertNotIn("\\", hook.howto_command(str(setup), str(project)))


if __name__ == "__main__":
    unittest.main()
