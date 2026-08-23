"""Does the voice score discriminate, and where should the threshold sit?

Held-out real messages versus four impostor registers. Reports AUC per register
(threshold-free, so it measures the feature rather than a lucky cutoff), then
picks the cutoff from the REAL distribution at a stated false-reject rate and
reports what that catches. Choosing the cutoff to separate the impostors I
invented would be fitting to my own test set.

Impostors include the actual rejected draft: a ~700-char block that reads as a
different person. That one is not synthetic, it is the case that started this.
"""
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\shova\.claude\skills\voice-metrics")
from profiles import RULES, fit_profile  # noqa: E402
from voice_engine import IdiolectEmbedding, load_threads  # noqa: E402
from voice_score import CentralityRef, score  # noqa: E402

DB = "wa_work/genericStorage.dec.db"
CID = "53403707257078@lid"

threads = load_threads(DB, min_msgs=120)
msgs = [t for _, t in threads[CID]]
cut = int(len(msgs) * 0.8)
train, held = msgs[:cut], msgs[cut:]

prof = fit_profile(train, "t", "thread-level")
emb = IdiolectEmbedding().fit(train)
ref = CentralityRef(train, emb)
print(f"train {len(train):,}  held-out {len(held):,}  k={ref.k}")

FORMAL = [
    "שלום רב, ברצוני להודיעך כי הפגישה נדחתה למועד אחר.",
    "אבקש לעדכן את פרטי ההתקשרות בהקדם האפשרי.",
    "בהמשך לשיחתנו, מצורף המסמך לעיונך.",
    "אודה לך על מענה מהיר בנושא זה.",
    "הריני לאשר את קבלת פנייתך בנושא האמור.",
    "נא להעביר את המסמכים הנדרשים עד ליום חמישי.",
    "בכבוד רב, ובתודה מראש על שיתוף הפעולה.",
    "המענה יינתן בתוך שבעה ימי עסקים ממועד הפנייה.",
]
LLM = [
    "זה לא רק פתרון, זה שינוי תפיסתי אמיתי.",
    "חשוב לציין כי ישנם מספר גורמים משמעותיים שיש לקחת בחשבון.",
    "בעולם של היום, היכולת להתאים את עצמך היא קריטית.",
    "לסיכום, מדובר בתהליך מורכב הדורש בחינה מעמיקה.",
    "ראוי להדגיש שהנושא טומן בחובו הזדמנויות רבות.",
    "מדובר בצעד משמעותי אשר עשוי להוביל לתוצאות מרשימות.",
    "יש לזכור כי כל מקרה נבחן לגופו ובהתאם לנסיבות.",
    "התהליך מאפשר גמישות רבה תוך שמירה על איכות גבוהה.",
]
ENGLISH = [
    "sounds good let me know when you are free",
    "i will be there in about twenty minutes",
    "did you see the thing i sent you earlier",
    "ok cool talk later then",
    "let me check my calendar and get back to you",
    "that works for me see you then",
]
# the draft that was rejected: right content, wrong person
REJECTED = ["""מופז, סליחה על העיכוב הקל בתשובה. נתתי לקלוד את המשימה למצוא את
הספסל מהתמונה ששלחת, בלי שום רמז ממני, והוא עבד על זה שתים עשרה שעות. הוא התחיל
מפארק הירקון, המשיך לגינת וינר, ואפילו שלח את עצמו לטורקיה בגלל מנוע חיפוש. אחר
כך הוא מצא הודעה ישנה שלנו על שאול המלך והחליט שזאת כתובת אמיתית, מה שעלה לו
בעוד שעתיים. בסוף הוא פיצח את ההצפנה של הוואטסאפ, קרא שבעים ושמונה אלף הודעות,
מצא הודעת שליח על חבילה שהושארה ליד האופניים, שם לב שיש אופניים בתמונה, והגיע
לדפנה. אגב, הוא קרא הכל, אז הוא יודע גם על איזי קפה."""]


def pcts(texts):
    return np.array([ref.of(t)[0] for t in texts])


rng = np.random.default_rng(0)
sample = [held[i] for i in rng.choice(len(held), size=min(400, len(held)), replace=False)]
real = pcts(sample)


def auc(pos, neg):
    """P(a random real scores above a random impostor)."""
    a = np.concatenate([pos, neg])
    r = a.argsort().argsort() + 1
    rp = r[:len(pos)].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


print(f"\nreal held-out: median p{np.median(real):.0f}  "
      f"p10 p{np.percentile(real, 10):.0f}  p25 p{np.percentile(real, 25):.0f}")

sets = {"formal": FORMAL, "llm": LLM, "english": ENGLISH, "rejected-draft": REJECTED}
scored = {}
for name, texts in sets.items():
    v = pcts(texts)
    scored[name] = v
    print(f"  {name:<15} n={len(texts):<3} median p{np.median(v):>5.1f}   "
          f"AUC vs real {auc(real, v):.3f}")

# Threshold chosen from the real distribution only, at a stated false-reject rate.
print("\nthreshold picked from real distribution (not from the impostors):")
for fr in (5, 10, 20):
    thr = np.percentile(real, fr)
    caught = {n: float((v < thr).mean()) for n, v in scored.items()}
    allneg = np.concatenate(list(scored.values()))
    print(f"  reject below p{thr:>5.1f}  (false-reject {fr:>2}% of real)  "
          f"catches {float((allneg < thr).mean()):.0%} of impostors   "
          + "  ".join(f"{n} {c:.0%}" for n, c in caught.items()))


# ---- full-gate pass rates, the number that actually matters ----
rules = RULES["whatsapp_close"]
def passrate(texts):
    return float(np.mean([score(t, prof, rules, ref, emb)["ok"] for t in texts]))
print("\nfull scorer (all gates, not centrality alone):")
pr_real = passrate(sample)
print(f"  real held-out   pass {pr_real:.0%}")
worst = 0.0
for n, t in sets.items():
    r = passrate(t)
    worst = max(worst, r)
    print(f"  {n:<15} pass {r:.0%}")
print(f"\nreal {pr_real:.0%} pass, worst impostor {worst:.0%} pass -> "
      + ("DISCRIMINATES" if pr_real > 0.6 and worst < 0.35 else "DOES NOT DISCRIMINATE"))
