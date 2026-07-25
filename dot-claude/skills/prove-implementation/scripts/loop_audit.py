#!/usr/bin/env python3
"""Locate iteration constructs that deserve explicit design review."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


IO_MARKERS = {
    "execute", "executemany", "query", "commit", "fetch", "request", "get",
    "post", "put", "delete", "open", "read", "write", "sleep", "run", "call",
    "send", "recv", "invoke", "predict", "generate",
}
SCRIPT_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
LOOP_RE = re.compile(r"\b(for|while)\s*\(|\.(forEach|map|flatMap|reduce)\s*\(")
BLOCK_LOOP_RE = re.compile(r"\b(for\s+await\s*|for|while)\s*\(", re.MULTILINE)
IO_RE = re.compile(
    r"\b(await|fetch|query|execute|request|axios|sleep|readFile|writeFile|invoke|predict)\b"
)


def call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return ""


class PythonLoopVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, content_sha256: str) -> None:
        self.path = path
        self.content_sha256 = content_sha256
        self.depth = 0
        self.records: list[dict[str, Any]] = []

    def record(self, node: ast.AST, kind: str, condition: str = "") -> None:
        calls = sorted({
            call_name(item)
            for item in ast.walk(node)
            if isinstance(item, ast.Call) and call_name(item) in IO_MARKERS
        })
        awaits = any(isinstance(item, ast.Await) for item in ast.walk(node))
        flags: list[str] = []
        if self.depth:
            flags.append("nested_iteration")
        if calls:
            flags.append("possible_io_inside_iteration")
        if awaits:
            flags.append("await_inside_iteration")
        if kind == "while" and condition.strip() in {"True", "1"}:
            flags.append("syntactically_unbounded")
        self.records.append({
            "file": str(self.path),
            "content_sha256": self.content_sha256,
            "line": getattr(node, "lineno", None),
            "kind": kind,
            "depth": self.depth + 1,
            "condition": condition,
            "possible_io_calls": calls,
            "flags": flags,
            "review_questions": [
                "What bounds this iteration?",
                "Can work be batched, pushed down, streamed, indexed, or bounded concurrently?",
                "What ordering, idempotency, rate-limit, and memory constraints apply?",
                "What representative test or benchmark justifies this form?",
            ],
        })

    def visit_For(self, node: ast.For) -> None:
        self.record(node, "for", ast.unparse(node.iter))
        self.depth += 1
        self.generic_visit(node)
        self.depth -= 1

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.record(node, "async-for", ast.unparse(node.iter))
        self.depth += 1
        self.generic_visit(node)
        self.depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self.record(node, "while", ast.unparse(node.test))
        self.depth += 1
        self.generic_visit(node)
        self.depth -= 1

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.record(node, "list-comprehension", ast.unparse(node.generators[0].iter))
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self.record(node, "set-comprehension", ast.unparse(node.generators[0].iter))
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self.record(node, "dict-comprehension", ast.unparse(node.generators[0].iter))
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self.record(node, "generator-expression", ast.unparse(node.generators[0].iter))
        self.generic_visit(node)


def audit_python(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        raw = path.read_bytes()
        tree = ast.parse(raw.decode("utf-8", errors="replace"), filename=str(path))
    except SyntaxError as exc:
        return [], [f"{path}:{exc.lineno}: {exc.msg}"]
    visitor = PythonLoopVisitor(path, hashlib.sha256(raw).hexdigest())
    visitor.visit(tree)
    return visitor.records, []


def closing_delimiter(text: str, start: int, opening: str, closing: str) -> int | None:
    depth = 0
    quote = ""
    escaped = False
    line_comment = False
    block_comment = False
    index = start
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char == "/" and nxt == "/":
            line_comment = True
            index += 1
        elif char == "/" and nxt == "*":
            block_comment = True
            index += 1
        elif char in {"'", '"', "`"}:
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def script_record(
    path: Path,
    content_sha256: str,
    text: str,
    start: int,
    kind: str,
    header: str,
    body: str,
) -> dict[str, Any]:
    flags: list[str] = []
    if IO_RE.search(body):
        flags.append("possible_io_inside_iteration")
    if re.search(r"\bawait\b", body):
        flags.append("await_inside_iteration")
    if BLOCK_LOOP_RE.search(body):
        flags.append("nested_iteration")
    return {
        "file": str(path),
        "content_sha256": content_sha256,
        "line": text.count("\n", 0, start) + 1,
        "kind": kind,
        "depth": None,
        "condition": re.sub(r"\s+", " ", header).strip()[:240],
        "possible_io_calls": sorted(set(IO_RE.findall(body))),
        "flags": flags,
        "review_questions": [
            "What bounds this iteration?",
            "Would batching, Promise.all with a bound, streaming, or pushdown be safer?",
            "Does this preserve ordering, backpressure, rate limits, and error isolation?",
            "What representative test or benchmark justifies this form?",
        ],
    }


def audit_script(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    raw = path.read_bytes()
    content_sha256 = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    occupied_lines: set[int] = set()
    for match in BLOCK_LOOP_RE.finditer(text):
        open_paren = text.find("(", match.start())
        close_paren = closing_delimiter(text, open_paren, "(", ")")
        if close_paren is None:
            continue
        cursor = close_paren + 1
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor < len(text) and text[cursor] == "{":
            close_body = closing_delimiter(text, cursor, "{", "}")
            body = text[cursor + 1:close_body if close_body is not None else len(text)]
        else:
            statement_end = text.find(";", cursor)
            body = text[cursor:statement_end if statement_end >= 0 else len(text)]
        record = script_record(
            path,
            content_sha256,
            text,
            match.start(),
            re.sub(r"\s+", "-", match.group(1).strip()),
            text[match.start():close_paren + 1],
            body,
        )
        occupied_lines.add(record["line"])
        records.append(record)

    for number, line in enumerate(text.splitlines(), 1):
        match = LOOP_RE.search(line)
        if not match or number in occupied_lines or not match.group(2):
            continue
        flags = ["possible_io_inside_iteration"] if IO_RE.search(line) else []
        records.append({
            "file": str(path),
            "content_sha256": content_sha256,
            "line": number,
            "kind": f"javascript-typescript-{match.group(2)}",
            "depth": None,
            "condition": line.strip()[:240],
            "possible_io_calls": [],
            "flags": flags,
            "review_questions": [
                "What bounds this iteration?",
                "Would batching, Promise.all with a bound, streaming, or pushdown be safer?",
                "Does this preserve ordering, backpressure, rate limits, and error isolation?",
                "What representative test or benchmark justifies this form?",
            ],
        })
    return records, []


def audit(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if path.suffix.lower() == ".py":
        return audit_python(path)
    if path.suffix.lower() in SCRIPT_EXTENSIONS:
        return audit_script(path)
    return [], [f"unsupported file type: {path}"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for raw in args.paths:
        path = Path(raw)
        if not path.is_file():
            errors.append(f"not a file: {path}")
            continue
        found, failures = audit(path)
        records.extend(found)
        errors.extend(failures)
    flagged = sum(bool(item["flags"]) for item in records)
    print(json.dumps({
        "files": len(args.paths),
        "iterations": len(records),
        "flagged_for_review": flagged,
        "records": records,
        "errors": errors,
        "note": "Flags are review prompts, not proof of a defect.",
    }, indent=2))
    if errors:
        return 2
    if args.fail_on_review and flagged:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
