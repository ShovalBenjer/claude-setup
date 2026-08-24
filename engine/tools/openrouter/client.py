#!/usr/bin/env python3
"""OpenRouter client: a second opinion from a model that is not me.

Why this is in the setup at all. The refutation engine's whole premise is that a
claim is worth nothing until something tries to break it, and the cheapest strong
refuter is a model with no memory of how the claim was produced. The intended
external reviewer for that job was `codex`, and on 2026-07-25 the binary turned
out not to be installed on this machine at all. OpenRouter's free tier fills that
hole at zero cost: a different vendor's weights, reachable over plain HTTPS, with
no subscription attached.

Budget, from OpenRouter's own limits page (fetched 2026-07-25):
  - :free model variants, under $10 lifetime credit: 50 requests/day
  - :free model variants: 20 requests/minute
  - GET /api/v1/key reports the key's own limits and remaining credit
Both ceilings are enforced locally before the request leaves, by tools/lib/quota.

Model ids are NOT hardcoded. Free model slugs on OpenRouter appear and disappear
weekly, and a stale hardcoded slug fails as a 404 that reads like an auth problem.
`models` fetches the live catalogue, keeps only entries whose prompt AND
completion price are exactly zero, and caches it for a day.

Secret handling: the key is read through tools/lib/envload, which resolves it
case-insensitively (the .env name is lowercase `openrouter_api_key`). The value is
never printed, never logged to the ledger, and never interpolated into an error.

Usage:
  client.py key                                  key limits and remaining credit
  client.py models [--all] [--refresh]           free model catalogue
  client.py quota                                local ledger state for today
  client.py ask "question" [--model X] [--system S] [--max-tokens N]
  client.py refute --claim "..." [--evidence FILE] [--model X]
  client.py selftest                             one real free call, end to end
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from envload import require  # noqa: E402
from quota import DailyQuota, QuotaExhausted  # noqa: E402

API = "https://openrouter.ai/api/v1"
KEY_NAMES = ("openrouter_api_key", "OPENROUTER_API_KEY", "OPENROUTER_KEY")
FREE_PER_DAY = 50
MIN_INTERVAL_S = 3.0  # 20 req/min ceiling, with headroom
MODEL_CACHE = ROOT / "state" / "openrouter-models.json"
CACHE_TTL_S = 24 * 3600

# Attribution headers are optional but OpenRouter uses them for per-app rate
# accounting, and a named app is easier to revoke than an anonymous one.
APP_HEADERS = {
    "HTTP-Referer": "https://github.com/ShovalBenjer/claude-setup",
    "X-Title": "claude-setup refutation channel",
}

# Preference order when no --model is given. Substring match against the live
# catalogue, so a retired slug degrades to the next choice instead of erroring.
PREFERRED = ("deepseek", "qwen", "llama-3.3", "mistral", "gemma", "glm")


def _http(method: str, url: str, *, key: str | None, payload: dict | None = None,
          timeout: int = 180) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if key:
        headers["Authorization"] = "Bearer " + key
    headers.update(APP_HEADERS)
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
        # Distinguish "no network" from "provider said no". Conflating them is
        # how a dead channel gets reported as a refuted claim.
        return 0, {"error": {"message": "transport failure: {}".format(e.reason)}}


def key_info() -> tuple[int, dict]:
    return _http("GET", API + "/key", key=require(*KEY_NAMES))


def catalogue(refresh: bool = False) -> list[dict]:
    if not refresh and MODEL_CACHE.exists():
        age = time.time() - MODEL_CACHE.stat().st_mtime
        if age < CACHE_TTL_S:
            try:
                return json.loads(MODEL_CACHE.read_text(encoding="utf-8"))["data"]
            except (json.JSONDecodeError, KeyError):
                pass
    # /models is public; no key needed, and no daily-quota cost.
    status, data = _http("GET", API + "/models", key=None, timeout=60)
    if status != 200 or "data" not in data:
        raise SystemExit("model catalogue fetch failed: HTTP {} {}".format(
            status, json.dumps(data)[:400]))
    MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CACHE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data["data"]


def _price(m: dict, field: str) -> float:
    try:
        return float((m.get("pricing") or {}).get(field, "1"))
    except (TypeError, ValueError):
        return 1.0


def free_models(refresh: bool = False) -> list[dict]:
    free = [m for m in catalogue(refresh)
            if _price(m, "prompt") == 0.0 and _price(m, "completion") == 0.0]
    free.sort(key=lambda m: -(m.get("context_length") or 0))
    return free


def pick_model(refresh: bool = False) -> str:
    free = free_models(refresh)
    if not free:
        raise SystemExit("no zero-priced model in the catalogue right now")
    for want in PREFERRED:
        for m in free:
            if want in m["id"]:
                return m["id"]
    return free[0]["id"]


# Known non-conversational purposes. Modalities cannot separate these out: a
# safety classifier emits text like any chat model does, it just emits a policy
# label instead of an answer. This list is a heuristic on model ids and will miss
# families nobody has seen yet, which is acceptable because the cost of a miss is
# an unparseable verdict and a visible exit 2, not a wrong answer presented as
# right.
NON_CHAT_MARKERS = ("content-safety", "guard", "moderation", "embed", "rerank")


def _text_capable(m: dict) -> bool:
    """Is this model a text-in, text-out chat model?

    The zero-priced list mixes in music, vision, and safety-classifier models, and
    a refutation sent to a music model is a wasted call. The test is that text is
    the ONLY output modality, not merely one of them: the Lyria models advertise
    output_modalities ["text", "audio"] and are audio generators, so a
    "text is present" check waves them straight through. Input modality is not
    checked at all, because a model that also accepts images still accepts text.

    A record with no declared output modality is kept, since a missing field is
    not evidence of a missing capability.
    """
    if any(mark in m.get("id", "").lower() for mark in NON_CHAT_MARKERS):
        return False
    mods = (m.get("architecture") or {}).get("output_modalities")
    if not mods:
        return True
    return list(mods) == ["text"]


def candidates(model: str | None = None, limit: int = 4) -> list[str]:
    """The model to try first, then text-capable zero-priced alternates behind it."""
    free = [m["id"] for m in free_models() if _text_capable(m)]
    ordered: list[str] = []
    for want in PREFERRED:
        for mid in free:
            if want in mid and mid not in ordered:
                ordered.append(mid)
    ordered += [mid for mid in free if mid not in ordered]
    if model:
        ordered = [model] + [m for m in ordered if m != model]
    if not ordered:
        raise SystemExit("no zero-priced text model in the catalogue right now")
    return ordered[:max(1, limit)]


# Statuses where another model is worth trying. A 429 is the ordinary free-tier
# case: one model's provider is throttled, not the key, so a sibling usually
# answers. Any other 4xx means the request itself is wrong, and re-sending the
# same wrong request elsewhere would only reproduce the error.
RETRY_STATUS = (0, 429, 502, 503, 504, 524)


def chat(prompt: str, *, model: str | None = None, system: str | None = None,
         max_tokens: int = 1200, temperature: float = 0.0,
         note: str = "", fallbacks: int = 3) -> dict:
    """One completion, with failover across zero-priced models.

    Every attempt is logged, and a 429 is logged without being counted, so a
    throttled model costs nothing against the daily allowance. The model that
    actually answered is returned along with the attempts that did not, because a
    silent substitution would make a refutation impossible to reproduce.
    """
    q = DailyQuota("openrouter", FREE_PER_DAY)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    tried: list[dict] = []
    pool = candidates(model, limit=fallbacks + 1)
    for idx, attempt_model in enumerate(pool):
        q.guard()
        slept = q.pace(MIN_INTERVAL_S)
        t0 = time.time()
        status, data = _http("POST", API + "/chat/completions",
                             key=require(*KEY_NAMES),
                             payload={"model": attempt_model, "messages": messages,
                                      "max_tokens": max_tokens,
                                      "temperature": temperature})
        elapsed = round(time.time() - t0, 2)

        usage = (data.get("usage") or {}) if isinstance(data, dict) else {}
        q.record(
            counted=status not in (0, 429),
            model=attempt_model, status=status, ok=status == 200, elapsed_s=elapsed,
            paced_s=round(slept, 2), note=note,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

        if status == 200:
            choices = data.get("choices") or []
            # `.get("content", "")` is not enough: a reasoning model returns the key
            # PRESENT and set to null, so the default never fires and None escapes
            # into every caller. Measured 2026-07-31 with z-ai/glm-4.7-flash, which
            # crashed extract_json's re.search with "expected string or bytes-like
            # object, got 'NoneType'". Some reasoning models put the answer in
            # `reasoning` instead, so fall back to it before giving up.
            message = (choices[0].get("message") or {}) if choices else {}
            text = message.get("content") or message.get("reasoning") or ""
            return {"model": data.get("model", attempt_model), "text": text,
                    "usage": usage, "elapsed_s": elapsed, "id": data.get("id"),
                    "tried": tried}

        msg = ((data.get("error") or {}).get("message")
               if isinstance(data, dict) else None) or json.dumps(data)[:300]
        tried.append({"model": attempt_model, "status": status, "error": msg[:300]})
        if status not in RETRY_STATUS:
            break
        if idx < len(pool) - 1:
            print("note: {} returned HTTP {}, trying the next zero-priced model"
                  .format(attempt_model, status), file=sys.stderr)

    detail = "; ".join("{} HTTP {}: {}".format(t["model"], t["status"], t["error"])
                       for t in tried)
    raise SystemExit("openrouter: no model answered after {} attempt(s). {}".format(
        len(tried), detail))


REFUTE_SYSTEM = """You are an adversarial verifier. You are given a CLAIM and \
optional EVIDENCE. Your job is to REFUTE the claim, not to agree with it.

