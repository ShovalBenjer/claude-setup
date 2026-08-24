"""Multi-language symbol extraction + graph-relevance ranking (Layer 1 knowledge, AC-K1/K2).

The 2026 evidence (Aider, Codebase-Memory, Amazon AAAI 2026) is that a tree-sitter symbol/call
graph plus agentic-JIT retrieval beats a pre-built vector DB for code, so this extends the existing
Python-AST import graph to multiple languages via tree-sitter (the one accepted dependency) and adds
graph_relevance: the ranking term the retrieval layer uses to bias a context pack toward files the
current task actually touches, not lexical match alone. No daemon; the caller stats files on read.

extract_symbols is a thin real-tree-sitter reader (unit-tested against real source, no mocks);
graph_relevance is pure.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from tree_sitter_language_pack import get_parser

# tree-sitter node type -> the symbol kind we record, across the common grammars.
DEF_KINDS: dict[str, str] = {
    "function_definition": "function",   # python, c
    "class_definition": "class",         # python
    "function_declaration": "function",  # javascript, typescript, go
    "class_declaration": "class",        # javascript, typescript
    "method_definition": "method",       # javascript, typescript
    "method_declaration": "method",      # go, java
    "function_item": "function",         # rust
    "struct_item": "class",              # rust
}


def extract_symbols(source: str, language: str) -> list[dict[str, str]]:
    """Definitions (functions/classes/methods) in source, via tree-sitter, as [{name, kind}]."""
    parser = get_parser(language)
    tree = parser.parse(bytes(source, "utf8"))
    out: list[dict[str, str]] = []
    stack = [tree.root_node]
    func_values = {"arrow_function", "function", "function_expression", "generator_function"}
    class_values = {"class", "class_expression"}
    while stack:
        node = stack.pop()
        kind = DEF_KINDS.get(node.type)
        if kind:
            name_node = node.child_by_field_name("name")
            if name_node is not None and name_node.text is not None:
                out.append({"name": name_node.text.decode("utf8"), "kind": kind})
        elif node.type == "variable_declarator":
            # `const foo = () => {}` / `const Bar = class {}`: JS/TS carry most functions this way.
            value = node.child_by_field_name("value")
            name_node = node.child_by_field_name("name")
            if value is not None and name_node is not None and name_node.text is not None:
                if value.type in func_values:
                    out.append({"name": name_node.text.decode("utf8"), "kind": "function"})
                elif value.type in class_values:
                    out.append({"name": name_node.text.decode("utf8"), "kind": "class"})
        stack.extend(node.children)
    return out


IMPORT_TYPES = {"import_statement", "import_from_statement", "import_declaration"}


def extract_imports(source: str, language: str) -> list[str]:
    """Module references imported by source, via tree-sitter (the wiring edges of a file)."""
    parser = get_parser(language)
    tree = parser.parse(bytes(source, "utf8"))
    out: list[str] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in IMPORT_TYPES:
            ref = node.child_by_field_name("module_name") or node.child_by_field_name("source")
            if ref is not None and ref.text is not None:
                out.append(ref.text.decode("utf8").strip("'\"`"))
            else:
                # No named field (e.g. `import os`, `import x.y as z`): collect every dotted_name /
                # string descendant so aliased and multi-imports are captured, not just the first.
                inner = list(node.children)
                while inner:
                    child = inner.pop(0)
                    if child.type in {"dotted_name", "string"} and child.text is not None:
                        out.append(child.text.decode("utf8").strip("'\"`"))
                    else:
                        inner.extend(child.children)
        else:
            stack.extend(node.children)
    return out


def graph_relevance(
    edges: list[dict[str, Any]], task_terms: list[str], active_files: list[str]
) -> dict[str, float]:
    """Score each file node by centrality + task-term match + adjacency to session-active files.

    edges: [{source, target}] file references. Returns {file: score}. The three terms are weighted so
    a hub file whose name matches the task and sits next to a file the session is editing outranks a
    peripheral one, which is the bias agentic-JIT retrieval needs on top of lexical relevance.
    """
    adjacency: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        nodes.add(source)
        nodes.add(target)
        adjacency[source].add(target)
        reverse[target].add(source)
    if not nodes:
        return {}
    max_degree = max((len(adjacency[n]) + len(reverse[n]) for n in nodes), default=0) or 1
    active = set(active_files)
    terms = {term.lower() for term in task_terms}
    scores: dict[str, float] = {}
    for node in nodes:
        degree = (len(adjacency[node]) + len(reverse[node])) / max_degree
        term_hit = 1.0 if any(term in node.lower() for term in terms) else 0.0
        neighbours = adjacency[node] | reverse[node]
        near_active = 1.0 if (node in active or neighbours & active) else 0.0
        scores[node] = round(0.4 * degree + 0.3 * term_hit + 0.3 * near_active, 4)
    return scores
