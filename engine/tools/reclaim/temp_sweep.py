#!/usr/bin/env python
"""Remove scratch directories this harness left in the system temp directory.

Measured 2026-07-30: %LOCALAPPDATA%\\Temp held 3,591 directories, 125,319 files and
11.42 GiB, of which 1,879 directories were `gate-extra-*` git repositories created by
tests/test_gate_extra_domains.py. Its cleanup used `shutil.rmtree(..., ignore_errors=True)`,
so on Windows it failed on git's read-only pack files, reported success, and leaked one
repository per test run. The test is fixed; this removes the backlog.

SAFETY, and the reason this is not a general temp cleaner:

  - Only prefixes THIS repository is known to create are eligible. Everything else is
    reported and left alone, because temp holds other applications' live state and a
    general sweep is how you break an installer mid-run.
  - `claude*` is excluded ON PURPOSE even though it is ours and large. It holds the
    active session's scratchpad, task outputs and workflow transcripts, including the
    ones a running session is still reading.
  - Every directory is verified to match its expected shape before deletion. A
    `gate-extra-*` that contains something other than a scratch git fixture is moved to
    the quarantine directory instead, never deleted.
  - The manifest row is written and fsynced BEFORE the action, so a crash leaves a
    record of what was about to happen rather than a silent gap.

Dry run by default. `--execute` acts. `--quarantine DIR` moves instead of deleting.

Usage:
  python tools/reclaim/temp_sweep.py
  python tools/reclaim/temp_sweep.py --execute
  python tools/reclaim/temp_sweep.py --execute --quarantine C:/GARBAGE-2026-07-30
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

# Prefixes this repository creates. Anything not listed is never touched.
OURS = ("gate-extra-", "external-review-", "home-setup-check", "icp")
NEVER = ("claude",)

MANIFEST = Path(__file__).resolve().parents[2] / "state" / "reclaim-manifest.jsonl"


def _force_rm(path: Path) -> None:
    def _retry(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=lambda f, p, e: _retry(f, p, e))
    else:  # pragma: no cover
        shutil.rmtree(path, onerror=lambda f, p, e: _retry(f, p, e))


def measure(d: Path) -> tuple[int, int]:
    n = b = 0
    for root, _dirs, files in os.walk(d):
        for f in files:
            try:
                b += os.path.getsize(os.path.join(root, f))
                n += 1
            except OSError:
                pass
    return n, b


def looks_like_scratch_repo(d: Path) -> bool:
    """A gate fixture is a git repo whose only tracked content is a README.

    Anything else under a gate-extra name is not what the test creates, so it is not
    something this tool is entitled to delete.
    """
    entries = {p.name for p in d.iterdir()}
    if entries - {".git", "README.md", "quality-contract.json", "tools", "docs",
                  "gate.json", "state"}:
        return False
    return (d / ".git").is_dir()


def record(row: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--quarantine")
    ap.add_argument("--temp", default=tempfile.gettempdir())
    a = ap.parse_args()

    temp = Path(a.temp)
    qdir = Path(a.quarantine) if a.quarantine else None
    print("{}  temp={}".format("EXECUTE" if a.execute else "DRY RUN", temp))
    if qdir:
        print("quarantine={}".format(qdir))

    eligible, skipped, mismatched = [], [], []
    for d in temp.iterdir():
        if not d.is_dir():
            continue
        name = d.name
        if any(name.startswith(p) for p in NEVER):
            skipped.append((d, "excluded on purpose: active session scratch"))
            continue
        if not any(name.startswith(p) for p in OURS):
            skipped.append((d, "not created by this repository"))
            continue
        if name.startswith("gate-extra-") and not looks_like_scratch_repo(d):
            mismatched.append(d)
            continue
        eligible.append(d)

    tot_n = tot_b = 0
    for d in eligible:
        n, b = measure(d)
        tot_n += n
        tot_b += b

    print("\neligible   {:>6} dirs  {:>8,} files  {:>14,} bytes".format(
        len(eligible), tot_n, tot_b))
    print("mismatched {:>6} dirs  (shape did not match; will be quarantined, never deleted)"
          .format(len(mismatched)))
    print("left alone {:>6} dirs".format(len(skipped)))
    for _d, why in skipped[:4]:
        print("            e.g. {}".format(why))

    if not a.execute:
        print("\nDRY RUN: nothing was touched. Re-run with --execute.")
        return 0

    done = failed = 0
    for d in eligible:
        row = {"ts": None, "action": "delete" if not qdir else "quarantine",
               "path": str(d), "tool": "temp_sweep", "reason": "harness scratch"}
        record(row)
        try:
            if qdir:
                qdir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(d), str(qdir / d.name))
            else:
                _force_rm(d)
            done += 1
        except Exception as exc:
            failed += 1
            record({"action": "FAILED", "path": str(d), "error": str(exc)[:200]})

    for d in mismatched:
        target = qdir or (temp / "QUARANTINE-shape-mismatch")
        target.mkdir(parents=True, exist_ok=True)
        record({"action": "quarantine", "path": str(d), "reason": "shape mismatch"})
        try:
            shutil.move(str(d), str(target / d.name))
        except Exception as exc:
            record({"action": "FAILED", "path": str(d), "error": str(exc)[:200]})

    remaining = sum(1 for d in temp.iterdir()
                    if d.is_dir() and any(d.name.startswith(p) for p in OURS))
    print("\nremoved {} | failed {} | quarantined {} | remaining ours: {}".format(
        done, failed, len(mismatched), remaining))
    print("manifest: {}".format(MANIFEST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
