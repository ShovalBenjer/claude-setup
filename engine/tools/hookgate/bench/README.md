# bench

The measurement scripts behind `tools/hookgate/README.md` and behind
`docs/archive/HANDOFF-TO-LEARNING-2026-07-30-process-cost-and-boundaries.md`.

Landed here because the handoff cites them as reproducible lab material and they were
written in a session scratchpad, which does not survive the session. They are evidence, not
production tooling, and nothing in the gate imports them.

| script | question it answers | where it runs |
|---|---|---|
| `bench3.py` | What does an empty `main()` cost in Zig, Rust, and Go against Python? Needs the noop binaries built first. | Windows |
| `bench_spawn.py` | Same, for the real hook candidates, via native `CreateProcess` rather than through the MSYS layer. | Windows |
| `bench_fs.sh` | What does crossing `/mnt/c` cost against native ext4, on a real 5,763-file git repo? | inside WSL2 |
| `wslbench.py` | What is the compiled-binary spawn floor on Linux? Uses `/bin/true` as the floor proxy. | inside WSL2 |
| `fetch_audit.sh` | Which repositories actually have unpushed work, measured after a real `fetch` rather than off stale remote-tracking refs? | Windows |

Two methodological notes that the numbers depend on, both learned the hard way in the
session that produced them.

**Measure through the path the real caller uses.** An early run put Python startup at 106 ms.
The same binary measured 44 ms via native `CreateProcess`. The difference was Git Bash's
`fork` emulation, which the actual hook caller does not go through. `bench_spawn.py` and
`bench3.py` therefore drive `subprocess` from CPython rather than looping in shell.

**Report median and minimum.** Process-spawn distributions have a long right tail from
antivirus scan-on-execute and scheduler preemption, so the mean overstates steady-state cost.
Absolute figures on this machine drift up to about 25% between runs; the orderings did not
change across any run.

`bench_fs.sh` copies a 673 MB tree across the 9p boundary and took 131 seconds to do it.
That is expected, and it is part of what the script is demonstrating.
