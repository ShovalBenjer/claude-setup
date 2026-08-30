# -*- coding: utf-8 -*-
"""Local intent+risk classifier — the one genuine use for this laptop's local model.
qwen2.5:1.5b via Ollama, few-shot (zero-shot fails), ~3.5s/call, $0, offline, private.

Use: cheap first-pass triage before escalating to Claude. The risk tag feeds the
approval gate (high => require approval). No data leaves the machine (pii-handling).
Stress-tested 2026-07-23: 5/5 correct on the routing set. See
docs/analysis/2026-07-23-local-model-stress-test.md.

Usage: route_classify.py "your request text"   ->  {"route":..., "risk":...}
"""
import json
import sys
import urllib.request

MODEL = "qwen2.5:1.5b"
SYS = '''You label a request with route and risk. Reply with ONE json object only.
Examples:
Request: "add dark mode to the dashboard" -> {"route":"build","risk":"low"}
Request: "what does upsert_job do?" -> {"route":"question","risk":"low"}
Request: "drop the users table" -> {"route":"build","risk":"high"}
Request: "fix the typo in line 3" -> {"route":"quickfix","risk":"low"}
Request: "deploy to prod" -> {"route":"build","risk":"high"}
route is one of: build, question, quickfix, research.
risk is one of: low, med, high (high = irreversible / deletes / deploys / secrets).'''


def classify(text, timeout=120):
    body = json.dumps({
        "model": MODEL, "prompt": f'Request: "{text}" ->', "system": SYS,
        "stream": False, "format": "json",
        "options": {"temperature": 0, "num_predict": 30},
    }).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", body,
                                 {"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    out = json.loads(r.get("response", "{}"))
    route = out.get("route", "question")
    risk = out.get("risk", "low")
    if route not in ("build", "question", "quickfix", "research"):
        route = "question"
    if risk not in ("low", "med", "high"):
        risk = "low"
    return {"route": route, "risk": risk}


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or sys.stdin.read().strip()
    print(json.dumps(classify(text)))
