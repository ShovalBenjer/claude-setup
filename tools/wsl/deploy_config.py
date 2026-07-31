"""Translate the live Windows ~/.claude into a working WSL ~/.claude.

Not a copy. The live settings.json names Windows interpreters and Windows paths, and
it splits them across two fields:

    {"command": "python",
     "args": ["C:\\Users\\shova\\claude-setup\\tools\\bus\\bus.py", "inbox"]}

so a translator that reads `command` alone rewrites the interpreter and leaves every
script path pointing at C:\\Users. Measured on the live file: 4 of 4 interpreters looked
translatable and 100% of the actual script paths were in `args`.

Under Ubuntu `python` does not exist (only python3), Git-Bash does not exist,
powershell.exe has no equivalent, and a Windows venv puts its interpreter in
Scripts\\python.exe rather than bin/python. Paths are rewritten to the LINUX home, not
to /mnt/c: pointing WSL hooks at the Windows tree would make one hook fire from two
environments against two different repos.

Read-only against Windows. Writes only under the WSL home, always with LF.

    python tools/wsl/deploy_config.py            # report what would change
    python tools/wsl/deploy_config.py --execute  # write it
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

WIN_CLAUDE = r"C:\Users\shova\.claude"
WSL_HOME = "/home/shov"
WSL_CLAUDE = WSL_HOME + "/.claude"

# Deliberately not everything: caches, corpora, project transcripts and backups are
# large, machine-specific or private, and a fresh environment is the right moment to
# leave them behind.
COPY_DIRS = ["hooks", "rules", "output-styles", "commands", "agents", "skills"]

# Describes this machine rather than the operator's preferences.
DROP_KEYS = {"statusLine"}

# Longest prefix first, or a home path becomes /mnt/c and points back at Windows.
PREFIXES = [
    (r"C:\Users\shova\.claude", WSL_CLAUDE),
    ("C:/Users/shova/.claude", WSL_CLAUDE),
    ("/c/Users/shova/.claude", WSL_CLAUDE),
    (r"C:\Users\shova\claude-setup", WSL_HOME + "/claude-setup"),
    ("C:/Users/shova/claude-setup", WSL_HOME + "/claude-setup"),
    ("/c/Users/shova/claude-setup", WSL_HOME + "/claude-setup"),
    (r"C:\Users\shova", WSL_HOME),
    ("C:/Users/shova", WSL_HOME),
    ("/c/Users/shova", WSL_HOME),
]


def wsl(cmd: str, check: bool = True) -> tuple[int, str]:
    p = subprocess.run(["wsl.exe", "-d", "Ubuntu", "-e", "bash", "-lc", cmd],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    if check and p.returncode != 0:
        print("    wsl failed: " + out.strip()[:300])
    return p.returncode, out.strip()


def translate_path(value: str) -> tuple[str, list[str]]:
    """Rewrite one Windows path or interpreter name. Returns (new, notes)."""
    notes: list[str] = []
    new = value

    if "Git\\bin\\bash.exe" in new or "Git/bin/bash.exe" in new:
        return "bash", ["git-bash to bash"]
    if new.lower().endswith("powershell.exe"):
        return new, ["POWERSHELL: no Linux equivalent, hook will not run"]

    # Windows venv layout. The venv does not exist in WSL yet, so this is rewritten
    # AND flagged: the hook stays dead until `uv sync` runs inside the Linux clone.
    for a, b in ((r"\.venv\Scripts\python.exe", "/.venv/bin/python"),
                 ("/.venv/Scripts/python.exe", "/.venv/bin/python")):
        if a in new:
            new = new.replace(a, b)
            notes.append("venv layout to posix (venv NOT created yet)")

    for win, unix in PREFIXES:
        if win in new:
            new = new.replace(win, unix)
            notes.append("path to linux")
            break

    if new.startswith(WSL_HOME):
        new = new.replace("\\", "/")

    if new == "python":
        return "python3", notes + ["python to python3"]
    return new, sorted(set(notes))


def translate_hook(hk: dict) -> list[str]:
    """Rewrite a hook's command AND its args."""
    notes: list[str] = []
    cmd = hk.get("command")
    if isinstance(cmd, str):
        new, n = translate_path(cmd)
        hk["command"] = new
        notes += n
    args = hk.get("args")
    if isinstance(args, list):
        out = []
        for arg in args:
            if isinstance(arg, str):
                new, n = translate_path(arg)
                out.append(new)
                notes += n
            else:
                out.append(arg)
        hk["args"] = out
    return sorted(set(notes))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    print("{}  {} -> {}".format("EXECUTE" if a.execute else "DRY RUN",
                                WIN_CLAUDE, WSL_CLAUDE))

    src = os.path.join(WIN_CLAUDE, "settings.json")
    if not os.path.isfile(src):
        print("no settings.json at " + src)
        return 2
    data = json.load(open(src, encoding="utf-8"))

    print("\nSETTINGS")
    for k in sorted(DROP_KEYS & set(data)):
        data.pop(k)
        print("  drop   {}  (describes the Windows machine)".format(k))

    changed = 0
    dead: list[str] = []
    for event, matchers in (data.get("hooks") or {}).items():
        for m in matchers:
            for hk in m.get("hooks", []):
                before = json.dumps([hk.get("command"), hk.get("args")])
                notes = translate_hook(hk)
                after = json.dumps([hk.get("command"), hk.get("args")])
                if before != after or notes:
                    changed += 1
                    print("  {:16s} {}".format(event, ", ".join(notes) or "-"))
                    print("      -  {}".format(before[:104]))
                    print("      +  {}".format(after[:104]))
                for n in notes:
                    if "no Linux equivalent" in n or "NOT created" in n:
                        dead.append("{}: {}".format(event, n))
    print("  {} hook(s) rewritten".format(changed))
    if dead:
        print("\n  WILL NOT RUN until fixed separately:")
        for d in sorted(set(dead)):
            print("    - " + d)

    print("\nDIRECTORIES")
    for d in COPY_DIRS:
        w = os.path.join(WIN_CLAUDE, d)
        if not os.path.isdir(w):
            print("  skip   {}  (absent on Windows)".format(d))
            continue
        n = sum(len(f) for _r, _d, f in os.walk(w))
        print("  copy   {:14s} {} file(s)".format(d, n))
        if a.execute:
            wsl("mkdir -p {}/{}".format(WSL_CLAUDE, d))
            rc, _ = wsl("cp -r /mnt/c/Users/shova/.claude/{}/. {}/{}/".format(
                d, WSL_CLAUDE, d))
            if rc == 0:
                # A .sh written on Windows carries CRLF, and bash reports it as
                # "$'\\r': command not found", which reads like a missing hook rather
                # than a broken one.
                wsl("find {}/{} -name '*.sh' -exec sed -i 's/\\r$//' {{}} + "
                    "; find {}/{} -name '*.sh' -exec chmod +x {{}} +".format(
                        WSL_CLAUDE, d, WSL_CLAUDE, d), check=False)

    if not a.execute:
        print("\nDRY RUN: nothing written. Re-run with --execute.")
        return 0

    tmp = os.path.join(os.environ.get("TEMP", "."), "_settings_wsl.json")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    unix_tmp = tmp.replace("C:\\", "/mnt/c/").replace("\\", "/")
    wsl("mkdir -p {}".format(WSL_CLAUDE))
    rc, out = wsl("cp '{}' {}/settings.json".format(unix_tmp, WSL_CLAUDE))
    print("\nsettings.json written" if rc == 0 else "\nsettings.json FAILED: " + out)

    print("\nVERIFY")
    _rc, out = wsl("python3 -c \"import json,sys;"
                   "d=json.load(open('{}/settings.json'));"
                   "print('  events:', ' '.join(sorted(d.get('hooks',{{}}))));"
                   "print('  model:', d.get('model'));"
                   "print('  outputStyle:', d.get('outputStyle'))\"".format(WSL_CLAUDE),
                   check=False)
    print(out)
    _rc, out = wsl("ls {} | tr '\\n' ' '".format(WSL_CLAUDE), check=False)
    print("  tree: " + out.strip()[:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
