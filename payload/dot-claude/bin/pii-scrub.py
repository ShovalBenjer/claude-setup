#!/usr/bin/env python3
"""
pii-scrub.py — PII / secret gate for workflow and agent outputs.

Usage:
    pii-scrub.py [--check | --redact] [FILE]
    cat FILE | pii-scrub.py [--check | --redact]

Modes:
    --check   (default) Print "file:line  <PATTERN-TYPE>" for each hit.
              NEVER prints the matched value. Exits 1 on any hit, 0 if clean.
    --redact  Replace all hits with <REDACTED> in place (rewrites the file,
              or writes to stdout if stdin mode).

Pattern coverage:
    email, phone (Israeli + international), national-ID-shaped, tabular PII
    headers, password=, api_key, secret, Bearer tokens, AWS AKIA keys,
    ADO/connection-string patterns, PEM private keys.
"""

import re
import sys
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# Pattern registry  — (name, compiled-regex)
# All patterns are non-capturing where possible; matched VALUE is discarded.
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern]] = [
    # --- credentials / secrets ---
    (
        "password-assignment",
        re.compile(
            r"(?i)password\s*[=:]\s*[\"']?[^\s\"',;#]{4,}",
        ),
    ),
    (
        "api-key",
        re.compile(
            r"(?i)api[-_]?key\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{8,}",
        ),
    ),
    (
        "secret-assignment",
        re.compile(
            r"(?i)\bsecret\s*[=:]\s*[\"']?[^\s\"',;#]{4,}",
        ),
    ),
    (
        "bearer-token",
        re.compile(
            r"\bBearer\s+[A-Za-z0-9._\-]{10,}",
        ),
    ),
    (
        "aws-access-key",
        re.compile(
            r"\bAKIA[0-9A-Z]{16}\b",
        ),
    ),
    (
        "connection-string",
        re.compile(
            r"(?i)(Account|Pwd|Password)=[^;\"'\s]{4,}",
        ),
    ),
    (
        "pem-private-key",
        re.compile(
            r"-----BEGIN .{1,30}PRIVATE KEY-----",
        ),
    ),
    # --- PII ---
    (
        "email",
        re.compile(
            r"[a-zA-Z0-9._%+\-]{2,}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        ),
    ),
    (
        "israeli-phone",
        re.compile(
            r"\b(05[0-9][-\s]?\d{7}|\+972[-\s]?5[0-9][-\s]?\d{7})\b",
        ),
    ),
    (
        "international-phone",
        re.compile(
            r"\+[1-9]\d{6,14}\b",
        ),
    ),
    (
        "national-id-shaped",
        re.compile(
            r"(?<!\d)\d{9}(?!\d)",
        ),
    ),
    (
        "tabular-pii-header",
        re.compile(
            r"(?i)\b(first_name|last_name|full_name|email|phone)\b",
        ),
    ),
]

_REDACT_SUB = "<REDACTED>"


def _scan_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Return list of (1-based line number, pattern_name) for every hit."""
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, start=1):
        for name, pattern in _PATTERNS:
            if pattern.search(line):
                hits.append((lineno, name))
                break  # one report per line (first-match wins; avoids duplicates)
    return hits


def _redact_line(line: str) -> str:
    for _, pattern in _PATTERNS:
        line = pattern.sub(_REDACT_SUB, line)
    return line


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PII/secret gate — check or redact a file.",
        add_help=True,
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="File to scan. Omit to read from stdin.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--check",
        action="store_true",
        default=True,
        help="Report hits without printing matched values (default).",
    )
    mode_group.add_argument(
        "--redact",
        action="store_true",
        default=False,
        help="Replace matches with <REDACTED> in place.",
    )
    args = parser.parse_args()

    # --redact overrides the --check default
    redact_mode = args.redact

    # --- read input ---
    if args.file:
        path = Path(args.file)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"pii-scrub: cannot read {args.file}: {exc}", file=sys.stderr)
            return 2
        source_label = str(path)
    else:
        text = sys.stdin.read()
        source_label = "<stdin>"

    lines = text.splitlines(keepends=True)

    # --- redact mode ---
    if redact_mode:
        redacted = [_redact_line(ln) for ln in lines]
        result = "".join(redacted)
        if args.file:
            Path(args.file).write_text(result, encoding="utf-8")
            print(f"pii-scrub: redacted in place → {args.file}", file=sys.stderr)
        else:
            sys.stdout.write(result)
        return 0

    # --- check mode ---
    hits = _scan_lines(lines)
    if not hits:
        print(f"pii-scrub: CLEAN — {source_label}", file=sys.stderr)
        return 0

    for lineno, pattern_name in hits:
        # Print location + type ONLY — never the matched value
        print(f"{source_label}:{lineno}  <{pattern_name}>")

    print(
        f"\npii-scrub: BLOCKED — {len(hits)} hit(s) in {source_label}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
