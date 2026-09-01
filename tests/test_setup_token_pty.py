"""Tests for the pure pieces of tools/setup_token_pty.py.

The script's PTY flow is Windows-only (winpty is declared in no manifest, a documented
build-domain exclusion in docs/QUALITY-CONTRACT.md), so what this file pins is the part
that must hold on every host: importing the module has no side effects, the token
regex recognizes real token shapes, the prompt detector fires on the strings the CLI
actually prints, and redact() leaves no token in anything written to out.log. That
last one is the property the whole script exists for.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import setup_token_pty as stp  # noqa: E402

FAKE_TOKEN = "sk-ant-" + "a1B2c3D4e5F6g7H8i9J0kL"  # 22 chars past the prefix


def test_import_is_side_effect_free():
    # Importing on a host without winpty succeeded (or this file would have died at
    # the import above). The original module spawned the PTY and deleted state files
    # at import time; the winpty import now lives inside main().
    assert callable(stp.main)
    assert "winpty" not in sys.modules


def test_token_regex_matches_real_shapes():
    assert stp.TOKEN_RE.search(FAKE_TOKEN)
    assert stp.TOKEN_RE.search("noise before " + FAKE_TOKEN + " noise after")
    # OAuth-era tokens carry dashes and underscores past the prefix.
    assert stp.TOKEN_RE.search("sk-ant-oat01-" + "x" * 20)


def test_token_regex_rejects_non_tokens():
    assert not stp.TOKEN_RE.search("sk-ant-short")           # under 20 chars
    assert not stp.TOKEN_RE.search("sk-anthropic-" + "x" * 30)  # wrong prefix
    assert not stp.TOKEN_RE.search("paste your code below")


def test_prompt_seen_fires_on_cli_prompt_variants():
    assert stp.prompt_seen("Paste code here if prompted:")
    assert stp.prompt_seen("Enter the CODE: ")
    assert stp.prompt_seen("p a s t e   c o d e")  # spacing stripped before matching
    assert stp.prompt_seen("PASTE")


def test_prompt_seen_quiet_on_startup_noise():
    assert not stp.prompt_seen("")
    assert not stp.prompt_seen("Opening browser for authentication...")
    assert not stp.prompt_seen("claude setup-token v1.0")


def test_redact_removes_every_token_occurrence():
    buf = "line1 " + FAKE_TOKEN + "\nline2 " + FAKE_TOKEN + " trailing"
    red = stp.redact(buf)
    assert stp.TOKEN_RE.search(red) is None
    assert red.count("[TOKEN-CAPTURED]") == 2
    assert "line1" in red and "trailing" in red


def test_redact_keeps_only_the_last_8000_chars():
    buf = "x" * 9000 + FAKE_TOKEN
    red = stp.redact(buf)
    assert len(red) <= 8000
    assert stp.TOKEN_RE.search(red) is None
    assert red.endswith("[TOKEN-CAPTURED]")
