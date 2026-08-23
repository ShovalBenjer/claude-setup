"""Oracle for dot-claude/hooks/ship_gate_stop.py's load_gate(): which gate.py it imports.

The same symlink hazard test_ship_gate_howto.py fixed for howto_command() (2026-07-31)
recurred here in a different function, 2026-08-24. `load_gate()` picked its gate.py
candidate without ever trying the project directory `find_contract` had already
resolved, so a worktree-isolated session fell through past the ~/claude-setup symlink
fallback and imported the MAIN CHECKOUT's gate.py. That module's setup_root() derives
from its own __file__, so it pointed at the main checkout, not the worktree: ledger_state()
then read the main checkout's state/gate-runs.jsonl instead of the worktree's own, and a
real PASS recorded in the worktree's ledger stayed invisible to the hook every turn.

Built from scratch so it does not depend on this machine's own symlink or worktree
surviving, same discipline as test_ship_gate_howto.py.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "dot-claude" / "hooks" / "ship_gate_stop.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("ship_gate_stop_under_test_load_gate", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


hook = _load(HOOK_PATH)


class LoadGateProjectFirst(unittest.TestCase):
    def test_a_worktree_with_its_own_gate_py_is_preferred_over_the_symlink_fallback(self):
        """The exact regression: a project directory (a worktree, in the real incident)
        carries its own tools/gate/gate.py. That copy must win over any fixed-path
        fallback, symlinked or not, because only that copy's setup_root() lands back
        on the project itself."""
        with tempfile.TemporaryDirectory() as td:
            worktree = Path(td) / "repo" / ".claude" / "worktrees" / "some-worktree"
            (worktree / "tools" / "gate").mkdir(parents=True)
            (worktree / "tools" / "gate" / "gate.py").write_text(
                "def setup_root():\n    import os\n"
                "    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n",
                encoding="utf-8",
            )
            # A decoy elsewhere on the fallback chain: a DIFFERENT gate.py the fix must
            # not prefer once the project's own copy is available.
            decoy = Path(td) / "decoy"
            (decoy / "tools" / "gate").mkdir(parents=True)
            (decoy / "tools" / "gate" / "gate.py").write_text(
                "def setup_root():\n    return 'DECOY'\n", encoding="utf-8",
            )

            mod, where = hook.load_gate(str(worktree))
            self.assertEqual(Path(where), worktree / "tools" / "gate" / "gate.py")
            self.assertEqual(Path(mod.setup_root()), worktree)

    def test_no_project_gate_py_falls_back_to_the_existing_chain(self):
        """A contract-bearing directory with no gate.py of its own (the case the
        original fallback chain exists for) must still resolve via CLAUDE_SETUP_ROOT
        or the fixed candidates, unchanged by this fix."""
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "bare-project"
            project.mkdir()
            setup_root = Path(td) / "setup"
            (setup_root / "tools" / "gate").mkdir(parents=True)
            (setup_root / "tools" / "gate" / "gate.py").write_text(
                "def setup_root():\n    return 'FALLBACK'\n", encoding="utf-8",
            )

            import os
            old = os.environ.get("CLAUDE_SETUP_ROOT")
            os.environ["CLAUDE_SETUP_ROOT"] = str(setup_root)
            try:
                mod, where = hook.load_gate(str(project))
            finally:
                if old is None:
                    os.environ.pop("CLAUDE_SETUP_ROOT", None)
                else:
                    os.environ["CLAUDE_SETUP_ROOT"] = old

            self.assertEqual(Path(where), setup_root / "tools" / "gate" / "gate.py")
            self.assertEqual(mod.setup_root(), "FALLBACK")

    def test_no_project_argument_still_works_backward_compatibly(self):
        """load_gate() with no argument (its old call shape) must not raise."""
        mod, where = hook.load_gate()
        self.assertIsNotNone(mod)
        self.assertTrue(where)


if __name__ == "__main__":
    unittest.main()
