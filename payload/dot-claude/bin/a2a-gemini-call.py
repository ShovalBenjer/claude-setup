#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""a2a bridge to Gemini (free AI Studio tier) — the decorrelated second reviewer that
replaces Codex (ADR-0007 amended). Different model family = real independence for the
agreement gate (ADR-0004/0008). Model is an interchangeable ACTOR, not a fixed persona.

Auth: GEMINI_API_KEY env (free at aistudio.google.com/apikey).
Usage: a2a-gemini-call.py "<prompt>" [--model gemini-2.5-flash]
Returns JSON: {state, model, response_text, duration_ms, error?}
"""
import json, os, sys, time, urllib.request, urllib.error

MODEL = "gemini-2.5-flash"
if "--model" in sys.argv:
    MODEL = sys.argv[sys.argv.index("--model") + 1]
prompt = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else sys.stdin.read()


def call(prompt, model):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return {"state": "auth_failed", "model": model, "error": "GEMINI_API_KEY not set"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.2}}).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
        r = json.loads(urllib.request.urlopen(req, timeout=90).read())
        text = r["candidates"][0]["content"]["parts"][0]["text"]
        return {"state": "completed", "model": model, "response_text": text,
                "duration_ms": int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        return {"state": "failed", "model": model, "error": f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"}
    except Exception as e:
        return {"state": "failed", "model": model, "error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    print(json.dumps(call(prompt, MODEL), ensure_ascii=False))
