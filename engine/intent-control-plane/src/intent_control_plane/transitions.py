"""Depth-pass lifecycle as a guarded, durable state machine (AC-O1/O2).

A pass on an artifact moves through an ALLOW-list graph: drafted -> rubric-scored ->
{kept | rejected} -> regression-tested -> shipped, with 'reverted' as the compensating end
state. Reaching a later state without its predecessor is structurally impossible: advance_pass
reads the current state first (checkpoint-before), fails closed on an illegal jump (a swarm
worker cannot skip the eval gate under cost pressure), and only then persists. This is the
allow-list dual of the generic deny-list (ILLEGAL_TRANSITIONS) that cli.py uses for work items;
both write the same state_transitions table. Undo is a compensating transition to 'reverted'
(DBOS-over-sqlite semantics), never a literal reversal, matching the 2026 event-sourcing
convention that agents get compensating recovery, not true rollback.

Pure logic (is_allowed, transition_record) is unit + property tested; advance_pass /
current_pass_state / revert_pass are the thin sqlite I/O over the existing table.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from intent_control_plane.schema import connect, initialize
from intent_control_plane.util import stable_id, utc_now

GENESIS = "drafted"

# Allow-list: state -> the states it may legally advance to. Absent/empty set = terminal.
PASS_LIFECYCLE: dict[str, set[str]] = {
    "drafted": {"rubric-scored"},
    "rubric-scored": {"kept", "rejected"},
    "kept": {"regression-tested", "reverted"},
    "regression-tested": {"shipped", "rejected"},
    "shipped": {"reverted"},
    "rejected": set(),
    "reverted": set(),
}


def is_allowed(from_state: str | None, to_state: str) -> bool:
    """True only for a legal edge; from None (no prior transition) only the genesis is legal."""
    if from_state is None:
        return to_state == GENESIS
    return to_state in PASS_LIFECYCLE.get(from_state, set())


def transition_record(
    subject_id: str,
    from_state: str | None,
    to_state: str,
    actor: str,
    *,
    evidence_ids: list[str] | None = None,
    judge_verdict_ids: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build a state_transitions row; allowed_by_contract records whether the edge is legal."""
    return {
        "transition_id": stable_id("st"),
        "subject_id": subject_id,
        "from_state": from_state if from_state is not None else "",
        "to_state": to_state,
        "actor": actor,
        "allowed_by_contract": 1 if is_allowed(from_state, to_state) else 0,
        "evidence_ids_json": json.dumps(list(evidence_ids or []), sort_keys=True),
        "judge_verdict_ids_json": json.dumps(list(judge_verdict_ids or []), sort_keys=True),
        "reason": reason,
        "created_at_utc": utc_now(),
    }


def current_pass_state(base_dir: Path, subject_id: str) -> str | None:
    """The latest persisted state for a subject, or None if it has no transitions yet.

    Ordered by created_at_utc then rowid so several transitions in the same wall-clock second
    still resolve to the last one written.
    """
    initialize(base_dir)
    with connect(base_dir) as conn:
        row = conn.execute(
            "select to_state from state_transitions where subject_id = ? "
            "order by created_at_utc desc, rowid desc limit 1",
            (subject_id,),
        ).fetchone()
    return str(row["to_state"]) if row else None


def advance_pass(
    base_dir: Path,
    subject_id: str,
    to_state: str,
    actor: str,
    *,
    evidence_ids: list[str] | None = None,
    judge_verdict_ids: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Guarded transition: read current state, fail closed on an illegal edge, else persist.

    The read-check-insert runs in ONE `BEGIN IMMEDIATE` write transaction on a single connection, so
    concurrent advances on the same subject serialize; the loser blocks on the write lock, then
    re-reads the now-updated state and its is_allowed check fails closed. That makes the earlier
    check-then-insert race across two connections structurally impossible (audit #14). Raises
    ValueError on an illegal jump so an out-of-order transition is never recorded.
    """
    initialize(base_dir)
    conn = connect(base_dir)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "select to_state from state_transitions where subject_id = ? "
            "order by created_at_utc desc, rowid desc limit 1",
            (subject_id,),
        ).fetchone()
        from_state = str(row["to_state"]) if row else None
        if not is_allowed(from_state, to_state):
            conn.execute("ROLLBACK")
            raise ValueError(f"illegal pass transition: {from_state} -> {to_state} (subject {subject_id})")
        record = transition_record(
            subject_id,
            from_state,
            to_state,
            actor,
            evidence_ids=evidence_ids,
            judge_verdict_ids=judge_verdict_ids,
            reason=reason,
        )
        conn.execute(
            "insert into state_transitions ("
            " transition_id, subject_id, from_state, to_state, actor,"
            " allowed_by_contract, evidence_ids_json, judge_verdict_ids_json,"
            " reason, created_at_utc"
            ") values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record["transition_id"],
                record["subject_id"],
                record["from_state"],
                record["to_state"],
                record["actor"],
                record["allowed_by_contract"],
                record["evidence_ids_json"],
                record["judge_verdict_ids_json"],
                record["reason"],
                record["created_at_utc"],
            ),
        )
        conn.execute("COMMIT")
    finally:
        conn.close()
    return record


def revert_pass(
    base_dir: Path, subject_id: str, actor: str, reason: str | None = None
) -> dict[str, Any]:
    """Undo as a compensating transition to 'reverted' (legal from kept or shipped)."""
    return advance_pass(base_dir, subject_id, "reverted", actor, reason=reason or "compensating revert")
