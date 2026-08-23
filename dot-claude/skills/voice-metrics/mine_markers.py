"""Which formal/generated Hebrew markers are genuinely absent from real chat?

A hard-fail rule is only safe if the phrase never shows up in real messages.
Guessing produces rules that fire on legitimate text, so each candidate is
counted against the whole 35k-message corpus first. Anything with a non-trivial
count is rejected as a rule no matter how formal it sounds.
"""
import re
import sys

sys.path.insert(0, r"C:\Users\shova\.claude\skills\voice-metrics")
from voice_engine import load_threads  # noqa: E402

DB = "wa_work/genericStorage.dec.db"

CANDIDATES = {
    # formal register / officialese
    "הריני": r"הריני",
    "אבקש ל": r"אבקש ל",
    "אודה ל": r"אודה ל",
    "בכבוד רב": r"בכבוד רב",
    "נא ל": r"\bנא ל",
    "בהמשך לשיחתנו": r"בהמשך לשיחתנו",
    "לעיונך": r"לעיונ[ךכם]",
    "בהקדם האפשרי": r"בהקדם האפשרי",
    "אשר (relative)": r"\bאשר\b",
    "ברצוני": r"ברצוני",
    "להודיעך": r"להודיע[ךכם]",
    "פנייתך": r"פניית[ךכם]",
    # generated-assistant register
    "חשוב לציין": r"חשוב לציין",
    "ראוי להדגיש": r"ראוי להדגיש",
    "יש לזכור כי": r"יש לזכור כי",
    "בעולם של היום": r"בעולם של היום",
    "לסיכום": r"\bלסיכום\b",
    "מדובר ב": r"\bמדובר ב",
    "טומן בחובו": r"טומן בחובו",
    "לגופו": r"\bלגופו\b",
    "זה לא רק X זה Y": r"זה לא רק .{1,30}, ?זה ",
    "לא רק ... אלא גם": r"לא רק .{1,40}אלא גם",
    "ישנם מספר": r"ישנ[םן] מספר",
    "עשוי להוביל": r"עשוי להוביל",
    "תוך שמירה על": r"תוך שמירה על",
    "בהתאם לנסיבות": r"בהתאם לנסיבות",
    "משמעותי": r"משמעותי",
    "קריטי": r"קריטי",
}

threads = load_threads(DB, min_msgs=120)
texts = [t for msgs in threads.values() for _, t in msgs]
print(f"corpus: {len(texts):,} messages\n")
print(f"{'marker':<22} {'hits':>6} {'per 10k':>9}  verdict")
safe = []
for name, rx in sorted(CANDIDATES.items()):
    r = re.compile(rx)
    n = sum(1 for t in texts if r.search(t))
    rate = n * 10000 / len(texts)
    ok = n <= 3
    if ok:
        safe.append((name, rx, n))
    print(f"{name:<22} {n:>6} {rate:>9.2f}  {'SAFE as hard fail' if ok else 'reject: real usage'}")

print(f"\n{len(safe)} of {len(CANDIDATES)} candidates are safe:")
for name, rx, n in safe:
    print(f"  {name}  ({n} hits)   {rx}")
