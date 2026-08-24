"""Tests for `intent hud`: the brain-cache the statusline HUD reads."""
from __future__ import annotations

import json
from types import SimpleNamespace

from intent_control_plane import cli


def test_hud_writes_cache_with_brain_fields(tmp_path):
    out = tmp_path / "hud.json"
    result = cli.hud(SimpleNamespace(cwd=str(tmp_path), out=str(out)))
    assert set(result) >= {"repo", "estate", "gaps", "strategy", "strategy_pass", "updated_at"}
    assert out.exists()
    on_disk = json.loads(out.read_text())
    assert on_disk["repo"] == tmp_path.name
    assert isinstance(on_disk["gaps"], int)


def test_hud_fails_open_on_unscorable_dir(tmp_path):
    # an empty dir is not a scorable repo; hud must not crash, estate degrades to a dash
    result = cli.hud(SimpleNamespace(cwd=str(tmp_path), out=str(tmp_path / "hud.json")))
    assert result["estate"] in {"-"} or "/" in result["estate"]
