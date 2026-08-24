#!/usr/bin/env python3
"""Generate an image via gpt-image-2-general (Foundry brn-azai) and save to ~/.claude/assets/visuals/.

Usage:
  generate-visual.py "prompt text" [--out-name slug] [--size 1024x1024] [--style minimalist]

Outputs (stdout):
  - On success: a markdown reference line:  ![slug](/abs/path/to.png)
  - On failure: error to stderr, exit 1.

Auth: fetches brn-azai cog-svc key1 via `az cognitiveservices account keys list`.
      Falls back to env AZURE_OPENAI_API_KEY if set.

Implementation note: uses urllib directly. The Azure OpenAI Python SDK's
images.generate() sends `model` in the body which conflicts with the
deployment-in-URL pattern for gpt-image-2 (returns 400 "model does not exist").
Direct HTTP avoids that.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://brn-azai.openai.azure.com"
DEPLOYMENT = "gpt-image-2-general"
API_VERSION = "2025-04-01-preview"
OUT_DIR = Path.home() / ".claude" / "assets" / "visuals"


def get_key() -> str:
    env = os.environ.get("AZURE_OPENAI_API_KEY")
    if env:
        return env
    return subprocess.check_output(
        ["az", "cognitiveservices", "account", "keys", "list",
         "--name", "brn-azai", "-g", "AZAI_group", "--query", "key1", "-o", "tsv"],
        text=True,
    ).strip()


def slugify(text: str, max_len: int = 50) -> str:
    s = re.sub(r"[^a-zA-Z0-9\-_ ]+", "", text).strip().lower()
    s = re.sub(r"\s+", "-", s)[:max_len].rstrip("-")
    return s or f"visual-{int(time.time())}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", help="image prompt; what to show")
    ap.add_argument("--out-name", default=None, help="filename slug; default: derived from prompt")
    ap.add_argument("--size", default="1024x1024", help="1024x1024 | 1024x1536 | 1536x1024")
    ap.add_argument("--style", default="minimalist technical diagram, clean, monochrome with minimal accent color, labeled boxes and arrows where helpful, no decorative elements",
                    help="style suffix appended to prompt")
    ap.add_argument("--quality", default="medium", choices=["low", "medium", "high"], help="rendering quality")
    ap.add_argument("--no-pop", action="store_true", help="skip the popup window after generation")
    args = ap.parse_args()

    full_prompt = f"{args.prompt}. Style: {args.style}".strip()
    body = {
        "prompt": full_prompt,
        "n": 1,
        "size": args.size,
        "quality": args.quality,
        "output_format": "png",
    }

    url = f"{ENDPOINT}/openai/deployments/{DEPLOYMENT}/images/generations?api-version={API_VERSION}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "api-key": get_key(),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: image generation failed (HTTP {e.code}): {body[:600]}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: request failed: {e}", file=sys.stderr)
        return 1

    item = payload.get("data", [{}])[0]
    if "b64_json" in item:
        img_bytes = base64.b64decode(item["b64_json"])
    elif "url" in item:
        with urllib.request.urlopen(item["url"], timeout=60) as r:
            img_bytes = r.read()
    else:
        print(f"ERROR: response had neither b64_json nor url. Keys: {list(item.keys())}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = args.out_name or slugify(args.prompt)
    out_path = OUT_DIR / f"{slug}-{int(time.time())}.png"
    out_path.write_bytes(img_bytes)

    # Pop the visual unless user opted out
    if not args.no_pop:
        popper = Path.home() / ".claude" / "bin" / "pop-visual.sh"
        if popper.exists():
            # Pick window dimensions to match the requested image size sensibly
            w, h = ("1000", "720")
            if args.size == "1536x1024":
                w, h = ("1100", "740")
            elif args.size == "1024x1536":
                w, h = ("740", "1100")
            try:
                subprocess.Popen(
                    [str(popper), str(out_path), w, h],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception:
                pass  # popping is best-effort; the file is what matters

    print(f"![{slug}]({out_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
