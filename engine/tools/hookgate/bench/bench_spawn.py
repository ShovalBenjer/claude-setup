"""Spawn-cost benchmark using native CreateProcess, not MSYS fork emulation.

The earlier numbers in this session were taken through Git Bash, which routes process
creation through MSYS2's fork emulation. Claude Code spawns hooks from Node via
CreateProcess directly, so that layer was an artefact of the measuring instrument.
This driver uses subprocess from CPython, which is CreateProcess, and reports median
and min rather than mean because spawn distributions have a long right tail (Defender,
scheduler) and the min is the closest thing to the floor.
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOKS = Path.home() / ".claude" / "hooks"
RUST = HERE / "hookclient" / "target" / "release" / "hookclient.exe"

PAYLOAD = (
    b'{"tool_name":"Bash","tool_input":{"command":"echo hello"},'
    b'"cwd":"C:\\\\Users\\\\shova\\\\claude-setup"}'
)

CANDIDATES: list[tuple[str, list[str]]] = [
    ("rust hookclient.exe (noop)", [str(RUST)]),
    ("python -S -E -c pass", [sys.executable, "-S", "-E", "-c", "pass"]),
    ("python -c pass", [sys.executable, "-c", "pass"]),
    ("python -S -E merged_gate.py", [sys.executable, "-S", "-E", str(HERE / "merged_gate.py")]),
    ("python safety_gate.py", [sys.executable, str(HOOKS / "safety_gate.py")]),
    ("python pre_push_gate.py", [sys.executable, str(HOOKS / "pre_push_gate.py")]),
]

WARMUP = 20
RUNS = 200


def bench(argv: list[str]) -> list[float]:
    samples: list[float] = []
    for _ in range(WARMUP):
        subprocess.run(argv, input=PAYLOAD, capture_output=True)
    for _ in range(RUNS):
        t0 = time.perf_counter()
        subprocess.run(argv, input=PAYLOAD, capture_output=True)
        samples.append((time.perf_counter() - t0) * 1000.0)
    return samples


def main() -> int:
    if not RUST.exists():
        print("rust client missing at {}".format(RUST))
    print("{} warmup + {} runs each, native CreateProcess\n".format(WARMUP, RUNS))
    print("{:<32} {:>9} {:>9} {:>9} {:>9}".format("candidate", "median", "min", "p90", "mean"))
    print("-" * 72)
    rows = []
    for label, argv in CANDIDATES:
        if argv[0].endswith(".exe") and not Path(argv[0]).exists():
            print("{:<32} {:>9}".format(label, "SKIP"))
            continue
        s = sorted(bench(argv))
        med = statistics.median(s)
        rows.append((label, med, s[0]))
        print("{:<32} {:>8.2f}ms {:>8.2f}ms {:>8.2f}ms {:>8.2f}ms".format(
            label, med, s[0], s[int(len(s) * 0.9)], statistics.fmean(s)))
    print()
    if rows:
        base = next((m for lbl, m, _ in rows if lbl.startswith("rust")), None)
        if base:
            print("ratio against the rust floor (median):")
            for label, med, _ in rows:
                print("  {:<34} {:.1f}x".format(label, med / base))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
