"""Concurrent-session guard for shared-HOME destructive/git-hygiene ops.

HOME doubles as a git worktree of a shared codebase, and multiple Claude/Codex
sessions run in parallel there. A destructive git-hygiene command (worktree
prune, branch -D, clean -f, reset --hard, force-push, or a raw rm/mv on
.git) run by one session can silently break another session's in-flight
work. This module is the pure decision core: classify a command string as
destructive-in-this-context, then decide whether to allow it given how many
other live sessions exist and whether the caller explicitly overrode the gate.

The one impure bit (counting other live sessions via pgrep) is isolated in
`_live_other_sessions` so the decision logic itself stays unit-testable with
plain injected integers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

DESTRUCTIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"git\s+worktree\s+(prune|add|remove|move)\b"),
    re.compile(r"git\s+branch\s+-[dD]\b"),
    re.compile(r"git\s+clean\s+-f\w*"),
    re.compile(r"git\s+reset\s+--hard\b"),
    re.compile(r"git\s+checkout\s+--\s+\.(\s|$)"),
    re.compile(r"rm\s+-rf\s+~?/?\.git\b"),
    re.compile(r"\bmv\b.*~/\.git\b"),
    re.compile(r"git\s+push\s+.*(--force\b|-f\b)"),
]


def classify(cmd: str) -> bool:
    """Return True if cmd is a shared-HOME destructive/git-hygiene op."""
    return any(pattern.search(cmd) is not None for pattern in DESTRUCTIVE_PATTERNS)


def guard_decision(cmd: str, other_sessions: int, override: bool) -> dict[str, object]:
    """Decide whether cmd may run, given other live sessions and an override flag.

    Rule: non-destructive commands always pass. Destructive commands pass if
    explicitly overridden, or if no other session is live; otherwise deny and
    name the number of other live sessions in the reason.
    """
    if not classify(cmd):
        return {"allow": True, "reason": "not a shared-HOME destructive op"}
    if override:
        return {"allow": True, "reason": "allowed: explicit override set for destructive op"}
    if other_sessions > 0:
        return {
            "allow": False,
            "reason": (
                f"denied: {other_sessions} other live session(s) detected; "
                "destructive shared-HOME op blocked without override"
            ),
        }
    return {"allow": True, "reason": "allowed: no other live sessions detected"}


def decide(command: str, detected: int | None, override: bool) -> dict[str, object]:
    """Decide allow/deny given a (possibly failed) other-session count.

    `detected` is the number of other live sessions, or None if detection could
    not run at all. Non-destructive commands always pass. For a destructive
    command with detection unavailable (None), fail SAFE: deny unless overridden
    (a false block is annoying but overridable; a false allow is a collision).
    Otherwise defer to `guard_decision` with the detected count.
    """
    if not classify(command):
        return {"allow": True, "reason": "not a shared-HOME destructive op"}
    if detected is None:
        if override:
            return {"allow": True, "reason": "allowed: session detection unavailable, override set"}
        return {
            "allow": False,
            "reason": (
                "denied: session detection unavailable; blocking destructive "
                "shared-HOME op conservatively (set SESSION_GUARD_OVERRIDE=1 to proceed)"
            ),
        }
    return guard_decision(command, detected, override)


def _process_parents(ps_lines: list[str]) -> dict[int, int]:
    """Pure: parse `ps -eo pid=,ppid=` output into a {pid: ppid} map.

    Any line that is not exactly two integers is skipped.
    """
    parents: dict[int, int] = {}
    for raw in ps_lines:
        parts = raw.split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        parents[int(parts[0])] = int(parts[1])
    return parents


def _ancestor_pids(start_pid: int, parent_of: dict[int, int]) -> set[int]:
    """Pure: the ancestor pids of start_pid (exclusive), walking up parent_of.

    Stops at pid <= 1, an unknown pid, the start pid, or a cycle.
    """
    ancestors: set[int] = set()
    cur = parent_of.get(start_pid)
    while cur is not None and cur > 1 and cur != start_pid and cur not in ancestors:
        ancestors.add(cur)
        cur = parent_of.get(cur)
    return ancestors


def _count_other_sessions(entries: list[tuple[int, str]], exclude_pids: set[int]) -> int:
    """Pure: count distinct claude/codex processes that are NOT the caller's own.

    entries are (pid, cmdline); exclude_pids is the caller's own pid plus its full
    ancestor chain (its claude main process, node, and shells). A process counts
    if its cmdline mentions 'claude' or 'codex' (case-insensitive), it is not the
    pgrep invocation, and its pid is not in exclude_pids. Exclusion is by ancestor
    LINEAGE, not POSIX session id: a sibling session launched from the same
    terminal shares the caller's session id but is not in the caller's ancestor
    chain, so it is correctly counted (an under-count would let a concurrent
    session bypass the guard). The caller's own live descendants (subagents it
    spawned) are counted too, which over-counts during the caller's own fan-out,
    but that is the fail-safe direction (block, do not allow).
    """
    pids: set[int] = set()
    for pid, cmdline in entries:
        low = cmdline.lower()
        if "pgrep" in low:
            continue
        if "claude" not in low and "codex" not in low:
            continue
        if pid in exclude_pids:
            continue
        pids.add(pid)
    return len(pids)


def _detection_result(
    entries: list[tuple[int, str]], exclude_pids: set[int], any_probe_failed: bool
) -> int | None:
    """Pure: the other-session count, or None if any probe failed.

    Detection is trusted only when every pgrep probe ran. If any probe failed the
    picture is incomplete, so return None and let the caller fail safe (block)
    rather than risk an under-count that misses live sessions for the failed
    pattern.
    """
    if any_probe_failed:
        return None
    return _count_other_sessions(entries, exclude_pids)


def _probe_failed(returncode: int) -> bool:
    """Pure: True if a pgrep return code signals an error, not an empty result.

    pgrep exits 0 when it found matches and 1 when it found none (both are
    successful probes); 2 (usage) and 3 (fatal, e.g. cannot read /proc) mean the
    probe itself failed and its emptiness must not be trusted as 'no sessions'.
    """
    return returncode not in (0, 1)


def _read_process_parents() -> dict[int, int] | None:
    """Impure: read the whole process table's pid->ppid map via `ps`.

    Returns None on any failure (ps missing, timeout, empty) so the caller can
    fail safe rather than proceed without a lineage to exclude.
    """
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid=,ppid="],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    return _process_parents(result.stdout.splitlines()) or None


def _live_other_sessions() -> int | None:
    """Count live claude/codex processes outside the caller's own lineage.

    Returns the number of OTHER processes, or None if detection could not run at
    all (no process table, or every pgrep probe failed), so the caller can fail
    safe rather than assume zero. Builds the caller's exclusion set from its own
    pid plus its full ancestor chain (its claude main, node, and shells) via the
    process table, then runs `pgrep -af` (full command line, since Claude Code
    runs under `node`) for 'claude' and 'codex'. Excluding by ancestor LINEAGE,
    not POSIX session id, means a sibling session sharing this terminal's session
    is still counted. Detection is trusted only if EVERY probe ran: if any probe
    fails the result is None (the caller fails safe), because a partial result
    could miss live sessions for the failed pattern.
    """
    parent_of = _read_process_parents()
    if parent_of is None:
        return None
    own_pid = os.getpid()
    exclude = {own_pid} | _ancestor_pids(own_pid, parent_of)
    entries: list[tuple[int, str]] = []
    seen: set[int] = set()
    any_probe_failed = False
    for pattern in ("claude", "codex"):
        try:
            result = subprocess.run(
                ["pgrep", "-af", pattern],
                capture_output=True,
                text=True,
                timeout=2,
            )
        except Exception:
            any_probe_failed = True
            continue
        if _probe_failed(result.returncode):
            any_probe_failed = True
            continue
        for raw in result.stdout.splitlines():
            line = raw.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if not parts[0].isdigit():
                continue
            pid = int(parts[0])
            if pid in seen:
                continue
            seen.add(pid)
            cmdline = parts[1] if len(parts) > 1 else ""
            entries.append((pid, cmdline))
    return _detection_result(entries, exclude, any_probe_failed)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the PreToolUse hook shim.

    Fast path: non-destructive commands never shell out to pgrep. Only a
    classified destructive command pays the cost of live-session detection.
    Exit 0 on allow, 2 on deny (distinct from other CLI failure modes in
    this repo, which is enough for a hook shim to branch on).
    """
    parser = argparse.ArgumentParser(prog="session-guard")
    parser.add_argument("--command", required=True)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    command: str = args.command

    if not classify(command):
        print(json.dumps({"allow": True, "reason": "not a shared-repo destructive op"}))
        return 0

    override = os.environ.get("SESSION_GUARD_OVERRIDE") == "1"
    detected = _live_other_sessions()
    decision = decide(command, detected, override)
    print(json.dumps(decision))
    return 0 if decision["allow"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
