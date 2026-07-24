"""Tier-1 deterministic eval checks: the cheap, free, sub-ms gate before the LLM judges.

Tier-1 runs BEFORE the Foundry judges (grok / DeepSeek). Every check here is pure and
deterministic: JSON parsing, key presence, regex, and function-call shape, no model call
involved. A tier-1 failure short-circuits the judge call entirely, so the expensive LLM
judges only ever see outputs that already pass structural validation, and cost is saved
on every row that fails a structural check.

This is the standalone tier-1 layer: mojuco sim2real rung 1 / PRD T4.1. Wiring this into
the live eval pipeline is a separate, shared-HOME task; this module is self-contained and
unwired by design.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Tier1Result:
    """One deterministic check outcome: which check, did it pass, and why."""

    check: str
    passed: bool
    reason: str


def check_valid_json(text: str) -> Tier1Result:
    """Passed if text parses as JSON. Reason names the parse error otherwise."""
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return Tier1Result(check="valid_json", passed=False, reason=f"invalid json: {exc}")
    return Tier1Result(check="valid_json", passed=True, reason="ok")


def check_required_keys(text: str, keys: list[str]) -> Tier1Result:
    """Parse text as a JSON object; passed if all keys are present."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return Tier1Result(check="required_keys", passed=False, reason=f"invalid json: {exc}")
    if not isinstance(parsed, dict):
        return Tier1Result(
            check="required_keys", passed=False, reason="invalid json: not an object"
        )
    missing = [key for key in keys if key not in parsed]
    if missing:
        return Tier1Result(
            check="required_keys", passed=False, reason=f"missing keys: {', '.join(missing)}"
        )
    return Tier1Result(check="required_keys", passed=True, reason="ok")


def check_regex(text: str, pattern: str, should_match: bool = True) -> Tier1Result:
    """Passed if bool(re.search(pattern, text)) == should_match.

    Use should_match=True for a required pattern, should_match=False for forbidden content.
    An invalid regex (from a bad fixture) returns a failed result, never crashes the gate.
    """
    try:
        matched = bool(re.search(pattern, text))
    except re.error as exc:
        return Tier1Result(
            check="regex", passed=False, reason=f"invalid pattern {pattern!r}: {exc}"
        )
    if matched == should_match:
        return Tier1Result(check="regex", passed=True, reason="ok")
    if should_match:
        reason = f"required pattern not found: {pattern}"
    else:
        reason = f"forbidden pattern found: {pattern}"
    return Tier1Result(check="regex", passed=False, reason=reason)


def check_function_call(call: object, name: str, required_args: list[str]) -> Tier1Result:
    """Passed if call name matches and every required arg key is present.

    Accepts either call["arguments"] or call["args"], whichever is a dict. A
    non-dict `call` (a malformed model output) returns a failed result rather
    than raising, so structural validation reports the failure as tier-1.
    """
    if not isinstance(call, dict):
        return Tier1Result(
            check="function_call",
            passed=False,
            reason=f"not a call object: {type(call).__name__}",
        )
    call_name = call.get("name")
    if call_name != name:
        return Tier1Result(
            check="function_call",
            passed=False,
            reason=f"wrong name: expected {name!r}, got {call_name!r}",
        )
    arguments = call.get("arguments")
    if not isinstance(arguments, dict):
        arguments = call.get("args")
    if not isinstance(arguments, dict):
        arguments = {}
    missing = [arg for arg in required_args if arg not in arguments]
    if missing:
        return Tier1Result(
            check="function_call",
            passed=False,
            reason=f"missing args: {', '.join(missing)}",
        )
    return Tier1Result(check="function_call", passed=True, reason="ok")


def run_tier1(results: list[Tier1Result]) -> dict[str, Any]:
    """Aggregate tier-1 results into the judge gate.

    If passed is False, the caller should SKIP the LLM judges for that row and record
    the tier-1 failures instead, saving the judge call cost. An empty results list
    returns passed=True (total=0): with no structural checks there is nothing to fail,
    so the row correctly defers to the judges. A caller that wants to require checks can
    assert total > 0; failing closed here would spuriously reject unconfigured rows.
    """
    failures = [r.check for r in results if not r.passed]
    return {
        "passed": all(r.passed for r in results),
        "total": len(results),
        "failures": failures,
    }
