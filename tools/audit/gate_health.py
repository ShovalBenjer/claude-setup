#!/usr/bin/env python3
"""Validate the gate-run ledger for structural integrity.

state/gate-runs.jsonl is the meta-record of every quality gate run. At 19K+
rows it is the largest ledger in the repo and nothing validated its structure.
Measured 2026-08-30: 10 rows carry a domain verdict as an integer (exit code 2)
instead of the string "N/A", a type inconsistency that downstream consumers
would silently miscount.

Structural errors (parse failures, missing required fields) fail the gate.
Data quality issues in existing rows (non-string domain verdicts, verdict
contradictions) are warnings because the ledger is append-only and historical
rows cannot be retroactively fixed. Schema-evolution fields (duration_seconds,
run_id, unmeasured) are optional: older rows predate them and their absence
is expected, not an error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

LEDGER_FILE = "state/gate-runs.jsonl"

REQUIRED_FIELDS = {"ts", "project", "commit", "verdict", "domains"}
VALID_VERDICTS = {"PASS", "FAIL", "PARTIAL"}
VALID_DOMAIN_STATUSES = {"PASS", "FAIL", "N/A", "WAIVED", "UNCOVERED"}

_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def load_rows(project: str) -> tuple[list[dict], list[str]]:
    path = os.path.join(project, LEDGER_FILE)
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
    rows, parse_errors = load_rows(project)

    if parse_errors and not rows:
        for e in parse_errors:
            print(f"  {e}")
        return 2, parse_errors

    if not rows:
        print("  no gate-run entries found")
        return 2, ["no gate-run entries found"]

    findings: list[str] = []
    warnings: list[str] = []
    run_ids: dict[str, list[int]] = {}

    findings.extend(parse_errors)

    non_string_domains = 0

    for i, row in enumerate(rows):
        missing = REQUIRED_FIELDS - set(row.keys())
        if missing:
            findings.append(f"row {i}: missing required field(s): {', '.join(sorted(missing))}")
            continue

        ts = row.get("ts", "")
        if isinstance(ts, str) and not _TS_RE.match(ts):
            findings.append(f"row {i}: timestamp '{ts}' does not match ISO format")

        verdict = row.get("verdict")
        if verdict not in VALID_VERDICTS:
            findings.append(f"row {i}: invalid verdict '{verdict}'")

        domains = row.get("domains")
        if not isinstance(domains, dict):
            findings.append(f"row {i}: domains is not a dict")
            continue

        for dname, dval in domains.items():
            if not isinstance(dval, str):
                non_string_domains += 1
                if non_string_domains <= 5:
                    warnings.append(
                        f"row {i}: domain '{dname}' has non-string verdict "
                        f"{dval!r} (type {type(dval).__name__})"
                    )
            elif dval not in VALID_DOMAIN_STATUSES:
                findings.append(f"row {i}: domain '{dname}' has unrecognised status '{dval}'")

        blocking = row.get("blocking")
        if blocking is not None and not isinstance(blocking, list):
            warnings.append(f"row {i}: blocking is not a list")

        rid = row.get("run_id")
        if rid is not None:
            proj = row.get("project", "")
            key = f"{proj}:{rid}"
            if key not in run_ids:
                run_ids[key] = []
            run_ids[key].append(i)

    if non_string_domains > 5:
        warnings.append(
            f"... and {non_string_domains - 5} more non-string domain verdicts "
            f"({non_string_domains} total)"
        )

    for key, indices in run_ids.items():
        if len(indices) > 1:
            warnings.append(f"duplicate run_id {key} at rows {indices}")

    total = len(rows)
    projects = len({r.get("project") for r in rows})
    pass_count = sum(1 for r in rows if r.get("verdict") == "PASS")
    fail_count = sum(1 for r in rows if r.get("verdict") == "FAIL")
    partial_count = sum(1 for r in rows if r.get("verdict") == "PARTIAL")

    print(f"  rows: {total}, projects: {projects}")
    print(f"  verdicts: {pass_count} PASS, {fail_count} FAIL, {partial_count} PARTIAL")
    print(f"  warnings: {len(warnings)}, non-string domains: {non_string_domains}")

    if findings:
        for f in findings:
            print(f"  ERROR: {f}")
        return 1, findings

    print("  ledger integrity OK")
    return 0, findings


def selftest() -> int:
    failures: list[str] = []

    # Test 1: valid ledger passes
    with tempfile.TemporaryDirectory() as tmp:
        _write_rows(tmp, [
            {
                "ts": "2026-01-01T00:00:00", "project": "test",
                "project_path": "/tmp/test", "commit": "abc123",
                "dirty": False, "fingerprint": "fp1", "partial": False,
                "verdict": "PASS", "domains": {"build": "PASS", "unit": "PASS"},
                "blocking": [],
            },
        ])
        code, findings = check(tmp)
        if code != 0:
            failures.append(f"valid entry returned {code}, expected 0")

    # Test 2: malformed JSON detected
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "gate-runs.jsonl"), "w") as f:
            f.write("{not valid json\n")
        code, findings = check(tmp)
        if code != 2:
            failures.append(f"malformed JSON returned {code}, expected 2")

    # Test 3: missing required field detected
    with tempfile.TemporaryDirectory() as tmp:
        _write_rows(tmp, [
            {"ts": "2026-01-01T00:00:00", "project": "test"},
        ])
        code, findings = check(tmp)
        if code != 1:
            failures.append(f"missing fields returned {code}, expected 1")
        if not any("missing required" in f for f in findings):
            failures.append("missing-field finding not produced")

    # Test 4: non-string domain verdict is a warning, not a failure
    with tempfile.TemporaryDirectory() as tmp:
        _write_rows(tmp, [
            {
                "ts": "2026-01-01T00:00:00", "project": "test",
                "commit": "abc", "verdict": "PASS",
                "domains": {"build": "PASS", "todo_inbox": 2},
                "blocking": [],
            },
        ])
        code, findings = check(tmp)
        if code != 0:
            failures.append(f"non-string domain returned {code}, expected 0 (warning only)")

    # Test 5: invalid verdict value detected
    with tempfile.TemporaryDirectory() as tmp:
        _write_rows(tmp, [
            {
                "ts": "2026-01-01T00:00:00", "project": "test",
                "commit": "abc", "verdict": "MAYBE",
                "domains": {"build": "PASS"}, "blocking": [],
            },
        ])
        code, findings = check(tmp)
        if code != 1:
            failures.append(f"invalid verdict returned {code}, expected 1")

    # Test 6: no file returns 2
    with tempfile.TemporaryDirectory() as tmp:
        code, _ = check(tmp)
        if code != 2:
            failures.append(f"no file returned {code}, expected 2")

    # Test 7: schema-evolution fields don't cause false positives
    with tempfile.TemporaryDirectory() as tmp:
        _write_rows(tmp, [
            {
                "ts": "2026-01-01T00:00:00", "project": "test",
                "commit": "abc", "verdict": "PASS",
                "domains": {"build": "PASS"}, "blocking": [],
            },
            {
                "ts": "2026-01-02T00:00:00", "project": "test",
                "commit": "def", "verdict": "PASS",
                "domains": {"build": "PASS"}, "blocking": [],
                "duration_seconds": 5.0, "run_id": "abc123",
            },
        ])
        code, findings = check(tmp)
        if code != 0:
            failures.append(f"mixed-schema entries returned {code}, expected 0")

    # Test 8: PARTIAL is a valid verdict
    with tempfile.TemporaryDirectory() as tmp:
        _write_rows(tmp, [
            {
                "ts": "2026-01-01T00:00:00", "project": "test",
                "commit": "abc", "verdict": "PARTIAL",
                "domains": {"build": "PASS"}, "blocking": [],
            },
        ])
        code, findings = check(tmp)
        if code != 0:
            failures.append(f"PARTIAL verdict returned {code}, expected 0")

    for line in failures:
        print(f"FAIL {line}")
    if not failures:
        print(f"PASS gate_health selftest (8 checks)")
    return 1 if failures else 0


def _write_rows(project: str, rows: list[dict]) -> None:
    state_dir = os.path.join(project, "state")
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "gate-runs.jsonl"), "w") as f:
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
