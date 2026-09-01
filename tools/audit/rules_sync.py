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
import tempfile
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
    # With no live tree, every payload rule would read as "not deployed". That is a
    # true statement about a runner and a useless one, so the comparison sets are
    # emptied here and report() states the skip.
    if not LIVE.is_dir():
        live_files = dict(payload_files)

    only_payload = sorted(set(payload_files) - set(live_files))
    only_live = sorted(set(live_files) - set(payload_files))
    differing, shrunk = [], []
    # Counted, not inferred. An empty `shrunk` is the healthy answer AND the answer a
    # loop that never ran gives, so the two are indistinguishable from the output
    # alone. That is not hypothetical: `mutate.py --spec rules` reports the seeding
    # line above as load-bearing, and with it removed the loop below iterates an empty
    # intersection on any runner while the report still prints "rules clean (shrink
    # only)". This counter is what the selftest reads to tell those two apart.
    shrink_checked = 0

    for name in sorted(set(payload_files) & set(live_files)):
        shrink_checked += 1
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
            "shrink_checked": shrink_checked,
            "only_payload": only_payload, "only_live": only_live,
            "differing": differing, "shrunk": shrunk}


def report(res: dict) -> int:
    problems = 0

    # NO LIVE TREE IS NOT A FAILURE. Corrected 2026-08-05 after this domain turned
    # the Ship gate red on every GitHub runner with
    # "FAIL live rules directory does not exist: /home/runner/.claude/rules".
    # That is L-2026-07-31-g exactly: a host-shaped default, correct on the machine
    # it was written on, silently answering the wrong question on the other. A CI
    # runner has no ~/.claude and never will; asking whether the repo matches a
    # deployment that does not exist is not a question with a right answer.
    #
    # The SHRINK half is host-independent, because it compares the payload against
    # its own git history, and it is the half that matters: it is the check that
    # would have caught 2bb97a8. So drift is skipped and shrink still runs, and the
    # skip is stated rather than assumed, because a domain that silently checks half
    # of what its name implies is worse than one that fails.
    live_present = Path(res["live_dir"]).is_dir()
    if not live_present:
        print("SKIP drift: no live rules tree at {} (expected on CI). The deployment "
              "half is unanswerable here; the shrink half below still runs."
              .format(res["live_dir"]))

    if live_present:
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
    if live_present:
        print("rules clean: {} rule(s), repo and live identical, none below {:.0%} of its "
              "recorded maximum".format(res["counted"], SHRINK_FLOOR))
    else:
        print("rules clean (shrink only): {} rule(s) examined, none below {:.0%} of its "
              "recorded maximum. Drift against a live tree was NOT checked."
              .format(res.get("shrink_checked", 0), SHRINK_FLOOR))
    return 0



def _report_without_live_tree() -> tuple[int, str, dict]:
    """Run the domain as a CI runner would see it: no ~/.claude at all.

    In its own function because rebinding the module-level LIVE inside selftest()
    needs a `global` declaration ahead of every other use of the name in that
    function, and putting one there is a footgun aimed at whoever edits the
    selftest next.
    """
    import contextlib
    import io

    global LIVE
    saved = LIVE
    try:
        LIVE = Path("/nonexistent-ci-runner-home/.claude/rules")
        res = scan()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = report(res)
        return rc, buf.getvalue(), res
    finally:
        LIVE = saved


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
    # The upper bound, which the first two versions of this file both left open and
    # which `mutate.py --spec rules` reported as SURVIVED. 2bb97a8 also trimmed four
    # rules legitimately and none fell below 0.9, so a floor above that flags healthy
    # files on every run. An oracle that fires on correct input gets waived, and a
    # waived domain is not a weaker guard, it is no guard.
    if 0.90 * 5557 < 5557 * SHRINK_FLOOR:
        failures.append("the floor is above 0.90, so the legitimate trims in the same "
                        "commit (no-emojis, no-mocks, task-verification, "
                        "tdd-enforcement) would all be reported as damage")

    res = scan()
    if res["counted"] == 0:
        failures.append("no rules were found at all, so a clean result would be vacuous")
    if not isinstance(res["shrunk"], list) or not isinstance(res["differing"], list):
        failures.append("scan did not return the expected shape")

    # A rule present in exactly one tree must fail, both ways round. Checked against
    # the real report function on synthetic input, because the two directions have
    # different consequences and both were wrong to miss. Its output is captured so a
    # passing selftest does not print lines that read as failures.
    import contextlib  # noqa: PLC0415
    import io

    def _quiet_report(res: dict) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return report(res)

    # live_dir MUST be a directory that exists, and str(LIVE) is not one on a CI
    # runner. report() decides whether to run the drift loops by testing this path,
    # so with an absent one the next four cases exercise the skip branch and every
    # one of them "passes" by never being checked. Measured 2026-08-05: the named CI
    # step reported exactly that, three drift assertions failing on the runner and
    # green here. Same lesson as the bug this file was corrected for, one layer up.
    _live_probe = tempfile.TemporaryDirectory()
    base = {"payload_dir": str(PAYLOAD), "live_dir": _live_probe.name, "counted": 1,
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

    # The CI regression, pinned. This domain reddened every GitHub runner for a day
    # with "live rules directory does not exist". Both halves are asserted: no live
    # tree must NOT fail, and the shrink half must still be evaluated, because a
    # domain that quietly checks half of its name is worse than one that fails.
    rc_ci, out, res_ci = _report_without_live_tree()
    if rc_ci != 0:
        failures.append("no live tree fails the domain, which is the CI regression itself")
    if "SKIP drift" not in out:
        failures.append("the skipped drift half was not stated out loud")
    if "shrink" not in out.lower():
        failures.append("the shrink half did not report, so the domain checked nothing")
    # The assertion above is satisfied by the word "shrink" in the clean message
    # itself, so it holds whether the loop examined 22 rules or zero. `mutate.py
    # --spec rules` proved that: removing the live_files seeding in scan() left this
    # selftest green while the domain checked nothing on every runner. The count is
    # the only thing that separates the two.
    n_payload = len(list(PAYLOAD.glob("*.md"))) if PAYLOAD.is_dir() else 0
    if n_payload == 0:
        failures.append("no payload rules found, so every shrink assertion is vacuous")
    elif res_ci.get("shrink_checked") != n_payload:
        failures.append("with no live tree the shrink half examined {} of {} payload "
                        "rules, so the one check that still runs on CI is not running "
                        "over all of them".format(res_ci.get("shrink_checked"), n_payload))

    _live_probe.cleanup()

    for line in failures:
        print("  [FAIL] " + line)
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
    print("  ok    no live tree skips drift, still runs shrink, and says which half ran")
    print("  ok    the shrink half examined every payload rule with no live tree")
    print("  ok    the floor sits at or below 0.90, so legitimate trims are not flagged")
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
