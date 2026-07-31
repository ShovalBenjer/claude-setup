"""The A-seam: a `DurableBackend` interface so transitions.py is swappable, not a rewrite.

`transitions.py` already holds the pure lifecycle contract (`PASS_LIFECYCLE`, `is_allowed`,
`transition_record`) plus a sqlite-backed I/O layer (`advance_pass` / `current_pass_state` /
`revert_pass`). This module proves that I/O layer is one interchangeable implementation behind
a narrow `Protocol`, not the only way to run the lifecycle: a future Temporal workflow or a DBOS
transaction function can implement the same three methods and drop in wherever code depends on
`DurableBackend`, with zero changes to the allow-list contract itself.

`InMemoryBackend` is the reference implementation: a plain `dict[str, list[dict]]` of subject ->
transition history, in-process only (no sqlite, no filesystem). It enforces the exact same
allow-list as the sqlite backend by importing `is_allowed` and `transition_record` from
`transitions.py` rather than re-deriving the graph, so both backends can never drift apart on
what counts as a legal edge. Illegal jumps raise `ValueError` and are never appended to history
(fail closed, matching `advance_pass`). `compensate` is the same compensating-transition-to-
'reverted' semantics as `transitions.revert_pass`, not a literal rollback.
"""
from __future__ import annotations

from typing import Any, Protocol

from intent_control_plane.transitions import is_allowed, transition_record


class DurableBackend(Protocol):
    """The swap seam: anything with these three methods can stand in for the sqlite I/O layer."""

    def advance(self, subject_id: str, to_state: str) -> dict[str, Any]:
        """Guarded transition to `to_state`; raises ValueError on an illegal edge."""
        ...

    def current_state(self, subject_id: str) -> str | None:
        """The latest state for `subject_id`, or None if it has no transitions yet."""
        ...

    def compensate(self, subject_id: str, actor: str) -> dict[str, Any]:
        """Compensating transition to 'reverted', recorded under the given actor."""
        ...


class InMemoryBackend:
    """Reference `DurableBackend`: an in-process dict of subject -> transition history.

    No sqlite, no filesystem, and no project state beyond the instance itself, so it is cheap to
    construct per-test and safe for concurrent instances in the same process. The allow-list is
    enforced by delegating to `transitions.is_allowed`, never re-implemented here.
    """

    def __init__(self, actor: str = "system") -> None:
        self._actor = actor
        self._transitions: dict[str, list[dict[str, Any]]] = {}

    def advance(self, subject_id: str, to_state: str) -> dict[str, Any]:
        from_state = self.current_state(subject_id)
        if not is_allowed(from_state, to_state):
            raise ValueError(
                f"illegal pass transition: {from_state} -> {to_state} (subject {subject_id})"
            )
        record = transition_record(subject_id, from_state, to_state, self._actor)
        self._transitions.setdefault(subject_id, []).append(record)
        return record

    def current_state(self, subject_id: str) -> str | None:
        history = self._transitions.get(subject_id)
        if not history:
            return None
        return str(history[-1]["to_state"])

    def compensate(self, subject_id: str, actor: str) -> dict[str, Any]:
        from_state = self.current_state(subject_id)
        to_state = "reverted"
        if not is_allowed(from_state, to_state):
            raise ValueError(
                f"illegal pass transition: {from_state} -> {to_state} (subject {subject_id})"
            )
        record = transition_record(
            subject_id, from_state, to_state, actor, reason="compensating revert"
        )
        self._transitions.setdefault(subject_id, []).append(record)
        return record
