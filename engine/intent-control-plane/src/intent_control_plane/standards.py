"""Per-project compliance scoring against the 2026 dimension standards.

Encodes the machine-checkable parts of the research standards into a scorecard across
five dimensions: repo organization, code health, documentation, testing, CI/CD. Each
dimension yields passed/total checks and the failing checks as gaps. Deterministic,
read-only. This is the fitness-function view of a whole project estate.

Standards spec: ~/docs/repo-standards-2026-07-09.md.
Run: `python -m intent_control_plane.standards [~/projects]`.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from intent_control_plane.project_map import _SKIP, ci_state, discover_test_suites, structure_class

DIMENSIONS = ("repo_org", "code_health", "docs", "testing", "cicd", "supply_chain")


def _pytext(root: Path) -> str:
    p = root / "pyproject.toml"
    return p.read_text(errors="ignore") if p.exists() else ""


def has_lint_config(root: Path) -> bool:
    """A configured linter/formatter (ruff, eslint) is the code-health floor."""
    return (
        "[tool.ruff" in _pytext(root)
        or (root / ".ruff.toml").exists()
        or (root / "eslint.config.js").exists()
        or (root / ".eslintrc.json").exists()
    )


def has_type_config(root: Path) -> bool:
    """Static typing config (mypy/pyright/tsconfig)."""
    return (
        "[tool.mypy" in _pytext(root)
        or (root / "mypy.ini").exists()
        or (root / "tsconfig.json").exists()
        or (root / ".pyrightconfig.json").exists()
    )


def _ci_text(root: Path) -> str:
    """Concatenated lowercased pipeline + workflow text, for supply-chain checks."""
    parts = []
    files = list(root.glob("azure-pipelines*.y*ml")) + list((root / ".github" / "workflows").glob("*.y*ml"))
    for p in files:
        with contextlib.suppress(OSError):
            parts.append(p.read_text(errors="ignore"))
    return "\n".join(parts).lower()


def supply_chain_checks(root: Path) -> dict[str, bool]:
    """Dimension 6: supply-chain floor, Azure-translated (pinned deps, SAST, secret scan)."""
    ci = _ci_text(root)
    lockfiles = ("uv.lock", "poetry.lock", "package-lock.json", "bun.lock", "Cargo.lock")
    return {
        "pinned_deps": any((root / lf).exists() for lf in lockfiles),
        "sast_in_ci": any(t in ci for t in ("bandit", "semgrep", "codeql")),
        "secret_scan": (root / ".secrets.baseline").exists()
        or any(t in ci for t in ("detect-secrets", "gitleaks", "trufflehog")),
    }


def nested_git_count(root: Path, depth: int = 3) -> int:
    """Count nested .git dirs (the repo-in-repo defect), bounded, skipping vendored trees."""
    prune = _SKIP - {".git"}
    n = 0
    for dirpath, dirnames, _ in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        if len(rel.parts) >= depth:
            dirnames[:] = []
            continue
        if ".git" in dirnames and rel != Path("."):
            n += 1
        dirnames[:] = [d for d in dirnames if d not in prune]
    return n


def _dim(checks: dict[str, bool]) -> dict[str, Any]:
    return {
        "passed": sum(checks.values()),
        "total": len(checks),
        "gaps": [name for name, ok in checks.items() if not ok],
    }


def score_repo(root: Path) -> dict[str, Any]:
    """Score one repo across all five dimensions."""
    tests = discover_test_suites(root)
    ci = ci_state(root)
    blocking = ci["has_ci"] and not ci["advisory_gates"]
    docs = root / "docs"
    dims = {
        "repo_org": _dim({
            "readme": (root / "README.md").exists(),
            "docs_dir": docs.is_dir(),
            "adr": (docs / "adr").is_dir(),
            "single_git": nested_git_count(root) == 0,
        }),
        "code_health": _dim({
            "lint_config": has_lint_config(root),
            "type_config": has_type_config(root),
        }),
        "docs": _dim({
            "readme": (root / "README.md").exists(),
            "contract_or_map": (docs / "API_CONTRACT.md").exists()
            or (docs / "RUNBOOK.md").exists()
            or (docs / "REPO-MAP.md").exists(),
            "adr": (docs / "adr").is_dir(),
        }),
        "testing": _dim({
            "has_tests": tests["files"] > 0,
            "runner": tests["runner"] is not None,
            "gated_in_ci": blocking and tests["files"] > 0,
        }),
        "cicd": _dim({
            "has_ci": ci["has_ci"],
            "blocking_gates": blocking,
        }),
        "supply_chain": _dim(supply_chain_checks(root)),
    }
    passed = sum(d["passed"] for d in dims.values())
    total = sum(d["total"] for d in dims.values())
    return {"name": root.name, "class": structure_class(root), "score": f"{passed}/{total}", "dimensions": dims}


def score_projects(root: Path) -> list[dict[str, Any]]:
    return [score_repo(d) for d in sorted(root.iterdir()) if d.is_dir() and (d / ".git").exists()]


def render_markdown(records: list[dict[str, Any]]) -> str:
    head = "| Project | Class | " + " | ".join(DIMENSIONS) + " | Score |"
    sep = "|" + "---|" * (len(DIMENSIONS) + 3)
    lines = ["# Project Standards Scorecard", "",
             "Per dimension: checks passed / total. Bars defined in repo-standards-2026-07-09.md.",
             "", head, sep]
    for r in records:
        cells = [f"{r['dimensions'][d]['passed']}/{r['dimensions'][d]['total']}" for d in DIMENSIONS]
        lines.append(f"| {r['name']} | {r['class']} | " + " | ".join(cells) + f" | {r['score']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0]).expanduser() if args else Path.home() / "projects"
    records = score_projects(root)
    print(render_markdown(records))
    print(json.dumps({"count": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
