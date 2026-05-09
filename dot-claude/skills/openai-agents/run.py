#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=2.30"]
# ///
"""
Run an OpenAI Assistant with full step observability.

Usage:
    run.py <asst_id> "<prompt>"

Stdout: assistant final text (pipe-safe).
Stderr: reasoning, tool-call cards, run lifecycle.
Exit:   0 on completed, non-zero on failed/cancelled/expired.

Auth: reads OPENAI_API_KEY from env. Pull via:
    export OPENAI_API_KEY=$(az keyvault secret show --vault-name Shoval --name openai-api-key --query value -o tsv)
"""
from __future__ import annotations

import json
import os
import sys

from openai import OpenAI


def err(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> int:
    if len(sys.argv) < 3:
        err("usage: run.py <asst_id> \"<prompt>\"")
        return 2
    asst_id, prompt = sys.argv[1], sys.argv[2]

    if not os.environ.get("OPENAI_API_KEY"):
        err("OPENAI_API_KEY not set — pull from Shoval KV first")
        return 2

    client = OpenAI()
    thread = client.beta.threads.create(messages=[{"role": "user", "content": prompt}])
    err(f"[thread] {thread.id}")

    final_text: list[str] = []
    with client.beta.threads.runs.stream(thread_id=thread.id, assistant_id=asst_id) as stream:
        for event in stream:
            t = getattr(event, "event", None) or type(event).__name__
            data = getattr(event, "data", event)

            if t == "thread.run.created":
                err(f"[run] {data.id} → in_progress")
            elif t == "thread.run.step.created":
                step_type = getattr(data, "type", "?")
                err(f"  [step] {step_type}")
            elif t == "thread.run.step.delta":
                delta = getattr(data, "delta", None)
                step_details = getattr(delta, "step_details", None) if delta else None
                if step_details and getattr(step_details, "type", None) == "tool_calls":
                    for tc in getattr(step_details, "tool_calls", []) or []:
                        name = (
                            getattr(getattr(tc, "function", None), "name", None)
                            or getattr(tc, "type", "tool")
                        )
                        err(f"    └─ tool_call: {name}")
            elif t == "thread.message.delta":
                delta = getattr(data, "delta", None)
                content = getattr(delta, "content", []) if delta else []
                for block in content or []:
                    if getattr(block, "type", None) == "text":
                        chunk = getattr(getattr(block, "text", None), "value", "") or ""
                        if chunk:
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                            final_text.append(chunk)
            elif t == "thread.run.completed":
                err("\n[run] completed")
            elif t == "thread.run.failed":
                err(f"\n[run] FAILED: {json.dumps(getattr(data, 'last_error', {}), default=str)}")
                return 1
            elif t in ("thread.run.cancelled", "thread.run.expired"):
                err(f"\n[run] {t.split('.')[-1]}")
                return 1

    if not final_text:
        err("[run] no text output")
    else:
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
