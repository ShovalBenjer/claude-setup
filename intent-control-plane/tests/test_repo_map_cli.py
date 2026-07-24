"""Tests for the `intent repo-map` subcommand that wires project_map into the CLI."""
from __future__ import annotations

from types import SimpleNamespace

from intent_control_plane import cli


def _fake_repo(root, name="repo1"):
    repo = root / name
    (repo / ".git").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    return repo


def test_repo_map_markdown(tmp_path):
    _fake_repo(tmp_path)
    md = cli.repo_map(SimpleNamespace(root=str(tmp_path), format="md"))
    assert isinstance(md, str)
    assert "# Project Map" in md
    assert "repo1" in md


def test_repo_map_json(tmp_path):
    _fake_repo(tmp_path)
    js = cli.repo_map(SimpleNamespace(root=str(tmp_path), format="json"))
    assert js["count"] == 1
    assert js["records"][0]["name"] == "repo1"


def test_repo_map_cli_dispatch(tmp_path, capsys):
    _fake_repo(tmp_path)
    rc = cli.main(["repo-map", str(tmp_path), "--format", "json"])
    assert rc == 0
    assert '"count": 1' in capsys.readouterr().out
