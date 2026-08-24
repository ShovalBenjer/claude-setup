#!/usr/bin/env python3
"""a2a-foundry-call.py — synchronous bridge from Claude → Azure Foundry agents.

Auth: bearer token via `az account get-access-token --resource https://cognitiveservices.azure.com`.
Falls back to env AZURE_OPENAI_API_KEY if `az` unavailable.

Endpoint pattern (from KNOWLEDGE-BASE.md):
    https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai/applications/<agent>/

Two paths:
- Applications endpoint (KB-only queries): faster, but returns 500 on tool calls
- Responses API (raw): handles tool calls, slightly different envelope

This v1 uses Applications endpoint by default. Pass --responses-api to switch.

Usage:
    a2a-foundry-call.py <agent-name> "<prompt>" [--timeout 30] [--responses-api]
    a2a-foundry-call.py seekapa "what is the OTP send rate limit?"
    a2a-foundry-call.py AxiaCS "explain KYC tier 2 requirements" --timeout 60

Output:
    JSON to stdout: {state, agent, response_text, duration_ms, error?}
    Audit logged to ~/.claude/cache/a2a/audit.jsonl

Exit codes: 0 = ok, 1 = failed/timeout, 2 = config/auth error
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Add ~/.claude/bin to import path so we can use a2a_audit
sys.path.insert(0, str(Path.home() / ".claude" / "bin"))
import importlib.util


def _import_audit():
    spec = importlib.util.spec_from_file_location("a2a_audit", Path.home() / ".claude" / "bin" / "a2a-audit.py")
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


FOUNDRY_BASE = "https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai"
RESOURCE = "https://cognitiveservices.azure.com"
DEFAULT_TIMEOUT = 30


def get_token() -> str:
    """Bearer token via az CLI; falls back to env var."""
    env = os.environ.get("AZURE_OPENAI_API_KEY")
    if env:
        return env
    try:
        out = subprocess.check_output(
            ["az", "account", "get-access-token", "--resource", RESOURCE,
             "--query", "accessToken", "-o", "tsv"],
            text=True, stderr=subprocess.DEVNULL, timeout=10,
        ).strip()
        if not out:
            raise RuntimeError("empty token")
        return out
    except Exception as e:
        print(f"ERROR: cannot get Azure token: {e}", file=sys.stderr)
        print("       set AZURE_OPENAI_API_KEY or run `az login` first", file=sys.stderr)
        sys.exit(2)


def call_applications_api(agent: str, prompt: str, token: str, timeout: int) -> tuple[str, str]:
    """Use the Applications endpoint — KB-only style queries.

    Returns (response_text, raw_json).
    """
    url = f"{FOUNDRY_BASE}/applications/{agent}/responses"
    body = {
        "input": [
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)

    # Extract text from response — shape varies; this is the common path
    text = ""
    if isinstance(data, dict):
        text = data.get("output_text") or ""
        if not text and "output" in data:
            for item in data.get("output", []):
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        text += c.get("text", "")
    return text, raw


def call_responses_api(agent: str, prompt: str, token: str, timeout: int) -> tuple[str, str]:
    """Raw Responses API with agent_reference — handles tool calls.

    Returns (response_text, raw_json).
    """
    url = f"{FOUNDRY_BASE}/responses"
    body = {
        "input": [
            {"role": "user", "content": prompt},
        ],
        "agent": {"name": agent, "type": "agent_reference"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)

    text = data.get("output_text", "")
    if not text and isinstance(data.get("output"), list):
        for item in data["output"]:
            for c in item.get("content", []) or []:
                if isinstance(c, dict) and c.get("type") == "output_text":
                    text += c.get("text", "")
    return text, raw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("agent", help="agent name, e.g. seekapa or AxiaCS")
    ap.add_argument("prompt")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--responses-api", action="store_true", help="use raw Responses API instead of Applications")
    ap.add_argument("--from-addr", default="claude:home")
    ap.add_argument("--conversation-id", default=None)
    args = ap.parse_args()

    audit = _import_audit()
    to_addr = f"foundry:{args.agent}"
    prompt_hash = (audit.hash_prompt if audit else lambda p: "")(args.prompt)
    started = time.monotonic()

    try:
        token = get_token()
        if args.responses_api:
            text, raw = call_responses_api(args.agent, args.prompt, token, args.timeout)
        else:
            text, raw = call_applications_api(args.agent, args.prompt, token, args.timeout)
        duration_ms = int((time.monotonic() - started) * 1000)
        state = "completed" if text else "failed"
        result = {
            "state": state,
            "agent": args.agent,
            "from": args.from_addr,
            "to": to_addr,
            "response_text": text,
            "duration_ms": duration_ms,
            "conversation_id": args.conversation_id,
        }
        if not text:
            result["error"] = "empty response from agent"
        if audit:
            audit.log_call(args.from_addr, to_addr, prompt_hash, duration_ms, state,
                           args.conversation_id, mode="applications" if not args.responses_api else "responses")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if state == "completed" else 1)
    except urllib.error.HTTPError as e:
        duration_ms = int((time.monotonic() - started) * 1000)
        body = ""
        try:
            body = e.read().decode("utf-8")[:500]
        except Exception:
            pass
        if audit:
            audit.log_call(args.from_addr, to_addr, prompt_hash, duration_ms, "failed",
                           args.conversation_id, error=f"HTTP {e.code}", body=body[:200])
        print(json.dumps({"state": "failed", "error": f"HTTP {e.code}", "body": body, "duration_ms": duration_ms}), file=sys.stdout)
        sys.exit(1)
    except (urllib.error.URLError, TimeoutError) as e:
        duration_ms = int((time.monotonic() - started) * 1000)
        if audit:
            audit.log_call(args.from_addr, to_addr, prompt_hash, duration_ms, "timeout",
                           args.conversation_id, error=str(e))
        print(json.dumps({"state": "timeout", "error": str(e), "duration_ms": duration_ms}), file=sys.stdout)
        sys.exit(1)
    except Exception as e:
        duration_ms = int((time.monotonic() - started) * 1000)
        if audit:
            audit.log_call(args.from_addr, to_addr, prompt_hash, duration_ms, "failed",
                           args.conversation_id, error=str(e))
        print(json.dumps({"state": "failed", "error": str(e), "duration_ms": duration_ms}), file=sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
