#!/usr/bin/env python3
"""Prove a selftest can actually fail.

A green selftest is unfalsified, not verified. A check that cannot fail carries no
more information than one that cannot pass, and this repo is full of tools whose
selftests nobody had ever seen go red. So break each behaviour a module claims to
guarantee, one at a time, in a COPY of that module, and require its own selftest to
go red on every one. A mutation that survives names a check that is decorative.

This is not hypothetical hygiene. The first run against tools/bus/bus.py had two
survivors and both were real defects in the tests: one case planted its fixture
with the test's own writer (so it passed with the product's field removed), and the
canonical wire format had no cross-version oracle (so a shape change stayed
invisible while invalidating every row already on disk). Both are fixed and both
are now guarded here.

  python tools/audit/mutate.py --spec bus
  python tools/audit/mutate.py --spec refute
  python tools/audit/mutate.py --spec all

Exit 0 only when every mutation in every requested spec was applied AND caught.
Exit 2 when a baseline copy is not green, because then no "caught" below could be
attributed to a mutation rather than to the copy.

Why the mutant is written BESIDE the original instead of into a temp directory:
several targets resolve their repo root from __file__, and refute.py additionally
runs verifiers with cwd=ROOT. A copy under %TEMP% gets a ROOT that does not exist,
subprocess.run raises OSError, every case turns BROKEN, and every mutation then
looks "caught" for a reason that has nothing to do with the check under test. That
is a harness that manufactures its own green. Mutants are named _mutant_*.py, are
removed in a finally block, and stale ones are swept at startup and reported.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = Path(__file__).resolve().parent / "mutations"
MUTANT_GLOB = "_mutant_*.py"


def load_spec(name: str):
    """Load a spec by PATH, not by package name.

    tools/ is not a package here (no __init__.py, and adding one would change how
    every other script in the tree imports), so an import_module on
    tools.audit.mutations.<name> raises ModuleNotFoundError. Loading by file path
    works regardless of how the repo is laid out or which cwd this runs from.
    """
    path = SPEC_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_mutspec_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load mutation spec from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def available_specs() -> list[str]:
    return sorted(p.stem for p in SPEC_DIR.glob("*.py") if p.stem != "__init__")


def sweep_stale(target: Path) -> None:
    for stale in target.parent.glob(MUTANT_GLOB):
        print("  swept stale mutant left by an earlier crash: {}".format(stale.name))
        stale.unlink(missing_ok=True)


class Busy(RuntimeError):
    pass


def acquire_lock() -> Path:
    """Refuse to run twice at once, rather than produce quiet nonsense.

    Mutants are named per-index in the target's own directory and swept at startup,
    so two concurrent runs would overwrite and delete each other's files: one run's
    subprocess reads a mutant the other wrote, or finds none at all and turns
    BROKEN, which this harness then reports as "caught". Both C-015 and C-022 in the
    claims ledger invoke this file, so a gate run alongside the CI job is not
    hypothetical.

    mkdir is atomic on Windows and POSIX, so it is the lock. Nothing here tries to
    detect whether the recorded pid is still alive: a wrong liveness guess either
    blocks a legitimate run forever or lets the collision through, and an operator
    reading the pid can answer it correctly in one look.
    """
    lock = SPEC_DIR.parent / ".mutate-lock"
    try:
        lock.mkdir()
    except FileExistsError:
        who = ""
        try:
            who = (lock / "pid").read_text(encoding="utf-8").strip()
        except OSError:
            pass
        raise Busy(
            "another mutation run holds {}{}.\nMutants are written beside their "
            "target with per-index names, so two runs would overwrite each other and "
            "the verdicts would be meaningless. If that process is gone, remove the "
            "directory and re-run.".format(lock, " (pid {})".format(who) if who else ""))
    (lock / "pid").write_text(str(os.getpid()), encoding="utf-8")
    return lock


def run_spec(name: str) -> int:
    spec = load_spec(name)
    target = ROOT / spec.TARGET
    if not target.exists():
        print("MISSING TARGET: {} (spec {})".format(target, name))
        return 2

    original = target.read_text(encoding="utf-8")
    print("=== spec {}: {} ({} mutations) ===".format(name, spec.TARGET, len(spec.MUTATIONS)))
    if not spec.MUTATIONS:
        # A spec with no mutations would mutate nothing, catch nothing, and exit 0.
        # That is the third instance of this defect class found in two days, this
        # time in the harness built to catch it, so it is pinned here rather than
        # trusted to reviewer attention.
        print("EMPTY SPEC: {} declares no mutations, so nothing was checked".format(name))
        return 2
    sweep_stale(target)

    # The unmutated copy must be green, or every "caught" below is meaningless.
    base = target.parent / "_mutant_baseline.py"
    try:
        base.write_text(original, encoding="utf-8")
        r = subprocess.run([sys.executable, str(base), *spec.ARGV],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=str(ROOT))
        print("baseline (unmutated copy): exit {}".format(r.returncode))
        if r.returncode != 0:
            print("ABORT: the copy is not green, so nothing below could be "
                  "attributed to a mutation")
            print((r.stdout or "")[-2000:])
            print((r.stderr or "")[-1000:])
            return 2
    finally:
        base.unlink(missing_ok=True)
    print()

    unguarded: list[str] = []
    crash_caught: list[str] = []
    applied = 0
    for i, (mname, meaning, find, repl) in enumerate(spec.MUTATIONS):
        n = original.count(find)
        if n != 1:
            # Not applied is not the same as not caught, and it is worse: the
            # pattern drifted, so this behaviour is now unmeasured while the
            # harness still prints a mostly green run.
            print("  [SKIP]     {}  <- pattern matches {} times, cannot target it"
                  .format(mname, n))
            unguarded.append("{} (pattern did not match; NOT applied)".format(mname))
            continue
        applied += 1
        p = target.parent / "_mutant_{}.py".format(i)
        try:
            p.write_text(original.replace(find, repl), encoding="utf-8")
            r = subprocess.run([sys.executable, str(p), *spec.ARGV],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", cwd=str(ROOT))
        finally:
            p.unlink(missing_ok=True)
        caught = r.returncode != 0
        caught_by = [l.strip()[7:] for l in (r.stdout or "").splitlines()
                     if l.strip().startswith("[FAIL]")]
        # A selftest that DIED is not the same evidence as a selftest that reported a
        # failing check. A crash exits nonzero for a reason nothing named, and it
        # also stops the run, so however many later checks existed went unmeasured
        # while this still prints as caught. Name it instead of blurring it.
        crashed = "Traceback (most recent call last)" in ((r.stderr or "") + (r.stdout or ""))
        print("  [{}] {}".format("caught  " if caught else "SURVIVED", mname))
        print("             regression: {}".format(meaning))
        if caught and caught_by:
            print("             caught by: {}".format(
                "; ".join(c.split("  <- ")[0] for c in caught_by[:3])))
        elif caught and crashed:
            print("             caught by: the selftest CRASHED, no check named it. "
                  "Nonzero, but later checks went unrun")
            crash_caught.append(mname)
        elif caught:
            print("             caught by: nonzero exit with no [FAIL] line and no "
                  "traceback. Confirm this is the intended reason")
            crash_caught.append(mname)
        else:
            print("             NOTHING FAILED. This behaviour is unguarded.")
            unguarded.append(mname)

    hard = [u for u in unguarded if "NOT applied" not in u]
    print()
    print("spec {}: {} of {} applied, {} caught, {} survived".format(
        name, applied, len(spec.MUTATIONS), applied - len(hard), len(hard)))
    for u in unguarded:
        print("UNGUARDED: " + u)
    # Not a failure: nonzero is still detection, and for some mutations (removing the
    # crash handler itself) a crash is the only possible signal. But it is weaker
    # evidence than a named check, so it is never left implicit.
    for c in crash_caught:
        print("WEAK SIGNAL: {} was caught without a named failing check".format(c))
    return 1 if unguarded else 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="mutate.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", default="all",
                    help="spec name, or 'all'. available: " + ", ".join(available_specs()))
    a = ap.parse_args()

    names = available_specs() if a.spec == "all" else [a.spec]
    unknown = [n for n in names if n not in available_specs()]
    if unknown:
        print("unknown spec(s): {}. available: {}".format(
            ", ".join(unknown), ", ".join(available_specs())))
        return 2
    if not names:
        # A run that mutates nothing must not report success. This is the same
        # defect class the specs themselves exist to catch.
        print("no mutation specs found under {}. Nothing was checked.".format(SPEC_DIR))
        return 2

    try:
        lock = acquire_lock()
    except Busy as e:
        print("REFUSING TO RUN: {}".format(e))
        return 2

    worst = 0
    try:
        for n in names:
            rc = run_spec(n)
            worst = max(worst, rc)
            print()
    finally:
        shutil.rmtree(lock, ignore_errors=True)
    if worst == 0:
        print("every mutation in {} spec(s) was applied and every one was caught: "
              "these selftests can fail, and do".format(len(names)))
    return worst


if __name__ == "__main__":
    sys.exit(main())
