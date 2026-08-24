"""Oracle for the refutation layer's portability across the two hosts this repo runs on.

Measured 2026-07-31 on WSL, `python tools/refute/refute.py run`:

    26 claims: 0 held, 0 REFUTED, 26 broken verifier

Every one failed with `could not launch pwsh: [Errno 2] No such file or directory:
'powershell'`. Single cause, whole layer. The tool was honest about it (its own
message says a broken verifier is not a pass and the claim stays unknown, and the
run exits nonzero) so nothing was being falsely certified. What was lost is the
layer itself: on the host the operator now works from, no claim in this repository
had a working falsifier, which is the exact failure mode `refute` exists to catch,
turned on the checker.

The content was never Windows-specific. 19 of the 26 were already
`python tools\\refute\\checks\\<name>.py` and needed only a shell that exists and a
path separator that resolves. The other 7 used PowerShell built-ins for things
Python does on both platforms.

These tests pin the property, not the fix: every registered claim must be launchable
on whatever host is running the suite. A verifier that cannot start proves nothing,
and a proof layer that only works on one of two machines is not a proof layer.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFUTE = ROOT / "engine" / "tools" / "refute" / "refute.py"
LEDGER = ROOT / "knowledge" / "state" / "claims-verify.jsonl"


def _load():
    spec = importlib.util.spec_from_file_location("refute_under_test", REFUTE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


refute = _load()


def _claims():
    return [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]


class EveryClaimIsLaunchableHere(unittest.TestCase):
    def test_no_claim_declares_a_shell_this_host_does_not_have(self):
        """The regression itself. `pwsh` is a legitimate declaration on Windows and a
        dead one under WSL, so the ledger may not hard-code an interpreter that only
        one of the two hosts has."""
        from shutil import which
        missing = []
        for c in _claims():
            shell = (c.get("shell") or "portable").lower()
            if shell in ("pwsh", "powershell", "ps") and not (which("pwsh") or which("powershell")):
                missing.append(c["id"])
            if shell == "bash" and not which("bash"):
                missing.append(c["id"])
        self.assertEqual(missing, [], "claims that cannot launch on this host: %s" % missing)

    def test_no_verify_command_uses_a_backslash_path(self):
        """`python tools\\refute\\checks\\x.py` is not a path on Linux, it is a string
        with escapes in it. Forward slashes resolve on BOTH hosts, so there was never
        a reason for the backslash form."""
        bad = [c["id"] for c in _claims() if "\\" in c.get("verify", "")]
        self.assertEqual(bad, [], "claims with backslash paths: %s" % bad)

    def test_no_verify_command_hardcodes_a_windows_home(self):
        """`$env:USERPROFILE` and `%USERPROFILE%` name the Windows profile, and the WSL
        clone is not under it. A verifier runs with cwd=ROOT, so relative paths are
        both shorter and correct."""
        bad = [c["id"] for c in _claims()
               if "USERPROFILE" in c.get("verify", "") or "HOMEPATH" in c.get("verify", "")]
        self.assertEqual(bad, [], "claims pinned to a Windows home: %s" % bad)

    def test_the_portable_shell_is_understood_by_the_runner(self):
        """A ledger value the runner rejects would turn every migrated row into a
        different flavour of broken verifier, which is the same outage wearing a new
        message."""
        verdict, rc, out = refute.run_verifier(
            {"id": "T", "verify": "python -c \"import sys; sys.exit(0)\"", "shell": "portable"})
        self.assertEqual(verdict, refute.HELD, out)

    def test_an_unknown_shell_is_still_broken_and_not_silently_run(self):
        """The fix must not become 'run everything under the default shell'. A typo in
        the shell field has to stay loud."""
        verdict, rc, out = refute.run_verifier(
            {"id": "T", "verify": "exit 0", "shell": "nonesuch"})
        self.assertEqual(verdict, refute.BROKEN, out)

    def test_a_portable_failure_is_refuted_not_broken(self):
        """A verifier that runs and says no is a REFUTATION, which is the signal. Only
        a verifier that cannot run is broken. Collapsing the two would hide real
        refutations behind an infrastructure message."""
        verdict, rc, out = refute.run_verifier(
            {"id": "T", "verify": "python -c \"import sys; sys.exit(3)\"", "shell": "portable"})
        self.assertEqual(verdict, refute.REFUTED, out)

    def test_no_verify_command_uses_powershell_syntax(self):
        """The nastiest failure this fix can cause, and it did cause it once.

        C-017 kept `if (Get-Command codex -ErrorAction SilentlyContinue) {...}` after
        migration. Under /bin/sh that is not a portability error the runner can
        detect: sh parses it, chokes on the brace, and exits nonzero, which
        `run_verifier` correctly reads as the claim being REFUTED. So an
        infrastructure fault arrived wearing the costume of a finding, in the one
        tool whose whole job is telling those apart. A broken verifier at least says
        it is broken.

        The migration therefore has to be checked at the SOURCE, not at the exit code.
        """
        import re
        ps = re.compile(
            r"\$env:|\$LASTEXITCODE|\*>\s*\$null|"
            r"\b(?:Get|Set|New|Test|Select|Measure|Write|Start|ForEach)-[A-Z][A-Za-z]+\b|"
            r"-ErrorAction\b|-NoProfile\b")
        bad = [(c["id"], ps.search(c.get("verify", "")).group(0))
               for c in _claims() if ps.search(c.get("verify", ""))]
        self.assertEqual(bad, [], "claims still written in PowerShell: %s" % bad)

    def test_every_check_script_the_ledger_names_exists(self):
        """A ledger row pointing at a missing script is a broken verifier that looks
        like a configured one."""
        missing = []
        for c in _claims():
            for tok in c.get("verify", "").split():
                if tok.endswith(".py") and tok.startswith("engine/tools/"):
                    if not (ROOT / tok).is_file():
                        missing.append((c["id"], tok))
        self.assertEqual(missing, [], "claims naming an absent check script: %s" % missing)


if __name__ == "__main__":
    unittest.main()
