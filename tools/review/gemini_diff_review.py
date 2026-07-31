#!/usr/bin/env python3
"""Gemini as a decorrelated second reviewer over a PULL REQUEST DIFF ONLY.

Data boundary, which is the reason this file exists separately from panel.py
rather than as a --provider flag on it: Gemini Free Tier terms permit Google to
use submitted content to improve its products, and the global operator contract
therefore bars sending employer or customer code, credentials, or PII to it.
This repository contains third-party PII under research-papers/el-vadt. So this
reviewer is never given a repository checkout, only the unified diff of a pull
request, and it refuses to run if handed anything that is not a diff.

Decorrelation (ADR-0004, persona-review-economy spec): the value of a second
reviewer is information asymmetry, so this actor sees a DIFFERENT and smaller
context than claude-code-review.yml, and belongs to a different model family
(google-gemini vs anthropic-claude). See tools/review/actors.json.

Findings are emitted through panel.py's emit_github_annotations, so they land on
the PR diff as GitHub workflow commands. Nothing here posts a comment: there is
one annotation mechanism in this repo and this file reuses it rather than
growing a second, bespoke commenter that would drift from it.

Usage:
  gemini_diff_review.py --diff-file pr.diff
  gemini_diff_review.py selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panel import emit_github_annotations  # noqa: E402

MODEL = "gemini-3.6-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
MAX_DIFF_BYTES = 200_000
TIMEOUT_S = 120

SEVERITIES = ("high", "medium", "low")

SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": list(SEVERITIES)},
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "check": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["severity", "file", "line", "check", "why"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["findings", "summary"],
}

INSTRUCTION = """You are an independent second reviewer on a pull request. You did
not write this change and you cannot see the rest of the repository: you have the
unified diff and nothing else. Review only what the diff shows.

Report, in order of priority: correctness bugs that change behavior; security
issues (anchor to OWASP/CWE where the mapping is real); contract and boundary
violations such as unchecked errors at IO edges, untyped data crossing a process
boundary, unsafe path handling, and unquoted shell interpolation.

Rules that matter more than volume:
- Every finding cites the file and the line as they appear in the diff.
- `file` must be a path present in the diff, and `line` a line number in the new
  file. If you cannot locate a finding precisely, do not report it.
- If the diff is too small or too opaque to support a finding, return an empty
  findings list and say so in the summary. An invented nit is worse than silence,
  because a second reviewer's only value is that its errors are uncorrelated with
  the first reviewer's, and noise is correlated across all models.
- Do not report formatting or style. CI already enforces those.
- Do not comment on anything you would need the rest of the repository to judge.
"""


class GeminiError(RuntimeError):
    pass


def api_key() -> str:
    """Return the key from the environment. Never logged, never in an exception."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiError(
            "GEMINI_API_KEY is not set in this process. In Actions it must be "
            "passed through `env:` from secrets; a secret is not automatically "
            "an environment variable."
        )
    return key


def looks_like_diff(text: str) -> bool:
    """Refuse anything that is not a unified diff.

    This is the enforcement of the data boundary in the module docstring. If a
    caller ever pipes a file tree, a checkout listing, or a whole source file to
    this script, it must fail rather than quietly ship repository content to a
    free tier that may train on it.
    """
    return any(line.startswith("diff --git ") for line in text.splitlines())


