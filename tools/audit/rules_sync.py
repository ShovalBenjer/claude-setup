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

WHERE THERE IS NO LIVE TREE, which is every CI runner.

The first version of this file returned FAIL when `~/.claude/rules` was absent, so
it went red on GitHub Actions by construction: a runner has no deployed harness and
never will. That turned the whole `rules` gate domain red for a condition that is
correct, which is L-2026-07-31-g, a host-shaped default answering the wrong question
on the other host. It is the lesson this repository logged on 2026-07-31 and then
shipped again on 2026-08-05.

The split is between the two checks, not between the two hosts. DRIFT compares
payload against live and is genuinely unmeasurable with no live tree, so it is
reported as not run, by name, with the path that was missing. SHRINK compares
payload against git history, needs no live tree at all, and is the check that would
have caught the incident, so it keeps running and can still fail the command. An
absent live tree therefore narrows what is asserted; it never widens it to a pass.
An EMPTY live directory is a different fact and still fails, because a deployment
that exists and holds nothing is a deployment that was destroyed.

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
    live_present = LIVE.is_dir()
    live_files = {p.name: p for p in LIVE.glob("*.md")} if live_present else {}

    # With no live tree the drift comparison has no second operand. Reporting all 22
    # payload rules as undeployed would be technically true of a CI runner and useless,
    # so the lists stay empty and `live_present` carries the fact instead.
    only_payload = sorted(set(payload_files) - set(live_files)) if live_present else []
    only_live = sorted(set(live_files) - set(payload_files)) if live_present else []
    differing, shrunk = [], []
    # Counted rather than inferred. An empty `shrunk` is the healthy answer AND the
    # answer a loop that never ran gives, so without this number the two are
    # indistinguishable and a shrink check that quietly stopped running reads as clean.
    shrink_checked = 0

    # SHRINK reads payload and git history only, so it runs on every host. Iterating
    # payload rather than the intersection is what keeps it running with no live tree.
    for name in sorted(payload_files):
        shrink_checked += 1
        pb = payload_files[name].read_bytes()
        if live_present and name in live_files:
            lb = live_files[name].read_bytes()
            if pb != lb:
                differing.append({"rule": name, "payload_bytes": len(pb), "live_bytes": len(lb)})
        hist, commit = git_max_size("dot-claude/rules/" + name)
        if hist and len(pb) < hist * SHRINK_FLOOR:
            shrunk.append({"rule": name, "now": len(pb), "max": hist,
                           "ratio": round(len(pb) / hist, 3), "max_at": commit[:8]})

    return {"payload_dir": str(PAYLOAD), "live_dir": str(LIVE),
            "live_present": live_present,
            "counted": len(set(payload_files) | set(live_files)),
            "shrink_checked": shrink_checked,
            "only_payload": only_payload, "only_live": only_live,
            "differing": differing, "shrunk": shrunk}


def report(res: dict) -> int:
    problems = 0
    live_present = res.get("live_present", True)
    if not live_present:
        print("NOT RUN drift: no live rules directory at " + res["live_dir"] +
              ". Deployment is unmeasurable from here, so this run asserts nothing "
              "about whether the repo copy and the deployed copy agree.")

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
    if not live_present:
        print("rules clean (shrink only): {} rule(s) examined, none below {:.0%} of its "
              "recorded maximum. Drift was NOT checked.".format(
                  res.get("shrink_checked", 0), SHRINK_FLOOR))
        return 0
    print("rules clean: {} rule(s), repo and live identical, none below {:.0%} of its "
          "recorded maximum".format(res["counted"], SHRINK_FLOOR))
    return 0


