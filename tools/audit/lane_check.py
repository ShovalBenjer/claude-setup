#!/usr/bin/env python3
"""Lane-enforcement oracle: the most recent claims row must name this repo's lane.

Why this exists: cross-lane work is the most frequently logged lesson in
state/lessons.jsonl. A session that starts in claude-setup belongs to Lane A
(harness). A session whose claims row says Lane B, C, or D is doing another
lane's work from the wrong checkout, which is the structural defect charters.md
exists to prevent.

What it checks:
  1. state/claims.jsonl exists and has at least one row.
  2. The most recent row carries a lane field.
  3. That lane, resolved through tools/lib/lanes.py, is "A" (the harness lane).

Exit codes: 0 = pass, 1 = fail, 2 = cannot measure.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

EXPECTED_LANE = "A"
EXPECTED_LANE_NAME = "claude-setup harness"


def _find_project(project: str) -> str | None:
    claims = os.path.join(project, "state", "claims.jsonl")
    if os.path.isfile(claims):
        return claims
    return None


def _read_latest_claim(path: str) -> dict | None:
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
    return last


def _resolve_lane(claim: dict) -> tuple[str, str]:
    lane = claim.get("lane", "?")
    ts = claim.get("ts") or claim.get("claimed_at") or claim.get("date") or ""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "lib"))
    import lanes
    return lanes.resolve(lane, ts)


def run_check(project: str) -> int:
    claims_path = _find_project(project)
    if claims_path is None:
        print("CANNOT MEASURE: state/claims.jsonl not found")
        return 2

    claim = _read_latest_claim(claims_path)
    if claim is None:
        print("FAIL: state/claims.jsonl is empty (no claim rows)")
        return 1

    letter, name = _resolve_lane(claim)
    claim_id = claim.get("id") or claim.get("proposal_id") or "(unnamed)"
    claim_date = claim.get("date") or claim.get("claimed_at") or claim.get("ts") or "?"

    if letter == EXPECTED_LANE:
        print(f"PASS: latest claim '{claim_id}' ({claim_date}) is lane {letter} ({name})")
        return 0

    print(f"FAIL: latest claim '{claim_id}' ({claim_date}) is lane {letter} ({name}), "
          f"expected lane {EXPECTED_LANE} ({EXPECTED_LANE_NAME})")
    return 1


def selftest() -> int:
    failures = []

    def check(label: str, got, want):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    with tempfile.TemporaryDirectory() as tmp:
        state = os.path.join(tmp, "state")
        os.makedirs(state)
        claims = os.path.join(state, "claims.jsonl")

        # 1. missing file
        os.makedirs(os.path.join(tmp, "empty_proj", "state"), exist_ok=True)
        check("missing claims", run_check(os.path.join(tmp, "empty_proj")), 2)

        # 2. empty file
        with open(claims, "w") as f:
            f.write("")
        check("empty file", run_check(tmp), 1)

        # 3. correct lane A (current scheme)
        with open(claims, "w") as f:
            f.write(json.dumps({"id": "test", "lane": "A",
                                "date": "2026-08-30"}) + "\n")
        check("lane A passes", run_check(tmp), 0)

        # 4. wrong lane B
        with open(claims, "w") as f:
            f.write(json.dumps({"id": "test", "lane": "B",
                                "date": "2026-08-30"}) + "\n")
        check("lane B fails", run_check(tmp), 1)

        # 5. historical lane B (pre-cutover = harness = A)
        with open(claims, "w") as f:
            f.write(json.dumps({"proposal_id": "old", "lane": "B",
                                "ts": "2026-07-29"}) + "\n")
        check("pre-cutover B resolves to A", run_check(tmp), 0)

        # 6. multiple rows, latest wins
        with open(claims, "w") as f:
            f.write(json.dumps({"id": "first", "lane": "B",
                                "date": "2026-08-30"}) + "\n")
            f.write(json.dumps({"id": "second", "lane": "A",
                                "date": "2026-08-30"}) + "\n")
        check("latest row wins", run_check(tmp), 0)

        # 7. latest row is wrong lane
        with open(claims, "w") as f:
            f.write(json.dumps({"id": "first", "lane": "A",
                                "date": "2026-08-30"}) + "\n")
            f.write(json.dumps({"id": "second", "lane": "C",
                                "date": "2026-08-30"}) + "\n")
        check("latest wrong lane fails", run_check(tmp), 1)

    for line in failures:
        print(f"FAIL {line}")
    n = len(failures)
    print(f"lane_check selftest: {7 - n}/7 passed, {n} failed")
    return n


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(1 if selftest() else 0)
    project = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(run_check(project))
