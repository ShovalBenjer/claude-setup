"""Rust vs Go vs Zig vs Python: process spawn cost on Windows, native CreateProcess.

Empty main() in all three compiled languages, so the measurement isolates
CreateProcess + language runtime init + exit. That is the term under debate; the
stdin read the real hook needs is microseconds and identical across all of them.

Reported as median and min. Spawn distributions on Windows have a long right tail
(Defender, scheduler preemption), so the mean overstates the steady-state cost and
the min is the closest available estimate of the floor.
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import time
from pathlib import Path

S = Path(__file__).resolve().parent
HOOKS = Path.home() / ".claude" / "hooks"

CANDIDATES = [
    ("zig   (empty main)", [str(S / "noop_zig" / "noop_zig.exe")]),
    ("rust  (empty main)", [str(S / "noop_rust" / "target" / "release" / "noop_rust.exe")]),
    ("go    (empty main)", [str(S / "noop_go" / "noop_go.exe")]),
    ("rust  (full client)", [str(S / "hookclient" / "target" / "release" / "hookclient.exe")]),
    ("go    (full client)", [str(S / "goclient" / "hookclient_go.exe")]),
    ("python -S -E -c pass", [sys.executable, "-S", "-E", "-c", "pass"]),
    ("python -c pass", [sys.executable, "-c", "pass"]),
    ("python -S -E merged_gate", [sys.executable, "-S", "-E", str(S / "merged_gate.py")]),
    ("python safety_gate.py", [sys.executable, str(HOOKS / "safety_gate.py")]),
]

WARMUP = 30
RUNS = 300


def main() -> int:
    print("{} warmup + {} runs each, native CreateProcess, stdin=DEVNULL\n".format(WARMUP, RUNS))
    print("{:<28}{:>10}{:>10}{:>10}{:>9}".format("candidate", "median", "min", "p90", "size"))
    print("-" * 67)
    rows = []
    for label, argv in CANDIDATES:
        exe = Path(argv[0])
        if not exe.exists():
            print("{:<28}{:>10}".format(label, "MISSING"))
            continue
        target = Path(argv[-1]) if argv[-1].endswith((".py", ".exe")) else exe
        size = target.stat().st_size if target.exists() else 0
        for _ in range(WARMUP):
            subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True)
        s = []
        for _ in range(RUNS):
            t0 = time.perf_counter()
            subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True)
            s.append((time.perf_counter() - t0) * 1000.0)
        s.sort()
        med = statistics.median(s)
        rows.append((label, med, s[0]))
        print("{:<28}{:>8.2f}ms{:>8.2f}ms{:>8.2f}ms{:>8.0f}K".format(
            label, med, s[0], s[int(RUNS * 0.9)], size / 1024))
    print()
    if rows:
        base = min(m for _, m, _ in rows)
        print("ratio against the fastest measured (median {:.2f}ms):".format(base))
        for label, med, _ in rows:
            print("  {:<28} {:6.2f}x".format(label, med / base))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
