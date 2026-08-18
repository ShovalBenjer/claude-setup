#!/usr/bin/env python3
"""Free-tier LLM router: one chat() call, several lanes, quota failover.

Reanimation stage 2 uses this; nothing else should hardcode a provider. Lanes are
OpenAI-compatible chat-completions endpoints keyed from ~/.env (or the environment):
Qwen/DashScope primary (best Hebrew), then NVIDIA NIM, then HuggingFace router. A
lane that 4xx/429/5xx-fails or is keyless is skipped and the next is tried; chat()
raises only when every lane is exhausted.

stdlib urllib, no httpx: this must run in the harness with no install step, and one
JSON POST does not justify a dependency.

DATA BOUNDARY (pii-handling): callers must tokenize third-party PII BEFORE calling
this. The router will send whatever it is given to a hosted free tier, so raw
private text must never reach it. Reanimation stage 2 masks first; see mask.py.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

_ENV_CACHE: dict[str, str] | None = None


def _load_env() -> dict[str, str]:
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE
    env: dict[str, str] = dict(os.environ)
    dotenv = Path.home() / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip())
    _ENV_CACHE = env
    return env


# Each lane: (name, key_var, base_url, model). Order is failover priority.
LANES = [
    ("qwen", "QWEN_API_KEY",
     "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
     "qwen-plus"),
    ("nvidia", "NVIDIA_API_KEY",
     "https://integrate.api.nvidia.com/v1/chat/completions",
     "meta/llama-3.1-70b-instruct"),
    ("hf", "HUGGINGFACE_API_KEY",
     "https://router.huggingface.co/v1/chat/completions",
     "Qwen/Qwen2.5-72B-Instruct"),
]


class AllLanesFailed(RuntimeError):
    pass


def _post(url: str, key: str, model: str, messages: list[dict],
          temperature: float, timeout: float) -> str:
    body = json.dumps({"model": model, "messages": messages,
                       "temperature": temperature}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.loads(r.read())
    return payload["choices"][0]["message"]["content"]


def chat(messages: list[dict], *, temperature: float = 0.4,
         timeout: float = 90, retries_per_lane: int = 2,
         only: str | None = None) -> tuple[str, str]:
    """Return (content, lane_name). Tries lanes in order until one answers."""
    env = _load_env()
    errors = []
    for name, key_var, url, model in LANES:
        if only and name != only:
            continue
        key = env.get(key_var, "").strip()
        if not key:
            errors.append(f"{name}: no key")
            continue
        for attempt in range(retries_per_lane):
            try:
                return _post(url, key, model, messages, temperature, timeout), name
            except urllib.error.HTTPError as e:
                code = e.code
                errors.append(f"{name}: HTTP {code}")
                if code == 429 and attempt + 1 < retries_per_lane:
                    time.sleep(2 * (attempt + 1))
                    continue
                break  # 4xx/5xx: next lane
            except (urllib.error.URLError, TimeoutError, KeyError,
                    IndexError, json.JSONDecodeError) as e:
                errors.append(f"{name}: {type(e).__name__}")
                break
    raise AllLanesFailed("; ".join(errors))


if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) or "Reply with the single word: ok"
    try:
        out, lane = chat([{"role": "user", "content": prompt}], temperature=0)
        print(f"[{lane}] {out}")
    except AllLanesFailed as e:
        print(f"all lanes failed: {e}", file=sys.stderr)
        sys.exit(1)
