#!/usr/bin/env python3
"""PostToolUse:Agent entrypoint: record which subagent actually ran.

The global contract in `~/.claude/CLAUDE.md` states, under Delegation, that
spawns "are now recorded in state/agent-spawns.jsonl beside what the router
named, so the ratio is checkable rather than assumed." On 2026-08-07 that
sentence was false in all three of its parts: this file did not exist in either
clone, `state/agent-spawns.jsonl` did not exist, and `~/.claude/settings.json`
had been wiring the missing path at PostToolUse since whenever it was added, so
every agent spawn produced a hook error and no record. It surfaced only because
three agents were spawned in one turn and the harness reported the failure three
times. A rule that asserts a measurement nobody built is worse than a rule that
admits the measurement is missing, because the first one stops anybody looking.

WHAT THE RATIO IS. `~/.claude/rules/gastown-company-registry.md` maps every skill
to one of 19 owning personas, and the measurement of record is that 0 of the 19
had ever been spawned. Two things have to be written down to check that: which
persona the router NAMED for a prompt, which `~/.claude/hooks/route.py` already
appends to `state/routing.jsonl`, and which subagent was actually SPAWNED, which
is this file. Neither alone answers it. The router naming a persona nobody uses
and a session spawning general-purpose for everything look identical if you only
have one of the two ledgers.

WHY THE ROUTING ROW IS LOOKED UP RATHER THAN JOINED LATER. `routing.jsonl` rows
carry a timestamp and an empty session field, so a join after the fact is a
guess about which prompt a spawn belongs to. Reading the most recent routing row
at spawn time is also a guess, but a narrower one, and it is recorded as
`router_named_at` so the distance between the two timestamps is visible instead
of implied. A spawn matched to a routing row from four minutes ago is a weaker
claim than one matched to a row from four seconds ago, and only the ledger can
say which happened.

WHY EVERY FAILURE IS SWALLOWED. This runs after every Agent call. A hook that
raises turns a working spawn into a reported error, which is precisely the shape
of the defect being fixed here. Nothing this writes is load-bearing for the
session, so it writes what it can and exits 0 regardless.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

LEDGER = os.path.join("state", "agent-spawns.jsonl")
ROUTING = os.path.join("state", "routing.jsonl")

# How far back a routing row may sit and still be treated as this spawn's own.
# Beyond it the row is recorded as absent rather than attached, because a stale
# association is a worse input to the ratio than a missing one: it invents an
# agreement between router and spawn that nobody observed.
ROUTER_WINDOW_SECONDS = 300


def setup_root() -> str:
    """The repository this hook writes its ledgers into.

    Walks up from the current working directory looking for the marker the
    other tools use. Falls back to the directory this file lives two levels
    under, which is correct when the hook fires from an unrelated cwd.
    """
    here = os.path.abspath(os.getcwd())
    while True:
        if os.path.isfile(os.path.join(here, "quality-contract.json")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def last_routing_row(root: str, now: datetime.datetime) -> dict | None:
    """The most recent router decision, if one landed inside the window."""
    path = os.path.join(root, ROUTING)
    try:
        with open(path, encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            row = json.loads(line)
            when = datetime.datetime.fromisoformat(row["ts"])
        except (ValueError, KeyError):
            continue
        if (now - when).total_seconds() <= ROUTER_WINDOW_SECONDS:
            return row
        return None
    return None


def row_for(payload: dict, root: str, now: datetime.datetime) -> dict:
    """The ledger row for one spawn, router context attached where it exists."""
    tool_input = payload.get("tool_input") or {}
    routed = last_routing_row(root, now)
    return {
        "ts": now.isoformat(timespec="seconds"),
        "subagent_type": tool_input.get("subagent_type") or "general-purpose",
        "description": tool_input.get("description") or "",
        "model": tool_input.get("model") or "",
        "background": bool(tool_input.get("run_in_background", True)),
        "isolation": tool_input.get("isolation") or "",
        "prompt_chars": len(tool_input.get("prompt") or ""),
        "session": payload.get("session_id") or "",
        "cwd": payload.get("cwd") or "",
        "router_named": (routed or {}).get("personas") or [],
        "router_skills": (routed or {}).get("skills") or [],
        "router_named_at": (routed or {}).get("ts") or "",
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    try:
        root = setup_root()
        path = os.path.join(root, LEDGER)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row_for(payload, root, datetime.datetime.now())) + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
