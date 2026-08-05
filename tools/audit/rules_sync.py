#!/usr/bin/env python3
"""Guard the global rules against the failure that already happened to them.

WHAT HAPPENED, from git rather than from memory.

`dot-claude/rules/` holds the global rules deployed to `~/.claude/rules/`, which are
loaded into every session in every project. On 2026-08-04 twelve of them were found
at roughly a tenth of their original size: `boundary-contracts.md` was 488 bytes
against 5557 at first commit, and what the 488 bytes had lost was the entire
enforceable half. The full rule carries an eight-point checklist, five mandatory
boundary test cases, a fail-closed 502 requirement and three named language-level
bans (`x, _ := json.Marshal(...)`, discarded `io.ReadAll` errors, bare
`except: pass` around parsing, unchecked `JSON.parse`). The compressed rule says
"prefer explicit types or schemas over raw passthrough" and stops.

One commit did it: `2bb97a8 chore(config): sync tracked global contract and rules
with the live tree`, which removed 986 lines across 17 rule files and added 166.
The direction is the whole point. It was framed as a sync, and it ran from a
degraded LIVE tree into the good REPO copy, so the version-controlled original was
overwritten by the damaged deployment. `skills_sync.py` measures drift for
`dot-claude/skills` in both directions and says nothing about rules, so nothing
in the repository could see this.

WHAT THIS CHECKS, and why the second check is the one that matters.

1. DRIFT. Payload and live must be identical, same as skills_sync does for skills.
   This catches an undeployed edit and a live-only edit.
2. SHRINK. Every rule is compared against its own largest version in git history.
   A rule that is now a fraction of its recorded maximum is reported, because that
   is what a destructive sync looks like from the outside and a byte count is the
   one signal that survives when the content itself is gone. This is the check that
   would have caught 2bb97a8 on the day it landed.

Check 2 is deliberately NOT symmetric. Growth is never flagged: a rule gaining a
correction row is the system working, and `model-selection.md` is larger than any
historical version precisely because two effort-level corrections were appended to
it rather than editing the losing side out.

    python tools/audit/rules_sync.py check
    python tools/audit/rules_sync.py check --json
    python tools/audit/rules_sync.py selftest
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAYLOAD = REPO / "dot-claude" / "rules"
LIVE = Path.home() / ".claude" / "rules"

# A rule at less than this fraction of its historical maximum is reported. Set from
# the incident rather than by taste: the twelve damaged rules sat between 0.06 and
# 0.21 of their originals, and the smallest legitimate trim in the same commit
# (no-emojis, no-mocks, task-verification, tdd-enforcement) stayed above 0.9.
SHRINK_FLOOR = 0.60


def git_max_size(rel: str) -> tuple[int, str]:
    """Largest recorded size of a tracked file, and the commit it came from.

    Walks every commit that touched the path rather than reading only the parent,
    because the damage here was a single commit and comparing against HEAD~1 would
    have compared a truncated file to a truncated file.
    """
    try:
        commits = subprocess.run(
            ["git", "-C", str(REPO), "log", "--format=%H", "--", rel],
            capture_output=True, text=True, timeout=120).stdout.split()
    except Exception:  # noqa: BLE001
        return 0, ""
    best, best_c = 0, ""
    for c in commits:
        blob = subprocess.run(["git", "-C", str(REPO), "show", "{}:{}".format(c, rel)],
                              capture_output=True, timeout=60).stdout
        if len(blob) > best:
            best, best_c = len(blob), c
    return best, best_c


def scan() -> dict:
    payload_files = {p.name: p for p in PAYLOAD.glob("*.md")} if PAYLOAD.is_dir() else {}
    live_files = {p.name: p for p in LIVE.glob("*.md")} if LIVE.is_dir() else {}

    only_payload = sorted(set(payload_files) - set(live_files))
    only_live = sorted(set(live_files) - set(payload_files))
    differing, shrunk = [], []

    for name in sorted(set(payload_files) & set(live_files)):
        pb = payload_files[name].read_bytes()
        lb = live_files[name].read_bytes()
        if pb != lb:
            differing.append({"rule": name, "payload_bytes": len(pb), "live_bytes": len(lb)})
        hist, commit = git_max_size("dot-claude/rules/" + name)
        if hist and len(pb) < hist * SHRINK_FLOOR:
            shrunk.append({"rule": name, "now": len(pb), "max": hist,
                           "ratio": round(len(pb) / hist, 3), "max_at": commit[:8]})

    return {"payload_dir": str(PAYLOAD), "live_dir": str(LIVE),
            "counted": len(set(payload_files) | set(live_files)),
            "only_payload": only_payload, "only_live": only_live,
            "differing": differing, "shrunk": shrunk}


def report(res: dict) -> int:
    problems = 0
    if not Path(res["live_dir"]).is_dir():
        print("FAIL live rules directory does not exist: " + res["live_dir"])
        return 1

    for name in res["only_payload"]:
        print("FAIL {} is in the repo and NOT deployed; every session is missing it".format(name))
        problems += 1
    for name in res["only_live"]:
        print("FAIL {} is live and NOT tracked; it vanishes on a fresh machine".format(name))
        problems += 1
    for d in res["differing"]:
        print("FAIL {} differs between repo and live ({} vs {} bytes)".format(
            d["rule"], d["payload_bytes"], d["live_bytes"]))
        problems += 1
    for s in res["shrunk"]:
        print("FAIL {} is {} bytes against {} at {} (ratio {}). A rule that lost most of "
              "itself is the 2bb97a8 failure; restore it or record why it shrank.".format(
                  s["rule"], s["now"], s["max"], s["max_at"], s["ratio"]))
        problems += 1

    if problems:
        print("\n{} problem(s) across {} rule(s)".format(problems, res["counted"]))
        return 1
    print("rules clean: {} rule(s), repo and live identical, none below {:.0%} of its "
          "recorded maximum".format(res["counted"], SHRINK_FLOOR))
    return 0


def selftest() -> int:
    failures = []

    # The shrink rule is arithmetic and is checked as arithmetic, so the threshold
    # cannot drift without this going red.
    if not (400 < 5557 * SHRINK_FLOOR):
        failures.append("the floor would not have flagged boundary-contracts at 488 of 5557")
    if 488 >= 5557 * SHRINK_FLOOR:
        failures.append("488 of 5557 does not trip the floor, so the incident would recur")
    if 183 < 183 * SHRINK_FLOOR:
        failures.append("an unchanged file trips the floor")
    if 6273 < 4565 * SHRINK_FLOOR:
        failures.append("growth trips the floor, so appending a correction would fail the gate")

    res = scan()
    if res["counted"] == 0:
        failures.append("no rules were found at all, so a clean result would be vacuous")
    if not isinstance(res["shrunk"], list) or not isinstance(res["differing"], list):
        failures.append("scan did not return the expected shape")

    # A rule present in exactly one tree must fail, both ways round. Checked against
    # the real report function on synthetic input, because the two directions have
    # different consequences and both were wrong to miss. Its output is captured so a
    # passing selftest does not print lines that read as failures.
    import contextlib, io  # noqa: PLC0415

    def _quiet_report(res: dict) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return report(res)

    base = {"payload_dir": str(PAYLOAD), "live_dir": str(LIVE), "counted": 1,
            "only_payload": [], "only_live": [], "differing": [], "shrunk": []}
    if _quiet_report(dict(base, only_payload=["x.md"])) == 0:
        failures.append("an undeployed rule passes")
    if _quiet_report(dict(base, only_live=["y.md"])) == 0:
        failures.append("an untracked live rule passes")
    if _quiet_report(dict(base, differing=[{"rule": "z.md", "payload_bytes": 1, "live_bytes": 2}])) == 0:
        failures.append("a rule that differs between repo and live passes")
    if _quiet_report(dict(base, shrunk=[{"rule": "w.md", "now": 488, "max": 5557,
                                         "ratio": 0.09, "max_at": "146cb7b4"}])) == 0:
        failures.append("a truncated rule passes, which is the whole incident")
    if _quiet_report(base) != 0:
        failures.append("a clean tree fails, so the oracle cannot go green")

    for line in failures:
        print("  FAIL  " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    488 of 5557 trips the shrink floor, so 2bb97a8 would have been caught")
    print("  ok    an unchanged file does not trip it")
    print("  ok    a rule that GREW does not trip it, so corrections stay appendable")
    print("  ok    a rule in the repo but not deployed fails")
    print("  ok    a rule live but not tracked fails")
    print("  ok    a repo/live byte difference fails, and a truncated rule fails")
    print("  ok    a clean tree passes, so the oracle can go green as well as red")
    print("  ok    the live tree was actually read ({} rules)".format(res["counted"]))
    print("VERDICT: rules drift and rule truncation both fail closed")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="rules_sync.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--json", action="store_true")
    sub.add_parser("selftest")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return selftest()
    res = scan()
    if args.json:
        print(json.dumps(res, indent=2))
        return 0 if not (res["only_payload"] or res["only_live"] or res["differing"] or res["shrunk"]) else 1
    return report(res)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
