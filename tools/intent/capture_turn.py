#!/usr/bin/env python3
"""UserPromptSubmit entrypoint: turn one typed prompt into a tracked ticket.

Reads the hook payload on stdin and writes two records. Ordering between them is the
design, not an accident:

  1. A chained row in `state/prompt-tickets.jsonl`. Hashes only, no prompt text, so the
     file can live in git. This write is the one that must not fail.
  2. Best effort, the full event in `~/.intent` including the verbatim text, plus an
     intent card and a CAPTURED transition.

Step 2 is wrapped and its failure is swallowed, because a hook that raises on every
prompt is worse than a hook that records less. Step 1 needs no venv, no sqlite and no
package import, so the durable half survives an environment the enrichment half cannot.

WHY NOT THE TRANSCRIPT. An earlier draft took `promptId`, `parentUuid` and `uuid` from
`~/.claude/projects/<slug>/<session>.jsonl`, following the 2026-07-29 specs which call
that file the timeline. Claude Code documents that format as internal and subject to
change on any release, so a hook parsing it would break silently on an upgrade and take
prompt capture with it. Everything here comes from the hook payload, which is a
documented input. Transcript ids are accepted if the payload happens to carry them, and
their absence never fails a capture. Recorded as L-2026-07-29-e.

WHY THE TRANSITION IS WRITTEN HERE rather than through `intent capture` plus
`intent state transition`. That CLI path takes `--from-state` from its caller and never
reads what the subject's current state actually is, so it accepts any pair a caller
invents: a fresh subject was pushed JUDGED_PASS to SHIPPED to CLOSED_VERIFIED with no
evidence, all exit 0, and every row it writes hardcodes `allowed_by_contract = 1`. This
module reads the stored state first, checks the edge against the allow-list in
`tickets.py`, and records the real verdict in that column. Measured 2026-07-29.

Output is deliberately empty. On UserPromptSubmit, anything this prints on exit 0 is
injected into the session's context, so a chatty hook would tax every single turn.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "tools" / "intent") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "intent"))

import tickets  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def prompt_text(payload: dict[str, Any]) -> str:
    """The typed text. `prompt` is the documented key; the rest are defensive."""
    for key in ("prompt", "user_prompt", "text", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            inner = value.get("text") or value.get("content")
            if isinstance(inner, str) and inner.strip():
                return inner
    return ""


def repo_and_branch(cwd: str) -> tuple[str, str]:
    """Name the repo by its directory and ask git for the branch.

    Only the repo NAME is recorded, never the absolute path: the path leaks a home
    directory and a user name into a git-tracked file for no analytical gain.
    """
    root = Path(cwd) if cwd else Path.cwd()
    name = root.name or "unknown"
    branch = ""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(root), capture_output=True, timeout=5, shell=False,
        )
        if proc.returncode == 0:
            branch = proc.stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return name, branch


def enrich(payload: dict[str, Any], ticket: str, text: str, sha: str, seq: int) -> None:
    """Write the full event, the intent card and the CAPTURED transition.

    Every failure here is swallowed by the caller. This is the half that needs the venv
    and the sqlite store, and neither is worth a blocked prompt.
    """
    import argparse

    # The package is not installed. It lives in this repo, and the live settings.json
    # runs this hook under plain `python3`, an interpreter with no venv and nothing of
    # ours on its path. Without this line the import below raised ModuleNotFoundError,
    # the caller's bare except swallowed it, and every prompt from the 2026-07-31 WSL
    # move to 2026-08-10 wrote its hash and dropped its text. Ten days, no signal,
    # because the swallow is correct and the interpreter was wrong.
    #
    # Inserted here rather than at module scope on purpose: step 1, the durable hashed
    # row, must keep needing no package import at all, and a top-level path change would
    # blur the line the docstring draws between the two halves.
    src = REPO_ROOT / "intent-control-plane" / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from intent_control_plane.cli import capture, extract_intent
    from intent_control_plane.schema import DEFAULT_BASE_DIR, connect
    from intent_control_plane.util import stable_id

    metadata = {
        "text_sha": sha,
        "seq": seq,
        "cwd": payload.get("cwd", ""),
        "ticket": ticket,
    }
    # Vendor ids are recorded when the payload offers them and never required. See the
    # module docstring: the transcript schema they come from is not a public contract.
    for key, dest in (("prompt_id", "prompt_id"), ("promptId", "prompt_id"),
                      ("message_uuid", "message_uuid"), ("uuid", "message_uuid")):
        value = payload.get(key)
        if isinstance(value, str) and value:
            metadata[dest] = value

    args = argparse.Namespace(
        base_dir=DEFAULT_BASE_DIR, event_type="user_prompt",
        session=str(payload.get("session_id", "")), repo=str(payload.get("cwd", "")),
        branch=None, bead=ticket, workflow=None, actor="shoval",
        authority="raw_user_prompt", text=text, metadata=json.dumps(metadata),
    )
    result = capture(args)

    try:
        extract_intent(argparse.Namespace(base_dir=DEFAULT_BASE_DIR,
                                          event=result["event_id"]))
    except Exception:  # noqa: BLE001 - an absent card must not lose the event
        pass

    # Read-then-check inside one write transaction. The stored state decides the legal
    # edge, never the caller. See the module docstring for what the CLI path does.
    conn = connect(DEFAULT_BASE_DIR)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "select to_state from state_transitions where subject_id = ? "
            "order by created_at_utc desc, rowid desc limit 1",
            (ticket,),
        ).fetchone()
        current = row[0] if row else None
        allowed = tickets.is_allowed(current, tickets.GENESIS)
        conn.execute(
            "insert into state_transitions (transition_id, subject_id, from_state,"
            " to_state, actor, allowed_by_contract, evidence_ids_json,"
            " judge_verdict_ids_json, reason, created_at_utc)"
            " values (?,?,?,?,?,?,?,?,?,?)",
            (stable_id("st"), ticket, current or "", tickets.GENESIS, "hook",
             1 if allowed else 0, "[]", "[]", "prompt captured", utc_now()),
        )
        conn.execute("COMMIT")
    finally:
        conn.close()


def main() -> int:
    try:
        payload: Any = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        return 0

    # Silent during real automation, matching every other hook in this tree.
    if os.environ.get("CLAUDE_LOOP_MODE") or os.environ.get("CODEX_AUTOMATION_ID"):
        return 0

    text = prompt_text(payload)
    if not text.strip():
        return 0

    try:
        session = str(payload.get("session_id", ""))
        repo, branch = repo_and_branch(str(payload.get("cwd", "")))
        sha = tickets.text_sha(text)
        row = tickets.append_for_prompt(
            session=session, repo=repo, branch=branch, prompt_sha=sha, ts=utc_now(),
        )
    except Exception:  # noqa: BLE001 - never block a prompt
        return 0

    # Per-session, so it reads as "the Nth prompt of this session" rather than as a
    # global row number that means nothing once two sessions interleave.
    try:
        seq = sum(1 for r in tickets.read_rows() if r.get("session") == session)
    except Exception:  # noqa: BLE001
        seq = 0

    try:
        enrich(payload, row["id"], text, sha, seq)
    except Exception:  # noqa: BLE001 - the durable row is already written
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
