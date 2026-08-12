"""Oracle for host path translation, the defect class that fired three times today.

2026-07-31, one repository, one morning, three separate tools reporting confident
falsehoods for the same reason:

  1. `tools/selfimprove/scan.py` called every bash hook missing, because Git Bash
     writes `/c/Users/...` and that is a relative path on Linux. Fixed in 24e01de by
     a `/proc/version` probe.
  2. `tools/refute/refute.py` reported 26 of 26 verifiers broken, because they
     declared `shell: "pwsh"`. Fixed in aeaecd3.
  3. `tools/audit/pointers.py` reported 12 HIGH wired-missing hooks in
     `dot-claude/settings.json`. All 12 files EXIST. Every one resolves under
     `/mnt/c`, checked by hand before this module was written.

The third is the worst of the three because it is the one that reads as rot. A
missing hook is a real and common defect, so twelve of them is a believable finding,
and `pointers scan` exits FAIL on it. Anyone acting on that report would go looking
for damage that is not there, and the genuinely dead pointers in the same output are
buried under twelve false ones.

`dot-claude/` is PAYLOAD, the committed copy of a Windows `~/.claude`. Its absolute
Windows paths are CORRECT for the host it deploys to. A checker that resolves them
against the Linux filesystem is asking the wrong question, not finding an answer.

Rule this pins: translation happens only where a Windows drive is actually mounted.
On bare Linux with no `/mnt/c`, a `C:` path is genuinely unreachable and must stay
unreachable, or the fix becomes a way to make every absent path look present.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "tools" / "lib" / "hostpaths.py"


def _load():
    spec = importlib.util.spec_from_file_location("hostpaths_under_test", MOD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


hp = _load()


class Translation(unittest.TestCase):
    """`mounts` is injected so both hosts' behaviour is testable from either host."""

    HAVE = {"c": Path("/mnt/c"), "d": Path("/mnt/d")}
    NONE: dict = {}

    def test_a_windows_drive_path_resolves_under_the_mount(self):
        self.assertEqual(
            hp.translate(r"C:\Users\shova\.claude\hooks\safety_gate.py", mounts=self.HAVE),
            Path("/mnt/c/Users/shova/.claude/hooks/safety_gate.py"))

    def test_a_windows_path_with_spaces_survives(self):
        """`C:\\Program Files\\Git\\bin\\bash.exe` is one of the twelve. A translator
        that splits on whitespace loses it and reports it absent, which is the bug
        wearing a different hat."""
        self.assertEqual(
            hp.translate(r"C:\Program Files\Git\bin\bash.exe", mounts=self.HAVE),
            Path("/mnt/c/Program Files/Git/bin/bash.exe"))

    def test_the_msys_form_resolves_to_the_same_place(self):
        """Git Bash writes `/c/Users/...` for the identical file. Both spellings are
        in the live settings.json, so both must land on one path."""
        self.assertEqual(
            hp.translate("/c/Users/shova/.claude/hooks/session-recall.sh", mounts=self.HAVE),
            Path("/mnt/c/Users/shova/.claude/hooks/session-recall.sh"))

    def test_the_drive_letter_is_case_insensitive(self):
        self.assertEqual(hp.translate(r"c:\tmp\x", mounts=self.HAVE), Path("/mnt/c/tmp/x"))
        self.assertEqual(hp.translate(r"D:/tmp/x", mounts=self.HAVE), Path("/mnt/d/tmp/x"))

    def test_an_unmounted_drive_is_left_alone(self):
        """The whole safety property. With no `/mnt/z`, `Z:\\x` is genuinely
        unreachable and must stay that way, or this becomes a machine for making
        absent paths look present."""
        got = hp.translate(r"Z:\x\y", mounts=self.HAVE)
        self.assertEqual(got, Path(r"Z:\x\y"))

    def test_no_mounts_at_all_means_no_translation(self):
        """Bare Linux, or Windows itself. Nothing may be rewritten."""
        for raw in (r"C:\Users\x", "/c/Users/x"):
            self.assertEqual(hp.translate(raw, mounts=self.NONE), Path(raw))

    def test_a_posix_path_is_never_touched(self):
        """`/home/shov/...` and `/usr/bin/env` must pass through byte-identical. The
        MSYS rule is one letter between slashes; `/home/...` is four."""
        for raw in ("/home/shov/.claude/hooks/x.sh", "/usr/bin/env", "/c", "/cc/x"):
            self.assertEqual(hp.translate(raw, mounts=self.HAVE), Path(raw))

    def test_a_relative_path_is_never_touched(self):
        self.assertEqual(hp.translate("tools/gate/gate.py", mounts=self.HAVE),
                         Path("tools/gate/gate.py"))

    def test_a_wsl_unc_path_resolves_to_the_distro_root(self):
        """PowerShell reaches WSL files as \\\\wsl.localhost\\<distro>\\path; run
        FROM that distro, the local form is /path. Appeared 2026-08-12: the live
        Notification hook wires notify-toast.ps1 by UNC and pointers.py called an
        existing file missing."""
        got = hp.translate(r"\\wsl.localhost\Ubuntu\home\u\x.ps1",
                           mounts=self.HAVE, distro="Ubuntu")
        self.assertEqual(got, Path("/home/u/x.ps1"))

    def test_the_wsl_dollar_spelling_resolves_too(self):
        got = hp.translate(r"\\wsl$\Ubuntu\home\u\x.ps1",
                           mounts=self.HAVE, distro="Ubuntu")
        self.assertEqual(got, Path("/home/u/x.ps1"))

    def test_a_unc_for_another_distro_is_left_alone(self):
        """The safety property, same as an unmounted drive: a Debian path is not
        reachable at / on Ubuntu, and pretending otherwise makes absent paths
        look present."""
        raw = r"\\wsl.localhost\Debian\home\u\x.ps1"
        self.assertEqual(hp.translate(raw, mounts=self.HAVE, distro="Ubuntu"),
                         Path(raw))

    def test_a_unc_outside_wsl_entirely_is_left_alone(self):
        raw = r"\\wsl.localhost\Ubuntu\home\u\x.ps1"
        self.assertEqual(hp.translate(raw, mounts=self.HAVE, distro=None),
                         Path(raw))

    def test_exists_uses_the_translation(self):
        """The caller-facing helper. pointers.py asks "is this file there", not
        "what would this path be", so the translation has to be inside the answer."""
        self.assertTrue(hp.exists(str(MOD), mounts=self.HAVE))
        self.assertFalse(hp.exists(r"C:\definitely\not\here.txt", mounts=self.HAVE))


class RealHost(unittest.TestCase):
    def test_the_twelve_wired_missing_hooks_resolve_on_this_host(self):
        """The regression itself, against the real filesystem. Skips where there is
        no Windows mount, because there the finding would be true."""
        if not Path("/mnt/c").is_dir():
            self.skipTest("no /mnt/c on this host; the Windows payload is genuinely unreachable")
        import json
        settings = json.loads((ROOT / "dot-claude" / "settings.json").read_text(encoding="utf-8"))
        missing = []
        for event, groups in settings.get("hooks", {}).items():
            for group in groups:
                for h in group.get("hooks", []):
                    for tok in [h.get("command", "")] + list(h.get("args", []) or []):
                        if not isinstance(tok, str):
                            continue
                        if ("\\" in tok or tok.startswith("/c/")) and not hp.exists(tok):
                            missing.append((event, tok))
        self.assertEqual(missing, [], "still unresolved after translation: %s" % missing)


if __name__ == "__main__":
    unittest.main()
