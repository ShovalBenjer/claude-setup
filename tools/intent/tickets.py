#!/usr/bin/env python3
"""Prompt tickets: identity, lifecycle, and the git-tracked chained mirror.

Deliberately free of any `intent_control_plane` import. That package lives in a venv
and is not importable from the system interpreter the root suite runs under, so
putting the pure logic here is what lets it be tested at all. `capture_turn.py` is
the thin glue that has both dependencies.

A ticket is not a row in a table. It is a `PT-` id plus every event that cites it,
and its current state is the newest transition recorded for it. The id is derived
from content, not minted from a clock or a counter, so replaying the ledger
reproduces it and the 587 historical prompts can be given ids without inventing
provenance.

The chained mirror in git carries hashes and no prompt text. `~/.intent` stays the
only place the operator's words live, which makes a loss there unrecoverable but
detectable, and keeps prompt text out of a tracked file. That trade was chosen
deliberately (spec open question 2) and is the reason `text_sha` is covered by the
chain: without it, swapping which prompt a ticket refers to would leave no trace.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "tools" / "bus") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "bus"))
if str(REPO_ROOT / "tools" / "lib") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "lib"))

from bus import canonical, file_lock, row_altered, row_hash, row_id  # noqa: E402
try:
    from tracing import inject as trace_inject  # noqa: E402
except ImportError:
    def trace_inject(row):
        return row

TICKETS = REPO_ROOT / "state" / "prompt-tickets.jsonl"

# The fields a ticket row commits to. `chain_fields` is NOT listed: canonical()
# covers the declaration on top of whatever is named here, so listing it would be
# redundant and, worse, would make a fixture pass whether or not that guarantee
# holds. `hash` is absent because a value cannot commit to itself.
PT_CHAIN_FIELDS = ("branch", "id", "prev", "repo", "session", "state", "text_sha", "ts")

GENESIS = "CAPTURED"

# Allow-list, not deny-list. A deny-list answers "is this edge forbidden", which
# silently permits every edge nobody thought to forbid, including CAPTURED straight
# to CLOSED_VERIFIED.
TICKET_LIFECYCLE: dict[str, set[str]] = {
    "CAPTURED": {"TRIAGED", "NOT_WORK", "SUPERSEDED"},
    "TRIAGED": {"OPEN", "NOT_WORK", "SUPERSEDED"},
    "OPEN": {"IN_PROGRESS", "CLOSED_WONTDO", "SUPERSEDED"},
    "IN_PROGRESS": {"BLOCKED_OPERATOR", "CLOSED_VERIFIED", "CLOSED_WONTDO", "OPEN"},
    "BLOCKED_OPERATOR": {"IN_PROGRESS", "CLOSED_WONTDO", "SUPERSEDED"},
    "CLOSED_VERIFIED": set(),
    "CLOSED_WONTDO": {"OPEN"},          # reopening is legal; closing is not final
    "NOT_WORK": {"TRIAGED"},            # a misclassification must be correctable
    "SUPERSEDED": set(),
}
TICKET_STATES = frozenset(TICKET_LIFECYCLE)


# Openers that mark text as authored by the harness rather than typed by the operator.
# Shared with the transcript backfill on purpose: the hook and the recovery path must
# agree on what a prompt is, or one of them mints tickets the other refuses to recognise.
# Measured 2026-08-10, before this list was applied at capture: 93 of 1,306 ledger rows
# were `<task-notification>` blocks, which Claude Code delivers through UserPromptSubmit
# exactly like a typed prompt. Prefix matching, never substring, so a prompt that quotes
# one of these partway through is still a prompt.
HARNESS_PREFIXES = (
    "<system-reminder",
    "<local-command",
    "<command-name",
    "<command-message",
    "<command-args",
    "<user-prompt-submit-hook",
    "<bash-input",
    "<bash-stdout",
    "<task-notification>",
    "Caveat:",
    "[Request interrupted",
    "This session is being continued from a previous conversation",
    "Continue the conversation from",
)


def is_harness_authored(text: str) -> bool:
    """True when the text was injected by the harness rather than typed."""
    return text.strip().startswith(HARNESS_PREFIXES)


# Exact members, never a length threshold. "is this short" is a proxy for "is this
# meaningless" that gets it wrong in the direction that loses work: `push. merge`,
# `whats left?` and `fixed env` are all short and all carry intent. A closed set can
# only ever be wrong about the words actually in it.
ACK_WORDS = frozenset({
    "y", "yes", "yeah", "yep", "ok", "okay", "k", "go", "go on", "goo", "continue",
    "next", "push", "commit", "commit push", "push it", "ey", "do it", "proceed",
    "done", "stop", "n", "no", "wait", "again", "sure", "fine", "thanks", "thank you",
    "ty", "good", "great", "nice", "cool", "perfect", "agreed", "approved", "correct",
})


def normalize(text: str) -> str:
    """Whitespace-collapsed, lowercased. The form the ack allow-list is tested against."""
    return " ".join(text.split()).strip().lower()


def classify(text: str) -> tuple[str | None, str | None]:
    """`(class, rule_id)` when a closed replayable rule fires, `(None, None)` otherwise.

    Two rules, both exact. Everything else stays `CAPTURED`, which is an honest
    outcome: a prompt nobody has read yet is not the same as a prompt with no work in
    it, and collapsing the two is how a backlog silently loses things.

    Deterministic and free of any model call, so a `NOT_WORK` classification can be
    re-derived from the text alone and challenged. That is what makes the transition
    guard possible: a human cannot hand-wave a prompt out of the queue, only a named
    rule that reproduces can.
    """
    stripped = text.strip()
    if re.fullmatch(r"/[a-z][a-z0-9:_-]*", stripped):
        return "control", "R1"
    if normalize(stripped) in ACK_WORDS:
        return "ack", "R2"
    return None, None


def text_sha(text: str) -> str:
    """The content key for a prompt. Full width: this is an identity, not a digest."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ticket_id(session_id: str, prompt_sha: str, occurrence_index: int) -> str:
    """`PT-<12 hex>`, derived from content so that replay reproduces it.

    `occurrence_index` is what keeps a repeated prompt from collapsing. Typing "run
    the tests" twice in one session is two pieces of work, not one, and without the
    index both would derive the same id and the second would silently adopt the
    first's transition history.

    No clock and no randomness, so the 587 corpus prompts that predate any capture
    hook can be given ids from what is already recorded about them. It also sidesteps
    the same-second `ts` collision in that corpus, which a timestamp-derived id would
    have to special-case.
    """
    payload = json.dumps(
        {"session_id": session_id, "text_sha": prompt_sha,
         "occurrence_index": occurrence_index},
        sort_keys=True, separators=(",", ":"),
    )
    return "PT-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def is_allowed(from_state: str | None, to_state: str) -> bool:
    """True only for a legal edge. From None, only the genesis state is legal."""
    if from_state is None:
        return to_state == GENESIS
    return to_state in TICKET_LIFECYCLE.get(from_state, set())


