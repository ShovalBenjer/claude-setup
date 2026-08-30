#!/usr/bin/env python3
"""Reanimation jutsu, stages 2-3: extract a persona card from a thread, map-reduce.

Map: split the corpus into conversation windows, mask each (mask.Vault), and ask a
free-tier lane (router.chat) for a structured record of traits/opinions/running
jokes/how-they-are-funny per window. Reduce: merge the window records into one
persona card and fold in the stage-1 statistical fingerprint. Stage 3 assembly also
selects a verbatim exemplar bank (real messages, the few-shot soul) straight from
the local corpus, never through a model.

Boundaries: the corpus is both voices (no sender column), so the card describes the
thread's shared voice, stated in the card. Only masked chunks reach a lane. The
exemplar bank stays local. Cost lands on the free tiers, never on Claude.

Usage:
  persona.py <corpus_dir> [--windows N] [--exemplars K] [--lane qwen]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mask as _mask  # noqa: E402
import router as _router  # noqa: E402

MAP_SYS = (
    "You analyze a slice of a WhatsApp thread (Hebrew/English, both speakers "
    "interleaved, PII replaced by <TOKEN> placeholders). Return STRICT JSON with "
    "keys: traits (list of short strings), opinions (list), running_jokes (list), "
    "recurring_topics (list), humor (one sentence on what is funny here). Base "
    "everything on the text; empty lists are fine. No prose outside the JSON.")

REDUCE_SYS = (
    "You merge several JSON analyses of one person's conversation into ONE persona "
    "card. Deduplicate, keep the most distinctive and best-supported items, drop "
    "one-offs. Return STRICT JSON: traits, opinions, running_jokes, "
    "recurring_topics, voice (2-3 sentences on how they talk), humor (2 sentences). "
    "No prose outside the JSON.")


def windows(corpus: Path, size: int) -> list[str]:
    msgs = [json.loads(l)["text"] for l in corpus.read_text(encoding="utf-8").splitlines() if l.strip()]
    return ["\n".join(msgs[i:i + size]) for i in range(0, len(msgs), size)]


def _json_only(s: str) -> dict:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1].removeprefix("json").strip() if "```" in s else s
    a, b = s.find("{"), s.rfind("}")
    return json.loads(s[a:b + 1]) if a >= 0 else {}


def exemplars(corpus: Path, k: int) -> list[str]:
    """Distinctive real messages: longest unique-ish lines, local only."""
    seen, picks = set(), []
    rows = [json.loads(l)["text"] for l in corpus.read_text(encoding="utf-8").splitlines() if l.strip()]
    for t in sorted(rows, key=len, reverse=True):
        key = t[:20]
        if key in seen or len(t) < 8:
            continue
        seen.add(key)
        picks.append(t)
        if len(picks) >= k:
            break
    return picks


def build(corpus_dir: Path, n_windows: int, k_exemplars: int,
          lane: str | None) -> dict:
    corpus = corpus_dir / "corpus.jsonl"
    fp = json.loads((corpus_dir / "fingerprint.json").read_text()) \
        if (corpus_dir / "fingerprint.json").is_file() else {}
    meta = json.loads((corpus_dir / "meta.json").read_text())

    wins = windows(corpus, size=60)
    if n_windows and len(wins) > n_windows:
        step = len(wins) // n_windows
        wins = wins[::step][:n_windows]

    records, lanes_used = [], set()
    vault = _mask.Vault()
    for w in wins:
        masked = vault.mask(w)
        try:
            out, used = _router.chat(
                [{"role": "system", "content": MAP_SYS},
                 {"role": "user", "content": masked}],
                temperature=0.3, only=lane)
            lanes_used.add(used)
            records.append(_json_only(out))
        except (_router.AllLanesFailed, json.JSONDecodeError):
            continue

    card = {}
    if records:
        try:
            merged, used = _router.chat(
                [{"role": "system", "content": REDUCE_SYS},
                 {"role": "user", "content": json.dumps(records, ensure_ascii=False)}],
                temperature=0.2, only=lane)
            lanes_used.add(used)
            card = _json_only(merged)
        except (_router.AllLanesFailed, json.JSONDecodeError):
            card = {"error": "reduce failed", "raw_records": len(records)}

    return {
        "contact": meta.get("contact"),
        "direction_known": False,
        "note": "thread is both speakers; card is the shared voice, not one person",
        "fingerprint": fp,
        "card": card,
        "exemplars": exemplars(corpus, k_exemplars),
        "windows_analyzed": len(records),
        "lanes_used": sorted(lanes_used),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("corpus_dir")
    ap.add_argument("--windows", type=int, default=8,
                    help="how many sampled windows to send to a lane (cost control)")
    ap.add_argument("--exemplars", type=int, default=40)
    ap.add_argument("--lane", default=None, help="pin one lane, e.g. qwen")
    a = ap.parse_args(argv)
    d = Path(a.corpus_dir).expanduser()
    if not (d / "corpus.jsonl").is_file():
        print(f"no corpus in {d}", file=sys.stderr)
        return 2
    card = build(d, a.windows, a.exemplars, a.lane)
    (d / "persona.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    c = card.get("card", {})
    print(f"{card['contact']}: {card['windows_analyzed']} windows via "
          f"{card['lanes_used']}, {len(c.get('traits', []))} traits, "
          f"{len(card['exemplars'])} exemplars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
