"""Are the two clusters speakers, or topics?

The cross-thread contrast passed, but an 84/16 split is not what a two-party
thread looks like, so a competing explanation survives: cluster A is "generic
chatter" (similar in every thread) and cluster B is "distinctive chatter"
(different in every thread). That would reproduce the same contrast without
locating a single speaker.

Alternation separates the two. Speakers alternate: A B A B. Topics persist:
A A A B B B. Compared against the chance rate implied by the marginal split,
speakers sit above it and topics sit below.
"""
import sys
import numpy as np

sys.path.insert(0, r"C:\Users\shova\.claude\skills\voice-metrics")
from voice_engine import IdiolectEmbedding, load_threads, turns, _two_means  # noqa: E402

DB = "wa_work/genericStorage.dec.db"

threads = load_threads(DB, min_msgs=120)
flat = [t for m in threads.values() for _, t in m]
emb = IdiolectEmbedding().fit(flat)
print(f"threads {len(threads)}, messages {len(flat):,}\n")

for gap in (0, 30, 90, 300):
    alt, bal, n = [], [], 0
    for cid, msgs in threads.items():
        if gap == 0:
            units = [[t] for _, t in msgs]          # message-level, no grouping
        else:
            units = turns(msgs, gap=gap)
        if len(units) < 20:
            continue
        Z = emb.transform([" ".join(u) for u in units])
        m = _two_means(Z)
        if m.all() or not m.any():
            continue
        p = m.mean()
        chance = 2 * p * (1 - p)                     # P(switch) if independent
        obs = float((m[1:] != m[:-1]).mean())
        alt.append(obs - chance)
        bal.append(min(p, 1 - p))
        n += 1
    print(f"gap={gap:>3}s  threads={n:>2}  "
          f"minority share {np.mean(bal):.3f}  "
          f"alternation minus chance {np.mean(alt):+.3f}")

print("\npositive = alternating = speaker-like; negative = sticky = topic-like")
