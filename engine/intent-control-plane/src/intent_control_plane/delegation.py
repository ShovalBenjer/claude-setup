"""Delegation flywheel: executor choice, ranked repair queue, verify gate.

Pure functions only, no shell calls except in `main`. Parts:

- `choose_executor`: Codex-first, Haiku-fallback routing over the a2a-codex-call.sh
  JSON contract (see ~/.claude/bin/a2a-codex-call.sh). That contract emits
  `{"state": "completed" | "failed" | "timeout" | "rate_limited" | "auth_failed", ...}`.
  Only `"completed"` routes to Codex; every other observed state, and any unknown or
  missing state, fails toward Haiku (the executor that is still available).
- `build_queue`: turns a `standards.score_repo()` scorecard list into a ranked, flat
  repair queue, one item per repo per failing dimension.
- `render_queue`: renders a `build_queue()` queue as a markdown table.
- `verify_gate`: compares a before/after `score_repo()` pair plus a test-pass flag into
  a single pass/fail verdict for whether an automated repair round counted.
- `main`: wires the live estate scorecard (`standards.score_projects()`) into
  `build_queue()` and prints the rendered queue.

Run: `python -m intent_control_plane.delegation [~/projects]`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from intent_control_plane import standards


def choose_executor(a2a_result: dict[str, Any]) -> str:
    """Codex-first, Haiku-fallback executor choice from an a2a-codex-call.sh result.

    Contract: `a2a_result` is the parsed JSON from a2a-codex-call.sh, at minimum
    `{"state": str}`. `state == "completed"` routes to `"codex"`. Every other
    state ("rate_limited", "auth_failed", "failed", "timeout", any unrecognized
    value, or a missing "state" key) routes to `"haiku"`, since Haiku is the
    fallback executor that stays available when Codex is rate-limited, unauthed,
    erroring, or the contract itself is malformed.
    """
    if a2a_result.get("state") == "completed":
        return "codex"
    return "haiku"


def build_queue(scorecard: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank a `standards.score_repo()` scorecard into a flat repair queue.

    One item per repo per FAILING dimension (passed < total). Each item is
    `{"repo", "dimension", "failing_checks", "priority"}` where `failing_checks`
    is the dimension's `gaps` list and `priority` is `total - passed` (the size
    of the gap). The queue is sorted by priority descending (biggest gaps
    first), then by repo name, then by dimension name for a stable order among
    ties.
    """
    queue: list[dict[str, Any]] = []
    for record in scorecard:
        repo = record["name"]
        for dimension, stats in record["dimensions"].items():
            passed, total = stats["passed"], stats["total"]
            if passed < total:
                queue.append({
                    "repo": repo,
                    "dimension": dimension,
                    "failing_checks": stats["gaps"],
                    "priority": total - passed,
                })
    queue.sort(key=lambda item: (-item["priority"], item["repo"], item["dimension"]))
    return queue


def render_queue(queue: list[dict[str, Any]]) -> str:
    """Render a `build_queue()` queue as a markdown table, biggest gap first.

    Columns: Repo | Dimension | Priority | Failing checks, with `failing_checks`
    joined by ", ". Header and separator are always present, even for an empty
    queue (a header-only table, not an empty string).
    """
    head = "| Repo | Dimension | Priority | Failing checks |"
    sep = "|---|---|---|---|"
    lines = [head, sep]
    for item in queue:
        checks = ", ".join(item["failing_checks"])
        lines.append(f"| {item['repo']} | {item['dimension']} | {item['priority']} | {checks} |")
    return "\n".join(lines)


def _parse_score(record: dict[str, Any]) -> int:
    """Extract the passed-count from a `score_repo()` record's "p/t" score string."""
    passed, _, _ = record["score"].partition("/")
    return int(passed)


def verify_gate(before: dict[str, Any], after: dict[str, Any], tests_passed: bool) -> dict[str, Any]:
    """Gate one repair round: did it actually improve the score, with tests green?

    `before`/`after` are `standards.score_repo()` records (each carries a "p/t"
    score string). Returns `{"counts", "delta", "reason"}`. `counts` is True only
    when `tests_passed` is True AND the after-passed count is strictly greater
    than the before-passed count; a rise in score with failing tests, or passing
    tests with a flat or dropped score, does not count. `delta` is the raw
    passed-count change (after minus before), which can be zero or negative.
    """
    before_passed = _parse_score(before)
    after_passed = _parse_score(after)
    delta = after_passed - before_passed
    if not tests_passed:
        reason = "tests failed"
    elif delta <= 0:
        reason = "score did not improve"
    else:
        reason = "score improved and tests passed"
    counts = tests_passed and delta > 0
    return {"counts": counts, "delta": delta, "reason": reason}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0]).expanduser() if args else Path.home() / "projects"
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}))
        return 2
    scorecard = standards.score_projects(root)
    queue = build_queue(scorecard)
    print(render_queue(queue))
    print(json.dumps({"count": len(queue)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
