#!/usr/bin/env python3
"""Request one corrective turn when a completion claim lacks evidence."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


COMPLETION = re.compile(
    r"(?i)(?:\b(?:all done|done|fully (?:done|complete|working)|"
    r"production[- ]ready|verified|fixed|implemented(?: successfully)?|"
    r"everything works|it works|implementation is complete|"
    r"deployed successfully|is deployed|now live)\b|"
    r"(?<![\u0590-\u05FF])(?:הושלם|תוקן|אומת|מוכן לפרודקשן)"
    r"(?![\u0590-\u05FF])|"
    r"(?<![\u0590-\u05FF])(?:הקוד|זה|המימוש|המערכת)\s+"
    r"(?:עובד|עובדת)(?![\u0590-\u05FF]))"
)
EVIDENCE = re.compile(
    r"(?i)(?:\b(?:test(?:ed|s|ing)?|pytest|vitest|jest|cargo test|go test|"
    r"benchmark(?:ed|s|ing)?|lint(?:ed|ing)?|"
    r"typecheck(?:ed|ing)?|build(?:s|ing| passed)?|command|output|"
    r"passed|exit code|sha256|screenshot|oracle|property test|mutation|"
    r"residual risk|not run|unverified)\b|(?:בדיקה|בדיקות|נבדק|פקודה|פלט|סיכון))"
)


def assistant_text(payload: dict[str, Any]) -> str:
    for key in ("last_assistant_message", "assistant_message", "response", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for nested in ("text", "content"):
                item = value.get(nested)
                if isinstance(item, str):
                    return item
    return ""


def main() -> int:
    try:
        payload: Any = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError
        text = assistant_text(payload)
        stop_hook_active = payload.get("stop_hook_active") is True
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        print("{}")
        return 0

    if not stop_hook_active and COMPLETION.search(text) and not EVIDENCE.search(text):
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": (
                        "Evidence check: the response makes a strong completion or quality "
                        "claim without naming an executable check. Calibrate the claim and "
                        "state what was tested, what was not tested, and residual risk."
                    )
                }
            )
        )
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
