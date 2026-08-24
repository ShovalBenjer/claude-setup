"""Generic helpers: timestamps, stable ids, PII redaction.

No project imports, so any module can depend on it without a cycle.
"""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

SECRET_PATTERNS = [
    re.compile(r"sk-proj-[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)\b[A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*=\s*\S+"),
]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:10]}"


def redact(text: str) -> tuple[str, str]:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    state = "raw_local" if redacted == text else "redacted_for_model"
    return redacted, state
