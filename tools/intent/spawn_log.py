#!/usr/bin/env python3
"""Record every subagent spawn, and whether it followed the route.

THE NUMBER THIS EXISTS TO MOVE.

Measured 2026-08-05 across 66 transcripts in `~/.claude/projects/`: **0 of 19 company
personas has ever been spawned.** Every delegation went to `general-purpose` (23) or
`Explore` (5). The registry defines 19 personas owning 99 skills and says Mayor Opus
classifies the task and selects them; nothing in the estate could tell you that had never
happened, because nothing recorded a spawn at all.

`state/skill-use.jsonl` looks like it should cover this and structurally cannot. It is
written by a `PostToolUse` hook with `matcher: Skill`, so it fires for the Skill tool and
never for the Agent tool. Counting skills and counting delegations are different
questions, and only one of them had an answer.

WHY THIS LOGS A COMPARISON RATHER THAN AN EVENT.

`tools/intent/route.py` already names a persona on every matching prompt and appends it to
`state/routing.jsonl`. So at spawn time there are two facts available: what the router
said this work belonged to, and what the model actually delegated to. Logging only the
second gives a count. Logging both gives the question worth asking, which is whether
routing changes behaviour or is merely decorative.

That distinction matters because the honest answer might be no. A router that names a
persona which nobody ever spawns is the same class of artifact as the agent feed that
posted 146 lines to zero readers, and this repo has now built three message surfaces and
used one. `agreed` is the field that would show it, and it is allowed to come out false.

WHAT IS DELIBERATELY NOT HERE.

No judgement of whether the spawn went well, for the same reason `skill-usage-log.sh`
refuses it: a hook that scored its own invocation would be the self-congratulation failure
mode. Outcome is joined later from `gate-runs.jsonl` and `refutations.jsonl`.

    echo '{"tool_name":"Agent","tool_input":{"subagent_type":"qa-lab"}}' | python3 spawn_log.py
    python3 tools/intent/spawn_log.py --report
    python3 tools/intent/spawn_log.py --selftest
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO = Path(os.environ.get("CLAUDE_OS_DIR", str(Path.home() / "claude-setup"))).expanduser()
LEDGER = REPO / "state" / "agent-spawns.jsonl"
ROUTING = REPO / "state" / "routing.jsonl"
AGENTS_DIR = Path.home() / ".claude" / "agents"

# The two Claude Code builtins. Everything else is either a company persona or a
# project-specific agent, and the distinction is the whole measurement.
BUILTINS = {"general-purpose", "Explore", "Plan", "claude", "statusline-setup"}


# Words the agent filenames drop from a persona heading. Measured, not guessed: three of
# the 19 personas are named "X and Y Office" in the registry and `x-y-office.md` on disk.
# Without this, `MCP and Tooling Office` slugs to `mcp-and-tooling-office`, no file
# matches, and `agreed` can never be true for those three no matter what is spawned.
_DROPPED = {"and"}


def slug(persona: str) -> str:
    """`QA Lab` -> `qa-lab`, matching the filenames in ~/.claude/agents/.

    The registry writes personas as prose headings and the Agent tool takes a
    subagent_type that must match a filename. Nothing in the estate declares that mapping,
    so it is derived here rather than duplicated as a table that could disagree with the
    directory. The derivation is verified against the real directory in selftest, which is
    how the dropped-`and` case was found: it was written naively first and three personas
    silently could not be matched.
    """
    return "-".join(w for w in persona.lower().split() if w not in _DROPPED)


def known_personas() -> set[str]:
    """subagent_type values that resolve to a real agent definition file.

    Read from disk rather than from the registry, because the registry is a claim about
    ownership and the directory is the thing the Agent tool actually resolves against.
    They disagree today: 4 agent files have no registry entry.
    """
    try:
        return {p.stem for p in AGENTS_DIR.glob("*.md")}
    except OSError:
        return set()


def last_route(session: str) -> dict:
    """The most recent routing decision, preferring the same session.

    Falls back to the newest row of any session rather than to nothing, because
    CLAUDE_SESSION_ID is not exported into hook env on this host (PERSONA-08), so
    same-session matching would silently never fire and every spawn would look unrouted.
    The fallback is recorded in the row as `route_match` so a reader can tell a real join
    from a best-effort one.
    """
    try:
        rows = [json.loads(l) for l in ROUTING.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, json.JSONDecodeError):
        return {}
    if not rows:
        return {}
    if session:
        same = [r for r in rows if r.get("session") == session]
        if same:
            return dict(same[-1], route_match="session")
    return dict(rows[-1], route_match="latest-any-session")


def build_row(payload: dict, personas: set[str], route: dict) -> dict | None:
    """The recorded comparison. Returns None for a call that is not an Agent spawn."""
    tool = payload.get("tool_name", "")
    inp = payload.get("tool_input") or {}
    subagent = str(inp.get("subagent_type") or "").strip()
    if tool != "Agent" and not subagent:
        return None
    # An Agent call with no subagent_type is the DEFAULT, which is general-purpose. That
    # is the single most important row to record: it is what all 28 measured delegations
    # were, and dropping it would erase the very number this file exists to move.
    if not subagent:
        subagent = "general-purpose"

    routed = (route.get("personas") or [None])[0]
    routed_slug = slug(routed) if routed else ""
    cwd = payload.get("cwd") or os.getcwd()
    return {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "subagent_type": subagent,
        "is_builtin": subagent in BUILTINS,
        "is_known_agent": subagent in personas,
        "routed_persona": routed or "",
        "routed_slug": routed_slug,
        "agreed": bool(routed_slug) and routed_slug == subagent,
        "route_match": route.get("route_match", "none"),
        "description": str(inp.get("description") or "")[:160],
        "session": payload.get("session_id", ""),
        "project": os.path.basename(str(cwd).rstrip("/\\")) or "unknown",
        # Absent on purpose: any judgement of how the spawn went. Joined later from
        # gate-runs.jsonl and refutations.jsonl, never scored by the thing being measured.
        "outcome": None,
    }


def report() -> int:
    try:
        rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, json.JSONDecodeError):
        rows = []
    if not rows:
        print("no spawns recorded yet at {}".format(LEDGER))
        return 0
    builtin = sum(1 for r in rows if r.get("is_builtin"))
    persona = len(rows) - builtin
    agreed = sum(1 for r in rows if r.get("agreed"))
    routed = sum(1 for r in rows if r.get("routed_slug"))
    print("{} spawn(s): {} to a builtin, {} to a company persona".format(
        len(rows), builtin, persona))
    print("{} had a routing decision available; {} of those matched it".format(routed, agreed))
    seen: dict[str, int] = {}
    for r in rows:
        seen[r["subagent_type"]] = seen.get(r["subagent_type"], 0) + 1
    for k in sorted(seen, key=lambda x: -seen[x]):
        print("  {:<28} {}".format(k, seen[k]))
    return 0


def selftest() -> int:
    failures = []
    personas = {"qa-lab", "review-board", "mayor-opus"}

    r = build_row({"tool_name": "Agent", "tool_input": {"subagent_type": "qa-lab"},
                   "cwd": "/x/claude-setup"}, personas,
                  {"personas": ["QA Lab"], "route_match": "session"})
    if not r or not r["agreed"]:
        failures.append("a spawn matching the routed persona was not recorded as agreed")
    if not r["is_known_agent"] or r["is_builtin"]:
        failures.append("a company persona was classified as a builtin or as unknown")

    d = build_row({"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose"}},
                  personas, {"personas": ["QA Lab"], "route_match": "session"})
    if d["agreed"]:
        failures.append("a general-purpose spawn against a QA Lab route reported as "
                        "agreed, which would hide the exact gap being measured")
    if not d["is_builtin"]:
        failures.append("general-purpose was not classified as a builtin")

    # The default. All 28 measured delegations had no explicit subagent_type, and losing
    # them would erase the number this file exists to move.
    dflt = build_row({"tool_name": "Agent", "tool_input": {"description": "x"}}, personas, {})
    if dflt is None:
        failures.append("an Agent call with no subagent_type was DROPPED; that is the "
                        "default and it is what every measured delegation was")
    elif dflt["subagent_type"] != "general-purpose":
        failures.append("an Agent call with no subagent_type was not recorded as "
                        "general-purpose")

    if build_row({"tool_name": "Bash", "tool_input": {"command": "ls"}}, personas, {}) is not None:
        failures.append("a non-Agent tool call was recorded as a spawn")

    unrouted = build_row({"tool_name": "Agent", "tool_input": {"subagent_type": "qa-lab"}},
                         personas, {})
    if unrouted["agreed"]:
        failures.append("a spawn with NO routing decision reported as agreed, so an "
                        "absent route would read as a followed one")
    if unrouted["route_match"] != "none":
        failures.append("a spawn with no routing decision does not say so")

    if slug("QA Lab") != "qa-lab" or slug("Mayor Opus") != "mayor-opus":
        failures.append("the persona-to-filename mapping is wrong, so no spawn can ever "
                        "agree with a route")

    if r["outcome"] is not None:
        failures.append("the hook scored its own spawn, which is the self-congratulation "
                        "failure mode skill-usage-log.sh refuses by name")

    # THE JOIN, exercised against a planted routing ledger. Without this the fallback
    # branch never runs in a selftest and a mutation making it claim "session" survives,
    # which would turn a best-effort join into a fictional agreement rate.
    import tempfile  # noqa: PLC0415

    global ROUTING  # noqa: PLW0603
    saved_routing = ROUTING
    try:
        with tempfile.TemporaryDirectory() as td:
            ROUTING = Path(td) / "routing.jsonl"
            ROUTING.write_text(
                json.dumps({"session": "S1", "personas": ["QA Lab"]}) + "\n"
                + json.dumps({"session": "S2", "personas": ["Review Board"]}) + "\n",
                encoding="utf-8")
            same = last_route("S1")
            other = last_route("S9")
            empty_file = Path(td) / "absent.jsonl"
            ROUTING = empty_file
            none_at_all = last_route("S1")
    finally:
        ROUTING = saved_routing

    if same.get("route_match") != "session" or (same.get("personas") or [""])[0] != "QA Lab":
        failures.append("a same-session routing row was not matched as `session`")
    if other.get("route_match") != "latest-any-session":
        failures.append("a cross-session fallback did not announce itself as a fallback, "
                        "so a best-effort join reads as a real one and the agreement rate "
                        "computed from it is fiction")
    if (other.get("personas") or [""])[0] != "Review Board":
        failures.append("the fallback did not take the NEWEST routing row")
    if none_at_all:
        failures.append("an absent routing ledger produced a route out of nothing")

    live = known_personas()
    if AGENTS_DIR.exists() and len(live) < 5:
        failures.append("only {} agent definition(s) were found, so is_known_agent is "
                        "meaningless".format(len(live)))

    # EVERY registry persona must slug to a file that exists. Asserted against the real
    # registry and the real directory, because a mapping verified only on fixtures is a
    # mapping verified against my own assumptions. This is what caught the dropped `and`:
    # three personas are "X and Y Office" in prose and `x-y-office.md` on disk, so the
    # naive slug matched nothing and `agreed` could never be true for them.
    try:
        reg = (Path.home() / ".claude" / "rules" / "gastown-company-registry.md")
        headings = [l[4:].strip() for l in reg.read_text(encoding="utf-8").splitlines()
                    if l.startswith("### ")]
    except OSError:
        headings = []
    if headings and live:
        unresolved = sorted(h for h in headings if slug(h) not in live)
        if unresolved:
            failures.append("{} registry persona(s) do not slug to an agent file, so a "
                            "spawn can never agree with a route naming them: {}".format(
                                len(unresolved), ", ".join(unresolved)))

    for line in failures:
        print("  FAIL  " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    a spawn matching its route is agreed; general-purpose against a route is not")
    print("  ok    an Agent call with no subagent_type records as general-purpose, not dropped")
    print("  ok    a non-Agent tool call is not a spawn")
    print("  ok    an absent routing decision never reads as a followed one")
    print("  ok    persona headings map to agent filenames, `and` included")
    print("  ok    every registry persona resolves to a real agent file")
    print("  ok    the hook records no judgement of its own spawn")
    print("  ok    a same-session join says `session`, a fallback says so, and an absent ledger joins nothing")
    print("  ok    {} agent definition(s) resolve on this host".format(len(live)))
    print("VERDICT: every delegation is recorded with what was routed beside what was spawned")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    if "--report" in argv:
        return report()

    # Hook edge. Fails open and silent, and always emits valid JSON: a logging hook that
    # can fail the turn is worse than no logging.
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        row = build_row(payload, known_personas(),
                        last_route(payload.get("session_id", "")))
        if row:
            LEDGER.parent.mkdir(parents=True, exist_ok=True)
            with LEDGER.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
