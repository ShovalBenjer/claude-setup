#!/usr/bin/env python3
"""Create and validate an implementation evidence record."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "implementation-proof.v1"
RISK_LEVELS = {"low", "medium", "high"}
CHECK_STATUSES = {"pass", "fail", "not_run", "not_applicable"}
CLAIM_STATUSES = {"verified", "staged", "assumed", "rejected"}
STRONG_CLAIM = re.compile(
    r"\b(best|optimal|optimized|fastest|complete|production[- ]ready)\b",
    re.IGNORECASE,
)
NEGATED_STRONG_CLAIM = re.compile(
    r"\b(?:not|never|isn't|is not|cannot be)\b.{0,32}"
    r"\b(?:best|optimal|optimized|fastest|complete|production[- ]ready)\b",
    re.IGNORECASE,
)


def make_template(goal: str, risk: str) -> dict[str, Any]:
    record = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "goal": goal,
        "risk": risk,
        "constraints": [],
        "acceptance_criteria": [
            {"id": "AC1", "text": "Replace with observable behavior", "oracle": ""}
        ],
        "candidates": [
            {
                "id": "simple",
                "approach": "Simplest correct implementation",
                "time_complexity": "unknown",
                "space_complexity": "unknown",
                "advantages": [],
                "risks": [],
                "when_it_wins": "",
            },
            {
                "id": "alternative",
                "approach": "A materially different viable implementation",
                "time_complexity": "unknown",
                "space_complexity": "unknown",
                "advantages": [],
                "risks": [],
                "when_it_wins": "",
            },
        ],
        "selected": {"candidate_id": "", "rationale": "", "evidence": []},
        "loop_audit": [],
        "verification": {
            "checks": [
                {
                    "id": "C1",
                    "kind": "test",
                    "command": "",
                    "status": "not_run",
                    "exit_code": None,
                    "ran_at": "",
                    "output_sha256": "",
                    "output_digest": "",
                    "repo_state": {
                        "cwd": "",
                        "captured_at": "",
                        "git_commit": None,
                        "diff_sha256": None,
                    },
                    "acceptance_ids": ["AC1"],
                }
            ],
            "benchmark": {
                "status": "not_applicable",
                "command": "",
                "candidate_results": {},
                "conditions": "",
            },
            "independent_review": {
                "status": "not_run",
                "reviewer_id": "",
                "reviewed_at": "",
                "reviewer_context": "",
                "evidence": [],
                "findings": [],
            },
        },
        "claims": [
            {"claim": "", "status": "assumed", "evidence": []}
        ],
        "residual_risks": [],
    }
    if risk == "high":
        record["candidates"].append(
            {
                "id": "third-option",
                "approach": "A third materially different viable implementation",
                "time_complexity": "unknown",
                "space_complexity": "unknown",
                "advantages": [],
                "risks": [],
                "when_it_wins": "",
            }
        )
    return record


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(record.get("schema_version") == SCHEMA_VERSION,
            f"schema_version must be {SCHEMA_VERSION}", errors)
    require(bool(str(record.get("goal", "")).strip()), "goal is required", errors)

    risk = record.get("risk")
    require(risk in RISK_LEVELS, f"risk must be one of {sorted(RISK_LEVELS)}", errors)

    criteria = record.get("acceptance_criteria")
    require(isinstance(criteria, list) and bool(criteria),
            "at least one acceptance criterion is required", errors)
    criterion_ids: set[str] = set()
    if isinstance(criteria, list):
        for index, item in enumerate(criteria):
            require(isinstance(item, dict), f"acceptance_criteria[{index}] must be an object", errors)
            if not isinstance(item, dict):
                continue
            cid = str(item.get("id", "")).strip()
            require(bool(cid), f"acceptance_criteria[{index}].id is required", errors)
            require(cid not in criterion_ids, f"duplicate acceptance id: {cid}", errors)
            criterion_ids.add(cid)
            require(bool(str(item.get("text", "")).strip()),
                    f"acceptance criterion {cid or index} needs text", errors)
            require(bool(str(item.get("oracle", "")).strip()),
                    f"acceptance criterion {cid or index} needs an observable oracle", errors)

    candidates = record.get("candidates")
    minimum = 3 if risk == "high" else 2
    require(isinstance(candidates, list) and len(candidates) >= minimum,
            f"{risk or 'selected'} risk requires at least {minimum} candidates", errors)
    candidate_ids: set[str] = set()
    if isinstance(candidates, list):
        for index, item in enumerate(candidates):
            require(isinstance(item, dict), f"candidates[{index}] must be an object", errors)
            if not isinstance(item, dict):
                continue
            cid = str(item.get("id", "")).strip()
            require(bool(cid), f"candidates[{index}].id is required", errors)
            require(cid not in candidate_ids, f"duplicate candidate id: {cid}", errors)
            candidate_ids.add(cid)
            for field in ("approach", "time_complexity", "space_complexity", "when_it_wins"):
                require(bool(str(item.get(field, "")).strip()),
                        f"candidate {cid or index} needs {field}", errors)
            require(bool(item.get("risks")), f"candidate {cid or index} needs risks", errors)

    selected = record.get("selected")
    require(isinstance(selected, dict), "selected must be an object", errors)
    if isinstance(selected, dict):
        selected_id = str(selected.get("candidate_id", "")).strip()
        require(selected_id in candidate_ids,
                "selected.candidate_id must match a candidate", errors)
        require(bool(str(selected.get("rationale", "")).strip()),
                "selected.rationale is required", errors)
        require(bool(selected.get("evidence")), "selected.evidence is required", errors)

    loop_audit = record.get("loop_audit", [])
    require(isinstance(loop_audit, list), "loop_audit must be a list", errors)
    if isinstance(loop_audit, list):
        for index, item in enumerate(loop_audit):
            require(isinstance(item, dict), f"loop_audit[{index}] must be an object", errors)
            if not isinstance(item, dict):
                continue
            require(bool(str(item.get("purpose", "")).strip()),
                    f"loop_audit[{index}] needs purpose", errors)
            require(bool(str(item.get("bound", "")).strip()),
                    f"loop_audit[{index}] needs a bound", errors)
            require(bool(str(item.get("content_sha256", "")).strip()),
                    f"loop_audit[{index}] needs content_sha256", errors)
            require(bool(item.get("alternatives_considered")),
                    f"loop_audit[{index}] needs alternatives_considered", errors)
            require(item.get("n_plus_one_checked") is True,
                    f"loop_audit[{index}] must check N+1/I-O behavior", errors)

    verification = record.get("verification")
    require(isinstance(verification, dict), "verification must be an object", errors)
    checks: list[dict[str, Any]] = []
    benchmark: dict[str, Any] = {}
    review: dict[str, Any] = {}
    if isinstance(verification, dict):
        raw_checks = verification.get("checks")
        require(isinstance(raw_checks, list) and bool(raw_checks),
                "verification.checks requires at least one check", errors)
        if isinstance(raw_checks, list):
            checks = [c for c in raw_checks if isinstance(c, dict)]
            covered: set[str] = set()
            check_ids: set[str] = set()
            for index, check in enumerate(raw_checks):
                require(isinstance(check, dict), f"verification.checks[{index}] must be an object", errors)
                if not isinstance(check, dict):
                    continue
                status = check.get("status")
                require(status in CHECK_STATUSES,
                        f"verification.checks[{index}].status is invalid", errors)
                require(bool(str(check.get("kind", "")).strip()),
                        f"verification.checks[{index}].kind is required", errors)
                check_id = str(check.get("id", "")).strip()
                require(bool(check_id),
                        f"verification.checks[{index}].id is required", errors)
                require(check_id not in check_ids,
                        f"duplicate verification check id: {check_id}", errors)
                check_ids.add(check_id)
                require(status != "fail",
                        f"verification.checks[{index}] is failing", errors)
                acceptance_ids = {str(x) for x in check.get("acceptance_ids", [])}
                require(bool(acceptance_ids),
                        f"verification.checks[{index}] needs acceptance_ids", errors)
                unknown = acceptance_ids - criterion_ids
                require(not unknown,
                        f"verification.checks[{index}] has unknown acceptance ids: {sorted(unknown)}", errors)
                if status == "pass":
                    require(bool(str(check.get("command", "")).strip()),
                            f"passing check {index} needs its command", errors)
                    require(check.get("exit_code") == 0,
                            f"passing check {index} needs exit_code 0", errors)
                    require(bool(str(check.get("ran_at", "")).strip()),
                            f"passing check {index} needs ran_at", errors)
                    require(bool(str(check.get("output_sha256", "")).strip()),
                            f"passing check {index} needs output_sha256", errors)
                    require(bool(str(check.get("output_digest", "")).strip()),
                            f"passing check {index} needs output_digest", errors)
                    repo_state = check.get("repo_state")
                    require(isinstance(repo_state, dict),
                            f"passing check {index} needs repo_state", errors)
                    if isinstance(repo_state, dict):
                        require(bool(str(repo_state.get("cwd", "")).strip()),
                                f"passing check {index} repo_state needs cwd", errors)
                        require(bool(str(repo_state.get("captured_at", "")).strip()),
                                f"passing check {index} repo_state needs captured_at", errors)
                    covered.update(acceptance_ids)
            missing = criterion_ids - covered
            require(not missing,
                    f"no passing verification covers acceptance ids: {sorted(missing)}", errors)

        raw_benchmark = verification.get("benchmark")
        require(isinstance(raw_benchmark, dict), "verification.benchmark must be an object", errors)
        if isinstance(raw_benchmark, dict):
            benchmark = raw_benchmark
            require(benchmark.get("status") in CHECK_STATUSES,
                    "verification.benchmark.status is invalid", errors)
            require(benchmark.get("status") != "fail",
                    "verification.benchmark is failing", errors)
            if benchmark.get("status") == "pass":
                require(bool(str(benchmark.get("command", "")).strip()),
                        "passing benchmark needs command", errors)
                require(bool(str(benchmark.get("conditions", "")).strip()),
                        "passing benchmark needs conditions", errors)
                results = benchmark.get("candidate_results", {})
                require(isinstance(results, dict) and len(results) >= 2,
                        "passing benchmark needs at least two candidate_results", errors)
                if isinstance(results, dict):
                    unknown_results = set(results) - candidate_ids
                    require(not unknown_results,
                            f"benchmark has unknown candidate ids: {sorted(unknown_results)}", errors)
                    selected_id = str(record.get("selected", {}).get("candidate_id", ""))
                    require(selected_id in results,
                            "benchmark must include the selected candidate", errors)

        raw_review = verification.get("independent_review")
        require(isinstance(raw_review, dict),
                "verification.independent_review must be an object", errors)
        if isinstance(raw_review, dict):
            review = raw_review
            require(review.get("status") in CHECK_STATUSES,
                    "independent_review.status is invalid", errors)
            require(review.get("status") != "fail",
                    "independent_review is failing", errors)
            if risk == "high":
                require(review.get("status") == "pass",
                        "high-risk work requires a passing independent review", errors)
                require(bool(str(review.get("reviewer_id", "")).strip()),
                        "high-risk review needs reviewer_id", errors)
                require(bool(str(review.get("reviewed_at", "")).strip()),
                        "high-risk review needs reviewed_at", errors)
                require(bool(str(review.get("reviewer_context", "")).strip()),
                        "high-risk review needs reviewer_context", errors)
                require(bool(review.get("evidence")),
                        "high-risk review needs evidence", errors)

    claims = record.get("claims")
    require(isinstance(claims, list) and bool(claims), "at least one claim is required", errors)
    strong_claim_present = False
    if isinstance(claims, list):
        for index, claim in enumerate(claims):
            require(isinstance(claim, dict), f"claims[{index}] must be an object", errors)
            if not isinstance(claim, dict):
                continue
            text = str(claim.get("claim", "")).strip()
            status = claim.get("status")
            require(bool(text), f"claims[{index}].claim is required", errors)
            require(status in CLAIM_STATUSES, f"claims[{index}].status is invalid", errors)
            if status == "verified":
                require(bool(claim.get("evidence")),
                        f"verified claim {index} needs evidence", errors)
            strong_claim_present = (
                strong_claim_present
                or (
                    status == "verified"
                    and bool(STRONG_CLAIM.search(text))
                    and not bool(NEGATED_STRONG_CLAIM.search(text))
                )
            )

    if strong_claim_present:
        require(benchmark.get("status") == "pass",
                "best/optimal/optimized/fastest/complete claims require a passing benchmark", errors)
        require(len(benchmark.get("candidate_results", {})) >= 2,
                "strong claims require benchmark results for at least two candidates", errors)

    require(isinstance(record.get("residual_risks"), list),
            "residual_risks must be a list", errors)
    return errors


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("proof record must be a JSON object")
    return data


def command_new(args: argparse.Namespace) -> int:
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(make_template(args.goal, args.risk), indent=2) + "\n",
                    encoding="utf-8")
    print(path)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    errors = validate(load(Path(args.path)))
    result = {"valid": not errors, "errors": errors}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


def command_summary(args: argparse.Namespace) -> int:
    record = load(Path(args.path))
    errors = validate(record)
    selected = record.get("selected", {})
    statuses = [item.get("status") for item in record.get("verification", {}).get("checks", [])]
    print(json.dumps({
        "goal": record.get("goal"),
        "risk": record.get("risk"),
        "selected": selected.get("candidate_id"),
        "verification_statuses": statuses,
        "valid": not errors,
        "error_count": len(errors),
        "residual_risks": record.get("residual_risks", []),
    }, indent=2))
    return 0 if not errors else 1


def capture_repo_state(cwd: Path) -> dict[str, Any]:
    cwd = cwd.resolve()
    if cwd.is_file():
        cwd = cwd.parent
    state: dict[str, Any] = {
        "cwd": str(cwd),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": None,
        "diff_sha256": None,
    }
    try:
        root = next(
            (parent for parent in (cwd, *cwd.parents) if (parent / ".git").exists()),
            None,
        )
        home = Path.home().resolve()
        if root is None or root.resolve() == home or root.parent == root:
            return state
        root = root.resolve()
        git = ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root)]
        state["cwd"] = str(root)
        commit = subprocess.run(
            [*git, "rev-parse", "HEAD"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        if commit.returncode == 0:
            state["git_commit"] = commit.stdout.decode("utf-8", errors="replace").strip()
            unstaged = subprocess.run(
                [*git, "diff", "--binary", "HEAD"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            staged = subprocess.run(
                [*git, "diff", "--binary", "--cached"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            if unstaged.returncode == 0 and staged.returncode == 0:
                untracked_hash = hashlib.sha256()
                untracked = subprocess.run(
                    [*git, "ls-files", "--others", "--exclude-standard", "-z"],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                if untracked.returncode != 0:
                    return state
                raw_paths = sorted(filter(None, untracked.stdout.split(b"\0")))
                if len(raw_paths) > 5000:
                    return state
                total_bytes = 0
                sensitive_directories = {".ssh", ".aws", ".azure", ".claude", ".codex"}
                sensitive_names = {
                    "credentials.json", "settings.local.json", "id_rsa",
                    "id_ed25519", "known_hosts",
                }
                for raw_path in raw_paths:
                    untracked_hash.update(len(raw_path).to_bytes(8, "big"))
                    untracked_hash.update(raw_path)
                    relative = raw_path.decode("utf-8", errors="replace")
                    file_path = root / relative
                    resolved = file_path.resolve(strict=False)
                    try:
                        resolved.relative_to(root)
                    except ValueError:
                        return state
                    lowered_parts = {part.lower() for part in Path(relative).parts}
                    lowered_name = file_path.name.lower()
                    sensitive = (
                        bool(lowered_parts & sensitive_directories)
                        or lowered_name in sensitive_names
                        or lowered_name == ".env"
                        or lowered_name.startswith(".env.")
                        or file_path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
                    )
                    if file_path.is_symlink():
                        untracked_hash.update(b"\0SYMLINK_NOT_FOLLOWED\0")
                    elif sensitive and file_path.exists():
                        untracked_hash.update(b"\0SENSITIVE_CONTENT_REDACTED\0")
                        untracked_hash.update(file_path.stat().st_size.to_bytes(8, "big"))
                    elif file_path.is_file():
                        size = file_path.stat().st_size
                        total_bytes += size
                        if size > 16 * 1024 * 1024 or total_bytes > 128 * 1024 * 1024:
                            return state
                        with file_path.open("rb") as stream:
                            for block in iter(lambda: stream.read(1024 * 1024), b""):
                                untracked_hash.update(block)
                state["diff_sha256"] = hashlib.sha256(
                    unstaged.stdout
                    + b"\n"
                    + staged.stdout
                    + b"\nUNTRACKED\n"
                    + untracked_hash.digest()
                ).hexdigest()
    except (OSError, subprocess.SubprocessError):
        pass
    return state


def command_run_check(args: argparse.Namespace) -> int:
    path = Path(args.path)
    record = load(path)
    checks = record.get("verification", {}).get("checks", [])
    matches = [
        check for check in checks
        if isinstance(check, dict) and check.get("id") == args.check_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one check with id {args.check_id!r}")
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise ValueError("run-check requires a command after --")
    cwd = Path(args.cwd).resolve() if args.cwd else path.parent.resolve()
    check = matches[0]
    attempted_at = datetime.now(timezone.utc).isoformat()
    check.update(
        {
            "command": subprocess.list2cmdline(command),
            "status": "fail",
            "exit_code": None,
            "ran_at": attempted_at,
            "output_sha256": "",
            "output_digest": "execution did not complete",
            "repo_state": capture_repo_state(cwd),
        }
    )
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            timeout=args.timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        marker = type(exc).__name__.encode("ascii")
        digest = hashlib.sha256(marker).hexdigest()
        check.update(
            {
                "output_sha256": digest,
                "output_digest": f"execution_error:{type(exc).__name__}",
            }
        )
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "check_id": args.check_id,
                    "status": "fail",
                    "exit_code": None,
                    "error_type": type(exc).__name__,
                    "record": str(path),
                },
                indent=2,
            )
        )
        return 2
    output = result.stdout + b"\n" + result.stderr
    digest = hashlib.sha256(output).hexdigest()
    check.update(
        {
            "command": subprocess.list2cmdline(command),
            "status": "pass" if result.returncode == 0 else "fail",
            "exit_code": result.returncode,
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "output_sha256": digest,
            "output_digest": f"sha256:{digest}; bytes:{len(output)}",
            "repo_state": capture_repo_state(cwd),
        }
    )
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "check_id": args.check_id,
                "status": check["status"],
                "exit_code": result.returncode,
                "output_sha256": digest,
                "output_bytes": len(output),
                "record": str(path),
            },
            indent=2,
        )
    )
    return 0 if result.returncode == 0 else 1


def command_state(args: argparse.Namespace) -> int:
    print(json.dumps(capture_repo_state(Path(args.cwd).resolve()), indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new")
    new.add_argument("--goal", required=True)
    new.add_argument("--risk", choices=sorted(RISK_LEVELS), default="medium")
    new.add_argument("--output", required=True)
    new.set_defaults(func=command_new)
    check = sub.add_parser("validate")
    check.add_argument("path")
    check.set_defaults(func=command_validate)
    summary = sub.add_parser("summary")
    summary.add_argument("path")
    summary.set_defaults(func=command_summary)
    run_check = sub.add_parser("run-check")
    run_check.add_argument("path")
    run_check.add_argument("--check-id", required=True)
    run_check.add_argument("--cwd")
    run_check.add_argument("--timeout", type=float, default=120.0)
    run_check.set_defaults(func=command_run_check)
    state = sub.add_parser("state")
    state.add_argument("--cwd", required=True)
    state.set_defaults(func=command_state)

    raw_args = sys.argv[1:]
    executable: list[str] = []
    if raw_args and raw_args[0] == "run-check" and "--" in raw_args:
        divider = raw_args.index("--")
        executable = raw_args[divider + 1:]
        raw_args = raw_args[:divider]
    args = parser.parse_args(raw_args)
    if args.command == "run-check":
        args.command = executable
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
