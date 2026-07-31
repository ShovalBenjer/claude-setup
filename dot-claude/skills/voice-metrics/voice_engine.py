"""Idiolect embedding + speaker separation over the local WhatsApp corpus.

Why a corpus-trained embedding and not a pretrained sentence encoder:

  1. Pretrained multilingual encoders embed *meaning*. Voice matching needs
     *idiolect*: spelling habits, elongation (חחחח), abbreviation, emoji, burst
     rhythm. Two messages with identical meaning and different handwriting must
     land far apart, which is the opposite of what a semantic encoder does.
  2. The corpus is private message content. A hosted embedding API would ship it
     off the machine, so anything requiring a network call is out regardless of
     quality.

So the model is hashed character n-gram TF-IDF, PCA-whitened, fitted on this
corpus only. numpy is the sole dependency.

SPEAKER DIRECTION IS NOT AVAILABLE, AND THE ATTEMPT TO INFER IT FAILED.

genericStorage.dec.db is WhatsApp Desktop's search mirror; it has no sender
column, and no other decrypted store carries one. An unsupervised recovery was
attempted here (cluster each thread into two voices, then pick the side that
recurs across threads, since exactly one person is in every thread) and it was
rejected by its own diagnostic:

    owner-side cross-thread agreement   +0.884
    counterparty cross-thread agreement +0.430   gap +0.455, permutation p<0.001

    alternation minus chance, per gap setting:
      message-level -0.010 | 30s -0.019 | 90s -0.012 | 300s +0.006

The contrast looked strong, but speakers alternate (A B A B) and these labels do
not: alternation sits at chance for every segmentation. The clusters are
generic-versus-thread-specific vocabulary, which reproduces the same contrast
with no speaker information in it. See scratchpad/spell/diag_turns.py.

Consequence for every metric below: per-contact statistics are THREAD-LEVEL,
both sides combined. Label them that way. For a close friend writing in the same
register they remain a usable target, but "his authored messages" is a claim this
corpus cannot support. separate_speakers() is kept only so the negative result
stays reproducible; do not use its output as authorship.
"""
import hashlib
import os
import re
import sqlite3
import numpy as np

DIM = 2048          # hashing-trick width before PCA
NGRAMS = (3, 4)     # character n-gram orders
COMPONENTS = 64     # PCA output dimension
BURST_GAP_SEC = 90  # gap above which a new speaker turn is assumed to start


# ---------------------------------------------------------------- text

_ELONG = re.compile(r"(.)\1{2,}")
_DIGIT = re.compile(r"\d")
_WS = re.compile(r"\s+")


def normalize(t):
    """Collapse the things that vary run-to-run but not writer-to-writer."""
    t = _ELONG.sub(r"\1\1", t)      # חחחחחח and חחח are the same habit
    t = _DIGIT.sub("#", t)
    t = _WS.sub(" ", t).strip()
    return t.lower()


def ngrams(t):
    t = f" {normalize(t)} "
    for n in NGRAMS:
        for i in range(len(t) - n + 1):
            yield t[i:i + n]


_HCACHE = {}


def _hash(s):
    """Stable 64-bit hash. Python's built-in hash() is salted per process, so
    using it would make every run produce a different embedding."""
    h = _HCACHE.get(s)
    if h is None:
        h = int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "little")
        _HCACHE[s] = h
    return h


# ---------------------------------------------------------------- model

