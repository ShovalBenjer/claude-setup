"""Score a draft against a measured profile.

The central idea, and the reason this is not just a length check:

  A draft should land in the MIDDLE of the real distribution, not at the top of
  it. Maximising similarity to the corpus centroid produces the most average
  possible message, which is precisely the generated-text signature. So
  similarity is scored as a band (target p25-p75 of how similar real messages
  are to the centroid), and a draft that is more central than 90% of real
  messages is flagged, not rewarded.

Same logic for every metric: too short fails, too long fails, and suspiciously
median fails on the shape metrics where realism depends on variance.
"""
import re
import sys

import numpy as np

from profiles import HARD_FAIL, RULES, measure

# Metrics where only the upper bound is enforced.
ONE_SIDED = {"chars", "words", "lines", "mean_line"}


def _snap(m, p):
    """Nearest stored percentile. Profiles keep a fixed set of cut points, so a
    rule asking for p20 must resolve rather than KeyError."""
    have = sorted(int(k[1:]) for k in m if k.startswith("p"))
    return min(have, key=lambda x: abs(x - p))


def _band_score(v, m, lo=25, hi=75):
    """1.0 inside the band, decaying outside, 0 past p1/p99."""
    p = {k: m[k] for k in m}
    lo, hi = _snap(m, lo), _snap(m, hi)
    lo_v, hi_v = p[f"p{lo}"], p[f"p{hi}"]
    if lo_v <= v <= hi_v:
        return 1.0
    if v < lo_v:
        floor = p.get("p10", lo_v)
        span = max(1e-9, lo_v - floor)
        return max(0.0, 1.0 - (lo_v - v) / (2 * span))
    ceil = p.get("p95", hi_v)
    span = max(1e-9, ceil - hi_v)
    return max(0.0, 1.0 - (v - hi_v) / (2 * span))


def hard_fails(text):
    out = []
    for name, (rx, why) in HARD_FAIL.items():
        for mt in rx.finditer(text):
            out.append((name, why, mt.group(0)[:60]))
    return out


class CentralityRef:
    """How close a draft sits to the real corpus, as a percentile.

    Uses mean similarity to the k nearest real messages, NOT distance to the
    corpus centroid. The centroid was tried first and failed its validation:
    formal Hebrew scored p76 and passed 100% of the time. The reason is that a
    centroid of a diffuse casual cloud lands in generic-language territory, so
    bland text is close to it almost by definition. kNN asks a better question:
    does anything in the corpus actually look like this? Generic text can be
    near the average of everything while resembling nothing.

    Built once per corpus. Scoring one burst must not re-embed the corpus: doing
    that inside the variant loop is 40 variants x 12 bursts x 8.5k messages of
    redundant work, which is the difference between a second and ten minutes.
    """

    def __init__(self, corpus_texts, emb, k=8, ref_sample=1500, seed=0):
        self.emb = emb
        self.k = k
        self.Z = emb.transform(corpus_texts)
        c = self.Z.mean(axis=0)
        self.centroid = c / max(1e-12, np.linalg.norm(c))
        # Reference distribution: leave-one-out kNN similarity of real messages
        # to the rest of the corpus. A draft is compared against this, so the
        # question becomes "is this as corpus-like as a real message is".
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(self.Z), size=min(ref_sample, len(self.Z)), replace=False)
        S = self.Z[idx] @ self.Z.T
        S[np.arange(len(idx)), idx] = -1.0          # drop self-match
        part = np.partition(S, -k, axis=1)[:, -k:]
        self.real = np.sort(part.mean(axis=1))

    def _knn(self, z):
        s = self.Z @ z
        k = min(self.k, len(s))
        return float(np.partition(s, -k)[-k:].mean())

    def of(self, draft):
        z = self.emb.transform([draft])[0]
        d = self._knn(z)
        pct = float(np.searchsorted(self.real, d) / len(self.real) * 100.0)
        return pct, d


def centrality(draft, corpus_texts, emb):
    """Where the draft sits in the distribution of real-message centrality.

    Returns (percentile, cosine). A percentile near 100 means the draft is more
    centroid-like than almost every real message: over-averaged, not on-voice.
    """
    ref = corpus_texts if isinstance(corpus_texts, CentralityRef) \
        else CentralityRef(corpus_texts, emb)
    return ref.of(draft)


