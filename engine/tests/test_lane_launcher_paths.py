"""Oracle for the WSL half of tools/workspace/make_lane_launchers.py.

THE DEFECT

The generator was written when every session started from a Windows shell, so it
read `pathlib.Path.home()` for both jobs it has to do:

  - decide whether a lane's repo EXISTS, which needs a path this process can stat
  - write that repo into a `.lnk`, which needs a path Explorer and wt.exe can open

On Windows those two are the same string and the conflation is invisible. Run the
same script from WSL and `Path.home()` is `/home/shov`, so every lane resolves to
a directory that does not exist, every row prints MISSING DIR, and `--apply`
writes nothing while exiting 0 on the plan path. A generator that silently
produces an empty plan is worse than one that crashes: the operator sees a clean
run and concludes the launchers are current.

WHAT THESE CHECKS PIN

  - The two path forms stay separate. A Windows form reaching `is_dir()`, or a
    `/mnt/c` form reaching a shortcut argument, is the original conflation back.
  - Detection is by `/proc/version`, not by `os.name`, because a Linux `os.name`
    is also what a real Linux box reports and that box has no `C:` to translate.
  - The drive-letter translation is exact, including the backslash direction,
    since `wt.exe -d /mnt/c/...` fails in a way that only shows up at click time.

These are unit checks on pure functions with the converter injected, so they run
identically on Windows, WSL, and CI Linux. What they do NOT cover: whether
`powershell.exe` is reachable from this WSL distro, which is an integration fact
and is asserted at runtime by the script itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "workspace"))
import make_lane_launchers as mll  # noqa: E402


WSL_PROC = "Linux version 6.6.87.1-microsoft-standard-WSL2 (root@build) #1 SMP"
BARE_LINUX_PROC = "Linux version 6.8.0-45-generic (buildd@lcy02) #45-Ubuntu SMP"


class TestDetectWsl:
    def test_microsoft_kernel_is_wsl(self):
        assert mll.detect_wsl("posix", WSL_PROC) is True

    def test_bare_linux_is_not_wsl(self):
        assert mll.detect_wsl("posix", BARE_LINUX_PROC) is False

    def test_windows_is_never_wsl_whatever_proc_says(self):
        assert mll.detect_wsl("nt", WSL_PROC) is False

    def test_absent_proc_version_is_not_wsl(self):
        assert mll.detect_wsl("posix", None) is False


class TestWinToLocal:
    def test_translates_drive_letter_and_slashes(self):
        assert mll.win_to_local(r"C:\Users\shova\claude-setup", wsl=True) == \
            "/mnt/c/Users/shova/claude-setup"

    def test_lowercases_the_drive_letter(self):
        assert mll.win_to_local(r"D:\repos\x", wsl=True) == "/mnt/d/repos/x"

    def test_is_identity_when_not_under_wsl(self):
        win = r"C:\Users\shova\claude-setup"
        assert mll.win_to_local(win, wsl=False) == win

    def test_unc_and_other_shapes_pass_through_rather_than_guessing(self):
        unc = r"\\wsl$\Ubuntu\home\shov"
        assert mll.win_to_local(unc, wsl=True) == unc


class TestPlanKeepsTheFormsApart:
    """The whole point: one row carries both paths, each used for one job."""

    def _rows(self, wsl: bool):
        return mll.plan(win_home=r"C:\Users\shova",
                        win_desktop=r"C:\Users\shova\Desktop",
                        wsl=wsl,
                        exists=lambda p: True)

    def test_shortcut_fields_are_windows_form_under_wsl(self):
        for r in self._rows(wsl=True):
            assert r["cwd_win"].startswith("C:\\"), r
            assert "/mnt/" not in r["args"], r
            assert "/mnt/" not in r["lnk"], r

    def test_existence_check_uses_the_local_form_under_wsl(self):
        for r in self._rows(wsl=True):
            assert r["cwd_local"].startswith("/mnt/c/"), r

    def test_the_two_forms_collapse_on_windows(self):
        for r in self._rows(wsl=False):
            assert r["cwd_local"] == r["cwd_win"], r

    def test_existence_is_asked_about_the_local_path_only(self):
        asked: list[str] = []

        def spy(p: str) -> bool:
            asked.append(p)
            return True

        mll.plan(win_home=r"C:\Users\shova",
                 win_desktop=r"C:\Users\shova\Desktop",
                 wsl=True, exists=spy)
        assert asked, "plan() never checked existence at all"
        assert all(p.startswith("/mnt/c/") for p in asked), asked

    def test_lanes_do_not_collapse_to_one_directory(self):
        """Inherited from test_workspace_launcher.py: a menu whose entries all
        point at one repo is the hardcoded shortcut wearing a costume."""
        rows = self._rows(wsl=True)
        assert len({r["cwd_win"] for r in rows}) > 1

    def test_every_row_declares_its_lane_in_the_command(self):
        for r in self._rows(wsl=True):
            assert "CLAUDE_LANE='{}'".format(r["lane"]) in r["args"], r


class TestExistenceIsNotAssumed:
    def test_missing_directory_is_reported_not_silently_dropped(self):
        rows = mll.plan(win_home=r"C:\Users\shova",
                        win_desktop=r"C:\Users\shova\Desktop",
                        wsl=True, exists=lambda p: False)
        assert rows, "a missing directory must still appear in the plan"
        assert all(r["exists"] is False for r in rows)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
