"""Codebase knowledge map: per-file, per-function structure + wiring for any repo.

The harness answer to "the agent opened in a repo has no wiring knowledge" (the live widgora widget/
scroll bug was a symptom). Walks a repo READ-ONLY and, for each source file, extracts its functions
and classes (symbol_graph.extract_symbols) and its imports (extract_imports, the wiring edges), then
renders a per-file/per-function map an agent can load as context. Deterministic (tree-sitter); a
later pass can enrich each function with an LLM summary. Never writes to the scanned repo.

Pure logic (language_for) + read-only file walks; the __main__ prints the map so a repo's
CLAUDE.md / docs can pin it for the agent.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from intent_control_plane.symbol_graph import extract_imports, extract_symbols

LANG_BY_SUFFIX = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
}

_PRUNE = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".ruff_cache", ".hypothesis", ".playwright-mcp",
}


def language_for(suffix: str) -> str | None:
    """The tree-sitter language for a file suffix, or None if unsupported."""
    return LANG_BY_SUFFIX.get(suffix.lower())


def build_file_map(path: Path) -> dict[str, Any]:
    """Read-only per-file map: {path, language, functions, classes, imports}."""
    file_path = Path(path)
    language = language_for(file_path.suffix)
    if language is None:
        return {"path": str(file_path), "language": None, "functions": [], "classes": [], "imports": []}
    empty = {"path": str(file_path), "language": language, "functions": [], "classes": [], "imports": []}
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return empty
    try:
        symbols = extract_symbols(source, language)
        imports = extract_imports(source, language)
    except Exception:
        return empty
    return {
        "path": str(file_path),
        "language": language,
        "functions": [s["name"] for s in symbols if s["kind"] in ("function", "method")],
        "classes": [s["name"] for s in symbols if s["kind"] == "class"],
        "imports": imports,
    }


def build_codebase_map(root: Path, max_files: int = 4000) -> list[dict[str, Any]]:
    """Walk a repo read-only and map every supported source file (pruning vendored/cache dirs)."""
    base = Path(root)
    maps: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE and not d.startswith(".")]
        for name in sorted(filenames):
            if language_for(Path(name).suffix) is None:
                continue
            full = Path(dirpath) / name
            file_map = build_file_map(full)
            # as_posix(), not str(): the map is a portable artifact. It gets rendered to
            # markdown, handed to an agent, diffed between runs and compared against
            # paths written elsewhere in this package, all of which use forward slashes.
            # str() emits `sub\b.py` on Windows, so the same repo produced two different
            # maps depending on which machine walked it, and every cross-run diff showed
            # every nested file as changed.
            file_map["path"] = full.relative_to(base).as_posix()
            maps.append(file_map)
            if len(maps) >= max_files:
                return maps
    return maps


def render_markdown(maps: list[dict[str, Any]], title: str = "Codebase map") -> str:
    """Render the per-file/per-function map + imports (wiring) as agent-loadable markdown."""
    lines = [f"# {title}", "", f"{len(maps)} source files. Per-file functions/classes + imports (wiring).", ""]
    for file_map in sorted(maps, key=lambda x: str(x["path"])):
        lines.append(f"## {file_map['path']}  ({file_map.get('language') or '?'})")
        if file_map.get("classes"):
            lines.append(f"- classes: {', '.join(file_map['classes'])}")
        if file_map.get("functions"):
            lines.append(f"- functions: {', '.join(file_map['functions'])}")
        if file_map.get("imports"):
            lines.append(f"- imports: {', '.join(sorted(set(file_map['imports'])))}")
        lines.append("")
    return "\n".join(lines)


def _main(argv: list[str] | None = None) -> int:
    """CLI: print the codebase map for a repo so its CLAUDE.md/docs can pin it for the agent."""
    import argparse

    parser = argparse.ArgumentParser(prog="codebase-map")
    parser.add_argument("root")
    parser.add_argument("--title", default="Codebase map")
    args = parser.parse_args(argv)
    print(render_markdown(build_codebase_map(Path(args.root).expanduser()), title=args.title))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
