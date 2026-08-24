# Build a Hebrew lexicon from hspell 1.4 sources.
# hspell ships ISO-8859-8 text; everything is decoded and re-emitted as UTF-8.
# wolig.pl inflects nouns/adjectives, woo.pl inflects verbs; the .hif files add
# function words, extra words and irregular (biza) forms.
import subprocess, os, io, sys

HS = "hspell-1.4"
OUT = "he_lexicon.txt"
ENC = "iso-8859-8"


def run_gen(script, data):
    try:
        p = subprocess.run(["perl", script, data], cwd=HS, capture_output=True, timeout=600)
        if p.returncode != 0:
            print(f"  {script} rc={p.returncode} {p.stderr[:120]!r}")
        return p.stdout.decode(ENC, errors="replace")
    except Exception as e:
        print(f"  {script} failed: {e}")
        return ""


words = set()


def add(text, label):
    n0 = len(words)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # hif/dat lines can carry comma-separated variants and trailing flags
        for tok in line.replace(",", " ").split():
            # wolig marks smichut (construct state) with a trailing "-" and
            # unknown-vocalization with a leading "*"; both are annotation, and
            # dropping the token instead of the marker loses every construct
            # form (גינת, בית) from the lexicon.
            tok = tok.strip().lstrip("*").rstrip("-")
            # keep Hebrew letters plus geresh/gershayim used in real words
            if tok and all("֐" <= c <= "ת" or c in "'\"׳״" for c in tok):
                words.add(tok)
    print(f"  +{len(words)-n0:>7} from {label}  (total {len(words)})")


print("generating inflected forms...")
add(run_gen("wolig.pl", "wolig.dat"), "wolig.pl (nouns/adjectives)")
add(run_gen("woo", "woo.dat"), "woo (verbs)")
# shemp.dat is the shem-pe'ula (gerund) table; hspell runs it back through
# wolig. Without it the lexicon has no חיפוש, no התכתבות, no verbal nouns at all.
add(run_gen("wolig.pl", "shemp.dat"), "wolig.pl on shemp.dat (verbal nouns)")

print("reading word files...")
for fn in ("milot.hif", "extrawords.hif", "biza-nouns.hif", "biza-verbs.hif"):
    p = os.path.join(HS, fn)
    if os.path.exists(p):
        add(io.open(p, "rb").read().decode(ENC, errors="replace"), fn)

with io.open(OUT, "w", encoding="utf-8") as f:
    for w in sorted(words):
        f.write(w + "\n")
print(f"\nwrote {OUT}: {len(words):,} forms, {os.path.getsize(OUT)//1024} KB")