def score(draft, profile, rules, corpus_texts=None, emb=None):
    """Full report for one draft. Metric bands + hard fails + centrality."""
    m = measure(draft)
    rep = {"metrics": {}, "fails": [], "warns": [], "score": 0.0}

    # No fitted profile: run the asserted rules only. Borrowing a chat profile
    # to band a blog post produces a page of warnings that say nothing except
    # "a post is longer than a text", which is fake precision.
    if profile is None:
        for name, why, snippet in hard_fails(draft):
            rep["fails"].append(f"hard fail [{name}]: {why} -> {snippet!r}")
        rep["profile"] = None
        rep["score"] = 1.0 if not rep["fails"] else 0.0
        rep["ok"] = not rep["fails"]
        return rep

    lo, hi = rules.get("band", (25, 75))
    any_dist = next(iter(profile["metrics"].values()))
    lo, hi = _snap(any_dist, lo), _snap(any_dist, hi)

    total, wsum = 0.0, 0.0
    for key, dist in profile["metrics"].items():
        v = m[key]
        # line_cv is only defined for a burst that has several lines
        if key == "line_cv" and m["lines"] < 2:
            continue
        # a send with no letters at all (an emoji, a number) has no script mix
        if key == "heb_rate" and not any(c.isalpha() for c in draft):
            continue
        s = _band_score(v, dist, lo, hi)
        gate = key in rules.get("gates", [])
        # Being short is never the generated-text tell; being long is. So the
        # low side of a size metric is advisory and the high side is a gate.
        if gate and key in ONE_SIDED and v < dist[f"p{lo}"]:
            gate = False
        rep["metrics"][key] = {
            "value": round(v, 4), "p50": dist["p50"],
            "band": [dist[f"p{lo}"], dist[f"p{hi}"]],
            "score": round(s, 3), "gate": gate,
        }
        w = 3.0 if gate else 1.0
        total += w * s
        wsum += w
        if gate and s < 0.5:
            rep["fails"].append(
                f"{key}={v:.4g} outside p{lo}-p{hi} [{dist[f'p{lo}']:.4g}, {dist[f'p{hi}']:.4g}]")
        elif s < 0.5:
            rep["warns"].append(f"{key}={v:.4g} off-profile (p50 {dist['p50']:.4g})")

    # explicit ceilings: a platform limit is not a soft band
    for key, lim in rules.get("ceiling", {}).items():
        cap = profile["metrics"][key][lim] if isinstance(lim, str) else lim
        if m[key] > cap:
            rep["fails"].append(f"{key}={m[key]:.4g} over ceiling {cap:.4g}")

    for name, why, snippet in hard_fails(draft):
        rep["fails"].append(f"hard fail [{name}]: {why} -> {snippet!r}")

    if corpus_texts and emb is not None:
        pct, cos = centrality(draft, corpus_texts, emb)
        rep["centrality_pct"] = round(pct, 1)
        rep["centrality_cos"] = round(cos, 4)
        # Measured on held-out data: AUC 0.93 against the real rejected draft,
        # 0.91 formal register, 0.81 English, 0.74 generated register. Genuinely
        # informative, nowhere near reliable enough to auto-reject on its own, so
        # only the bottom decile fails and the next quartile warns. At p10 the
        # false-reject rate on real messages is 10% and it catches 39% of
        # impostors. Treat it as evidence, not as a verdict.
        if pct < 10:
            rep["fails"].append(
                f"centrality p{pct:.0f}: less like this thread than 90% of real "
                f"messages in it")
        elif pct < 25:
            rep["warns"].append(f"centrality p{pct:.0f}: weakly on-voice")
        elif pct > 97:
            rep["warns"].append(f"centrality p{pct:.0f}: near-duplicate of existing messages")
        total += 3.0 * (1.0 if 25 <= pct <= 97 else 0.3)
        wsum += 3.0

    rep["score"] = round(total / max(1e-9, wsum), 3)
    rep["ok"] = not rep["fails"]
    return rep


def render(rep, title=""):
    out = []
    flag = "PASS" if rep["ok"] else "FAIL"
    out.append(f"{flag}  score {rep['score']:.3f}  {title}")
    for f in rep["fails"]:
        out.append(f"  FAIL  {f}")
    for w in rep["warns"]:
        out.append(f"  warn  {w}")
    if "centrality_pct" in rep:
        out.append(f"  centrality: p{rep['centrality_pct']} (target p15-p85)")
    gated = [(k, v) for k, v in rep["metrics"].items() if v["gate"]]
    for k, v in gated:
        out.append(f"  {k:<10} {v['value']:>8.4g}   band [{v['band'][0]:.4g}, "
                   f"{v['band'][1]:.4g}]  p50 {v['p50']:.4g}")
    return "\n".join(out)
