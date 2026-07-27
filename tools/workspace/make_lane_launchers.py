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

HOME = pathlib.Path.home()
DESKTOP = HOME / "Desktop"
WT = HOME / "AppData" / "Local" / "Microsoft" / "WindowsApps" / "wt.exe"

# (lane, label, working dir, one-line charter scope)
LANES = [
    ("B", "Claude B - harness", HOME / "claude-setup",
     "rules, hooks, skills, schedulers, review fabric, a2a bridges, autonomy rails"),
    ("C", "Claude C - resume engine", HOME / "Downloads" / "new-recruit",
     "hiring machine, arms, applications, job scans"),
    ("D", "Claude D - learning", HOME / "Downloads" / "daily-deep-learning",
     "the PWA, learning cards, study loops"),
    ("A", "Claude A - concierge", HOME / "claude-setup",
     "intent intake, routing, notifications. NEVER implements"),
]


def plan() -> list[dict]:
    rows = []
    for lane, label, cwd, scope in LANES:
        # -NoExit keeps the shell after claude exits, matching the current shortcut.
        # $env:CLAUDE_LANE is set inside the pwsh command so it reaches the claude
        # process and any hook it spawns.
        cmd = "$env:CLAUDE_LANE='{}'; claude".format(lane)
        rows.append({
            "lane": lane,
            "label": label,
            "cwd": str(cwd),
            "exists": cwd.is_dir(),
            "args": '-d "{}" pwsh -NoExit -Command "{}"'.format(cwd, cmd),
            "lnk": str(DESKTOP / (label + ".lnk")),
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

    rows = plan()
    print(f"windows terminal : {WT}  exists={WT.exists()}")
    print(f"desktop          : {DESKTOP}  exists={DESKTOP.is_dir()}\n")
    for r in rows:
        mark = " " if r["exists"] else "  MISSING DIR"
        print(f"  [{r['lane']}] {r['label']}{mark}")
        print(f"        cwd  {r['cwd']}")
        print(f"        args {r['args']}")
        print(f"        {r['scope']}")
    print("\nThe existing 'Claude new-recruit (Admin).lnk' is left in place. Delete it "
          "by hand once a lane launcher has replaced it in your habits.")

    if not args.apply:
        print("\nPLAN ONLY. Re-run with --apply to write the shortcuts.")
        return 0

    if not WT.exists():
        print("\nwt.exe not found; nothing written.")
        return 1

    rc = 0
    for r in rows:
        if not r["exists"]:
            print(f"  skipped {r['lane']}: {r['cwd']} does not exist")
            continue
        script = PS_TEMPLATE.format(
            lnk=ps_quote(r["lnk"]), target=ps_quote(str(WT)),
            args=ps_quote(r["args"]), cwd=ps_quote(r["cwd"]),
            desc=ps_quote("Lane {}: {}".format(r["lane"], r["scope"])))
        p = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if p.returncode == 0:
            print(f"  ok   lane {r['lane']}: {os.path.basename(r['lnk'])}")
        else:
            rc = 1
            print(f"  FAIL lane {r['lane']}: {(p.stderr or '').strip()[:200]}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
