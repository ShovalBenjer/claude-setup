"""Tests for the deterministic project-map scanner (pure detectors, tmp_path fixtures)."""
from __future__ import annotations

from intent_control_plane.project_map import (
    azure_targets,
    ci_state,
    discover_test_suites,
    is_agentic_langgraph,
    python_import_graph,
    python_imports,
    render_markdown,
    scan_repo,
    structure_class,
)


def test_langgraph_detection_from_deps(tmp_path):
    (tmp_path / "requirements.txt").write_text("langgraph>=0.3\nhttpx\n")
    assert is_agentic_langgraph(tmp_path) is True


def test_no_langgraph_when_absent(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests\nhttpx\n")
    assert is_agentic_langgraph(tmp_path) is False


def test_structure_class_azure_function(tmp_path):
    (tmp_path / "host.json").write_text("{}")
    assert structure_class(tmp_path) == "azure-function-app"


def test_structure_class_harness(tmp_path):
    (tmp_path / "hooks").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    assert structure_class(tmp_path) == "harness-tooling"


def test_azure_targets_from_pipeline(tmp_path):
    (tmp_path / "azure-pipelines.yml").write_text(
        "variables:\n  webAppName: 'agent-call-tracker'\n  resourceGroup: AZAI_group\n"
    )
    got = azure_targets(tmp_path)
    assert "agent-call-tracker" in got
    assert "AZAI_group" in got


def test_test_suites_discovers_and_names_runner(tmp_path):
    (tmp_path / "test_a.py").write_text("def test_x():\n    assert True\n")
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    suites = discover_test_suites(tmp_path)
    assert suites["files"] == 1
    assert suites["runner"] == "pytest"


def test_ci_state_flags_advisory_gate(tmp_path):
    (tmp_path / "azure-pipelines.yml").write_text("steps:\n  - script: ruff check || true\n")
    ci = ci_state(tmp_path)
    assert ci["has_ci"] is True
    assert ci["advisory_gates"] is True


def test_python_imports_absolute_paths():
    src = "import os\nfrom pkg.core import thing\nimport a.b.c\n"
    assert python_imports(src) == ["os", "pkg.core", "a.b.c"]


def test_python_imports_keeps_relative_prefix():
    src = "from .core import x\nfrom . import util\nfrom ..pkg import y\n"
    assert python_imports(src) == [".core", ".util", "..pkg"]


def test_python_imports_tolerates_syntax_error():
    assert python_imports("def broken(:\n") == []


def test_python_import_graph_counts_absolute_relative_and_excludes_stdlib(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("VALUE = 1\n")
    (pkg / "a.py").write_text("from mypkg.core import VALUE\n")  # absolute internal
    (pkg / "b.py").write_text("from .core import VALUE\n")  # relative internal
    (pkg / "c.py").write_text("import os\n")  # stdlib, excluded
    (pkg / "os.py").write_text("SHADOW = 1\n")  # local module sharing a stdlib name
    graph = python_import_graph(tmp_path)
    assert graph["hub_module"] == "core"
    assert graph["hub_indegree"] == 2  # a.py absolute + b.py relative, not c.py's stdlib os
    assert graph["internal_import_edges"] == 2  # `import os` is NOT internal despite os.py


def test_scan_repo_and_render_include_import_hub(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "core.py").write_text("X = 1\n")
    (tmp_path / "a.py").write_text("from .core import X\n")  # relative -> internal
    record = scan_repo(tmp_path)
    assert record["imports"]["hub_module"] == "core"
    md = render_markdown([record])
    assert "| Hub |" in md
    assert "core (1)" in md