def request_review(diff: str, key: str) -> dict:
    body = {
        "contents": [{"parts": [{"text": INSTRUCTION + "\n\n<diff>\n" + diff + "\n</diff>"}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
            "temperature": 0,
        },
    }
    req = urllib.request.Request(
        ENDPOINT.format(MODEL),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # The body can echo request context; the status alone is the safe signal.
        raise GeminiError("Gemini API returned HTTP {}".format(exc.code)) from None
    except Exception as exc:  # noqa: BLE001
        raise GeminiError("Gemini API call failed: {}".format(type(exc).__name__)) from None
    return parse_response(payload)


def parse_response(payload: dict) -> dict:
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise GeminiError("Gemini response had no candidate text") from None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        raise GeminiError("Gemini response was not the requested JSON") from None
    findings = value.get("findings") or []
    clean = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity", "")).lower()
        if sev not in SEVERITIES:
            continue
        try:
            line = int(f.get("line", 0))
        except (TypeError, ValueError):
            line = 0
        clean.append({
            "severity": sev,
            "file": str(f.get("file", "")),
            "line": line,
            "check": "gemini/" + str(f.get("check", "review")),
            "why": str(f.get("why", "")),
        })
    return {"findings": clean, "summary": str(value.get("summary", ""))}


def cmd_review(args: argparse.Namespace) -> int:
    diff = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
    if not diff.strip():
        print("gemini-review: empty diff, nothing to review")
        return 0
    if not looks_like_diff(diff):
        print("gemini-review: input is not a unified diff; refusing to send it "
              "(see the data boundary in this file's docstring)", file=sys.stderr)
        return 2
    if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
        print("gemini-review: diff exceeds {} bytes; reviewing the first slice "
              "only".format(MAX_DIFF_BYTES))
        diff = diff.encode("utf-8")[:MAX_DIFF_BYTES].decode("utf-8", "ignore")

    try:
        result = request_review(diff, api_key())
    except GeminiError as exc:
        # Degrade loudly, never silently: claude-code-review.yml is still the
        # primary reviewer, and a dead second reviewer must be visible as dead
        # rather than read as "found nothing" (ADR-0004 degradation clause).
        print("::warning title=gemini-review unavailable::{}".format(exc))
        print("gemini-review: DEGRADED, {}".format(exc), file=sys.stderr)
        return 0 if args.soft_fail else 1

    findings = result["findings"]
    written = emit_github_annotations(findings)
    print("gemini-review: {} finding(s), {} annotated".format(len(findings), written))
    print("summary: {}".format(result["summary"]))
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    """Offline checks. Makes no API call, so CI can run it without the secret."""
    failures = []

    if looks_like_diff("just some prose\nnot a diff\n"):
        failures.append("looks_like_diff accepted non-diff text")
    if not looks_like_diff("diff --git a/x.py b/x.py\n+pass\n"):
        failures.append("looks_like_diff rejected a real diff")

    good = {"candidates": [{"content": {"parts": [{"text": json.dumps({
        "summary": "s",
        "findings": [
            {"severity": "high", "file": "a.py", "line": 3, "check": "c", "why": "w"},
            {"severity": "bogus", "file": "b.py", "line": 1, "check": "c", "why": "w"},
            {"severity": "low", "file": "c.py", "line": "notanint", "check": "c", "why": "w"},
        ],
    })}]}}]}
    parsed = parse_response(good)
    if len(parsed["findings"]) != 2:
        failures.append("parse_response kept a finding with an invalid severity")
    if parsed["findings"][1]["line"] != 0:
        failures.append("parse_response did not coerce a non-integer line to 0")
    if not parsed["findings"][0]["check"].startswith("gemini/"):
        failures.append("parse_response did not namespace the check id")

    for bad, label in (({}, "empty payload"),
                       ({"candidates": [{"content": {"parts": [{"text": "nope"}]}}]},
                        "non-JSON text")):
        try:
            parse_response(bad)
            failures.append("parse_response accepted " + label)
        except GeminiError:
            pass

    saved = os.environ.pop("GEMINI_API_KEY", None)
    try:
        api_key()
        failures.append("api_key did not raise when the key is absent")
    except GeminiError as exc:
        if "GEMINI_API_KEY" not in str(exc):
            failures.append("api_key error did not name the missing variable")
    finally:
        if saved is not None:
            os.environ["GEMINI_API_KEY"] = saved

    for f in failures:
        print("FAIL: " + f)
    print("gemini_diff_review selftest: {}".format("FAIL" if failures else "ok"))
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    rev = sub.add_parser("review", help="review a unified diff")
    rev.add_argument("--diff-file", required=True)
    rev.add_argument("--json-out")
    rev.add_argument("--soft-fail", action="store_true",
                     help="exit 0 even when the actor is unreachable")
    rev.set_defaults(func=cmd_review)

    st = sub.add_parser("selftest", help="offline checks, no API call")
    st.set_defaults(func=cmd_selftest)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
