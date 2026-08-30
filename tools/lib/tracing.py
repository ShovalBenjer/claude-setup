"""Run-level tracing context for state/*.jsonl ledgers.

Every top-level command (gate run, bus send, corpus ingest, ...) generates a
run_id at entry. That id threads through every ledger row the command writes,
so downstream tools can answer "all events for run X in order" across every
state file.

The context is propagated through an environment variable (CLAUDE_RUN_ID) so
child processes inherit it without explicit plumbing, and through a module-level
variable so in-process writers see it without imports beyond this file.

Shape follows OTLP (trace_id + span_id + parent_span_id) but carries no SDK
dependency. A row with run_id but no span_id is a top-level event; one with
both participates in a span tree.
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from typing import Any

_ACTIVE_RUN_ID: str | None = None
_ACTIVE_SPAN: _Span | None = None

ENV_VAR = "CLAUDE_RUN_ID"


def generate_run_id() -> str:
    return uuid.uuid4().hex[:16]


def current_run_id() -> str | None:
    return _ACTIVE_RUN_ID or os.environ.get(ENV_VAR) or None


class _Span:
    __slots__ = ("span_id", "parent_span_id", "name", "start_ns")

    def __init__(self, name: str, parent_span_id: str | None = None):
        self.span_id = uuid.uuid4().hex[:16]
        self.parent_span_id = parent_span_id
        self.name = name
        self.start_ns = time.monotonic_ns()


@contextmanager
def run_context(run_id: str | None = None):
    """Set the active run_id for the duration of a block.

    Nested calls inherit the outer run_id unless an explicit one is passed,
    matching the OTLP rule that a trace_id is set once at the root.
    """
    global _ACTIVE_RUN_ID
    prev = _ACTIVE_RUN_ID
    rid = run_id or generate_run_id()
    _ACTIVE_RUN_ID = rid
    old_env = os.environ.get(ENV_VAR)
    os.environ[ENV_VAR] = rid
    try:
        yield rid
    finally:
        _ACTIVE_RUN_ID = prev
        if old_env is None:
            os.environ.pop(ENV_VAR, None)
        else:
            os.environ[ENV_VAR] = old_env


@contextmanager
def span(name: str):
    """Create a child span under the current run.

    Yields a span_id that callers can pass to inject() or record alongside
    their own data.
    """
    global _ACTIVE_SPAN
    prev = _ACTIVE_SPAN
    parent = prev.span_id if prev else None
    s = _Span(name, parent)
    _ACTIVE_SPAN = s
    try:
        yield s.span_id
    finally:
        _ACTIVE_SPAN = prev


def inject(row: dict[str, Any]) -> dict[str, Any]:
    """Add trace fields to a dict before writing it to a ledger.

    Does not overwrite existing fields, so a caller that sets run_id
    explicitly (e.g. bus.py for hash-chain compatibility) keeps control.
    Returns the same dict for chaining.
    """
    rid = current_run_id()
    if rid and "run_id" not in row:
        row["run_id"] = rid
    s = _ACTIVE_SPAN
    if s:
        if "span_id" not in row:
            row["span_id"] = s.span_id
        if s.parent_span_id and "parent_span_id" not in row:
            row["parent_span_id"] = s.parent_span_id
        if "span_name" not in row:
            row["span_name"] = s.name
    return row
