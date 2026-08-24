"""Per-use-case styling rules.

Two kinds of number live here and they must not be confused.

  MEASURED   derived from a corpus by fit_profile(); regenerate, never hand-edit.
  RULED      a stylistic decision with no corpus behind it, e.g. "no em dashes".
             These are asserted, and marked as asserted.

Every WhatsApp profile is THREAD-LEVEL: the store has no sender column and the
attempt to recover one failed its own diagnostic (see voice_engine docstring).
So a "median 20 chars" figure describes the conversation, not one writer.
"""
import json
import math
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))

EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐❤]")
URL = re.compile(r"https?://\S+")


# ------------------------------------------------------------------ metrics

def measure(text):
    """The metric vector for one unit of output (one message, or one post)."""
    lines = [l for l in text.split("\n") if l.strip()]
    words = text.split()
    n = max(1, len(text))
    lens = [len(l) for l in lines] or [0]
    # Script mix is checked directly rather than left to the embedding. Text in
    # the wrong script has almost no n-grams in common with the corpus, so its
    # TF-IDF row is near zero and every such text collapses to the same point
    # after centring: the embedding cannot rank what it cannot represent.
    heb = sum("א" <= c <= "ת" for c in text)
    lat = sum(c.isascii() and c.isalpha() for c in text)
    return {
        "heb_rate": heb / max(1, heb + lat),
        "chars": len(text),
        "words": len(words),
        "lines": len(lines),
        "mean_line": statistics.mean(lens),
        # lopsidedness. Generated bursts come out evenly sized; real ones do not,
        # so this is the metric that catches the Staccato Burst tell.
        "line_cv": (statistics.pstdev(lens) / statistics.mean(lens)) if statistics.mean(lens) else 0.0,
        "emoji": len(EMOJI.findall(text)),
        "emoji_rate": len(EMOJI.findall(text)) / n,
        "question": text.count("?") + text.count("？"),
        "exclaim": text.count("!"),
        "comma_rate": text.count(",") / n,
        "dash": text.count("—") + text.count("–"),
        "urls": len(URL.findall(text)),
        "upper_rate": sum(c.isupper() for c in text) / n,
    }


def fit_run_profile(msgs, name, gap=180):
    """Distribution of *runs*: consecutive sends with no long pause.

    A burst message is several sends in a row, so scoring it needs two profiles.
    The per-message profile says how long one send runs to. This one says how
    many sends come in a row and how uneven their lengths are, which is where
    the evenness tell actually lives: a generated burst is five sends of the
    same size, a real one is 40 chars, 6, 60, 11.
    """
    runs, cur, prev = [], [], None
    for ts, text in msgs:
        t = ts // 1000 if ts > 1e12 else ts
        if prev is not None and t - prev > gap and cur:
            runs.append(cur)
            cur = []
        cur.append(text)
        prev = t
    if cur:
        runs.append(cur)
    sends = [len(r) for r in runs]
    cvs = []
    for r in runs:
        if len(r) < 2:
            continue
        L = [len(x) for x in r]
        mu = statistics.mean(L)
        cvs.append(statistics.pstdev(L) / mu if mu else 0.0)
    prof = {"name": name, "scope": f"runs, gap<{gap}s, thread-level both sides",
            "n": len(runs), "kind": "MEASURED", "metrics": {}}
    for key, vals in (("sends", sends), ("len_cv", cvs)):
        if not vals:
            continue
        prof["metrics"][key] = {f"p{p}": round(_pct(vals, p), 4)
                                for p in (10, 25, 50, 75, 90, 95, 99)}
    return prof