def build_row(
    *,
    ticket: str,
    ts: str,
    session: str,
    repo: str,
    branch: str,
    prompt_sha: str,
    state: str,
    prev: str,
) -> dict[str, Any]:
    """One mirror row, hashed over its declared fields plus the declaration.

    Carries no prompt text and no `cwd` beyond the repo name, so this file can sit in
    git without publishing what was typed.
    """
    row: dict[str, Any] = {
        "id": ticket,
        "ts": ts,
        "session": session,
        "repo": repo,
        "branch": branch,
        "text_sha": prompt_sha,
        "state": state,
        "chain_fields": list(PT_CHAIN_FIELDS),
        "prev": prev,
    }
    row["hash"] = row_hash(row)
    return row


def read_rows(path: Path = TICKETS) -> list[dict[str, Any]]:
    """Every parseable row. A torn line is skipped, never raised.

    This is read by a hook that runs on every prompt. A parse error here would block
    the session, which is a far worse outcome than one unreadable row.
    """
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def tip(path: Path = TICKETS) -> str:
    """The id of the newest row, or "" when the file is empty or absent."""
    rows = read_rows(path)
    return row_id(rows[-1]) if rows else ""


def append_row(row: dict[str, Any], path: Path = TICKETS) -> None:
    """Append one row under the same exclusive lock the bus uses.

    The lock is not optional. Two sessions prompting at once would otherwise fork the
    chain: both read the same tip, both write `prev` pointing at it, and the file now
    has two rows claiming the same predecessor, which verify reports as a break with
    no way to tell which row is the intruder. On Windows the unlocked case is worse
    still, because the appends can destroy each other outright rather than fork.
    """
    trace_inject(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    with file_lock(path):
        try:
            if path.exists() and path.stat().st_size:
                with path.open("rb") as fh:
                    fh.seek(-1, 2)
                    torn = fh.read(1) != b"\n"
                if torn:
                    with path.open("ab") as fh:
                        fh.write(b"\n")
        except OSError:
            pass
        with path.open("ab") as fh:
            fh.write(payload)


def append_chained(
    *, ticket: str, ts: str, session: str, repo: str, branch: str,
    prompt_sha: str, state: str, path: Path = TICKETS,
) -> dict[str, Any]:
    """Read the tip and append in one locked critical section.

    Reading the tip outside the lock is the fork described in `append_row`, so the
    read has to be inside it. That is why this exists rather than callers composing
    `tip()` and `append_row()` themselves: the composition is the bug.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        rows = read_rows(path)
        prev = row_id(rows[-1]) if rows else ""
        row = build_row(ticket=ticket, ts=ts, session=session, repo=repo,
                        branch=branch, prompt_sha=prompt_sha, state=state, prev=prev)
        payload = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        try:
            if path.exists() and path.stat().st_size:
                with path.open("rb") as fh:
                    fh.seek(-1, 2)
                    torn = fh.read(1) != b"\n"
                if torn:
                    with path.open("ab") as fh:
                        fh.write(b"\n")
        except OSError:
            pass
        with path.open("ab") as fh:
            fh.write(payload)
    return row


def append_for_prompt(
    *, session: str, repo: str, branch: str, prompt_sha: str, ts: str,
    state: str = GENESIS, path: Path = TICKETS,
) -> dict[str, Any]:
    """Mint a ticket for one prompt and append its row, all inside one lock.

    The occurrence index counts how many times this exact prompt has already been seen
    in this session, and the ticket id is derived from it. So the count and the append
    are one operation or they are wrong: two sessions typing the same words at the same
    moment would both read a count of zero, both derive the same id, and the second
    would silently adopt the first's history. Composing `ticket_id()` with
    `append_chained()` at the call site reintroduces exactly that gap, which is why this
    function exists rather than a docstring telling callers to be careful.

    Returns the appended row, whose `id` is the ticket.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        rows = read_rows(path)
        occurrence = sum(
            1 for r in rows
            if r.get("session") == session and r.get("text_sha") == prompt_sha
        )
        row = build_row(
            ticket=ticket_id(session, prompt_sha, occurrence), ts=ts, session=session,
            repo=repo, branch=branch, prompt_sha=prompt_sha, state=state,
            prev=row_id(rows[-1]) if rows else "",
        )
        payload = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        try:
            if path.exists() and path.stat().st_size:
                with path.open("rb") as fh:
                    fh.seek(-1, 2)
                    torn = fh.read(1) != b"\n"
                if torn:
                    with path.open("ab") as fh:
                        fh.write(b"\n")
        except OSError:
            pass
        with path.open("ab") as fh:
            fh.write(payload)
    return row


def verify(path: Path = TICKETS) -> list[tuple[int, str]]:
    """Every break in the chain, as (index, reason). Empty means intact.

    Two distinct failures are reported separately because they mean different things:
    an altered row means someone edited content in place, while a broken `prev` means
    a row was removed or reordered. Truncation of the newest rows is detectable by
    neither, since nothing outside this file records where the tip should be.
    """
    breaks: list[tuple[int, str]] = []
    prev_id: str | None = None
    for i, row in enumerate(read_rows(path)):
        if row_altered(row):
            breaks.append((i, f"row {row.get('id', '?')} no longer matches its hash"))
        elif prev_id is not None and row.get("prev", "") != prev_id:
            breaks.append((
                i,
                f"row {row.get('id', '?')} names prev "
                f"{row.get('prev', '') or '(empty)'} but the row before it is {prev_id}",
            ))
        prev_id = row_id(row)
    return breaks


__all__ = [
    "ACK_WORDS", "GENESIS", "HARNESS_PREFIXES", "is_harness_authored", "PT_CHAIN_FIELDS", "TICKETS", "TICKET_LIFECYCLE",
    "TICKET_STATES", "classify", "normalize",
    "append_chained", "append_for_prompt", "append_row", "build_row", "canonical",
    "file_lock", "is_allowed", "read_rows", "row_altered", "row_hash", "row_id",
    "text_sha", "ticket_id", "tip", "verify",
]
