# Can we build our own Dolt, and would it overcome theirs

Date: 2026-07-25
Question as asked: "gave you dolthub repo, can we do it our own version? Will
that overcome theirs?"

**Short answers: yes we could build a version of the part we actually use, no it
would not overcome theirs, and my recommendation is to build neither — because
the capability you want is already sitting in this repo unfinished.**

---

## 1. What Dolt actually is

A MySQL-wire-compatible relational database whose storage is a content-addressed
prolly tree, so a table has commits, branches, diffs and merges the way a
filesystem does under git.

- **334,628 non-test Go LOC** across three co-maintained repos.
- **239 contributors**, created 2019-07-24, still shipping (v2.2.2).

The five genuinely hard parts, measured:

1. **The prolly tree** — content-defined chunking via a Weibull keySplitter over
   buzhash. This is what makes a diff sub-linear instead of a full table scan.
2. **Three-way structural merge reconciled against SQL invariants** —
   `doltcore/merge` is 8,177 LOC. Merging two branches of a table without
   violating uniqueness, foreign keys and check constraints is the part that has
   no shortcut.
3. **The SQL engine** — go-mysql-server is 159,192 LOC, and its **enginetest
   suite alone is 223,038 LOC**. That number is the moat, not the engine.
4. **The MySQL binary wire protocol** — **Dolt's own team forked Vitess rather
   than write this.** When the people building the database decline to write a
   component, that is the strongest possible signal about its cost.
5. **Diff / history / blame system tables** — the actual user-facing feature,
   and the cheapest of the five.

**The moat, stated plainly:** broad MySQL compatibility provable at 223k-line
regression scale, sub-linear diff and merge that require the same class of
chunked tree, roughly seven years of edge-case hardening, and a wire protocol
Dolt itself would not write. Nothing about a single-operator setup changes any of
those numbers.

## 2. What we actually need it for

Measured row counts, not estimates:

| store | rows |
|---|---|
| `state/claims-verify.jsonl` | 26 |
| `state/refutations.jsonl` | 287 |
| `state/bus.jsonl` | 13 |
| `state/gate-runs.jsonl` | 132 |
| `state/lessons.jsonl` | 18 |
| `state/api-usage.jsonl` | 119 |
| `ledger.sqlite` — jobs / variants / approvals / applications / outcomes / runs / costs | 222 / 4 / 11 / 4 / 8 / 51 / 3 |
| `drops.jsonl` | 4,906 |

Total meaningful scale: a few thousand rows, single writer, single machine.

**The capability actually wanted is "what did this table say on the 25th".**

## 3. That capability already exists here, for `state/`

`state/*.jsonl` is **already git-tracked with real history**.
`git log --oneline -- state/claims-verify.jsonl` returns exactly 6 commits
(c55a401, db654d2, 0eb1639, 4940617, 2718a07, cce6851). So point-in-time
reconstruction is already one command: `git show <rev>:state/claims-verify.jsonl`.

Diff, history and blame — three of Dolt's five features — are already available
for the data that matters, because the data is append-only JSONL in git.

`tools/dolt/client.py` exists and has **zero callers anywhere in the tree**. It
was added today in commit 7bf4f9a. So the current state is not "we need Dolt", it
is "we added a Dolt client and never wired it to anything."

## 4. The four options

**(a) Run local Dolt as-is.** Real versioned SQL, zero build cost. Costs a Go
binary, a second query dialect, and a migration. The blocker is not technical:
DoltHub free accounts host **public** databases only, confirmed from DoltHub's
own docs, and this data includes resumes, ATS routing and application evidence.
So the hosted half is unavailable until a Pro account is confirmed, which removes
the main reason to adopt it.

**(b) git + append-only JSONL, as today.** Already working, already has history,
zero new dependencies, no new dialect. Weak at concurrent writers and at
querying across versions.

**(c) sqlite + an append-only audit table + a point-in-time reconstruction
script.** This is the missing piece for `ledger.sqlite`, which unlike `state/` is
gitignored (`.gitignore` lines 25-26 and 36-37) and therefore has **no history at
all**. Perhaps 150 lines.

**(d) Build our own engine.** Would need its own answer to all five hard parts
above. Against 334k LOC and 223k lines of compatibility tests.

## 5. Recommendation

**Build neither (a) nor (d).**

- Keep **(b)** for `state/`. It already answers the question Dolt would be
  adopted to answer.
- Add the reconstruction script from **(c)** to `ledger.py` **only when a
  concrete need appears** — a specific question about a specific past day that
  cannot be answered now. Not before. Building it speculatively is the same
  pipeline-engineering trap in a new costume.
- Revisit local Dolt only if a real cross-machine multi-writer need materialises
  **and** a private or self-hosted remote path is verified.
- Either wire `tools/dolt/client.py` to something real or delete it. A client
  with zero callers is a claim with no oracle.

## 6. Will it overcome theirs

**No.** Not on compatibility (223k lines of enginetest), not on diff/merge
performance (the prolly tree is the whole product), not on the wire protocol
(Dolt forked Vitess rather than write it), and not on hardening (seven years,
239 contributors). At a few thousand single-writer rows there is also nothing to
overcome — the comparison only exists if we adopt their problem.

## 7. Verification note against my own earlier draft

An adversarial refuter re-derived every load-bearing fact here and the
recommendation survived. It found one factual error, corrected above: an earlier
draft claimed `ledger.sqlite` and `drops.jsonl` were "not even in `.gitignore`".
**That is false** — both are listed in `new-recruit/.gitignore` at lines 25-26 and
36-37. The conclusion is unchanged; the citation was wrong and is fixed.
