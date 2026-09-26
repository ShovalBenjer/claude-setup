"""Randomised variant generation, then selection by score.

Why randomise at all. Given a set of lines to send, the deterministic choice is
to group them near the corpus median: median burst size, median line length.
Repeat that and every message has the same shape, which is the Staccato Burst
tell (real bursts are lopsided; generated ones come out evenly sized). The fix
is to draw the shape from the empirical distribution instead of its centre, so
the output varies the way the source varies.

Selection is not "highest score". A variant that maximises centrality is the
most average possible message. voice_score already bands centrality, and the
ranking here inherits that, so the winner is the most *plausible* variant, not
the most typical one.

Seeded throughout: same seed, same variants. Reproducibility beats novelty when
something has to be reviewed before it is sent.
"""
import numpy as np

from profiles import measure
from voice_score import CentralityRef, score


def empirical_bursts(texts, rng, gap_lines=True):
    """Observed burst sizes: how many lines real messages actually run to."""
    sizes = [max(1, len([l for l in t.split("\n") if l.strip()])) for t in texts]
    return np.array(sizes)


def sample_grouping(n_lines, burst_sizes, rng, max_tries=200):
    """Partition n_lines into consecutive groups, sizes drawn from the corpus.

    Rejection-samples until the partition covers exactly n_lines, then keeps the
    ordering as given: grouping is a rhythm decision, reordering would change
    meaning.
    """
    for _ in range(max_tries):
        groups, used = [], 0
        while used < n_lines:
            k = int(rng.choice(burst_sizes))
            k = min(k, n_lines - used)
            groups.append(k)
            used += k
            if len(groups) > n_lines:
                break
        if used == n_lines:
            return groups
    return [1] * n_lines


def _run_check(bursts, run_profile):
    """Run-level gates: how many sends, and how uneven their lengths are."""
    fails = []
    if not run_profile:
        return fails, None
    m = run_profile["metrics"]
    if "sends" in m and len(bursts) > m["sends"]["p95"]:
        fails.append(f"sends={len(bursts)} over run p95 {m['sends']['p95']:.0f}")
    L = [len(b) for b in bursts]
    cv = None
    if len(L) > 1:
        mu = sum(L) / len(L)
        cv = (sum((x - mu) ** 2 for x in L) / len(L)) ** 0.5 / mu if mu else 0.0
        if "len_cv" in m and cv < m["len_cv"]["p10"]:
            fails.append(f"burst lengths too even: cv={cv:.2f} below real p10 "
                         f"{m['len_cv']['p10']:.2f}")
    return fails, cv


def variants(lines, corpus_texts, profile, rules, emb=None, n=24, seed=0,
             run_profile=None):
    """Generate n randomised groupings of the same lines, scored and ranked.

    Each burst is a separate send, so each burst is scored against the
    per-message profile independently. The run is then scored as a run. Scoring
    the concatenation against a per-message profile compares 18 sends to the
    length of one, which fails every variant identically and tells you nothing.
    """
    rng = np.random.default_rng(seed)
    sizes = empirical_bursts(corpus_texts, rng)
    ref = CentralityRef(corpus_texts, emb) if emb is not None else None
    seen, out = set(), []
    for i in range(n * 6):
        if len(out) >= n:
            break
        g = tuple(sample_grouping(len(lines), sizes, rng))
        if g in seen:
            continue
        seen.add(g)
        bursts, k = [], 0
        for size in g:
            bursts.append("\n".join(lines[k:k + size]))
            k += size

        reps = [score(b, profile, rules, ref, emb) for b in bursts]
        fails = [f"burst {i+1}: {f}" for i, r in enumerate(reps) for f in r["fails"]]
        rfails, cv = _run_check(bursts, run_profile)
        fails += rfails
        cps = [r["centrality_pct"] for r in reps if "centrality_pct" in r]
        out.append({
            "grouping": list(g),
            "bursts": bursts,
            "score": round(sum(r["score"] for r in reps) / len(reps), 3),
            "ok": not fails,
            "fails": fails,
            "centrality_pct": round(sum(cps) / len(cps), 1) if cps else None,
            "max_burst_chars": max((measure(b)["chars"] for b in bursts), default=0),
            "line_cv": round(cv, 3) if cv is not None else None,
        })
    out.sort(key=lambda v: (not v["ok"], -v["score"]))
    return out


def render_variants(vs, top=3):
    lines = []
    for i, v in enumerate(vs[:top], 1):
        tag = "ok" if v["ok"] else "FAIL"
        lines.append(f"--- variant {i} [{tag}] score {v['score']:.3f} "
                     f"grouping {v['grouping']} cv {v['line_cv']} "
                     f"max burst {v['max_burst_chars']}ch"
                     + (f" centrality p{v['centrality_pct']}" if v["centrality_pct"] is not None else ""))
        for b in v["bursts"]:
            lines.append("  [send]")
            for l in b.split("\n"):
                lines.append(f"    {l}")
        for f in v["fails"]:
            lines.append(f"  FAIL {f}")
    return "\n".join(lines)
