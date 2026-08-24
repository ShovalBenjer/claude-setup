"""Tests for codebase_map.py: per-file, per-function structure + wiring for any repo.

The harness answer to "the agent opened in a repo has no wiring knowledge". Deterministic
(tree-sitter), read-only, real files via tmp_path (no mocks).
"""
from __future__ import annotations

from intent_control_plane.codebase_map import (
    build_codebase_map,
    build_file_map,
    language_for,
    render_markdown,
)


def test_language_for_maps_suffixes():
    assert language_for(".py") == "python"
    assert language_for(".tsx") == "tsx"
    assert language_for(".md") is None


def test_build_file_map_python(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("import os\nfrom a.b import c\ndef foo():\n    pass\nclass Bar:\n    def m(self):\n        pass\n")
    fm = build_file_map(f)
    assert "foo" in fm["functions"]
    assert "Bar" in fm["classes"]
    assert "os" in fm["imports"] and "a.b" in fm["imports"]


def test_build_codebase_map_walks_and_prunes(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    pass\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("def g():\n    pass\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.py").write_text("def h():\n    pass\n")
    (tmp_path / "readme.md").write_text("not source")
    paths = sorted(m["path"] for m in build_codebase_map(tmp_path))
    assert paths == ["a.py", "sub/b.py"]  # node_modules pruned, non-source skipped


def test_render_markdown_has_per_file_functions(tmp_path):
    (tmp_path / "a.py").write_text("def foo():\n    pass\nclass Bar:\n    pass\n")
    md = render_markdown(build_codebase_map(tmp_path), title="Widgora map")
    assert "# Widgora map" in md
    assert "a.py" in md and "foo" in md and "Bar" in md


def test_build_file_map_degrades_on_parse_error(tmp_path, monkeypatch):
    # H5: real tree-sitter is error-tolerant and will not throw on malformed source, so the parser
    # failure is fault-injected to prove the guard degrades one file to empty instead of crashing.
    f = tmp_path / "broken.py"
    f.write_text("def foo():\n    pass\n")

    def _boom(source: str, language: str) -> list[dict[str, str]]:
        raise RecursionError("tree-sitter blew its stack on a pathological file")

    monkeypatch.setattr("intent_control_plane.codebase_map.extract_symbols", _boom)
    fm = build_file_map(f)
    assert fm["functions"] == []
    assert fm["classes"] == []
    assert fm["language"] == "python"


def test_build_codebase_map_skips_unparseable_file_not_whole_walk(tmp_path, monkeypatch):
    # H5: one unparseable file must not abort the whole walk.
    (tmp_path / "a.py").write_text("def f():\n    pass\n")
    (tmp_path / "broken.py").write_text("def g():\n    pass\n")
    real_extract = build_file_map.__globals__["extract_symbols"]

    def _boom(source: str, language: str) -> list[dict[str, str]]:
        if "g()" in source:
            raise RecursionError("tree-sitter blew its stack on a pathological file")
        return real_extract(source, language)

    monkeypatch.setattr("intent_control_plane.codebase_map.extract_symbols", _boom)
    paths = sorted(m["path"] for m in build_codebase_map(tmp_path))
    assert paths == ["a.py", "broken.py"]
