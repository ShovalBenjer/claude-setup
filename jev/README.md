# jev

Cost/latency-aware model router. Picks the cheapest route that can plausibly
handle a task: local small LMs (Ollama) first, then free tiers (GitHub Models),
paid escalation only when the task needs it and the budget allows.

`router.py` holds the routing logic (`route()`, `estimate_complexity()`).
`test_router.py` is its pytest suite; it makes no model calls, only
availability probes, and passes when nothing is configured.

Used by the coffee-break deliberation (`.github/agent-coffee/run_coffee.py`);
no persona names a model, the router decides.
