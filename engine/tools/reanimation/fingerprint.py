#!/usr/bin/env python3
"""Reanimation jutsu, stage 1: the statistical fingerprint of one thread.

The MEASURED half of a persona: message-length distribution, Hebrew/English/emoji
mix, top n-grams and catchphrases, opener/closer habits, burst cadence. No model
call, no network, so it costs nothing and is deterministic. Reads a stage-0
corpus.jsonl, writes fingerprint.json beside it.

Stack note (numerical-stack rule): Polars is the tabular default, but this tool
must run inside the harness / CI runner with no dependency install step, and the
math here (counts, quantiles, ratios over ~10k rows) is a handful of stdlib passes.
Stdlib wins the stated constraint; Polars would add an install for no measured gain
at this size. Revisit if a corpus ever exceeds ~1M messages.

The thread has no sender column (see extract.py), so every statistic describes the
CONVERSATION, not one speaker. fingerprint.json says so in `direction_known`.
"""
import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

HEBREW = re.compile(r"[֐-׿]")
LATIN = re.compile(r"[A-Za-z]")
EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF❤]")
WORD = re.compile(r"[֐-׿A-Za-z']+")


def script_mix(texts: list[str]) -> dict[str, float]:
    he = lat = emo = 0
    for t in texts:
        he += len(HEBREW.findall(t))
        lat += len(LATIN.findall(t))
        emo += len(EMOJI.findall(t))
    total = he + lat or 1
    return {"hebrew_ratio": round(he / total, 3),
            "latin_ratio": round(lat / total, 3),
            "emoji_per_msg": round(emo / max(len(texts), 1), 3)}


def ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def fingerprint(corpus: Path) -> dict:
    texts: list[str] = []
    lengths: list[int] = []
    openers: Counter = Counter()
    all_tokens: list[str] = []
    for line in corpus.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        t = row["text"]
        texts.append(t)
        lengths.append(len(t))
        toks = WORD.findall(t.lower())
        all_tokens.extend(toks)
        if toks:
            openers[toks[0]] += 1
    if not texts:
        return {"messages": 0}

    uni = ngrams(all_tokens, 1)
    stop = {w for w, _ in uni.most_common(15)}  # crude high-freq filter
    bi = ngrams(all_tokens, 2)
    tri = ngrams(all_tokens, 3)

    return {
        "messages": len(texts),
        "direction_known": False,
        "length": {
            "mean": round(statistics.mean(lengths), 1),
            "median": statistics.median(lengths),
            "p90": sorted(lengths)[int(len(lengths) * 0.9)],
            "max": max(lengths),
        },
        "script_mix": script_mix(texts),
        "top_openers": [w for w, _ in openers.most_common(12)],
        "top_words": [g[0] for g, _ in uni.most_common(25)],
        "catchphrases_bigram": [" ".join(g) for g, c in bi.most_common(15) if c > 3],
        "catchphrases_trigram": [" ".join(g) for g, c in tri.most_common(12)
                                 if c > 2 and not set(g) <= stop],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("corpus_dir", help="a ~/.intent/reanimation/<slug> dir")
    a = ap.parse_args(argv)
    d = Path(a.corpus_dir).expanduser()
    corpus = d / "corpus.jsonl"
    if not corpus.is_file():
        print(f"no corpus.jsonl in {d}", file=sys.stderr)
        return 2
    fp = fingerprint(corpus)
    (d / "fingerprint.json").write_text(
        json.dumps(fp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{fp['messages']} msgs, "
          f"median {fp.get('length', {}).get('median', 0)} chars, "
          f"hebrew {fp.get('script_mix', {}).get('hebrew_ratio', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
