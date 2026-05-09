#!/usr/bin/env python3
"""Generate speech via ElevenLabs `eleven_multilingual_v2` and save MP3 to ~/.claude/assets/voice/.

Usage:
  generate-voice.py "text to speak" [--voice calm_female] [--out-name slug]
                                    [--no-pop] [--stability 0.5] [--similarity 0.75]

Outputs (stdout):
  - On success: a markdown reference line:  🔊 [slug](/abs/path/to.mp3) (NN.Ns, $X.XX)
  - On failure: error to stderr, exit 1.

Auth: fetches `ComplianceExam-ElevenLabsApiKey` from kv-seekapa-apps via az.
      Falls back to env ELEVENLABS_API_KEY if set.

Voice profiles match Oded's pattern (~/projects/.archive/Oded/.../tts_client.py).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ELEVEN_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_multilingual_v2"   # general default
HEBREW_MODEL = "eleven_v3"                 # Hebrew-correct rendering needs v3 + language_code
OUT_DIR = Path.home() / ".claude" / "assets" / "voice"

# Voice profiles (carried from Oded's TTS pattern; edit voice IDs if you re-cast)
VOICES = {
    "calm_female":          {"id": "jsCqWAovK2LkecY7zXl4", "stability": 0.7,  "similarity": 0.6},   # Freya
    "calm_male":            {"id": "VR6AewLTigWG4xSOukaG", "stability": 0.7,  "similarity": 0.6},   # Arnold
    "authoritative_female": {"id": "EXAVITQu4vr4xnSDxMaL", "stability": 0.6,  "similarity": 0.7},   # Bella
    "authoritative_male":   {"id": "pNInz6obpgDQGcFmaJgB", "stability": 0.6,  "similarity": 0.7},   # Adam
    "energetic_female":     {"id": "EXAVITQu4vr4xnSDxMaL", "stability": 0.4,  "similarity": 0.8},   # Bella
    "energetic_male":       {"id": "pNInz6obpgDQGcFmaJgB", "stability": 0.4,  "similarity": 0.8},   # Adam
    "premium_female":       {"id": "jsCqWAovK2LkecY7zXl4", "stability": 0.5,  "similarity": 0.75},  # Freya
    "premium_male":         {"id": "VR6AewLTigWG4xSOukaG", "stability": 0.5,  "similarity": 0.75},  # Arnold
}
DEFAULT_VOICE = "calm_female"


def get_key() -> str:
    env = os.environ.get("ELEVENLABS_API_KEY")
    if env:
        return env
    return subprocess.check_output(
        ["az", "keyvault", "secret", "show",
         "--vault-name", "kv-seekapa-apps",
         "--name", "ComplianceExam-ElevenLabsApiKey",
         "--query", "value", "-o", "tsv"],
        text=True,
    ).strip()


def slugify(text: str, max_len: int = 50) -> str:
    s = re.sub(r"[^a-zA-Z0-9\-_ ]+", "", text).strip().lower()
    s = re.sub(r"\s+", "-", s)[:max_len].rstrip("-")
    return s or f"voice-{int(time.time())}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", help="text to speak (Hebrew/English/Arabic supported)")
    ap.add_argument("--voice", default=DEFAULT_VOICE, choices=list(VOICES.keys()),
                    help=f"voice profile; default {DEFAULT_VOICE}")
    ap.add_argument("--out-name", default=None)
    ap.add_argument("--stability", type=float, default=None, help="override profile stability (0-1)")
    ap.add_argument("--similarity", type=float, default=None, help="override profile similarity_boost (0-1)")
    ap.add_argument("--no-pop", action="store_true", help="skip auto-play")
    ap.add_argument("--style", type=float, default=0.0, help="style exaggeration 0-1 (multilingual_v2 only)")
    ap.add_argument("--model", default=None, help=f"override model; default {DEFAULT_MODEL}, auto-switches to {HEBREW_MODEL} for Hebrew/Arabic")
    ap.add_argument("--language-code", default=None, help="ISO code (he, ar, en, ...); auto-detected from text if omitted")
    args = ap.parse_args()

    # Auto-detect Hebrew/Arabic and switch to v3 + language_code (multilingual_v2 mispronounces Hebrew as Arabic)
    has_hebrew = any('֐' <= ch <= '׿' for ch in args.text)
    has_arabic = any('؀' <= ch <= 'ۿ' for ch in args.text)
    auto_lang = "he" if has_hebrew else ("ar" if has_arabic else None)

    model_id = args.model or (HEBREW_MODEL if auto_lang else DEFAULT_MODEL)
    language_code = args.language_code or auto_lang

    profile = VOICES[args.voice]
    voice_id = profile["id"]
    stability = args.stability if args.stability is not None else profile["stability"]
    similarity = args.similarity if args.similarity is not None else profile["similarity"]

    body = {
        "text": args.text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity,
            "style": args.style,
            "use_speaker_boost": True,
        },
    }
    if language_code:
        body["language_code"] = language_code

    url = f"{ELEVEN_BASE}/text-to-speech/{voice_id}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "xi-api-key": get_key(),
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            audio_bytes = resp.read()
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: TTS failed (HTTP {e.code}): {body_err[:600]}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: request failed: {e}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = args.out_name or slugify(args.text)
    out_path = OUT_DIR / f"{slug}-{int(time.time())}.mp3"
    out_path.write_bytes(audio_bytes)

    elapsed = time.time() - t0
    chars = len(args.text)
    # Rough cost estimate (multilingual_v2 ≈ $0.30 / 1000 chars on standard tier)
    cost_est = (chars / 1000.0) * 0.30

    if not args.no_pop:
        popper = Path.home() / ".claude" / "bin" / "pop-voice.sh"
        if popper.exists():
            try:
                subprocess.Popen(
                    [str(popper), str(out_path)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception:
                pass

    print(f"🔊 [{slug}]({out_path}) ({elapsed:.1f}s gen, {chars} chars, ≈${cost_est:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
