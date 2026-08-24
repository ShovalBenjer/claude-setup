"""One launcher per charter lane, with the lane declared instead of inferred.

THE DEFECT THIS FIXES

`Claude new-recruit (Admin).lnk` runs:

    wt.exe -d "C:\\Users\\shova\\Downloads\\new-recruit" pwsh -NoExit -Command claude

`-d` pins the working directory to Lane C's repo. docs/charters.md assigns a lane
per working directory, so every session opened from the desktop reports Lane C no
matter what it is actually doing. On 2026-07-27 a session whose opening prompt was
pure Lane B work (terminal spawn, rc, harness settings) spent hours editing
claude-setup while its cwd said C. That is a launcher producing a wrong answer,
not an operator forgetting a rule.

THE FIX

A lane is DECLARED, not inferred. Each shortcut exports CLAUDE_LANE before
starting claude, so a SessionStart hook can read the lane directly rather than
guessing from a path a shortcut chose. cwd still matches the lane's repo, so
nothing that reads cwd breaks.

    python make_lane_launchers.py            # show the plan
    python make_lane_launchers.py --apply    # write the shortcuts
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# TWO PATH FORMS, NEVER ONE
#
# A shortcut is a Windows object: its target, arguments and working directory are
# read by Explorer and wt.exe, so they must be `C:\...`. Whether a lane's repo
# exists is a question THIS process answers with a stat, so under WSL it must be
# asked about `/mnt/c/...`. The original version used `pathlib.Path.home()` for
# both, which is correct on Windows and silently wrong from WSL: every lane
# resolved to `/home/shov/...`, every row printed MISSING DIR, and `--apply`
# wrote nothing while still exiting 0. tests/test_lane_launcher_paths.py holds
# the two forms apart.

def detect_wsl(os_name: str, proc_version: str | None) -> bool:
    """WSL is a Linux kernel that says microsoft. Bare Linux has no C: to reach."""
    if os_name == "nt":
        return False
    return bool(proc_version) and "microsoft" in proc_version.lower()


def _read_proc_version() -> str | None:
    try:
        return pathlib.Path("/proc/version").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


WSL = detect_wsl(os.name, _read_proc_version())


def win_to_local(win_path: str, wsl: bool) -> str:
    """`C:\\Users\\x` -> `/mnt/c/Users/x` under WSL, identity otherwise.

    Anything that is not a drive-letter path (UNC, `\\\\wsl$\\...`) is returned
    unchanged rather than guessed at, so a wrong translation cannot masquerade
    as a resolved path.
    """
    if not wsl:
        return win_path
    if len(win_path) >= 2 and win_path[1] == ":" and win_path[0].isalpha():
        return "/mnt/" + win_path[0].lower() + win_path[2:].replace("\\", "/")
    return win_path


def _powershell(expr: str) -> str | None:
    """Ask Windows itself for a known folder. Desktop can be redirected into
    OneDrive, so deriving it as home/Desktop is a guess that has already been
    wrong on this machine class."""
    try:
        p = subprocess.run(["powershell.exe", "-NoProfile", "-Command", expr],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    out = (p.stdout or "").strip()
    return out or None


def windows_folders() -> tuple[str, str]:
    """(user profile, desktop) in Windows form."""
    if not WSL:
        home = str(pathlib.Path.home())
        return home, str(pathlib.Path.home() / "Desktop")
    home = _powershell("[Environment]::GetFolderPath('UserProfile')")
    desk = _powershell("[Environment]::GetFolderPath('Desktop')")
    if not home:
        raise SystemExit(
            "cannot reach powershell.exe from this WSL distro, so the Windows "
            "user profile is unknown and no shortcut can be written. Run this "
            "from a Windows shell, or fix interop (/proc/sys/fs/binfmt_misc/WSLInterop)."
        )
    return home, (desk or home + "\\Desktop")


# (lane, label, path segments below the user profile, one-line charter scope)
LANES = [
    ("A", "Claude A - harness", ("claude-setup",),
     "rules, hooks, skills, schedulers, review fabric, a2a bridges, autonomy rails"),
    ("B", "Claude B - resume engine", ("Downloads", "new-recruit"),
     "hiring machine, arms, applications, job scans"),
    ("C", "Claude C - learning", ("Downloads", "daily-deep-learning"),
     "the PWA, learning cards, study loops"),
    ("D", "Claude D - content", ("Downloads", "daily-deep-learning"),
     "case ledgers, syndication; posting decisions stay with the operator"),
]
# Renumbered 2026-07-30 from B/C/D/E to A/B/C/D (operator decision). The old Lane A
# was the concierge lane, retired 2026-07-29 having never been used once, and its
# intake/routing scope folded into the harness lane. That left the live set starting
# at B with a hole at the front, so the letters were shifted down to close it. No
# charter's scope changed in the renumber. tools/lib/lanes.py owns the scheme and is
# the only correct way to read a lane letter out of a pre-cutover ledger row, because
# the letters collide across the boundary. The desktop .lnk files are REGENERATED
# from this list, so the labels above are what the operator will actually see, and a
# stale shortcut naming an old letter is the drift this comment exists to flag.


def plan(win_home: str, win_desktop: str, wsl: bool, exists=None) -> list[dict]:
    """One row per lane, carrying both path forms.

    `exists` is injected so the tests can drive the branch without a matching
    filesystem; it is always asked about the LOCAL form, never the Windows one.
    """
    if exists is None:
        def exists(p: str) -> bool:
            return os.path.isdir(p)

    rows = []
    for lane, label, segments, scope in LANES:
        cwd_win = "\\".join((win_home.rstrip("\\"),) + segments)
        cwd_local = win_to_local(cwd_win, wsl)
        # -NoExit keeps the shell after claude exits, matching the current shortcut.
        # $env:CLAUDE_LANE is set inside the pwsh command so it reaches the claude
        # process and any hook it spawns.
        cmd = "$env:CLAUDE_LANE='{}'; claude".format(lane)
        rows.append({
            "lane": lane,
            "label": label,
            "cwd_win": cwd_win,
            "cwd_local": cwd_local,
            "exists": bool(exists(cwd_local)),
            "args": '-d "{}" pwsh -NoExit -Command "{}"'.format(cwd_win, cmd),
            "lnk": win_desktop.rstrip("\\") + "\\" + label + ".lnk",
            "scope": scope,
        })
    return rows


PS_TEMPLATE = """
$ErrorActionPreference = 'Stop'
$sh = New-Object -ComObject WScript.Shell
$l = $sh.CreateShortcut({lnk})
$l.TargetPath = {target}
$l.Arguments = {args}
$l.WorkingDirectory = {cwd}
$l.Description = {desc}
$l.Save()
Write-Output ('wrote ' + {lnk})
"""


def ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    win_home, win_desktop = windows_folders()
    rows = plan(win_home, win_desktop, WSL)

    wt_win = "\\".join((win_home.rstrip("\\"), "AppData", "Local",
                        "Microsoft", "WindowsApps", "wt.exe"))
    wt_local = win_to_local(wt_win, WSL)
    desktop_local = win_to_local(win_desktop, WSL)

    print(f"host             : {'WSL (interop to Windows)' if WSL else 'Windows'}")
    print(f"windows terminal : {wt_win}  exists={os.path.isfile(wt_local)}")
    print(f"desktop          : {win_desktop}  exists={os.path.isdir(desktop_local)}\n")
    for r in rows:
        mark = " " if r["exists"] else "  MISSING DIR"
        print(f"  [{r['lane']}] {r['label']}{mark}")
        print(f"        cwd  {r['cwd_win']}")
        if WSL:
            print(f"        seen {r['cwd_local']}")
        print(f"        args {r['args']}")
        print(f"        {r['scope']}")
    print("\nThe existing 'Claude new-recruit (Admin).lnk' is left in place. Delete it "
          "by hand once a lane launcher has replaced it in your habits.")

    if not args.apply:
        print("\nPLAN ONLY. Re-run with --apply to write the shortcuts.")
        return 0

    if not os.path.isfile(wt_local):
        print(f"\nwt.exe not found at {wt_win}; nothing written.")
        return 1

    written = 0
    rc = 0
    for r in rows:
        if not r["exists"]:
            print(f"  skipped {r['lane']}: {r['cwd_win']} does not exist")
            continue
        script = PS_TEMPLATE.format(
            lnk=ps_quote(r["lnk"]), target=ps_quote(wt_win),
            args=ps_quote(r["args"]), cwd=ps_quote(r["cwd_win"]),
            desc=ps_quote("Lane {}: {}".format(r["lane"], r["scope"])))
        p = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if p.returncode == 0:
            written += 1
            print(f"  ok   lane {r['lane']}: {r['lnk'].rsplit(chr(92), 1)[-1]}")
        else:
            rc = 1
            print(f"  FAIL lane {r['lane']}: {(p.stderr or '').strip()[:200]}")

    if written == 0:
        # The WSL defect's real damage was here: every lane skipped, exit 0, and
        # an operator reading a clean run concluded the launchers were current.
        print("\nno shortcut was written. Every lane directory was missing, which "
              "means the paths above are wrong for this host, not that the work "
              "is done.")
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
