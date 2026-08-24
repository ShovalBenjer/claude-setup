#!/usr/bin/env python3
"""Live global config still matches the recorded baseline.

Why this exists, precisely: on 2026-07-25 at 00:44:42 another parallel session
rewrote BOTH ~/.claude/CLAUDE.md and ~/.claude/settings.json in the same second.
This session kept reasoning from the CLAUDE.md text injected at its start, which
no longer existed on disk. It nearly "corrected" a verifier that was right, to
agree with instructions that were gone. Six-plus concurrent sessions is the normal
operating mode here, so silent cross-session rewrites are not an edge case.

Drift is not automatically bad; unnoticed drift is. This makes the rewrite visible.

    python config_drift.py            check live files against the baseline
    python config_drift.py --record   accept current state as the new baseline

--record is deliberately a separate human act. A checker that writes its own
baseline when none exists would pass on first run having verified nothing, which
is the same vacuous-pass failure that made hooks_exist.py useless.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "state" / "config-baseline.json"

WATCHED = {
    "CLAUDE.md": HOME / ".claude" / "CLAUDE.md",
    "settings.json": HOME / ".claude" / "settings.json",
}


def fingerprint() -> dict[str, dict]:
    out = {}
    for name, path in WATCHED.items():
        if not path.exists():
            out[name] = {"present": False}
            continue
        raw = path.read_bytes()
        out[name] = {
            "present": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "mtime": dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        }
    return out


def record() -> int:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    snap = {
        "recorded": dt.datetime.now().isoformat(timespec="seconds"),
        "files": fingerprint(),
    }
    BASELINE.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    print(f"baseline recorded at {BASELINE}")
    for name, f in snap["files"].items():
        print(f"  {name}: {f.get('sha256', 'ABSENT')[:12]} "
              f"{f.get('bytes', 0)}b mtime={f.get('mtime', '-')}")
    return 0


def main(argv: list[str]) -> int:
    if "--record" in argv:
        return record()

    if not BASELINE.exists():
        print(f"no config baseline at {BASELINE}: run --record to establish one. "
              f"Until then config drift is UNKNOWN, not clean.")
        return 1

    try:
        snap = json.loads(BASELINE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"baseline is unreadable: {e}")
        return 1

    old = snap.get("files") or {}
    new = fingerprint()
    drift: list[str] = []

    for name in WATCHED:
        o, n = old.get(name), new.get(name)
        if o is None:
            drift.append(f"{name}: not in baseline (baseline is stale)")
            continue
        if o.get("present") and not n.get("present"):
            drift.append(f"{name}: DELETED since baseline")
            continue
        if not o.get("present") and n.get("present"):
            drift.append(f"{name}: CREATED since baseline")
            continue
        if o.get("sha256") != n.get("sha256"):
            drift.append(
                f"{name}: REWRITTEN since baseline "
                f"({o.get('bytes')}b -> {n.get('bytes')}b, "
                f"now mtime={n.get('mtime')}, baseline taken {snap.get('recorded')})")

    if drift:
        print(f"{len(drift)} config file(s) changed under this session:")
        for d in drift:
            print(f"  {d}")
        print("re-read them from disk before trusting injected context, "
              "then --record to accept.")
        return 1

    print(f"{len(WATCHED)} watched config files match the baseline "
          f"recorded {snap.get('recorded')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