Rules:
- Default to refuted=true when the evidence does not establish the claim. \
Absence of proof is not proof.
- A claim about a file, command, count, or deployed state is only supported by \
output showing that state. Reasoning about what "should" be true supports nothing.
- Name the single cheapest check that would settle it, as a literal command \
where possible.
- Do not praise, do not summarize, do not hedge across both sides.

Reply with ONLY a JSON object:
{"refuted": true|false, "confidence": 0.0-1.0, "why": "<one or two sentences>", \
"cheapest_check": "<command or observation>", "assumption_found": "<the load-bearing \
unstated assumption, or empty>"}"""


def extract_json(text: str) -> dict | None:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    blob = fence.group(1) if fence else None
    if blob is None:
        start = text.find("{")
        end = text.rfind("}")
        blob = text[start:end + 1] if 0 <= start < end else None
    if not blob:
        return None
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def cmd_refute(args) -> int:
    # A claim can come from a file instead of the command line. Two reasons, both
    # practical: a long claim does not survive shell quoting intact, and a claim
    # whose wording mentions credentials trips the shell guard even though nothing
    # sensitive is being printed. Reading it from a file keeps the command line
    # boring, which is the honest fix rather than rewording to slip past a check.
    claim = args.claim
    if args.claim_file:
        p = Path(args.claim_file)
        if not p.is_file():
            raise SystemExit("no such claim file: {}".format(p))
        claim = p.read_text(encoding="utf-8", errors="replace").strip()
    if not claim:
        raise SystemExit("empty claim: pass --claim or a non-empty --claim-file")
    args.claim = claim

    evidence = ""
    if args.evidence:
        p = Path(args.evidence)
        if not p.is_file():
            raise SystemExit("no such evidence file: {}".format(p))
        evidence = p.read_text(encoding="utf-8", errors="replace")[:args.evidence_chars]
    prompt = "CLAIM:\n{}\n".format(args.claim)
    if evidence:
        prompt += "\nEVIDENCE (may be partial, may be irrelevant):\n{}\n".format(evidence)
    else:
        prompt += "\nEVIDENCE: none supplied.\n"

    res = chat(prompt, model=args.model, system=REFUTE_SYSTEM,
               max_tokens=args.max_tokens, note="refute")
    verdict = extract_json(res["text"])
    out = {"claim": args.claim, "model": res["model"], "elapsed_s": res["elapsed_s"],
           "verdict": verdict, "raw": None if verdict else res["text"]}
    # Which model answered is part of the verdict's provenance, so a failover is
    # reported rather than hidden: the same command on another day may reach a
    # different model, and a reader needs to know that happened.
    if res.get("tried"):
        out["failed_over_from"] = res["tried"]
    print(json.dumps(out, indent=2, ensure_ascii=False))
    # Exit 1 when the claim was refuted, so this is usable as a shell verifier.
    # A malformed reply is also non-zero: an unparseable verdict is not a pass.
    if verdict is None:
        return 2
    return 1 if verdict.get("refuted") else 0


def cmd_ask(args) -> int:
    res = chat(args.prompt, model=args.model, system=args.system,
               max_tokens=args.max_tokens, temperature=args.temperature, note="ask")
    print(res["text"].strip())
    print("\n--- {} | {} prompt + {} completion tokens | {}s".format(
        res["model"], res["usage"].get("prompt_tokens", "?"),
        res["usage"].get("completion_tokens", "?"), res["elapsed_s"]), file=sys.stderr)
    return 0


def cmd_models(args) -> int:
    models = catalogue(args.refresh) if args.all else free_models(args.refresh)
    label = "all" if args.all else "zero-priced"
    print("{} models: {}   (cache {})".format(label, len(models), MODEL_CACHE))
    for m in models[:args.limit]:
        print("  {:52s} ctx={:>9} {}".format(
            m["id"][:52], m.get("context_length") or "?",
            "FREE" if _price(m, "prompt") == 0.0 and _price(m, "completion") == 0.0 else ""))
    if len(models) > args.limit:
        print("  ... and {} more".format(len(models) - args.limit))
    if not args.all:
        print("\ndefault pick: {}".format(pick_model()))
    return 0


def cmd_key(args) -> int:
    status, data = key_info()
    if status != 200:
        print("HTTP {}: {}".format(status, json.dumps(data)[:400]), file=sys.stderr)
        return 1
    d = data.get("data", data)
    for k in ("label", "usage", "limit", "limit_remaining", "is_free_tier",
              "rate_limit", "is_provisioning_key"):
        if k in d:
            print("{:18s} {}".format(k, d[k]))
    return 0


def cmd_quota(args) -> int:
    q = DailyQuota("openrouter", FREE_PER_DAY)
    print(q.summary())
    print("ledger: {}".format(q.ledger))
    rows = q.rows_today()
    for r in rows[-args.limit:]:
        print("  {} {:<38s} HTTP {} {}s{}".format(
            time.strftime("%H:%M:%S", time.localtime(r.get("ts", 0))),
            str(r.get("model", ""))[:38], r.get("status"), r.get("elapsed_s"),
            "" if r.get("counted", True) else "  (not counted)"))
    return 0


def cmd_selftest(args) -> int:
    print("1. key present by reference only (value never printed)")
    require(*KEY_NAMES)
    print("   ok")

    print("2. GET /key")
    status, data = key_info()
    print("   HTTP {} keys={}".format(status, sorted((data.get("data") or data).keys())))
    if status != 200:
        return 1

    print("3. free catalogue")
    free = free_models(refresh=True)
    print("   {} zero-priced models, default pick {}".format(len(free), pick_model()))

    print("4. one real free completion")
    res = chat("Reply with exactly the four characters: PONG", max_tokens=16,
               note="selftest")
    print("   model={} reply={!r} {}s".format(res["model"], res["text"].strip(),
                                              res["elapsed_s"]))

    print("5. ledger")
    print("   " + DailyQuota("openrouter", FREE_PER_DAY).summary())
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ask")
    p.add_argument("prompt")
    p.add_argument("--model")
    p.add_argument("--system")
    p.add_argument("--max-tokens", type=int, default=1200)
    p.add_argument("--temperature", type=float, default=0.0)
    p.set_defaults(fn=cmd_ask)

    p = sub.add_parser("refute")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--claim")
    g.add_argument("--claim-file", dest="claim_file")
    p.add_argument("--evidence")
    p.add_argument("--evidence-chars", type=int, default=24000)
    p.add_argument("--model")
    p.add_argument("--max-tokens", type=int, default=800)
    p.set_defaults(fn=cmd_refute)

    p = sub.add_parser("models")
    p.add_argument("--all", action="store_true")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_models)

    p = sub.add_parser("key")
    p.set_defaults(fn=cmd_key)

    p = sub.add_parser("quota")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(fn=cmd_quota)

    p = sub.add_parser("selftest")
    p.set_defaults(fn=cmd_selftest)

    args = ap.parse_args(argv[1:])
    try:
        return args.fn(args)
    except QuotaExhausted as e:
        print(str(e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
