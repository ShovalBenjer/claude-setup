"""Tests for the tier-1 deterministic eval checks module."""
from __future__ import annotations

from intent_control_plane.eval_tiers import (
    Tier1Result,
    check_function_call,
    check_regex,
    check_required_keys,
    check_valid_json,
    run_tier1,
)


def test_check_regex_invalid_pattern_fails_not_crashes():
    result = check_regex("anything", "[unclosed")
    assert result.passed is False
    assert "invalid pattern" in result.reason


def test_check_function_call_non_dict_fails_not_crashes():
    assert check_function_call("not a dict", "f", []).passed is False
    assert check_function_call(None, "f", []).passed is False


def test_run_tier1_empty_defers_to_judges():
    # no structural checks: pass (defer to the judges), total 0, intentional gate default.
    summary = run_tier1([])
    assert summary["passed"] is True
    assert summary["total"] == 0


def test_check_valid_json_pass():
    result = check_valid_json('{"a": 1}')
    assert result.passed is True
    assert result.check == "valid_json"


def test_check_valid_json_fail_on_truncated_json():
    result = check_valid_json('{"answer": ')
    assert result.passed is False
    assert result.check == "valid_json"
    assert result.reason


def test_check_required_keys_pass_when_all_present():
    result = check_required_keys('{"a": 1, "b": 2}', ["a", "b"])
    assert result.passed is True
    assert result.check == "required_keys"


def test_check_required_keys_fail_when_missing():
    result = check_required_keys('{"a": 1}', ["a", "b"])
    assert result.passed is False
    assert "b" in result.reason


def test_check_required_keys_fail_on_invalid_json():
    result = check_required_keys('{"a": ', ["a"])
    assert result.passed is False
    assert "invalid" in result.reason.lower() or "json" in result.reason.lower()


def test_check_regex_required_present_passes():
    result = check_regex("the answer is yes", r"\byes\b", should_match=True)
    assert result.passed is True
    assert result.check == "regex"


def test_check_regex_required_absent_fails():
    result = check_regex("the answer is no", r"\byes\b", should_match=True)
    assert result.passed is False


def test_check_regex_forbidden_absent_passes():
    result = check_regex("clean output", r"forbidden_token", should_match=False)
    assert result.passed is True


def test_check_regex_forbidden_present_fails():
    result = check_regex("this has forbidden_token in it", r"forbidden_token", should_match=False)
    assert result.passed is False


def test_check_function_call_pass_with_arguments_key():
    call = {"name": "book_flight", "arguments": {"destination": "TLV", "date": "2026-08-01"}}
    result = check_function_call(call, "book_flight", ["destination", "date"])
    assert result.passed is True
    assert result.check == "function_call"


def test_check_function_call_pass_with_args_key():
    call = {"name": "book_flight", "args": {"destination": "TLV", "date": "2026-08-01"}}
    result = check_function_call(call, "book_flight", ["destination", "date"])
    assert result.passed is True


def test_check_function_call_fail_wrong_name():
    call = {"name": "cancel_flight", "arguments": {"destination": "TLV"}}
    result = check_function_call(call, "book_flight", ["destination"])
    assert result.passed is False
    assert "name" in result.reason.lower()


def test_check_function_call_fail_missing_arg():
    call = {"name": "book_flight", "arguments": {"destination": "TLV"}}
    result = check_function_call(call, "book_flight", ["destination", "date"])
    assert result.passed is False
    assert "date" in result.reason


def test_run_tier1_all_pass():
    results = [
        Tier1Result(check="valid_json", passed=True, reason="ok"),
        Tier1Result(check="required_keys", passed=True, reason="ok"),
    ]
    summary = run_tier1(results)
    assert summary["passed"] is True
    assert summary["total"] == 2
    assert summary["failures"] == []


def test_run_tier1_one_fail_aggregates():
    results = [
        Tier1Result(check="valid_json", passed=True, reason="ok"),
        Tier1Result(check="required_keys", passed=False, reason="missing: b"),
    ]
    summary = run_tier1(results)
    assert summary["passed"] is False
    assert summary["total"] == 2
    assert summary["failures"] == ["required_keys"]