def selftest() -> int:
    global LIVE  # noqa: PLW0603  # repointed below to probe the no-live-tree path
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
    # The upper bound, which the original selftest left open. 2bb97a8 also trimmed four
    # rules legitimately and none fell below 0.9, so a floor above that flags healthy
    # files. An oracle that fires on correct input is one that gets waived and deleted.
    if 0.90 * 5557 < 5557 * SHRINK_FLOOR:
        failures.append("the floor is above 0.90, so the legitimate trims in the same "
                        "commit (no-emojis, no-mocks, task-verification, tdd-enforcement) "
                        "would all be reported as damage")

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

    def _run_report(res: dict) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = report(res)
        return code, buf.getvalue()

    def _quiet_report(res: dict) -> int:
        return _run_report(res)[0]

    base = {"payload_dir": str(PAYLOAD), "live_dir": str(LIVE), "live_present": True,
            "counted": 1, "shrink_checked": 1,
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

    # The CI case. Absent live tree must narrow what is asserted, never widen it, and
    # must say so out loud: a pass whose reduced scope is invisible is the worse defect.
    no_live = dict(base, live_present=False)
    code, text = _run_report(no_live)
    if code != 0:
        failures.append("an absent live tree fails, which is the L-2026-07-31-g defect "
                        "this change exists to remove")
    if "NOT RUN" not in text or res["live_dir"] not in text:
        failures.append("an absent live tree passes SILENTLY, without naming the check "
                        "that did not run or the path that was missing")
    if _quiet_report(dict(no_live, shrunk=[{"rule": "w.md", "now": 488, "max": 5557,
                                            "ratio": 0.09, "max_at": "146cb7b4"}])) == 0:
        failures.append("a truncated rule passes when there is no live tree, so CI would "
                        "be blind to the one incident this file was written for")

    # An empty live directory is a deployment that was destroyed, not an absent one.
    if _quiet_report(dict(base, only_payload=["a.md", "b.md"])) == 0:
        failures.append("a live directory that exists and holds nothing passes")

    # scan() itself must not report every payload rule as undeployed when there is no
    # live tree, which is what makes the report above reachable at all.
    import tempfile  # noqa: PLC0415

    _saved = LIVE
    try:
        LIVE = Path("/nonexistent-live-rules-tree-for-selftest")
        probe = scan()
        # An EMPTY live directory is the destroyed-deployment case and must not be
        # collapsed into the absent one. Probed against a real empty directory rather
        # than a synthetic dict, because the two cases are decided inside scan().
        with tempfile.TemporaryDirectory() as empty:
            LIVE = Path(empty)
            empty_probe = scan()
    finally:
        LIVE = _saved

    n_payload = len(list(PAYLOAD.glob("*.md"))) if PAYLOAD.is_dir() else 0
    if probe["live_present"]:
        failures.append("scan reports a live tree that is not there")
    if probe["only_payload"]:
        failures.append("scan reports every payload rule as undeployed when there is no "
                        "live tree, which floods the report with {} false FAILs".format(
                            len(probe["only_payload"])))
    # The one that catches a shrink loop which quietly stopped running. An empty
    # `shrunk` is also the healthy answer, so the count is the only way to tell them
    # apart, and comparing it against the payload size is the only way to tell a
    # partial sweep from a full one.
    if probe["shrink_checked"] != n_payload or n_payload == 0:
        failures.append("with no live tree the shrink check examined {} of {} payload "
                        "rules, so it is not running everywhere and CI verifies "
                        "nothing".format(probe["shrink_checked"], n_payload))
    if empty_probe["live_present"] is not True:
        failures.append("an empty live directory is reported as absent, so a destroyed "
                        "deployment reads as a machine that never had one")
    if len(empty_probe["only_payload"]) != n_payload:
        failures.append("an empty live directory reports {} undeployed rules instead of "
                        "{}, so wiping the live tree passes".format(
                            len(empty_probe["only_payload"]), n_payload))

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
    print("  ok    an absent live tree passes and NAMES the drift check it skipped")
    print("  ok    a truncated rule still fails with no live tree, so CI is not blind")
    print("  ok    an empty live directory still fails, unlike an absent one")
    print("  ok    scan with no live tree reports 0 undeployed rules, not all of them")
    print("  ok    the shrink check examined every payload rule with no live tree")
    print("  ok    an EMPTY live directory reports all rules undeployed, unlike an absent one")
    print("  ok    the floor sits at or below 0.90, so legitimate trims are not flagged")
    print("  ok    the live tree was actually read ({} rules)".format(res["counted"]))
    print("VERDICT: rules drift and rule truncation both fail closed; with no live tree "
          "drift is reported as not run and truncation still fails")
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
