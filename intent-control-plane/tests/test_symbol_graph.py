"""Tests for symbol_graph.py: multi-language symbol extraction + graph-relevance ranking (AC-K1/K2).

extract_symbols parses real source with tree-sitter (the one accepted dependency) across languages,
no mocks. graph_relevance is the pure ranking term the retrieval layer adds: it scores file nodes by
graph centrality, task-term match, and adjacency to session-active files, so a context pack is
biased toward what the current task actually touches rather than lexical match alone.
"""
from __future__ import annotations

from intent_control_plane.symbol_graph import extract_imports, extract_symbols, graph_relevance


def test_extract_symbols_arrow_functions_and_const_class():
    # JS/TS put most functions in const arrow form; dropping them undercounts the whole frontend.
    src = "const foo = () => {}\nexport const Bar = () => 1\nconst Baz = class {}\n"
    kinds = {s["name"]: s["kind"] for s in extract_symbols(src, "javascript")}
    assert kinds.get("foo") == "function"
    assert kinds.get("Bar") == "function"
    assert kinds.get("Baz") == "class"


def test_extract_imports_python():
    imps = extract_imports("import os\nfrom a.b import c\nimport x.y as z\n", "python")
    assert "os" in imps and "a.b" in imps and "x.y" in imps


def test_extract_imports_javascript():
    imps = extract_imports("import {a} from './mod'\nimport b from \"pkg\"\n", "javascript")
    assert "./mod" in imps and "pkg" in imps


def test_extract_symbols_python():
    source = "def foo():\n    return 1\n\nclass Bar:\n    def method(self):\n        pass\n"
    symbols = extract_symbols(source, "python")
    kinds = {s["name"]: s["kind"] for s in symbols}
    assert {"foo", "Bar", "method"} <= set(kinds)
    assert kinds["foo"] == "function"
    assert kinds["Bar"] == "class"


def test_extract_symbols_javascript():
    source = "function baz(){}\nclass Qux { greet(){} }\n"
    symbols = extract_symbols(source, "javascript")
    kinds = {s["name"]: s["kind"] for s in symbols}
    assert {"baz", "Qux", "greet"} <= set(kinds)
    assert kinds["baz"] == "function"
    assert kinds["Qux"] == "class"
    assert kinds["greet"] == "method"


def test_graph_relevance_boosts_term_match_and_active_adjacency():
    edges = [{"source": "a.py", "target": "b.py"}, {"source": "b.py", "target": "c.py"}]
    relevance = graph_relevance(edges, task_terms=["b"], active_files=["c.py"])
    # b.py: high degree + name matches the task term + adjacent to the active file -> top score
    assert relevance["b.py"] > relevance["a.py"]
    assert relevance["b.py"] >= relevance["c.py"]


def test_graph_relevance_empty_graph():
    assert graph_relevance([], task_terms=[], active_files=[]) == {}
