#!/usr/bin/env python3
"""Block merge/deploy/production-push verbs unless explicitly authorized.

WHY THIS EXISTS

EXT-2 (TODO.md, 2026-08-17), adopted from the external-landscape comparison's
"risk-classified pre-action guard" item (docs/analysis/2026-08-17-external-
landscape-comparison.md, citing Amazon's action risk classifier). It couples
the-loop-may-act.md's MAY / MAY-NOT list to an actual PreToolUse check instead
of leaving it as prose the loop is trusted to remember.

the-loop-may-act.md says the loop MAY NOT, without a per-action answer: merge
a pull request, deploy or touch production, push to main/master directly
(also covered by merges-are-the-operators.md and pre_push_gate.py), or run an
az/cloud deploy command. This hook is the mechanical half of that sentence.

STATUS: PAYLOAD ONLY, NOT WIRED

This file is not referenced in settings.json and does not run on any live
Bash call. Wiring it in is a separate, deliberate step (it would duplicate
pre_push_gate.py's main-branch check and needs to be reconciled with it
first, not layered blindly). Until then this is a testable unit with its own
selftest, per the oracle-selftest convention this repo already uses for
tools/audit/*.py.

CONTRACT

Reads the same PreToolUse Bash payload shape every other hook here reads
(JSON on stdin, `tool_input.command`). If the command matches a risk verb and
no authorization is present, it prints a denial reason naming
the-loop-may-act.md to stderr and exits 2, matching Claude Code's documented
PreToolUse block convention (nonzero exit blocks the tool call and stderr is
shown to the model). Authorization is either the environment variable
LOOP_MAY_ACT_AUTHORIZED=1 or a `--authorized-by-operator` token literally
present in the command string, and both are named explicitly in the denial
message so an operator (or a session acting on the operator's explicit
per-action answer) has a visible, auditable way to proceed.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

# Each entry: (compiled pattern, short label, the-loop-may-act.md clause it
# enforces). Kept as a plain tuple of tuples, not a class, because this data
# IS the rule and nothing here needs behavior beyond "does it match".
#
# Scope is deliberately narrow to the four MAY-NOT actions that are directly
# expressible as a Bash command verb: merging a PR, pushing straight to the
# deploy branch, and running a cloud deploy command. "Spend money" and
# "delete/overwrite" are not verb-shaped enough for a regex guard and stay
# governed by safety_gate.py and merges-are-the-operators.md instead.
RISK_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"(?i)\bgh\s+pr\s+merge\b"),
        "gh pr merge",
        "the-loop-may-act.md: 'Merge a pull request' is MAY NOT without a "
        "per-action answer; merges-are-the-operators.md is unchanged by this "
        "hook and outranks it.",
    ),
    (
        re.compile(r"(?i)\bgit\b[^\r\n;&|]{0,400}\bpush\b[^\r\n]*?(?:^|\s|:)(?:main|master)\s*$"),
        "git push (origin) main/master",
        "the-loop-may-act.md: a direct push to the deploy branch is not a "
        "MAY action; ADR-0012 says work ships through a PR.",
    ),
    (
        re.compile(r"(?i)\baz\s+(?:webapp|containerapp|functionapp|deployment)\b[^\r\n;&|]*\bdeploy\b|\baz\s+deployment\s+(?:group|sub)\s+create\b"),
        "az ... deploy",
        "the-loop-may-act.md: 'Deploy, or touch production' is MAY NOT; "
        "production-means-merged-and-smoked.md governs what production means.",
    ),
    (
        re.compile(r"(?i)\bazd\s+(?:up|deploy)\b"),
        "azd up / azd deploy",
        "the-loop-may-act.md: 'Deploy, or touch production' is MAY NOT.",
    ),
    (
        re.compile(r"(?i)\bwrangler\s+(?:deploy|publish)\b"),
        "wrangler deploy/publish",
        "the-loop-may-act.md: 'Deploy, or touch production' is MAY NOT.",
    ),
    (
        re.compile(r"(?i)\bnpm\s+run\s+deploy\b|\bkubectl\s+apply\b[^\r\n;&|]*\b(?:prod|production)\b"),
        "generic deploy / kubectl apply against prod",
        "the-loop-may-act.md: 'Deploy, or touch production' is MAY NOT.",
    ),
)

AUTH_ENV_VAR = "LOOP_MAY_ACT_AUTHORIZED"
AUTH_TOKEN = "--authorized-by-operator"


def is_authorized(command: str) -> bool:
    if os.environ.get(AUTH_ENV_VAR) == "1":
        return True
    return AUTH_TOKEN in command


def find_violation(command: str) -> tuple[str, str] | None:
    for pattern, label, reason in RISK_RULES:
        if pattern.search(command):
            return label, reason
    return None


def deny(label: str, reason: str) -> None:
    print(
        f"BLOCKED by pretooluse-risk-guard: matched risk verb '{label}'.\n{reason}\n"
        f"To proceed on an explicit per-action operator answer, set "
        f"{AUTH_ENV_VAR}=1 or include '{AUTH_TOKEN}' in the command.",
        file=sys.stderr,
    )


def evaluate(payload: dict[str, Any]) -> int:
    """Return the process exit code this hook would use for a given payload."""
    command = str(payload.get("tool_input", {}).get("command", ""))
    if not command:
        return 0
    violation = find_violation(command)
    if violation is None:
        return 0
    if is_authorized(command):
        return 0
    label, reason = violation
    deny(label, reason)
    return 2


def main() -> int:
    try:
        raw = sys.stdin.buffer.read()
        payload: Any = json.loads(raw.decode("utf-8"))
    except (AttributeError, json.JSONDecodeError, TypeError, UnicodeDecodeError):
        # Fail open on malformed input, same contract as every other hook here:
        # a broken guard must not brick the CLI.
        return 0
    if not isinstance(payload, dict):
        return 0
    return evaluate(payload)


def selftest() -> int:
    rc = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal rc
        print("  {}  {}".format("ok  " if ok else "MISS", label))
        if detail and not ok:
            print("        " + detail[:400])
        if not ok:
            rc = 1

    cases: list[tuple[str, dict[str, Any], int]] = [
        ("gh pr merge is blocked",
         {"tool_input": {"command": "gh pr merge 123 --squash"}}, 2),
        ("git push origin main is blocked",
         {"tool_input": {"command": "git push origin main"}}, 2),
        ("az webapp deploy is blocked",
         {"tool_input": {"command": "az webapp deploy --name x --resource-group y"}}, 2),
        ("azd up is blocked",
         {"tool_input": {"command": "azd up"}}, 2),
        ("wrangler deploy is blocked",
         {"tool_input": {"command": "wrangler deploy"}}, 2),
        ("a feature-branch push is allowed",
         {"tool_input": {"command": "git push -u origin feat/x"}}, 0),
        ("an ordinary read command is allowed",
         {"tool_input": {"command": "ls -la"}}, 0),
        ("gh pr view is not gh pr merge",
         {"tool_input": {"command": "gh pr view 123"}}, 0),
    ]
    for label, payload, expected in cases:
        got = evaluate(payload)
        check(label, got == expected, f"expected exit {expected}, got {got}")

    # authorization paths
    check("env-var authorization allows a merge",
          (lambda: (os.environ.__setitem__(AUTH_ENV_VAR, "1"),
                    evaluate({"tool_input": {"command": "gh pr merge 1"}}),
                    os.environ.pop(AUTH_ENV_VAR))[1])() == 0)
    check("inline authorization token allows a merge",
          evaluate({"tool_input": {
              "command": "gh pr merge 1 --authorized-by-operator"}}) == 0)

    # malformed / missing payload shapes fail open
    check("empty command does not block",
          evaluate({"tool_input": {}}) == 0)
    check("missing tool_input does not block",
          evaluate({}) == 0)

    print("\nVERDICT: {}".format(
        "risk verbs are blocked and authorized/benign commands pass"
        if rc == 0 else "selftest has failures above"))
    return rc


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        raise SystemExit(selftest())
    raise SystemExit(main())
