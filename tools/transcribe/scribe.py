"""Transcribe local audio or video with ElevenLabs Scribe, key by reference.

WHY THIS EXISTS

The operator records meetings in Hebrew with English technical code-switching, and
the measured error floor on that audio is high: two independent ASR passes of the
same recording disagreed on 12.4 per cent of words (856 of 977 agreeing), so the
choice of engine is not cosmetic. Scribe leads the AA-WER benchmark at 2.3 per
cent while the best open model on the HF Open ASR leaderboard sits at 5.63 per
cent, and that leaderboard is English-only, which makes the local-model gap on
Hebrew wider than those two numbers suggest.

WHY NOT CURL

The key must never reach a command line. An argv is visible in the process table
and lands in shell history and in any transcript of this session. tools/lib/envload
resolves it by reference out of a .env this repository does not own, and it stays in
memory. Multipart is assembled by hand for the same reason the rest of this tree is
stdlib-only: no new dependency for one POST.

USAGE

    python tools/transcribe/scribe.py OUT_DIR FILE [FILE ...]
    python tools/transcribe/scribe.py --model scribe_v1 OUT_DIR FILE

Writes <name>.json (full response, including any word timings and speaker labels)
and <name>.txt (plain text) per input. Never overwrites: an existing .json is
skipped, so a rerun after one failure does not re-spend on what already succeeded.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import envload  # noqa: E402

API = "https://api.elevenlabs.io/v1/speech-to-text"
KEY_NAMES = ("ELEVEN_LABS_KEY", "ELEVENLABS_API_KEY", "ELEVEN_API_KEY")


def _multipart(fields: dict[str, str], path: Path) -> tuple[bytes, str]:
    """Build a multipart/form-data body. Returns (body, content_type)."""
    boundary = "----claude" + uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += ("--%s\r\n" % boundary).encode()
        out += ('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode()
        out += str(v).encode("utf-8") + b"\r\n"
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    out += ("--%s\r\n" % boundary).encode()
    out += ('Content-Disposition: form-data; name="file"; filename="%s"\r\n'
            % path.name).encode("utf-8")
    out += ("Content-Type: %s\r\n\r\n" % ctype).encode()
    out += path.read_bytes() + b"\r\n"
    out += ("--%s--\r\n" % boundary).encode()
    return bytes(out), "multipart/form-data; boundary=" + boundary


def transcribe(path: Path, key: str, model: str, timeout: float) -> dict:
    fields = {
        "model_id": model,
        # A meeting, so speaker labels are worth having. Language is left to
        # auto-detect on purpose: this audio switches between Hebrew and English
        # mid-sentence, and pinning language_code to one of them is what degrades
        # the technical vocabulary that carries the meaning.
        "diarize": "true",
        "tag_audio_events": "true",
        "timestamps_granularity": "word",
    }
    body, ctype = _multipart(fields, path)
    req = urllib.request.Request(API, data=body, method="POST")
    req.add_header("Content-Type", ctype)
    req.add_header("xi-api-key", key)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default="scribe_v2")
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("out_dir")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv[1:])

    key = envload.get(*KEY_NAMES)
    if not key:
        print("no key found under any of: " + ", ".join(KEY_NAMES), file=sys.stderr)
        print("searched: " + ", ".join(str(p) for p in envload.env_files()),
              file=sys.stderr)
        return 2
    # Identifies the key across machines without disclosing it.
    print("key {} resolved, fingerprint {}".format(KEY_NAMES[0],
                                                   envload.fingerprint(key)))

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    failures = 0

    for raw in a.files:
        p = Path(raw)
        if not p.exists():
            print("MISSING " + str(p), file=sys.stderr)
            failures += 1
            continue
        dest = out / (p.stem + ".json")
        if dest.exists():
            print("skip (already done): " + dest.name)
            continue
        mb = p.stat().st_size / 1e6
        print("sending {} ({:.1f} MB) to {} ...".format(p.name, mb, a.model),
              flush=True)
        t0 = time.time()
        try:
            data = transcribe(p, key, a.model, a.timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            print("HTTP {} on {}: {}".format(e.code, p.name, detail),
                  file=sys.stderr)
            failures += 1
            continue
        except Exception as e:  # noqa: BLE001
            print("FAILED {}: {}".format(p.name, e), file=sys.stderr)
            failures += 1
            continue
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        text = data.get("text") or ""
        (out / (p.stem + ".txt")).write_text(text, encoding="utf-8")
        words = len(text.split())
        print("  ok in {:.0f}s: {} chars, {} words, language={} -> {}".format(
            time.time() - t0, len(text), words,
            data.get("language_code") or data.get("detected_language") or "?",
            dest.name))

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
