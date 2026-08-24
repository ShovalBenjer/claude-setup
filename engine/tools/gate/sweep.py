#!/usr/bin/env python3
"""Gate every repository in the estate from here, because the satellites never gate themselves.

WHY THIS SHAPE, and it is not the obvious one. The default answer to "the six governance
domains only exist in claude-setup" is to copy those rows into each satellite's contract.
That answer assumes the satellite runs its own gate. Measured 2026-08-05:

    new-recruit          state/gate-runs.jsonl   0 rows
    daily-deep-learning  state/gate-runs.jsonl   0 rows

Neither has ever executed its contract, so improving their inputs changes nothing. The
decision recorded in docs/taste.md is to move the EXECUTION to the place that already
runs, rather than move the configuration to places that do not. gate.py already takes
--project, so this needs no new resolution machinery.

WHAT IT DOES NOT DO. It does not merge contracts, fetch a fragment over the network, or
edit a satellite. Each repo keeps its own quality-contract.json and is gated as it stands.
The governance domains reach the satellites in a later pass; this file first establishes
that anything gates them at all, because a sweep over three repos that has run once is
worth more than a contract-inheritance design that has run zero times.

WHAT IT REPLACES. daily-deep-learning's contract currently shells out to
C:/Users/shova/claude-setup/tools/..., which resolves through /mnt/c to a THIRD clone whose
HEAD is f5d697e, predating today's panel.py corrections. So a satellite is already reaching
across repos for harness tooling, badly and invisibly. This makes that reach explicit,
one-directional, and pinned to whichever checkout is running the sweep.

    python tools/gate/sweep.py                 gate every repo in the estate
    python tools/gate/sweep.py --dry-run       show what would run
    python tools/gate/sweep.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
GATE = ROOT / "tools" / "gate" / "gate.py"

# The estate. A repo qualifies by declaring a contract, not by being listed somewhere,
# so a fourth repo joins by adding quality-contract.json and needs no edit here.
ESTATE_ROOT = pathlib.Path(os.environ.get("CLAUDE_ESTATE_ROOT",
                                          str(pathlib.Path.home() / "work" / "repos")))


def discover(estate: pathlib.Path) -> list[pathlib.Path]:
    if not estate.is_dir():
        return []
    # Dot-prefixed directories are git worktrees, not repositories. The first dry run
    # of this tool found .wt-rules-sync sitting beside the real repos with 16 domains
    # and 7,962 gate runs, because a parallel session had a worktree checked out there.
    # Sweeping it would gate the same contract twice and attribute the result to a repo
    # that does not exist.
    return sorted(p for p in estate.iterdir()
                  if not p.name.startswith(".")
                  and (p / "quality-contract.json").is_file())


def contract_size(repo: pathlib.Path) -> int:
    try:
        return len(json.loads((repo / "quality-contract.json").read_text(
            encoding="utf-8"))["domains"])
    except Exception:
        return -1


def ever_gated(repo: pathlib.Path) -> int:
    """Rows in the repo's own run ledger. Zero is the finding this tool exists for."""
    led = repo / "state" / "gate-runs.jsonl"
    try:
        return sum(1 for line in led.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def run_one(repo: pathlib.Path, timeout: int) -> tuple[str, int, str]:
    proc = subprocess.run(
        [sys.executable, str(GATE), "run", "--project", str(repo)],
        capture_output=True, text=True, timeout=timeout,
    )
    verdict = "UNKNOWN"
    for line in proc.stdout.splitlines():
        if line.startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip()
    return verdict, proc.returncode, proc.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    repos = discover(ESTATE_ROOT)
    if not repos:
        print("no repository under {} declares a quality-contract.json".format(ESTATE_ROOT))
        return 2

    print("estate: {}".format(ESTATE_ROOT))
    for r in repos:
        print("  {:<24} {:>2} domains   own gate runs: {}".format(
            r.name, contract_size(r), ever_gated(r)))
    print()

    if a.dry_run:
        for r in repos:
            print("would run: {} run --project {}".format(GATE, r))
        return 0

    worst = 0
    for r in repos:
        try:
            verdict, rc, _out = run_one(r, a.timeout)
        except subprocess.TimeoutExpired:
            verdict, rc = "TIMEOUT after {}s".format(a.timeout), 1
        print("{:<24} {}".format(r.name, verdict))
        worst = max(worst, rc)

    # Non-zero if ANY repo is red. A sweep that reports green because two of three
    # repos were skipped is the false-green class this estate already logs.
    return worst


def selftest() -> int:
    """Prove discovery finds a contract and ignores a directory without one."""
    import tempfile
    fails = []

    def check(cond, msg):
        print("[{}] {}".format("ok  " if cond else "FAIL", msg))
        if not cond:
            fails.append(msg)

    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        (base / "has-contract").mkdir()
        (base / "has-contract" / "quality-contract.json").write_text(
            '{"domains":{"unit":{"required":true}}}', encoding="utf-8")
        (base / "no-contract").mkdir()
        (base / "no-contract" / "README.md").write_text("nothing", encoding="utf-8")

        found = [p.name for p in discover(base)]
        check(found == ["has-contract"],
              "discovery finds a repo by its contract and ignores one without: got {}".format(found))
        check(contract_size(base / "has-contract") == 1,
              "domain count is read from the contract")
        check(ever_gated(base / "has-contract") == 0,
              "a repo with no run ledger reports zero, which is the finding not an error")
        check(discover(base / "does-not-exist") == [],
              "a missing estate root returns empty rather than raising")

    print()
    if fails:
        print("{} check(s) FAILED".format(len(fails)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
