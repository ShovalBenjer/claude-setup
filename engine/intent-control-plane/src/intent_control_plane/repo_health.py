"""AI-native repo-health checks: LOC budgets from the 2026 structure standard.

Operationalizes `~/docs/Next-Gen AI-Native Repo Structure  Best Practices for Agentic
Projects (July 2026).md` section 5.2 so the file/function/class budgets are an executable
check instead of prose. Advisory: it reports violations and never edits.

Run: `python -m intent_control_plane.repo_health <path>` (exit 1 if any hard violation).
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

# (soft, hard) line budgets from the standard, section 5.2.
FILE_BUDGET = (300, 500)
FUNC_BUDGET = (30, 50)
CLASS_BUDGET = (150, 300)
_SKIP_PARTS = {"__pycache__", ".venv", "node_modules", ".git", ".mypy_cache", ".ruff_cache"}


@dataclass(frozen=True)
class Finding:
    """One budget violation: a file, function, or class over its soft LOC budget."""

    path: str
    kind: str  # "file" | "function" | "class"
    name: str
    loc: int
    budget: tuple[int, int]

    @property
    def severity(self) -> str:
        """`hard` if over the hard cap, else `soft`."""
        return "hard" if self.loc > self.budget[1] else "soft"


def _node_loc(node: ast.AST) -> int:
    end = getattr(node, "end_lineno", None)
    start = getattr(node, "lineno", None)
    return (end - start + 1) if end and start else 0


def file_findings(path: Path, source: str | None = None) -> list[Finding]:
    """Budget violations in one Python file (file total, plus each function and class)."""
    text = source if source is not None else path.read_text(encoding="utf-8", errors="replace")
    findings: list[Finding] = []
    total = len(text.splitlines())
    if total > FILE_BUDGET[0]:
        findings.append(Finding(str(path), "file", path.name, total, FILE_BUDGET))
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return findings
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            loc = _node_loc(node)
            if loc > FUNC_BUDGET[0]:
                findings.append(Finding(str(path), "function", node.name, loc, FUNC_BUDGET))
        elif isinstance(node, ast.ClassDef):
            loc = _node_loc(node)
            if loc > CLASS_BUDGET[0]:
                findings.append(Finding(str(path), "class", node.name, loc, CLASS_BUDGET))
    return findings


def scan(root: Path, include_tests: bool = False) -> list[Finding]:
    """All budget violations under `root`, skipping caches, venvs, and (by default) tests."""
    findings: list[Finding] = []
    for py in sorted(root.rglob("*.py")):
        parts = py.relative_to(root).parts
        if any(p in _SKIP_PARTS for p in parts):
            continue
        if not include_tests and (py.name.startswith("test_") or "tests" in parts):
            continue
        findings.extend(file_findings(py))
    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI: print violations sorted by size; exit 1 if any hard violation exists."""
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0]).expanduser() if args else Path.cwd()
    findings = scan(root)
    hard = [f for f in findings if f.severity == "hard"]
    for f in sorted(findings, key=lambda f: -f.loc):
        print(f"[{f.severity}] {f.kind} {f.name} = {f.loc} LOC "
              f"(budget {f.budget[0]}/{f.budget[1]}) {f.path}")
    print(f"\n{len(findings)} over soft budget, {len(hard)} over hard budget in {root}")
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
