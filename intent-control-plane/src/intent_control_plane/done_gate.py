"""The mechanical anti-fake-completion gate (craft/completion research §Q1, §Q5).

"Done" is not commit + tests-green; it is wired + workflow-proven + evidence-attached. This module is
the machine-checkable part: a public symbol with zero live callers is a scaffold, not delivered code
(the exact failure the audit caught in this repo, and the widgora widgets-not-wired failure). done_verdict
composes the eight-item checklist into a pass/fail; unwired_public_symbols is the zero-caller detector
(stdlib ast for top-level public defs, then a ref-count across the non-test package); todo_hits flags
declared-incomplete code. The judge-needed axes (naming, abstraction, the craft critic) live elsewhere.

Pure decision logic (done_verdict, top_level_public_defs, count_symbol_refs); thin read-only file walks
for todo_hits / unwired_public_symbols. Zero-caller detection is a heuristic (like vulture); a common
name may read as wired, so treat the list as a review prompt, not a hard truth.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

_PRUNE = {"__pycache__", ".venv", "node_modules", ".git", "build", "dist"}
_TODO = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")


def top_level_public_defs(source: str) -> list[str]:
    """Names of module-level public functions/classes (no methods, no _private). Empty on syntax error."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and not node.name.startswith("_")
    ]


def count_symbol_refs(symbol: str, sources: list[str]) -> int:
    """Total whole-word occurrences of symbol across sources (definition line counts as one)."""
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    return sum(len(pattern.findall(source)) for source in sources)


def _package_py_files(root: Path) -> list[Path]:
    base = root / "src" if (root / "src").is_dir() else root
    return [
        path
        for path in base.rglob("*.py")
        if not any(part in _PRUNE for part in path.parts)
    ]


def unwired_public_symbols(root: Path) -> list[str]:
    """Public top-level symbols defined in the package but referenced only at their own definition.

    A symbol appearing exactly once across the non-test package (just its def) has no live caller: it is
    a scaffold. Tests live outside src/, so a test-only symbol still reads as unwired, matching the
    research rule "a live caller that is not a test file".
    """
    files = _package_py_files(Path(root))
    sources = [f.read_text(encoding="utf-8", errors="replace") for f in files]
    definitions: dict[str, None] = {}
    for source in sources:
        for name in top_level_public_defs(source):
            definitions[name] = None
    return sorted(name for name in definitions if count_symbol_refs(name, sources) <= 1)


def todo_hits(root: Path) -> list[str]:
    """`relpath:lineno` for every TODO/FIXME/HACK/XXX in the package (declared-incomplete code)."""
    base = Path(root)
    hits: list[str] = []
    for path in _package_py_files(base):
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if _TODO.search(line):
                hits.append(f"{path.relative_to(base)}:{lineno}")
    return hits


def done_verdict(checks: dict[str, Any]) -> dict[str, Any]:
    """Compose the done-gate checklist into {done, failing}. Any failing item blocks 'done'.

    checks keys: tests_green, types_clean, lint_clean, smoke_present (bool); unwired, todos (lists).
    """
    failing: list[str] = [
        flag for flag in ("tests_green", "types_clean", "lint_clean", "smoke_present") if not checks.get(flag)
    ]
    if checks.get("unwired"):
        failing.append("unwired:" + ",".join(checks["unwired"]))
    if checks.get("todos"):
        failing.append(f"todos:{len(checks['todos'])}")
    return {"done": not failing, "failing": failing}
