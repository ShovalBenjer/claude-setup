"""Does the speaker split find speakers, or just topics?

owner_sim from the engine is circular: the owner side is *chosen* as the one
nearest the global centroid, so it is near it by construction. The honest test
is a contrast:

  If the split is finding speakers, the owner-side centroids should agree with
  each other across unrelated threads far more than the counterparty-side
  centroids agree with each other, because the counterparties are 15 different
  people while the owner is one person.

  If the split is finding topics, both sides are mixtures of the same two
  people and the two agreement numbers collapse together.

Also runs a label-permutation null: reshuffle which side is called "owner" at
random and check the observed gap sits outside that null distribution.
"""
import sys
import numpy as np

sys.path.insert(0, r"C:\Users\shova\.claude\skills\voice-metrics")
from voice_engine import build, load_threads, turns  # noqa: E402

DB = "wa_work/genericStorage.dec.db"


def unit(v):
    return v / max(1e-12, np.linalg.norm(v))


def pairwise_mean(C):
    """Mean cosine between distinct rows of a centroid matrix."""
    G = C @ C.T
    n = len(C)
    return float((G.sum() - np.trace(G)) / (n * (n - 1)))


emb, threads, mine, theirs, owner, rep = build(DB, min_msgs=120)
print(f"threads: {rep['threads_used']}  messages: {rep['messages']:,}  "
      f"explained var: {rep['explained_variance']}")

cids = [c for c in mine if mine[c] and theirs.get(c)]
M = np.array([unit(emb.transform([" ".join(sum(mine[c], []))])[0]) for c in cids])
T = np.array([unit(emb.transform([" ".join(sum(theirs[c], []))])[0]) for c in cids])

mm, tt = pairwise_mean(M), pairwise_mean(T)
print(f"\nthreads compared        : {len(cids)}")
print(f"owner-side agreement    : {mm:+.4f}   (one person across {len(cids)} threads)")
print(f"counterparty agreement  : {tt:+.4f}   ({len(cids)} different people)")
print(f"gap                     : {mm - tt:+.4f}")

# permutation null: randomly reassign which side is "owner" per thread
rng = np.random.default_rng(0)
null = []
for _ in range(2000):
    flip = rng.random(len(cids)) < 0.5
    A = np.where(flip[:, None], T, M)
    B = np.where(flip[:, None], M, T)
    null.append(pairwise_mean(A) - pairwise_mean(B))
null = np.array(null)
p = float((null >= (mm - tt)).mean())
print(f"permutation null mean   : {null.mean():+.4f}  sd {null.std():.4f}")
print(f"p(null >= observed gap) : {p:.4f}   over 2000 permutations")

verdict = "SUPPORTED" if (mm - tt) > 0.05 and p < 0.05 else "NOT SUPPORTED"
print(f"\nspeaker separation: {verdict}")

# what the owner side actually looks like, as a shape check (no content printed)
lens = [len(m) for c in cids for t in mine[c] for m in t]
tlens = [len(m) for c in cids for t in theirs[c] for m in t]
print(f"\nowner-side messages     : {len(lens):,}  median {int(np.median(lens))} chars")
print(f"counterparty messages   : {len(tlens):,}  median {int(np.median(tlens))} chars")
