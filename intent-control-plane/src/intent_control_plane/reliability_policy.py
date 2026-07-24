"""Reliability plumbing (PRD A6): failover, retry, backoff, injection screening.

Pure decision functions for the runtime call loop: given a model ladder and an
error kind, decide the next model to try, whether to retry at all, and how long
to wait before the retry. Also screens free text for common prompt-injection
patterns before it reaches a model or a tool call. No I/O, no network, no
sleeping: the caller owns the actual failover/retry/sleep, these functions only
decide.
"""
from __future__ import annotations

import re

# Error kinds worth retrying: transient upstream conditions that often clear on
# their own. Everything else (bad credentials, malformed requests, unknown
# kinds) is treated as permanent and never retried.
_TRANSIENT_ERROR_KINDS = {"timeout", "rate_limit", "5xx"}

# (flag name, pattern) pairs used to screen text for prompt-injection attempts.
# Each pattern is matched case-insensitively; a hit appends the flag's name to
# the result. Order is fixed so results are deterministic.
_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_previous_instructions",
        re.compile(
            r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+"
            r"(?:instructions?|prompts?|rules?|context)",
            re.IGNORECASE,
        ),
    ),
    (
        "disregard_instructions",
        re.compile(
            r"disregard\s+(?:all\s+)?(?:previous|prior|above|earlier)?\s*"
            r"(?:instructions?|prompts?|rules?)",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_probe",
        re.compile(r"system\s*[- ]?prompt", re.IGNORECASE),
    ),
    (
        "role_override",
        re.compile(
            r"\byou\s+are\s+now\b"
            r"|\bact\s+as\s+(?:the\s+)?(?:system|admin|root|developer\s+mode)\b"
            r"|\bno\s+restrictions\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tool_exfil",
        re.compile(
            r"exfiltrat\w*"
            r"|send\s+.{0,40}\bto\s+attacker\b"
            r"|leak\w*\s+(?:the\s+)?(?:api\s*key|secret|credential|token)",
            re.IGNORECASE,
        ),
    ),
]


def next_model_on_error(current: str, ladder: list[str]) -> str | None:
    """The next model down a fallback ladder after ``current`` fails.

    Walks the ladder in the order given (e.g. ["opus", "sonnet", "haiku"] is
    high-cost to low-cost). Returns None when ``current`` is the last entry, or
    when ``current`` is not on the ladder at all: there is nowhere left to
    fail over to either way.
    """
    if current not in ladder:
        return None
    idx = ladder.index(current)
    if idx + 1 >= len(ladder):
        return None
    return ladder[idx + 1]


def should_retry(attempt: int, max_attempts: int, error_kind: str) -> bool:
    """Whether to retry after ``attempt`` given ``error_kind``.

    Only transient error kinds ({"timeout", "rate_limit", "5xx"}) are ever
    retried, and only while ``attempt`` is still below ``max_attempts``.
    Permanent kinds ("auth", "invalid_request") and any unrecognized kind
    never retry: an unknown failure mode is treated as non-transient rather
    than retried blindly.
    """
    if error_kind not in _TRANSIENT_ERROR_KINDS:
        return False
    return attempt < max_attempts


def backoff_seconds(attempt: int, base: float = 1.0, cap: float = 30.0) -> float:
    """Exponential backoff for ``attempt`` (1-indexed), capped at ``cap`` seconds.

    ``attempt=1`` waits ``base`` seconds, ``attempt=2`` waits ``base * 2``,
    ``attempt=3`` waits ``base * 4``, and so on, never exceeding ``cap``.
    """
    delay: float = base * (2.0 ** (attempt - 1))
    return min(delay, cap)


def injection_flags(text: str) -> list[str]:
    """Names of prompt-injection patterns matched in ``text`` (empty if none).

    Screens for common injection shapes: instruction-override phrasing
    ("ignore previous instructions", "disregard instructions"), attempts to
    surface the system prompt, role-override attempts ("you are now ...",
    "act as the system", "no restrictions"), and tool-exfiltration phrasing
    (sending secrets/keys to an external party). Matching is case-insensitive
    and additive: a text can trip more than one flag.
    """
    return [name for name, pattern in _INJECTION_PATTERNS if pattern.search(text)]
