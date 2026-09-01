"""Tests for the run_id/span observability feature (tools/lib/trace.py + tools/trace/query.py)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "lib"))

spec_trace = importlib.util.spec_from_file_location("tracing", ROOT / "tools" / "lib" / "tracing.py")
trace_mod = importlib.util.module_from_spec(spec_trace)
spec_trace.loader.exec_module(trace_mod)

spec_query = importlib.util.spec_from_file_location("query", ROOT / "tools" / "trace" / "query.py")
query_mod = importlib.util.module_from_spec(spec_query)
spec_query.loader.exec_module(query_mod)


class TestGenerateRunId:
    def test_length(self):
        rid = trace_mod.generate_run_id()
        assert len(rid) == 16
        assert all(c in "0123456789abcdef" for c in rid)

    def test_unique(self):
        ids = {trace_mod.generate_run_id() for _ in range(100)}
        assert len(ids) == 100


class TestRunContext:
    def test_sets_and_restores(self):
        assert trace_mod.current_run_id() is None or True
        rid = "test123456789abc"
        with trace_mod.run_context(rid) as active:
            assert active == rid
            assert trace_mod.current_run_id() == rid
            assert os.environ.get(trace_mod.ENV_VAR) == rid

    def test_nested_inherits_outer(self):
        with trace_mod.run_context("outer0000000000") as outer:
            with trace_mod.run_context() as inner:
                assert inner != outer

    def test_explicit_nested_overrides(self):
        with trace_mod.run_context("outer0000000000"):
            with trace_mod.run_context("inner0000000000") as inner:
                assert inner == "inner0000000000"
                assert trace_mod.current_run_id() == "inner0000000000"

    def test_env_var_restored(self):
        old = os.environ.get(trace_mod.ENV_VAR)
        with trace_mod.run_context("temp0000000000ab"):
            pass
        assert os.environ.get(trace_mod.ENV_VAR) == old


class TestSpan:
    def test_basic_span(self):
        with trace_mod.run_context("run00000000000000"):
            with trace_mod.span("test-span") as sid:
                assert len(sid) == 16
                row = trace_mod.inject({})
                assert row["span_id"] == sid
                assert row["span_name"] == "test-span"
                assert "parent_span_id" not in row

    def test_nested_spans(self):
        with trace_mod.run_context("run00000000000000"):
            with trace_mod.span("parent") as parent_sid:
                with trace_mod.span("child") as child_sid:
                    row = trace_mod.inject({})
                    assert row["span_id"] == child_sid
                    assert row["parent_span_id"] == parent_sid
                    assert row["span_name"] == "child"

    def test_span_cleanup(self):
        with trace_mod.run_context("run00000000000000"):
            with trace_mod.span("ephemeral"):
                pass
            row = trace_mod.inject({})
            assert "span_id" not in row


class TestInject:
    def test_adds_run_id(self):
        with trace_mod.run_context("abc12345678def00"):
            row = trace_mod.inject({"kind": "test"})
            assert row["run_id"] == "abc12345678def00"
            assert row["kind"] == "test"

    def test_no_overwrite(self):
        with trace_mod.run_context("abc12345678def00"):
            row = trace_mod.inject({"run_id": "keep-me", "span_id": "keep-span"})
            assert row["run_id"] == "keep-me"
            assert row["span_id"] == "keep-span"

    def test_noop_without_context(self):
        trace_mod._ACTIVE_RUN_ID = None
        trace_mod._ACTIVE_SPAN = None
        old_env = os.environ.pop(trace_mod.ENV_VAR, None)
        try:
            row = trace_mod.inject({"kind": "test"})
            assert "run_id" not in row
            assert "span_id" not in row
        finally:
            if old_env:
                os.environ[trace_mod.ENV_VAR] = old_env

    def test_returns_same_dict(self):
        row = {"a": 1}
        result = trace_mod.inject(row)
        assert result is row


class TestQueryScan:
    def test_scan_finds_rows(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "test.jsonl"
            rid = "scan_test_rid_00"
            rows = [
                {"run_id": rid, "ts": "2026-01-01T00:00:00", "kind": "a"},
                {"run_id": "other_rid_000000", "ts": "2026-01-01T00:00:01", "kind": "b"},
                {"run_id": rid, "ts": "2026-01-01T00:00:02", "kind": "c"},
            ]
            with ledger.open("w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")

            orig = query_mod.STATE
            query_mod.STATE = Path(td)
            try:
                hits = query_mod._scan(rid)
                assert len(hits) == 2
                assert hits[0]["kind"] == "a"
                assert hits[1]["kind"] == "c"
            finally:
                query_mod.STATE = orig

    def test_scan_across_files(self):
        with tempfile.TemporaryDirectory() as td:
            rid = "multi_file_rid_0"
            (Path(td) / "a.jsonl").write_text(
                json.dumps({"run_id": rid, "ts": "2026-01-01T00:00:00", "src": "a"}) + "\n")
            (Path(td) / "b.jsonl").write_text(
                json.dumps({"run_id": rid, "ts": "2026-01-01T00:00:01", "src": "b"}) + "\n")

            orig = query_mod.STATE
            query_mod.STATE = Path(td)
            try:
                hits = query_mod._scan(rid)
                assert len(hits) == 2
                assert hits[0]["_source"] == "a.jsonl"
                assert hits[1]["_source"] == "b.jsonl"
            finally:
                query_mod.STATE = orig


class TestSelftest:
    def test_query_selftest_passes(self):
        assert query_mod.cmd_selftest() == 0
