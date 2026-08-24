#!/usr/bin/env python3
"""NVIDIA NIM client: a second free second-opinion pool, not a window into weights.

Why this exists next to tools/openrouter. The refutation channel wants model
diversity: a claim survives more when refuters come from different vendors and
different weight families. build.nvidia.com exposes preview NIM endpoints
(OpenAI-compatible, integrate.api.nvidia.com) that serve large open models at
zero cost to a registered developer key, including families OpenRouter's free
tier rotates out. Separate vendor, separate quota bucket, separate failure
domain.

Scope honesty, recorded 2026-07-29 because the operator asked for "looking
inside models": these endpoints are HOSTED INFERENCE ONLY. No weights, no
activations, no internals. The one interior signal available is token logprobs
(--logprobs), and only on endpoints that expose them. Actual weights for open
models come from Hugging Face downloads, which is a different task with
different disk math.

Budget: NVIDIA does not publish a numeric per-day free ceiling for preview
endpoints (checked 2026-07-29; the catalog gates by RPM and account credits).
The 100/day ceiling and 1.5s pacing here are LOCAL POLICY so one runaway loop
cannot drain the account's credits, not vendor-documented numbers. Both are
enforced before the request leaves, via tools/lib/quota.

Secret handling: the key resolves through tools/lib/envload (os.environ first,
then the shared .env). Never printed, never ledgered, never in an error.

Usage:
  nim.py models [--all] [--refresh]        catalogue (cached 24h)
  nim.py quota                             local ledger state for today
  nim.py ask "question" [--model X] [--system S] [--max-tokens N] [--logprobs N]
  nim.py selftest [--live]                 offline logic checks; --live adds one real call
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from envload import require  # noqa: E402
from quota import DailyQuota, QuotaExhausted  # noqa: E402

API = "https://integrate.api.nvidia.com/v1"
KEY_NAMES = ("NVIDIA_API_KEY", "nvidia_api_key")
LOCAL_PER_DAY = 100          # local policy, not a vendor number (see docstring)
MIN_INTERVAL_S = 1.5
MODEL_CACHE = ROOT / "state" / "nvidia-models.json"
CACHE_TTL_S = 24 * 3600

# Preference order when no --model is given. Substring match against the live
# catalogue, so a retired slug degrades to the next choice instead of erroring.
PREFERRED = ("nemotron", "llama-3.3", "deepseek", "qwen", "mistral")

RETRY_STATUS = {0, 429, 500, 502, 503}


def _http(method: str, url: str, *, key: str | None, payload: dict | None = None,
          timeout: int = 180) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw[:800]}
        return e.code, parsed
    except urllib.error.URLError as e:
        # 0 = transport failure, distinct from "provider said no": a dead
        # network must not be reported as a model verdict or burn quota.
        return 0, {"error": {"message": "transport failure: {}".format(e.reason)}}


def catalogue(refresh: bool = False) -> list[dict]:
    if not refresh and MODEL_CACHE.exists():
        age = time.time() - MODEL_CACHE.stat().st_mtime
        if age < CACHE_TTL_S:
            try:
                return json.loads(MODEL_CACHE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass  # fall through to refetch; a corrupt cache is not an answer
    status, data = _http("GET", API + "/models", key=require(*KEY_NAMES))
    if status != 200:
        raise SystemExit("catalogue fetch failed: HTTP {} {}".format(
            status, json.dumps(data)[:300]))
    models = data.get("data", [])
    MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CACHE.write_text(json.dumps(models, indent=1), encoding="utf-8")
    return models


def pick_model(models: list[dict], preferred=PREFERRED) -> str:
    ids = [m.get("id", "") for m in models if m.get("id")]
    for needle in preferred:
        for mid in ids:
            if needle in mid:
                return mid
    if not ids:
        raise SystemExit("catalogue is empty; nothing to pick")
    return ids[0]


def chat(prompt: str, *, model: str | None, system: str | None,
         max_tokens: int, logprobs: int = 0) -> dict:
    key = require(*KEY_NAMES)
    quota = DailyQuota("nvidia", LOCAL_PER_DAY)
    quota.guard()
    mid = model or pick_model(catalogue())
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}]
    payload: dict = {"model": mid, "messages": messages, "max_tokens": max_tokens}
    if logprobs:
        payload["logprobs"] = True
        payload["top_logprobs"] = logprobs
    quota.pace(MIN_INTERVAL_S)
    status, data = _http("POST", API + "/chat/completions", key=key, payload=payload)
    # A refusal the provider never charged (429) and a dead transport (0) do
    # not consume the local allowance; anything that reached a model does.
    quota.record(counted=status not in (0, 429), model=mid, status=status)
    return {"status": status, "model": mid, "data": data}


def cmd_ask(args) -> int:
    out = chat(args.prompt, model=args.model, system=args.system,
               max_tokens=args.max_tokens, logprobs=args.logprobs)
    if out["status"] != 200:
        print("HTTP {} from {}: {}".format(
            out["status"], out["model"], json.dumps(out["data"])[:500]), file=sys.stderr)
        return 1
    choice = (out["data"].get("choices") or [{}])[0]
    print(choice.get("message", {}).get("content", ""))
    if args.logprobs:
        lp = choice.get("logprobs")
        if lp:
            print("--- logprobs ---", file=sys.stderr)
            json.dump(lp, sys.stderr, indent=1)
            print(file=sys.stderr)
        else:
            print("(endpoint returned no logprobs for {})".format(out["model"]),
                  file=sys.stderr)
    return 0


def cmd_models(args) -> int:
    models = catalogue(refresh=args.refresh)
    ids = sorted(m.get("id", "") for m in models if m.get("id"))
    show = ids if args.all else ids[:40]
    for mid in show:
        print(mid)
    if not args.all and len(ids) > len(show):
        print("... {} total; --all for the rest".format(len(ids)))
    print("default pick: {}".format(pick_model(models)), file=sys.stderr)
    return 0


def cmd_quota(_args) -> int:
    print(DailyQuota("nvidia", LOCAL_PER_DAY).summary())
    return 0


def cmd_selftest(args) -> int:
    """Offline logic checks. --live adds one real catalogue call + completion."""
    import tempfile
    failures = []

    def check(name, cond):
        print("{:8s} {}".format("ok" if cond else "FAIL", name))
        if not cond:
            failures.append(name)

    fake = [{"id": "nv/other-vision"}, {"id": "meta/llama-3.3-70b-instruct"},
            {"id": "nvidia/nemotron-x"}]
    check("pick honours preference order", pick_model(fake) == "nvidia/nemotron-x")
    check("pick degrades to next preference",
          pick_model(fake, preferred=("absent", "llama-3.3")) ==
          "meta/llama-3.3-70b-instruct")
    check("pick falls back to first id",
          pick_model(fake, preferred=("nothing-matches",)) == "nv/other-vision")

    with tempfile.TemporaryDirectory() as td:
        q = DailyQuota("nvidia-selftest", 2, ledger=Path(td) / "ledger.jsonl")
        q.record(counted=True, status=200)
        q.record(counted=False, status=429)
        check("429 does not consume allowance", q.used() == 1 and q.remaining() == 1)
        q.record(counted=True, status=400)
        got_exhausted = False
        try:
            q.guard()
        except QuotaExhausted:
            got_exhausted = True
        check("ceiling enforced before dispatch", got_exhausted)

    status, data = _http("GET", "http://127.0.0.1:1", key=None, timeout=1)
    check("dead transport maps to status 0", status == 0 and "error" in data)

    if args.live:
        models = catalogue(refresh=True)
        check("live catalogue is non-empty", len(models) > 0)
        out = chat("Reply with exactly: pong", model=None, system=None, max_tokens=8)
        check("live completion returns 200", out["status"] == 200)
        if out["status"] == 200:
            text = (out["data"].get("choices") or [{}])[0].get(
                "message", {}).get("content", "")
            check("live completion has content", bool(text.strip()))
            print("live model: {}".format(out["model"]), file=sys.stderr)

    print("selftest: {} checks, {} failed".format(
        6 + (3 if args.live else 0), len(failures)))
    return 1 if failures else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("models", help="free NIM catalogue (cached 24h)")
    m.add_argument("--all", action="store_true")
    m.add_argument("--refresh", action="store_true")
    m.set_defaults(fn=cmd_models)

    a = sub.add_parser("ask", help="one completion")
    a.add_argument("prompt")
    a.add_argument("--model")
    a.add_argument("--system")
    a.add_argument("--max-tokens", type=int, default=1024)
    a.add_argument("--logprobs", type=int, default=0, metavar="N",
                   help="request top-N token logprobs (stderr)")
    a.set_defaults(fn=cmd_ask)

    q = sub.add_parser("quota", help="local ledger state for today")
    q.set_defaults(fn=cmd_quota)

    s = sub.add_parser("selftest", help="offline logic checks")
    s.add_argument("--live", action="store_true",
                   help="add one real catalogue call and one tiny completion")
    s.set_defaults(fn=cmd_selftest)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except QuotaExhausted as e:
        print(str(e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
