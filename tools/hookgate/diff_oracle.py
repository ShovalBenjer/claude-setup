"""Differential oracle: does the Rust gate decide exactly what the Python gate decides?

This is the only thing that establishes the port is faithful. The Rust patterns are
generated copies of the Python ones, which removes transcription error but says nothing
about whether fancy-regex and Python's `re` AGREE on those patterns. They are different
engines with different lookaround semantics, different handling of `$` under DOTALL, and
different Unicode word-boundary rules. Byte-identical patterns are necessary and not
sufficient.

Both sides answer the same question for each command: the index of the FIRST rule that
matches, or -1. Any disagreement is a defect in the port, and a disagreement where
Python blocks and Rust does not is a security regression, so the two directions are
reported separately rather than as one count.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

S = Path(__file__).resolve().parent
HOOKS = Path.home() / ".claude" / "hooks"
# Resolved live-first with a repo fallback, which is exactly what regen_rules.py
# already does at its own SAFETY_GATE/FALLBACK pair. Until 2026-08-10 this file
# named only the live path and raised FileNotFoundError on any host without a
# deployed ~/.claude, so the one oracle that establishes the Rust port is
# faithful could not run on a CI runner or in a container at all. Third instance
# of the host-shaped class in one day, after skills_sync and refute.
SAFETY_GATE_LIVE = HOOKS / "safety_gate.py"
SAFETY_GATE_REPO = S.parents[1] / "dot-claude" / "hooks" / "safety_gate.py"
# The binary may be a Windows or a Linux build, and may live in this crate's own target/
# dir or be overridden. Checked in order; absent means the oracle SKIPS rather than passes,
# because "no binary" must never read as "the port agrees".
_CANDIDATES = [
    S / "target" / "release" / "hookgate.exe",
    S / "target" / "release" / "hookgate",
    S / "target" / "x86_64-unknown-linux-gnu" / "release" / "hookgate",
]
import os as _os
_env = _os.environ.get("HOOKGATE_BIN")
RUST = Path(_env) if _env else next((c for c in _CANDIDATES if c.exists()), _CANDIDATES[0])
CORPUS = S / "corpus.txt"


def resolve_safety_gate() -> Path:
    """Live copy if there is one, else the committed copy. Never neither."""
    if SAFETY_GATE_LIVE.exists():
        return SAFETY_GATE_LIVE
    if SAFETY_GATE_REPO.exists():
        return SAFETY_GATE_REPO
    raise SystemExit("no safety_gate.py at {} or {}".format(
        SAFETY_GATE_LIVE, SAFETY_GATE_REPO))


def load_python_rules(path: Path | None = None):
    spec = importlib.util.spec_from_file_location("sg", path or resolve_safety_gate())
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sg"] = mod
    spec.loader.exec_module(mod)
    return mod.RULES


def main() -> int:
    if not RUST.exists():
        print("SKIP: no hookgate binary at {}. Build it first:".format(RUST))
        print("  cd tools/hookgate && cargo build --release")
        return 77
    # Naming the resolved source is not decoration. On 2026-08-05 rules.rs was
    # found to have been generated from a file that was not the committed one,
    # and the whole incident turns on WHICH copy of safety_gate.py a run
    # compared against. A verdict that does not say which side it read is a
    # verdict about an unknown tree.
    source = resolve_safety_gate()
    print("python rules from: {} ({})".format(
        source, "live" if source == SAFETY_GATE_LIVE else "repo, no live tree here"))
    rules = load_python_rules(source)
    commands = [c for c in CORPUS.read_text(encoding="utf-8").splitlines() if c.strip()]

    py = []
    for cmd in commands:
        idx = -1
        for i, (pat, _reason) in enumerate(rules):
            if pat.search(cmd):
                idx = i
                break
        py.append(idx)

    proc = subprocess.run(
        [str(RUST), "--diff-mode"],
        input="\n".join(commands).encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        print("rust gate failed:", proc.stderr.decode("utf-8", "replace"))
        return 1
    if proc.stderr:
        print("rust stderr:", proc.stderr.decode("utf-8", "replace")[:2000])
    rs = [int(x) for x in proc.stdout.decode("utf-8").split()]

    if len(rs) != len(py):
        print("LENGTH MISMATCH: python {} vs rust {}".format(len(py), len(rs)))
        return 1

    security_regressions = []   # python blocks, rust does not: the dangerous direction
    false_positives = []        # rust blocks, python does not
    different_rule = []         # both block, different rule index

    for cmd, p, r in zip(commands, py, rs):
        if p == r:
            continue
        if p >= 0 and r < 0:
            security_regressions.append((cmd, p, r))
        elif p < 0 and r >= 0:
            false_positives.append((cmd, p, r))
        else:
            different_rule.append((cmd, p, r))

    blocked_py = sum(1 for x in py if x >= 0)
    blocked_rs = sum(1 for x in rs if x >= 0)
    print("corpus: {} commands".format(len(commands)))
    print("python blocks {}, rust blocks {}".format(blocked_py, blocked_rs))
    print()

    def dump(title, rows):
        print("{}: {}".format(title, len(rows)))
        for cmd, p, r in rows[:25]:
            print("   py={:>3} rs={:>3}  {}".format(p, r, cmd))

    dump("SECURITY REGRESSIONS (python blocks, rust allows)", security_regressions)
    dump("false positives (rust blocks, python allows)", false_positives)
    dump("different rule fired", different_rule)

    total = len(security_regressions) + len(false_positives) + len(different_rule)
    print()
    if total == 0:
        print("AGREEMENT: exact, on all {} commands".format(len(commands)))
        return 0
    print("DISAGREEMENTS: {}".format(total))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
