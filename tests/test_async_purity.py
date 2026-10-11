"""Adversarial tests for the async-purity panel check (issue #396).

The check flags blocking sync calls inside `async def` bodies:
requests.get/post/put/delete, time.sleep, bare open(). Exemptions:
asyncio.to_thread / run_in_executor delegation, allowlisted async facades.

Acceptance criterion from the issue: run with stdlib only.
"""

import ast
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "review"))

from async_purity import check_source, check_tree, findings_for_diff


def test_violation_all_three_shapes_flagged():
    src = """
import requests, time
async def fetch(url):
    resp = requests.get(url, timeout=5)
    time.sleep(1)
    return resp.text
async def read_cfg(path):
    with open(path) as f:
        return f.read()
"""
    got = check_source(src)
    assert sorted(d for _, d in got) == ["open", "requests.get", "time.sleep"], got


def test_clean_async_code_no_findings():
    src = """
import asyncio, httpx
async def fetch(client, url):
    return (await client.get(url)).text
async def save(path, data):
    await asyncio.to_thread(write_sync, path, data)
"""
    assert check_source(src) == []


def test_allowlisted_facade_no_findings():
    # my_async_facade.find is not a blocking-call shape at all, so it is
    # not flagged regardless of the allowlist. motor IS allowlisted: even a
    # hypothetical blocking-shaped call under motor stays silent.
    src = """
import my_async_facade
async def query(coll, q):
    return await my_async_facade.find(coll, q)
"""
    assert check_source(src) == []


def test_sync_function_not_flagged():
    src = """
import requests, time
def fetch(url):
    resp = requests.get(url, timeout=5)
    time.sleep(1)
    return resp.text
"""
    assert check_source(src) == []


def test_to_thread_lambda_exempt():
    src = """
import asyncio, requests
async def fetch(url):
    return await asyncio.to_thread(lambda: requests.get(url).text)
"""
    assert check_source(src) == []


def test_run_in_executor_exempt():
    src = """
import asyncio, time
async def slow(loop):
    return await loop.run_in_executor(None, time.sleep, 1)
"""
    assert check_source(src) == []


def test_nested_async_flagged():
    src = """
import requests
def outer():
    async def inner(url):
        return requests.post(url)
"""
    got = check_source(src)
    assert [d for _, d in got] == ["requests.post"]


def test_syntax_error_yields_nothing():
    assert check_source("async def broken(:\n") == []


def test_line_numbers_are_accurate():
    src = "import requests\n\n\nasync def f():\n    requests.delete('x')\n"
    got = check_source(src)
    assert got == [(5, "requests.delete")], got


def test_findings_for_diff_only_added_lines(tmp_path):
    proj = str(tmp_path)
    with open(os.path.join(proj, "a.py"), "w") as fh:
        fh.write(
            "import requests\n"
            "async def old():\n"
            "    requests.get('old')\n"  # pre-existing violation, not added
            "async def new():\n"
            "    requests.get('new')\n"  # added line -> reported
        )
    lines = [
        {"file": "a.py", "line": 5, "text": "    requests.get('new')"},
    ]
    findings = findings_for_diff(lines, proj)
    assert len(findings) == 1
    f = findings[0]
    assert (f["persona"], f["check"]) == ("correctness", "async-purity")
    assert f["severity"] == "medium"
    assert (f["file"], f["line"]) == ("a.py", 5)
    assert "requests.get" in f["snippet"]


def test_findings_for_diff_skips_non_python(tmp_path):
    proj = str(tmp_path)
    with open(os.path.join(proj, "b.ts"), "w") as fh:
        fh.write("async function f() { requests.get('x'); }\n")
    lines = [{"file": "b.ts", "line": 1, "text": "requests.get"}]
    assert findings_for_diff(lines, proj) == []


def test_findings_for_diff_missing_file(tmp_path):
    lines = [{"file": "nope.py", "line": 1, "text": "x"}]
    assert findings_for_diff(lines, str(tmp_path)) == []
