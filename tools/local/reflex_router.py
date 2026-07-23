# -*- coding: utf-8 -*-
"""Reflex router (SLM spec #2 + flywheel S1). Wraps the local classifier as a
cheap-first gate AND logs every decision to the flywheel jsonl — which becomes the
training data for a fine-tuned router specialist later (ADR-0009 flywheel).

PII-safe: logs a SHA1 of the text, never the text itself. Fail-open: if the local
model is down, returns route=escalate so nothing is silently kept-local.

Usage: reflex_router.py "request text"  -> {"route","risk","source","escalate"}
"""
import hashlib, json, os, sys, time, pathlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOG = pathlib.Path(os.environ.get("CLAUDE_OS_DIR", pathlib.Path.home() / "claude-setup")) \
    / "tools" / "local" / "flywheel" / "router_decisions.jsonl"
LOG.parent.mkdir(parents=True, exist_ok=True)

# high-risk always escalates to the frontier regardless of the small model's confidence
ESCALATE_IF = {"risk": {"high"}, "route": {"build", "research"}}


def route(text):
    try:
        from route_classify import classify
        r = classify(text)
        source = "local-1.5b"
    except Exception as e:
        r = {"route": "build", "risk": "high"}  # fail-closed to escalation
        source = f"fallback:{type(e).__name__}"
    escalate = r["risk"] in ESCALATE_IF["risk"] or r["route"] in ESCALATE_IF["route"]
    rec = {
        "ts": None,  # stamped by caller/collector; time.time() avoided for reproducibility
        "text_sha1": hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:12],
        "route": r["route"], "risk": r["risk"], "source": source, "escalate": escalate,
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return {**{k: rec[k] for k in ("route", "risk", "source", "escalate")}}


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or sys.stdin.read().strip()
    print(json.dumps(route(text)))
