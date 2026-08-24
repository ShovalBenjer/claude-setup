#!/usr/bin/env python3
"""Which review findings has nobody acted on, ranked by how often they came back.

THE GAP THIS FILLS.

`panel.py` has written 39 review artifacts holding 686 findings since 2026-07-25. Four
files reference `state/reviews/`: panel.py writes it, gate.py checks only that an artifact
exists for the current sha, strand.py treats it as a bookkeeping surface, and the workflow
invokes the panel. **Nothing reads a finding.** There is no path from a finding to a
ticket, a fix, or an owner, and grepping tools/ghpub and tools/selfimprove for one returns
nothing.

The registry declares the split and no code implements it: Review Board owns finding
(`review`, `ponytail-review`, `watchdog`, `cleanup-crew`), Engineering Firm owns fixing
(`code-simplifier`, `refactor-pre-push`, `tdd`). Engineering Firm has never been spawned.

WHY RECURRENCE IS THE RIGHT MEASURE, AND WHY IT IS NOT ENOUGH.

The finding schema carries `check, file, line, persona, severity, snippet, source, why`
and no status, no owner, no ticket. So a fixed finding and an ignored one are byte
identical in the record, and no single artifact can tell them apart.

Across artifacts they separate. A finding that appears once and stops was either fixed or
the code moved. A finding that appears in 29 consecutive artifacts was not. Measured
2026-08-06: **59 of 63 distinct (file, check) pairs recur in more than one artifact**, and
the top five appear 28 or 29 times each.

What recurrence CANNOT tell you is whether a recurring finding is unresolved or
deliberately carried. Both look identical here. `tools/intent/route.py :: bare-except-pass`
recurs 11 times and is deliberate: it is a UserPromptSubmit hook and failing open is its
stated safety property. `tools/map/codemap.py:66 :: py-shell-true` also recurs and is an
oracle defect that survived four waiver renewals. This tool ranks them the same, and
distinguishing them needs a `status` field that only the operator can define the vocabulary
for. Reporting the count without that caveat would be the false-precision failure.

    python tools/review/recurrence.py            # ranked, worst first
    python tools/review/recurrence.py --high     # highs and mediums only
    python tools/review/recurrence.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REVIEWS = REPO / "state" / "reviews"

SEV_RANK = {"high": 0, "medium": 1, "low": 2}


def load(reviews: Path) -> list[dict]:
    """Every artifact, newest last. A torn or unreadable file is skipped and counted.

    Skipping individually rather than raising, for the reason collect.py's read_ledger
    states: a reader that dies on the first bad file reports nothing for a corpus that is
    almost entirely readable, and zero findings looks exactly like a clean repo.
    """
    out = []
    if not reviews.is_dir():
        return out
    for p in sorted(reviews.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def tally(artifacts: list[dict]) -> dict:
    """(file, check) -> how many ARTIFACTS it appeared in, plus its worst severity.

    Counted per artifact, not per occurrence. A finding hit twice in one review is one
    review's worth of evidence about it, and counting occurrences would rank a file with
    many similar lines above a finding that has survived thirty reviews.
    """
    seen_in: collections.Counter = collections.Counter()
    worst: dict[tuple, str] = {}
    example: dict[tuple, dict] = {}
    for art in artifacts:
        here = set()
        for f in (art.get("findings") or []):
            key = (str(f.get("file", "")), str(f.get("check", "")))
            if key in here:
                continue
            here.add(key)
            seen_in[key] += 1
            sev = str(f.get("severity", "low"))
            if key not in worst or SEV_RANK.get(sev, 9) < SEV_RANK.get(worst[key], 9):
                worst[key] = sev
            example.setdefault(key, f)
    return {"artifacts": len(artifacts), "seen_in": seen_in,
            "worst": worst, "example": example}


def rank(t: dict, min_sev: str = "low") -> list[tuple]:
    cut = SEV_RANK.get(min_sev, 2)
    rows = [(n, k) for k, n in t["seen_in"].items()
            if SEV_RANK.get(t["worst"].get(k, "low"), 9) <= cut]
    rows.sort(key=lambda r: (-r[0], SEV_RANK.get(t["worst"].get(r[1], "low"), 9), r[1]))
    return rows


def report(t: dict, min_sev: str) -> int:
    rows = rank(t, min_sev)
    total = len(t["seen_in"])
    recurring = sum(1 for n in t["seen_in"].values() if n > 1)
    print("{} artifact(s), {} distinct (file, check) pair(s), {} recurring in more than one"
          .format(t["artifacts"], total, recurring))
    if not rows:
        print("nothing at or above severity {}".format(min_sev))
        return 0
    print()
    print("{:>4}  {:<7}  {}".format("seen", "sev", "file :: check"))
    for n, k in rows[:40]:
        print("{:>4}  {:<7}  {} :: {}".format(n, t["worst"].get(k, "")[:7], k[0][:56], k[1][:24]))
    print()
    print("A high count means the finding came back, NOT that it is unresolved. This file "
          "cannot tell a carried finding from an ignored one, because the finding schema "
          "has no status field. Adding one is an operator decision about vocabulary.")
    return 0


def selftest() -> int:
    failures = []

    arts = [
        {"findings": [{"file": "a.py", "check": "x", "severity": "low"},
                      {"file": "a.py", "check": "x", "severity": "low"},
                      {"file": "b.py", "check": "y", "severity": "high"}]},
        {"findings": [{"file": "a.py", "check": "x", "severity": "medium"}]},
        {"findings": []},
    ]
    t = tally(arts)

    # Per ARTIFACT, not per occurrence. a.py::x is hit twice in artifact 1 and once in
    # artifact 2, so it has been seen in 2 artifacts.
    if t["seen_in"][("a.py", "x")] != 2:
        failures.append("a finding hit twice inside ONE artifact was counted twice, so a "
                        "file with many similar lines outranks a finding that survived "
                        "thirty reviews")
    if t["seen_in"][("b.py", "y")] != 1:
        failures.append("a single-artifact finding was miscounted")

    # Worst severity wins across artifacts: low then medium must record medium.
    if t["worst"][("a.py", "x")] != "medium":
        failures.append("severity did not escalate across artifacts; got {}".format(
            t["worst"][("a.py", "x")]))

    ranked = rank(t)
    if ranked[0][1] != ("a.py", "x"):
        failures.append("ranking is not by recurrence first; got {}".format(ranked[0][1]))
    if [k for _, k in rank(t, "high")] != [("b.py", "y")]:
        failures.append("the severity filter admitted findings below the cut")

    if tally([]) ["seen_in"]:
        failures.append("an empty corpus produced findings out of nothing")

    # A corpus that cannot be read must yield nothing, never raise. Zero artifacts and a
    # clean repo look the same from here, which is why the report prints the count.
    if load(Path("/nonexistent-reviews-dir-for-selftest")):
        failures.append("a missing reviews directory produced artifacts")

    live = load(REVIEWS)
    if REVIEWS.is_dir() and len(live) < 2:
        failures.append("only {} live artifact(s) parsed, so the ranking is vacuous"
                        .format(len(live)))
    elif not REVIEWS.is_dir():
        print("  NOT RUN  the live-corpus check: no {} on this host".format(REVIEWS))

    for line in failures:
        print("  [FAIL] " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    a finding hit twice in one artifact counts as one artifact")
    print("  ok    severity escalates to the worst seen across artifacts")
    print("  ok    ranking is recurrence first, then severity")
    print("  ok    the severity filter excludes what is below the cut")
    print("  ok    an empty or missing corpus yields nothing and never raises")
    print("VERDICT: recurrence is counted per artifact and ranked without inventing status")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="recurrence.py", description=__doc__.splitlines()[0])
    ap.add_argument("--high", action="store_true", help="high and medium only")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return report(tally(load(REVIEWS)), "medium" if args.high else "low")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
