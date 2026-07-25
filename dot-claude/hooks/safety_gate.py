#!/usr/bin/env python3
"""Deny common destructive or secret-printing shell commands.

Claude Code sends hook input as JSON on stdin. The hook is deliberately
fail-open for malformed input so a broken guard cannot brick the CLI; native
permission rules remain the first line of defence. This is a guardrail, not an
OS security boundary: command syntax is too expressive for regex completeness.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any


RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?is)\brm\s+(?=[^\r\n]*(?:-[a-z]*r[a-z]*|--recursive))"
            r"[^\r\n]*(?:\s+[\"']?(?:/|~(?:/|\s|[\"']?$)|\$HOME|"
            r"[A-Za-z]:[\\/](?:\s|[\"']?$)|"
            r"[A-Za-z]:[\\/]Users[\\/][^\\/\s\"']+(?:[\\/]?[\"']?(?:\s|$))|"
            r"\.git(?:/|\s|[\"']?$)))"
        ),
        "Recursive deletion of a broad, home, root, or Git target is blocked.",
    ),
    (
        re.compile(
            r"(?is)(?:^|[;&|]\s*)remove-item\b"
            r"(?=[^\r\n]*-(?:recurse|r)\b)[^\r\n]*"
            r"(?:[A-Za-z]:\\(?:\s|[\"']?$)|\\Users\\[^\\\s]+(?:\s|[\"']?$)|"
            r"\$HOME|~(?:\\|\s|[\"']?$)|\.git)"
        ),
        "Recursive PowerShell deletion of a broad, home, or Git target is blocked.",
    ),
    (
        re.compile(
            r"(?is)(?:^|[;&|]\s*)(?:cmd(?:\.exe)?\s+/[ck]\s+)?"
            r"(?:rd|rmdir)\b(?=[^\r\n]*/s\b)[^\r\n]*"
            r"(?:[A-Za-z]:[\\/](?:\s|[\"']?$)|"
            r"[A-Za-z]:[\\/]Users[\\/][^\\/\s\"']+(?:[\\/]?[\"']?(?:\s|$))|"
            r"%USERPROFILE%|\.git)"
        ),
        "Recursive cmd deletion of a broad, home, or Git target is blocked.",
    ),
    (
        re.compile(r"(?i)\bgit\b[^\r\n;&|]{0,400}\breset\s+--hard\b"),
        "git reset --hard can discard work and is blocked.",
    ),
    (
        re.compile(r"(?i)\bgit\b[^\r\n;&|]{0,400}\bclean\b[^\r\n;&|]*-[a-z]*f"),
        "Forced git clean can delete untracked work and is blocked.",
    ),
    (
        re.compile(
            r"(?i)\bgit\b[^\r\n;&|]{0,400}\bbranch\b[^\r\n;&|]*"
            r"(?:\s-D\b|--delete\b[^\r\n;&|]*--force\b|"
            r"--force\b[^\r\n;&|]*--delete\b|\s-d\b[^\r\n;&|]*\s-f\b)"
        ),
        "Forced branch deletion is blocked.",
    ),
    (
        re.compile(r"(?i)\bgit\b[^\r\n;&|]{0,400}\bpush\b[^\r\n;&|]*(?:--force(?:-with-lease)?|-f)\b"),
        "Force-push is blocked.",
    ),
    (
        re.compile(
            r"(?i)\bgit\b[^\r\n;&|]{0,400}\bpush\b[^\r\n;&|]*"
            r"(?:--delete\b|--mirror\b|--prune\b|(?:^|\s)[+:][^\s]+)"
        ),
        "Remote ref deletion, mirror push, or forced refspec is blocked.",
    ),
    (
        re.compile(r"(?i)\bgit\b[^\r\n;&|]{0,400}\bcheckout\b[^\r\n;&|]{0,240}\s--\s+"),
        "git checkout -- can discard worktree changes and is blocked.",
    ),
    (
        re.compile(
            r"(?i)\bgit\b[^\r\n;&|]{0,400}\bcheckout\b"
            r"(?:[^\r\n;&|]*(?:-f|--force)\b|[^\r\n;&|]*\s\.\s*$)"
        ),
        "Forced checkout or checkout of the whole worktree can discard changes and is blocked.",
    ),
    (
        re.compile(
            r"(?i)\bgit\b[^\r\n;&|]{0,400}\bswitch\b"
            r"[^\r\n;&|]*--discard-changes\b"
        ),
        "git switch --discard-changes can discard worktree changes and is blocked.",
    ),
    (
        re.compile(r"(?i)\bgit\b[^\r\n;&|]{0,400}\brestore\b[^\r\n;&|]*--worktree\b"),
        "git restore --worktree can discard worktree changes and is blocked.",
    ),
    (
        re.compile(r"(?i)\bgit\b[^\r\n;&|]{0,400}\brestore\b(?![^\r\n;&|]*--staged\b)"),
        "git restore can discard worktree changes and is blocked unless it only unstages.",
    ),
    (
        re.compile(r"(?i)(?:curl|wget|iwr|irm)\b[^\r\n|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh|pwsh|powershell|iex)\b"),
        "Piping a network response directly into a shell is blocked.",
    ),
    (
        re.compile(
            r"(?is)\b(?:cat|type|get-content|gc|head|tail|sed|awk|base64|"
            r"xxd|strings|less|more|certutil)\b[^\r\n]*"
            r"(?:\.env(?:\.(?:local|production|staging|development|test|[^.\s\"']+\.local))?|"
            r"\.ssh[\\/][^\\/\s\"']+|credentials?\.(?:json|ya?ml|ini|txt)|"
            r"service[_-]?account[^\\/\s\"']*\.json|id_(?:rsa|ed25519)|"
            r"[^\\/\s\"']+\.(?:pem|key))(?:[\"']?(?:\s|$)|[)\]}])"
        ),
        "Printing a likely credential file into model-visible output is blocked.",
    ),
    (
        re.compile(
            r"(?is)\b(?:rg|grep|findstr|select-string|more)\b"
            r"[^\r\n;&|]{0,500}(?:^|\s)[\"']?(?:"
            r"\.env(?:\.(?:local|production|staging|development|test|[^.\s\"']+\.local))?|"
            r"\.ssh[\\/][^\\/\s\"']+|credentials?\.(?:json|ya?ml|ini|txt)|"
            r"service[_-]?account[^\\/\s\"']*\.json|id_(?:rsa|ed25519)|"
            r"[^\\/\s\"']+\.(?:pem|key))[\"']?(?:\s|$)"
        ),
        "A command that may print a credential file into model-visible output is blocked.",
    ),
    (
        re.compile(
            r"(?is)\b(?:python(?:3)?|py|powershell|pwsh|cmd|node|"
            r"ruby|perl|php)\b"
            r"[^\r\n;&|]{0,700}(?:"
            r"\.env(?:\.(?:local|production|staging|development|test|[^.\s\"']+\.local))?|"
            r"\.ssh[\\/][^\\/\s\"']+|credentials?\.(?:json|ya?ml|ini|txt)|"
            r"service[_-]?account[^\\/\s\"']*\.json|id_(?:rsa|ed25519)|"
            r"[^\\/\s\"']+\.(?:pem|key))"
        ),
        "An interpreter command may expose credential material to model-visible output.",
    ),
)


def emit_denial(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    try:
        payload: Any = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        command = str(payload.get("tool_input", {}).get("command", ""))
    except (AttributeError, json.JSONDecodeError, TypeError, UnicodeDecodeError):
        print("{}")
        return 0

    for pattern, reason in RULES:
        if pattern.search(command):
            emit_denial(reason)
            return 0

    print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
