# Bilingual spell check for drafts before publishing.
# Hebrew lexicon from hspell 1.4 (267k inflected forms), English from dwyl.
#
# Hebrew is agglutinative: prefixes ו ה ב ל מ כ ש fuse onto words, so a miss is
# retried after stripping prefixes. Slang is expected to miss; the point is to
# surface unknowns for a human to triage, not to auto-correct.
#
# Usage: python spellcheck.py <file> [<file> ...]
import io, re, sys, os

HE = "he_lexicon.txt"
EN = "en_words.txt"
HERE = os.path.dirname(os.path.abspath(__file__))

PREFIXES = ["ו", "ה", "ב", "ל", "מ", "כ", "ש", "וה", "וב", "ול", "ומ", "וכ", "וש",
            "שה", "שב", "של", "כש", "מה", "לכש", "ומה", "כשה"]

# known-good slang and proper nouns; not misspellings
ALLOW_HE = {
    "מופז", "צופאז", "איזי", "סבבה", "יאללה", "תכל'ס", "אחלה", "בקיצור",
    "חח", "חחח", "חחחח", "חחחחח", "נו", "וואו", "אינשאללה", "מבסוט",
    "דפנה", "עידו", "שובל", "קלוד", "וואטסאפ", "ווטסאפ", "גדנע",
    "ירקון", "וינר", "רמת", "איסטנבול", "טורקיה", "מיתולוגי",
}
ALLOW_EN = {
    "whatsapp", "sqlite", "json", "exif", "jfif", "gps", "cdp", "svg", "gif",
    "api", "url", "css", "html", "js", "ai", "llm", "icml", "fagen", "dl4c",
    "cloudflare", "github", "dev", "bluesky", "opus", "claude", "anthropic",
    "wal", "pbkdf", "aes", "cbc", "ofb", "sha", "dpapi", "tpm", "oduid",
    "ficus", "postmortem", "walkthrough", "greppable", "reimplemented",
    "syndication", "syndicated", "canonical", "changelog", "toolchain",
}


def load(path):
    p = os.path.join(HERE, path)
    if not os.path.exists(p):
        print(f"missing lexicon: {p}")
        sys.exit(1)
    return {w.strip() for w in io.open(p, encoding="utf-8") if w.strip()}


def he_known(w, lex):
    if w in lex:
        return True
    for p in sorted(PREFIXES, key=len, reverse=True):
        if w.startswith(p) and len(w) > len(p) + 1:
            if w[len(p):] in lex:
                return True
    # final-form letters sometimes appear mid-token in playful spelling
    return False


def check(path, he, en, include_code=False):
    text = io.open(path, encoding="utf-8").read()
    # In message drafts the deliverable itself sits in fenced blocks so it stays
    # copyable, so skipping fences there would skip everything worth checking.
    if not include_code:
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)

    # Hebrew letters are U+05D0..U+05EA; geresh/gershayim and the ASCII quotes
    # that stand in for them are allowed inside a token but cannot form one.
    he_tok = [t for t in re.findall(r"[א-ת׳״'\"]+", text)
              if re.search(r"[א-ת]", t)]
    en_tok = re.findall(r"[A-Za-z]{3,}", text)

    he_bad, en_bad = {}, {}
    for t in he_tok:
        w = t.strip("'\"׳״")
        if len(w) < 2 or w in ALLOW_HE:
            continue
        # collapse playful letter elongation: לךךךך -> לך
        norm = re.sub(r"(.)\1{2,}", r"\1", w)
        if not (he_known(w, he) or he_known(norm, he) or norm in ALLOW_HE):
            he_bad[w] = he_bad.get(w, 0) + 1
    for t in en_tok:
        w = t.lower()
        if w in ALLOW_EN or w in en:
            continue
        # removesuffix, not rstrip: rstrip("s") turns "class" into "cla"
        if any(w.endswith(sfx) and w[: -len(sfx)] in en
               for sfx in ("s", "es", "ed", "ing", "ly")):
            continue
        en_bad[t] = en_bad.get(t, 0) + 1

    print(f"\n=== {os.path.basename(path)} ===")
    print(f"tokens: {len(he_tok)} he, {len(en_tok)} en")
    if he_bad:
        print("Hebrew unknowns:")
        for w, n in sorted(he_bad.items(), key=lambda kv: -kv[1]):
            print(f"   {n:>3}x  {w}")
    else:
        print("Hebrew: clean")
    if en_bad:
        print("English unknowns:")
        for w, n in sorted(en_bad.items(), key=lambda kv: -kv[1])[:40]:
            print(f"   {n:>3}x  {w}")
    else:
        print("English: clean")


if __name__ == "__main__":
    args = sys.argv[1:]
    inc = "--include-code" in args
    files = [a for a in args if not a.startswith("--")]
    he, en = load(HE), load(EN)
    print(f"lexicons: {len(he):,} Hebrew forms, {len(en):,} English words")
    for f in files:
        check(f, he, en, include_code=inc)