def _pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return 0
    k = (len(xs) - 1) * p / 100
    f = math.floor(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def fit_profile(texts, name, scope):
    """Empirical distribution of every metric over real units of this kind."""
    ms = [measure(t) for t in texts if t.strip()]
    if not ms:
        raise ValueError(f"no texts for profile {name}")
    prof = {"name": name, "scope": scope, "n": len(ms), "kind": "MEASURED",
            "metrics": {}}
    for key in ms[0]:
        vals = [m[key] for m in ms]
        if key == "line_cv":
            # Over all messages this is ~0 everywhere, because a single-line
            # message has no line variance. Banding on that makes every
            # multi-line burst fail. It is only meaningful among messages that
            # actually have several lines.
            vals = [m[key] for m in ms if m["lines"] > 1] or [0.0]
        prof["metrics"][key] = {
            "p10": round(_pct(vals, 10), 4),
            "p25": round(_pct(vals, 25), 4),
            "p50": round(_pct(vals, 50), 4),
            "p75": round(_pct(vals, 75), 4),
            "p90": round(_pct(vals, 90), 4),
            "p95": round(_pct(vals, 95), 4),
            "p99": round(_pct(vals, 99), 4),
        }
    return prof


# ------------------------------------------------------------------ rules

# Asserted, not measured. Each entry says which metrics are hard gates for that
# surface and what the non-numeric rules are. The numeric bands come from the
# fitted profile at check time; these choose *which* bands are binding.
RULES = {
    "whatsapp_close": {
        "gates": ["chars", "lines", "line_cv", "heb_rate"],
        "band": (10, 90),          # target the middle of the real distribution
        "ceiling": {"chars": "p95"},
        "send_as": "burst",         # separate sends, not one block
        "notes": [
            "Ceiling is p95 of the thread, not p99: p99 is the rant, not the norm.",
            "Emoji rate is per-relationship; do not carry one contact's rate to another.",
            "Hebrew, lowercase, no terminal punctuation on short lines.",
        ],
    },
    "whatsapp_acquaintance": {
        "gates": ["chars", "lines"],
        "band": (25, 75),
        "ceiling": {"chars": "p90"},
        "send_as": "burst",
        "notes": ["Warmer than a work message, shorter than a close-friend burst.",
                  "No inside references; they read as presumptuous."],
    },
    "whatsapp_logistics": {
        "gates": ["chars", "lines", "question"],
        "band": (25, 75),
        "ceiling": {"chars": "p90"},
        "send_as": "single",
        "notes": ["One question per message or the second gets dropped.",
                  "State the time and place explicitly; no 'the usual'."],
    },
    "blog_post": {
        "gates": ["line_cv", "dash"],
        "band": (20, 80),
        "ceiling": {},
        "send_as": "document",
        "notes": [
            "Section lengths must be uneven; equal sections are the Symmetrical",
            "Section Length tell. Let importance set length.",
            "Zero em/en dashes, entities included.",
            "No Dramatic Fragment: delete any trailing clipped phrase and check",
            "whether anything was lost.",
            "Keep the mess: contradictions and dead ends are the subject.",
        ],
    },
    "devto": {
        "gates": ["line_cv", "dash"],
        "band": (20, 80),
        "ceiling": {},
        "send_as": "document",
        "notes": ["Front matter tags: at most 4, lowercase.",
                  "Canonical URL points at the self-hosted copy, not dev.to.",
                  "Code fences need a language or the highlighter picks one."],
    },
    "x": {
        "gates": ["chars", "dash", "emoji"],
        "band": (30, 70),
        "ceiling": {"chars": 280},
        "send_as": "thread",
        "notes": ["Hard 280 per post; the ceiling is a platform limit, not a style band.",
                  "First post carries the claim, not the setup.",
                  "No hashtag stuffing; one at most, or none."],
    },
    "bluesky": {
        "gates": ["chars", "dash"],
        "band": (30, 70),
        "ceiling": {"chars": 300},
        "send_as": "thread",
        "notes": ["Hard 300 per post.",
                  "Link cards render, so do not also paste the bare URL."],
    },
    "github_readme": {
        "gates": ["dash"],
        "band": (20, 80),
        "ceiling": {},
        "send_as": "document",
        "notes": ["Opens with what it is and how to run it, not with motivation.",
                  "Every command shown must have been executed."],
    },
    "recruiter_reply": {
        "gates": ["chars", "lines", "dash"],
        "band": (25, 75),
        "ceiling": {"chars": "p90"},
        "send_as": "single",
        "notes": ["No studied-not-shipped claims; resume claims need project evidence.",
                  "Name the constraint (location, stack, timing) in the first two lines."],
    },
}

# Tells that are a hard fail on every surface. Asserted.
HARD_FAIL = {
    "em_dash": (re.compile(r"[—–]|&mdash;|&ndash;"),
                "em/en dash: standing style rule, use a colon, comma or parenthesis"),
    "negative_parallel": (re.compile(r"\b(?:it'?s|this is|that'?s)\s+not\s+\w+[^.?!]{0,40},\s*it'?s\b", re.I),
                          "negative parallelism: 'not X, it's Y'"),
    "not_just": (re.compile(r"\bnot just\b[^.?!]{0,60}\bbut\b", re.I),
                 "'not just X but Y' construction"),
    "delve": (re.compile(r"\b(?:delve|leverage|robust|seamless|game.?chang\w+|"
                         r"navigat\w+ the (?:complex|landscape)|in today'?s\b)", re.I),
              "generic LLM register word"),
    "pivot_para": (re.compile(r"^(?:but here'?s|and here'?s|here'?s the thing|"
                              r"the (?:kicker|catch|twist))\b.{0,60}$", re.I | re.M),
                   "Pivot Paragraph: a line that only announces significance"),

    # Hebrew register markers. Every one of these was counted against the 35,472
    # message corpus first and appears at most twice; candidates that DO occur in
    # real chat were dropped, including several that sound just as formal:
    # משמעותי (37 hits), נא ל (35), קריטי (22), אשר (4), מדובר ב (4), and
    # לא רק...אלא גם (4). That last one is textbook negative parallelism and is
    # still real usage here, which is the reason for measuring instead of
    # guessing. Re-run scratchpad/spell/mine_markers.py before adding to this.
    "he_officialese": (re.compile(
        r"הריני|ברצוני|להודיע[ךכם]|פניית[ךכם]|לעיונ[ךכם]|בכבוד רב|"
        r"בהקדם האפשרי|בהמשך לשיחתנו|אבקש ל|אודה ל"),
        "formal Hebrew officialese, absent from this corpus"),
    "he_generated": (re.compile(
        r"חשוב לציין|ראוי להדגיש|יש לזכור כי|בעולם של היום|טומן בחובו|"
        r"ישנ[םן] מספר|עשוי להוביל|תוך שמירה על|בהתאם לנסיבות|\bלגופו\b|"
        r"\bלסיכום\b|זה לא רק .{1,30}, ?זה "),
        "generated-assistant Hebrew register, absent from this corpus"),
}


def load(path=None):
    path = path or os.path.join(HERE, "profiles.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(profiles, path=None):
    path = path or os.path.join(HERE, "profiles.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=1)
    return path
