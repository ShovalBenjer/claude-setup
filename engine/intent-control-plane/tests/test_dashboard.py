"""Tests for the control-plane dashboard data assembly (rich rendering is presentation)."""
from __future__ import annotations

from intent_control_plane.dashboard import a2a_usage


def test_a2a_usage_counts_and_fail_rate(tmp_path):
    p = tmp_path / "audit.jsonl"
    p.write_text(
        "\n".join(
            [
                '{"state":"completed","ts":"2026-07-08T10:00:00Z"}',
                '{"state":"completed","ts":"2026-07-08T11:00:00Z"}',
                '{"state":"auth_failed","ts":"2026-07-09T09:00:00Z"}',
            ]
        )
        + "\n"
    )
    u = a2a_usage(p)
    assert u["total"] == 3
    assert u["completed"] == 2
    assert u["failed"] == 1
    assert u["fail_rate"] == round(1 / 3, 3)
    assert u["by_state"]["completed"] == 2
    assert u["by_day"]["2026-07-08"] == 2


def test_a2a_usage_missing_file(tmp_path):
    u = a2a_usage(tmp_path / "does-not-exist.jsonl")
    assert u["total"] == 0
    assert u["fail_rate"] == 0.0
