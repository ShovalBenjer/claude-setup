#!/usr/bin/env python3
"""Validate the lessons ledger for parse integrity and report health metrics.

state/lessons.jsonl is an append-only ledger of operational lessons. This tool
checks that the ledger is parseable and structurally sound, and reports schema
completeness as informational output. Because the ledger is append-only,
pre-existing schema gaps in older rows cannot be retroactively fixed, so the
gate fails only on structural issues that indicate the ledger is breaking.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

LESSONS_FILE = "state/lessons.jsonl"

_DATED_ID_RE = re.compile(r"^L-\d{4}-\d{2}-\d{2}-[a-z]$")
_LEGACY_ID_RE = re.compile(r"^L\d+$")


def load_lessons(project: str) -> tuple[list[dict], list[str]]:
    """Load lessons, returning (rows, parse_errors)."""
    path = os.path.join(project, LESSONS_FILE)
    if not os.path.isfile(path):
        return [], ["ledger file not found"]
    rows: list[dict] = []
    errors: list[str] = []
    with open(path) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                errors.append(f"line {i + 1}: malformed JSON: {e}")
    return rows, errors


def check(project: str) -> tuple[int, list[str]]:
    """Validate the lessons ledger and return (exit_code, findings)."""
    lessons, parse_errors = load_lessons(project)

    if parse_errors and not lessons:
        for e in parse_errors:
            print(f"  {e}")
        return 2, parse_errors

    if not lessons:
        print("  no lessons found")
        return 2, ["no lessons found"]

    findings: list[str] = []
    warnings: list[str] = []
    seen_ids: dict[str, int] = {}

    findings.extend(parse_errors)

    for i, row in enumerate(lessons):
        lid = row.get("id")

        if lid is None:
            findings.append(f"row {i}: missing 'id' field")
            continue

        if lid in seen_ids:
            warnings.append(
                f"{lid}: duplicate ID (rows {seen_ids[lid]} and {i})"
            )
        seen_ids[lid] = i

        if not _DATED_ID_RE.match(lid) and not _LEGACY_ID_RE.match(lid):
            findings.append(f"{lid}: unrecognised ID format")

        if "status" not in row:
            warnings.append(f"{lid}: missing 'status'")

        if not row.get("ts") and not row.get("date"):
            warnings.append(f"{lid}: missing timestamp")

        has_content = any(row.get(f) for f in ("lesson", "detail", "class"))
        if not has_content:
            warnings.append(f"{lid}: no content field")

        if row.get("status") == "closed" and not row.get("closed_by") and not row.get("fix"):
            warnings.append(f"{lid}: closed without explanation")

    open_count = sum(1 for r in lessons if r.get("status") == "open")
    closed_count = sum(1 for r in lessons if r.get("status") == "closed")
    other_count = len(lessons) - open_count - closed_count
    falsifier_count = sum(1 for r in lessons if r.get("falsifier"))

    print(f"  lessons: {len(lessons)} total, {open_count} open, {closed_count} closed, {other_count} other")
    print(f"  falsifiers: {falsifier_count}, warnings: {len(warnings)}")

    if findings:
        for f in findings:
            print(f"  ERROR: {f}")
        return 1, findings

    print("  ledger integrity OK")
    return 0, findings


def selftest() -> int:
    """Prove the checker works end to end."""
    failures: list[str] = []

    # Test 1: valid ledger passes
    with tempfile.TemporaryDirectory() as tmp:
        _write_lessons(tmp, [
            {"id": "L-2026-01-01-a", "status": "open", "ts": "2026-01-01", "lesson": "test"},
            {"id": "L-2026-01-01-b", "status": "closed", "ts": "2026-01-01", "lesson": "done", "fix": "fixed"},
        ])
        code, findings = check(tmp)
        if code != 0:
            failures.append(f"valid ledger returned {code}, expected 0")

    # Test 2: malformed JSON detected
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "lessons.jsonl"), "w") as f:
            f.write("{not valid json\n")
        code, findings = check(tmp)
        if code != 2:
            failures.append(f"malformed JSON returned {code}, expected 2")

    # Test 3: missing ID detected
    with tempfile.TemporaryDirectory() as tmp:
        _write_lessons(tmp, [{"status": "open", "lesson": "no id"}])
        code, findings = check(tmp)
        if code != 1:
            failures.append(f"missing ID returned {code}, expected 1")
        if not any("missing 'id'" in f for f in findings):
            failures.append("missing-id finding not produced")

    # Test 4: duplicate ID is a warning, not a failure
    with tempfile.TemporaryDirectory() as tmp:
        _write_lessons(tmp, [
            {"id": "L-2026-01-01-a", "status": "open", "ts": "2026-01-01", "lesson": "first"},
            {"id": "L-2026-01-01-a", "status": "open", "ts": "2026-01-01", "lesson": "dupe"},
        ])
        code, findings = check(tmp)
        if code != 0:
            failures.append(f"duplicate ID returned {code}, expected 0 (warning only)")

    # Test 5: unrecognised ID format detected
    with tempfile.TemporaryDirectory() as tmp:
        _write_lessons(tmp, [
            {"id": "BAD-FORMAT", "status": "open", "ts": "2026-01-01", "lesson": "bad id"},
        ])
        code, findings = check(tmp)
        if code != 1:
            failures.append(f"bad ID format returned {code}, expected 1")

    # Test 6: legacy IDs tolerated
    with tempfile.TemporaryDirectory() as tmp:
        _write_lessons(tmp, [
            {"id": "L001", "status": "open", "ts": "2026-01-01", "lesson": "legacy"},
        ])
        code, findings = check(tmp)
        if code != 0:
            failures.append(f"legacy ID returned {code}, expected 0")

    # Test 7: no file returns 2
    with tempfile.TemporaryDirectory() as tmp:
        code, _ = check(tmp)
        if code != 2:
            failures.append(f"no file returned {code}, expected 2")

    # Test 8: schema warnings do not fail
    with tempfile.TemporaryDirectory() as tmp:
        _write_lessons(tmp, [
            {"id": "L-2026-01-01-a", "lesson": "missing status and ts"},
        ])
        code, findings = check(tmp)
        if code != 0:
            failures.append(f"schema-warning-only returned {code}, expected 0")

    for line in failures:
        print(f"FAIL {line}")
    if not failures:
        print(f"PASS lesson_check selftest (8 checks)")
    return 1 if failures else 0


def _write_lessons(project: str, rows: list[dict]) -> None:
    state_dir = os.path.join(project, "state")
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "lessons.jsonl"), "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command", choices=("check", "selftest"), default="check", nargs="?"
    )
    parser.add_argument("--project", default=os.getcwd())
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()
    code, _ = check(args.project)
    return code


if __name__ == "__main__":
    sys.exit(main())
