"""Append this session's charter lesson to state/lessons.jsonl.

charters.md rule 4 makes charter violations lessons. L-2026-07-27-a already
records "a Lane C session did Lane B's work"; this row exists because it happened
AGAIN, hours after the fix for it was written, which is the part that is new
information rather than a duplicate.

    python log_session_lesson.py --apply
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "state" / "lessons.jsonl"

ROW = {
    "id": "L-2026-07-27-c",
    "ts": "2026-07-27",
    "lane": "C",
    "status": "closed",
    "supersedes_context": "L-2026-07-27-a",
    "lesson": (
        "The same violation as L-2026-07-27-a recurred in the next session: "
        "undeclared lane, cwd Downloads\\new-recruit, and the whole session was "
        "Lane B harness work (taskbar pin, launcher tests, claude-setup commit "
        "e35123d). What is new is WHY it recurred. The fix for it already existed "
        "and worked: Start-Claude.ps1 plus four lane shortcuts, written 06:20-06:26. "
        "It changed nothing for ~11 hours because the taskbar pin, the only launcher "
        "actually used, was never repointed at it."
    ),
    "why_it_happened": (
        "The fix was installed next to the habit instead of inside it. Desktop "
        "shortcuts and a working chooser are both real artifacts, and both were "
        "reported as the fix, but the operator opens Claude from the taskbar. A "
        "correct mechanism on a surface nobody touches is staged, not deployed."
    ),
    "fix": (
        "tools/workspace/repoint_taskbar_pin.ps1 rewrites the pinned .lnk in place, "
        "preserving the icon and the elevation bit at header byte 21 that "
        "WScript.Shell.Save() clears, with a .bak and -Revert. Operator confirmed "
        "the chooser opens on click. tests/test_workspace_launcher.py::TaskbarPin "
        "asserts the live pin runs the chooser and not the old hardcoded -d form, "
        "so this specific gap is now measured rather than remembered."
    ),
    "residual": (
        "The pin's filename, and so its taskbar label, still says new-recruit; "
        "renaming a pinned .lnk orphans the pin, so that is a manual unpin/repin. "
        "The Lane B changes made from this Lane C session were not re-landed as "
        "proposals, same open item as L-2026-07-27-a."
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    existing = [json.loads(ln) for ln in
                LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if any(r.get("id") == ROW["id"] for r in existing):
        print(f"  {ROW['id']} already present; nothing to do")
        return 0

    line = json.dumps(ROW, ensure_ascii=False)
    print(f"  ledger  {LEDGER}  rows={len(existing)}")
    print(f"  append  {ROW['id']}  {len(line)} bytes")
    if not args.apply:
        print("\n  PLAN ONLY. Re-run with --apply.")
        return 0

    # Byte-level append with an explicit newline: the ledger is LF, and a text-mode
    # write on Windows would put a CRLF terminator on one row and not the others.
    with LEDGER.open("ab") as fh:
        fh.write(line.encode("utf-8") + b"\n")

    rows = [json.loads(ln) for ln in
            LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ok = len(rows) == len(existing) + 1 and rows[-1]["id"] == ROW["id"]
    print(f"\n  {'appended' if ok else 'VERIFY FAILED'}, rows={len(rows)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
