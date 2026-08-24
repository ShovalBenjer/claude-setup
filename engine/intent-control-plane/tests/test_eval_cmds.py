"""Tests for the wired eval pipeline: each sim2real core reachable via a CLI handler + recorded."""
from __future__ import annotations

import json
from types import SimpleNamespace

from intent_control_plane.eval_cmds import eval_kappa, eval_passk, eval_tier1, eval_trace_diff
from intent_control_plane.schema import connect, initialize


def _args(tmp_path, payload):
    base = tmp_path / ".intent"
    initialize(base)
    infile = tmp_path / "in.json"
    infile.write_text(json.dumps(payload))
    return SimpleNamespace(base_dir=base, file=str(infile))


def _eval_rows(base):
    with connect(base) as conn:
        return [tuple(r) for r in conn.execute("select eval_type, status from eval_results").fetchall()]


def test_eval_passk_computes_and_records(tmp_path):
    args = _args(tmp_path, {"trials": [[True, True, False], [True, False, False]], "ks": [1, 2]})
    report = eval_passk(args)
    assert report["pass_at_1"] == 0.5
    assert 1 in report["pass_k"] and 2 in report["pass_k"]
    assert _eval_rows(args.base_dir) == [("passk", "pass")]


def test_eval_kappa_computes_and_records(tmp_path):
    args = _args(tmp_path, {"judge": [1, 1, 0, 0], "human": [1, 1, 0, 0]})
    report = eval_kappa(args)
    assert report["cohens_kappa"] == 1.0
    assert report["interpretation"] == "almost perfect"
    assert _eval_rows(args.base_dir) == [("kappa", "pass")]


def test_eval_trace_diff_flags_divergence_and_records(tmp_path):
    payload = {
        "recorded": [{"ts": "t1", "action": "call_a"}, {"ts": "t2", "action": "call_b"}],
        "candidate": [{"ts": "t9", "action": "call_a"}, {"ts": "t9", "action": "call_X"}],
        "ignore": ["ts"],
    }
    args = _args(tmp_path, payload)
    result = eval_trace_diff(args)
    assert result["identical"] is False
    assert result["first_divergence"] == 1  # step 0 matches after ts is ignored; step 1 diverges
    assert _eval_rows(args.base_dir) == [("trace_diff", "fail")]


def test_eval_tier1_short_circuits_on_bad_json_and_records(tmp_path):
    args = _args(tmp_path, {"text": "not json", "checks": [{"type": "valid_json"}]})
    gate = eval_tier1(args)
    assert gate["passed"] is False
    assert "valid_json" in gate["failures"]
    assert _eval_rows(args.base_dir) == [("tier1", "fail")]


def test_eval_tier1_passes_valid_payload(tmp_path):
    payload = {
        "text": json.dumps({"a": 1, "b": 2}),
        "checks": [{"type": "valid_json"}, {"type": "required_keys", "keys": ["a", "b"]}],
    }
    args = _args(tmp_path, payload)
    gate = eval_tier1(args)
    assert gate["passed"] is True
    assert _eval_rows(args.base_dir) == [("tier1", "pass")]