class IdiolectEmbedding:
    """Hashed char-ngram TF-IDF -> PCA. Fit once on a corpus, then transform."""

    def __init__(self, dim=DIM, components=COMPONENTS, seed=0):
        self.dim = dim
        self.components = components
        self.seed = seed
        self.idf = None
        self.mean = None
        self.proj = None

    def _counts(self, docs):
        """(N, dim) float32 term-count matrix via the hashing trick."""
        X = np.zeros((len(docs), self.dim), dtype=np.float32)
        for i, d in enumerate(docs):
            row = X[i]
            for g in ngrams(d):
                # signed hashing keeps collisions from systematically inflating
                h = _hash(g)
                row[h % self.dim] += 1.0 if (h >> 32) & 1 else -1.0
        return X

    def _tfidf(self, X):
        X = np.sign(X) * np.log1p(np.abs(X))     # sublinear tf, sign preserved
        X *= self.idf
        n = np.linalg.norm(X, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return X / n

    def fit(self, docs):
        X = self._counts(docs)
        df = (X != 0).sum(axis=0).astype(np.float32)
        self.idf = np.log((1.0 + len(docs)) / (1.0 + df)) + 1.0
        X = self._tfidf(X)
        self.mean = X.mean(axis=0)
        Xc = X - self.mean
        # PCA through the dim x dim covariance: dim is 2048, so this is cheap
        # and avoids an SVD of the full N x dim matrix.
        cov = (Xc.T @ Xc) / max(1, len(docs) - 1)
        vals, vecs = np.linalg.eigh(cov.astype(np.float64))
        order = np.argsort(vals)[::-1][:self.components]
        self.proj = vecs[:, order].astype(np.float32)
        self.explained = float(vals[order].sum() / max(1e-12, vals.sum()))
        return self

    def transform(self, docs):
        X = self._tfidf(self._counts(docs))
        Z = (X - self.mean) @ self.proj
        n = np.linalg.norm(Z, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return Z / n


def cosine(A, b):
    return A @ (b / max(1e-12, np.linalg.norm(b)))


# ---------------------------------------------------------------- corpus

def load_threads(db, min_msgs=200, exclude_groups=True):
    """{chatId: [(timestamp, text), ...]} for two-party threads."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT chatId, CAST(timestamp AS INTEGER) ts, text FROM message "
        "WHERE text IS NOT NULL AND text<>'' ORDER BY chatId, ts").fetchall()
    con.close()
    threads = {}
    for cid, ts, text in rows:
        if exclude_groups and cid.endswith("@g.us"):
            continue
        if "http" in text or len(text) > 600:
            continue  # forwarded blobs and link previews are not authored text
        threads.setdefault(cid, []).append((ts or 0, text))
    return {c: m for c, m in threads.items() if len(m) >= min_msgs}


def turns(msgs, gap=BURST_GAP_SEC):
    """Group consecutive messages into speaker turns by time gap.

    A turn is a run of messages with no long pause, which in a two-party thread
    is usually one person talking. It is a heuristic, and it is why the speaker
    labels below are reported with a measured confidence rather than asserted.
    """
    out, cur = [], []
    prev = None
    for ts, text in msgs:
        t = ts // 1000 if ts > 1e12 else ts
        if prev is not None and t - prev > gap and cur:
            out.append(cur)
            cur = []
        cur.append(text)
        prev = t
    if cur:
        out.append(cur)
    return out


def _two_means(Z, seed=0, iters=25):
    """Split rows of Z into two clusters. Returns a boolean mask."""
    rng = np.random.default_rng(seed)
    if len(Z) < 2:
        return np.zeros(len(Z), dtype=bool)
    # init on the most separated pair found in a small random sample
    idx = rng.choice(len(Z), size=min(64, len(Z)), replace=False)
    S = Z[idx]
    G = S @ S.T
    i, j = np.unravel_index(np.argmin(G), G.shape)
    c0, c1 = S[i].copy(), S[j].copy()
    mask = np.zeros(len(Z), dtype=bool)
    for _ in range(iters):
        new = (Z @ c1) > (Z @ c0)
        if np.array_equal(new, mask):
            break
        mask = new
        if mask.any():
            c1 = Z[mask].mean(axis=0)
        if (~mask).any():
            c0 = Z[~mask].mean(axis=0)
    return mask


def separate_speakers(threads, emb, seed=0):
    """Infer which side of each thread is the account owner.

    Alternating turns give two candidate voices per thread. The owner is the
    voice that recurs across threads, so the per-thread assignment is chosen to
    maximise agreement with a global owner centroid, re-estimated to convergence.
    """
    per = {}
    for cid, msgs in threads.items():
        tn = turns(msgs)
        texts = [" ".join(t) for t in tn]
        if len(texts) < 8:
            continue
        Z = emb.transform(texts)
        mask = _two_means(Z, seed=seed)
        if mask.all() or not mask.any():
            continue
        per[cid] = (tn, Z, mask)

    # global owner centroid, initialised from the side of each thread that is
    # closest to the corpus mean, then refined
    owner = np.mean([Z.mean(axis=0) for _, Z, _ in per.values()], axis=0)
    labels = {}
    for _ in range(12):
        changed = False
        cents = []
        for cid, (tn, Z, mask) in per.items():
            a, b = Z[~mask].mean(axis=0), Z[mask].mean(axis=0)
            pick = 1 if float(b @ owner) > float(a @ owner) else 0
            if labels.get(cid) != pick:
                changed = True
            labels[cid] = pick
            cents.append(b if pick else a)
        new_owner = np.mean(cents, axis=0)
        new_owner /= max(1e-12, np.linalg.norm(new_owner))
        owner = new_owner
        if not changed:
            break

    # evidence: how separable was each thread, and how consistent is the owner
    seps, mine, theirs = [], {}, {}
    for cid, (tn, Z, mask) in per.items():
        pick = labels[cid]
        m = mask if pick else ~mask
        mine[cid] = [t for t, k in zip(tn, m) if k]
        theirs[cid] = [t for t, k in zip(tn, m) if not k]
        a, b = Z[~m].mean(axis=0), Z[m].mean(axis=0)
        a /= max(1e-12, np.linalg.norm(a))
        b /= max(1e-12, np.linalg.norm(b))
        seps.append(1.0 - float(a @ b))          # 0 = indistinguishable
        # owner-side agreement with the global centroid
        theirs.setdefault(cid, [])
    owner_sim = [float(emb.transform([" ".join(sum(v, []))])[0] @ owner)
                 for v in mine.values() if v]
    report = {
        "threads_used": len(per),
        "mean_separation": float(np.mean(seps)) if seps else 0.0,
        "owner_sim_mean": float(np.mean(owner_sim)) if owner_sim else 0.0,
        "owner_sim_min": float(np.min(owner_sim)) if owner_sim else 0.0,
        "thread_coverage": sum(1 for v in mine.values() if v) / max(1, len(per)),
    }
    return mine, theirs, owner, report


# ---------------------------------------------------------------- entry

def build(db, seed=0, min_msgs=200):
    threads = load_threads(db, min_msgs=min_msgs)
    flat = [t for msgs in threads.values() for _, t in msgs]
    emb = IdiolectEmbedding(seed=seed).fit(flat)
    mine, theirs, owner, report = separate_speakers(threads, emb, seed=seed)
    report["messages"] = len(flat)
    report["explained_variance"] = round(emb.explained, 4)
    return emb, threads, mine, theirs, owner, report


if __name__ == "__main__":
    import sys, json
    db = sys.argv[1] if len(sys.argv) > 1 else "wa_work/genericStorage.dec.db"
    if not os.path.exists(db):
        raise SystemExit(f"corpus not found: {db}")
    emb, threads, mine, theirs, owner, rep = build(db)
    print(json.dumps(rep, indent=2))
