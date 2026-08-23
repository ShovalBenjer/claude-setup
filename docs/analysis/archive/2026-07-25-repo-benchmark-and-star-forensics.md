# Three-way repo benchmark and star forensics

Date: 2026-07-25
Targets: `amirfish1/claude-command-center`, `Master0fFate/just-my-skills`,
`block/buzz`, each against this system (`claude-setup` + `new-recruit`).
Method: 13 parallel extraction agents, adversarial re-verification of every
finding, results read back from `journal.jsonl` rather than from agent summaries.

---

## 1. Did anyone buy stars

**All three: no evidence of purchase. No accusation is made against any of them.**
Every verdict survived a refuter whose instructions were to argue for purchase.

### The coverage boundary, stated first

The single most diagnostic signal is **categorically unobtainable in this
environment**. The REST `stargazers` endpoint returns 404 here for all three
targets *and* for controls `octocat/Hello-World` and `cli/cli` — confirmed across
two sessions with two different tokens. So per-star `starred_at` timestamps and
the account-age / follower distribution of stargazers could not be sampled for
anybody.

That absence is symmetric. It cannot be counted against any specific repo, and
"we could not check the best signal" is not a soft yes.

### What was measurable

| | stars | forks | stars:forks | verdict | confidence |
|---|---|---|---|---|---|
| `claude-command-center` | 103 | 8 | 12.9:1 | no evidence of purchase | medium |
| `just-my-skills` | 7 | 2 | 3.5:1 | no evidence of purchase | medium-low |
| `block/buzz` | 11,398 | 889 | 12.8:1 | no evidence of purchase | high |

Base rates for the ratio, gathered so 12.8:1 could be judged rather than
asserted: goose 9.06:1, ollama 10.34:1, browser-use 9.10:1, OpenHands 7.81:1,
cline 9.32:1. Buzz sits slightly above that band, which is what a single
mainstream-press spike does to a young repo, not what a purchase does.

**`claude-command-center`** — all 8 fork owners are distinct accounts with no
date clustering. One external contributor (`jaylfc`) has 4 merged PRs. Five
external issue filers (`itzdarc`, `gilhoffer`, `maxlevy-rakuten`, `syuval99`,
`enkayxyz`) span 2026-05-13 to 2026-07-24. The owner has 2,753 contributions.
Bought stars do not file issues over ten weeks or land merged PRs.

**`just-my-skills`** — both forkers are non-burner accounts (`IvanMo0` created
2026-01-14, `JoukoSalonen` created 2014-08-08). A 3.5:1 star:fork ratio beats the
base rate for its category: of six comparable niche prompt-library repos, most
have zero forks. The honest weak spot is that at n=7 the ratio is nearly
meaningless, and the strongest argument is really economic — buying 7 stars is
not a rational purchase.

**`block/buzz`** — the launch spike has an independent cause found directly, not
inferred: Jack Dorsey's X post on 2026-07-21 at 10:03pm, covered by 10+ outlets.
The counts were reproduced bit-for-bit.

---

## 2. What each repo actually is

### `amirfish1/claude-command-center` — real software, and the strongest of the three

- 225 code files, 266,809 LOC; 122 test files holding 1,664 `def test_`.
- A stdlib-only Python HTTP server. No framework, no dependency to audit.
- `server.py` is **78,240 lines in one file**. That is a fact about the repo, not
  a compliment.
- CI runs a py-compile matrix (3.9–3.13 × ubuntu/macos) plus a **live-boot smoke
  job** that boots the server and asserts two security invariants: a
  cross-origin POST returns 403, and a disabled plugin's route returns 404.
- `worker_engines.py:22-629` is a durable multi-engine work ledger with
  idempotency keys, and `reconcile_uncertain()` at `:113-150` replays only on
  live evidence rather than on a guess about what probably happened.

**Its CI has proven detection power, which is the rarest thing here.** A real run
recorded `conclusion: failure` at 2026-07-25T06:27:20Z, was fixed 9 minutes
later, and shipped as v5.11.1. Green that has been observed going red is worth
more than green that has never been tested.

Adopt: the on-disk `.jsonl`-as-source-of-truth read-only attach; the
idempotency-keyed ledger with evidence-gated recovery; roughly 20 lines of
live-boot CI smoke asserting one security invariant; the convention of naming a
regression test after the fix it guards.

Do not adopt: the Mac menu-bar wrapper and vendored Sparkle; the
curl-pipe-bash / Homebrew / DMG / telemetry distribution layer; the five extra
engine parsers; and the 78,240-line single-file server as an architecture.

### `Master0fFate/just-my-skills` — a prompt library, not software

- 24 files, 3,560 lines. **Zero code. Zero CI. `license: null`.**
- `evals.json` (12 cases) and `trigger-evals.json` (28 cases) look exactly like a
  test suite. **Nothing in the repo reads or grades them.** They are 40 written
  assertions that have never been executed.
- Ships "permanent, non-removable" self-attribution text and a 🟢🟡🔴 grading
  scheme.

Adopt: the SKILL.md / AGENTS.md authoring template, stripped of emoji and
self-branding; the eval-fixture JSON schema, which is a genuinely good oracle
*shape*; the parent-skill plus `subskills/*/SKILL.md` nesting.

Do not adopt: the non-removable self-attribution; the emoji grading; calling
unexecuted fixtures "tested"; and verbatim reuse of any text at all, because with
`license: null` there is no grant to rely on.

### `block/buzz` — the distribution lesson

Its engineering is not the interesting part for us. Its launch is: a named person
with reach posted it once, and tier-1 press did the rest. That is the one
capability in this comparison that cannot be built by writing better checks.

---

## 3. What we have that none of them have

Five measured, one partial. Each of these was run, not described.

1. **An executable claims ledger that refutes one of its own claims, live.**
   C-001 currently returns REFUTED with rc=1, reproduced three times. None of the
   three repos has a mechanism that can call its own README wrong.
2. **Mutation-tested selftests.** Across 4 specs, 90 of 90 planted mutations were
   caught, 0 survivors. This is the answer to "are your tests real" that
   `just-my-skills` cannot give at all and `claude-command-center` gives only by
   volume.
3. **A ship gate that refuses a stale green against a changed tree.** The tree
   fingerprint invalidates a pass the moment the tree moves, so a prior green
   cannot be cited after three more edits.
4. **A hash-chained bus that reports its own honest boundary** — "13 rows: 1
   chained, 12 predate chaining" — rather than implying the whole history is
   protected.
5. **A revertable snapshot/undo with a secrets-denying policy half.**
6. *(Partial)* `quality-contract.json` files that self-report **failing** domains.
   Partial because it is a self-audit: the file both declares the standard and
   grades against it.

## 4. What they have that we do not — the honest losses

State these first, because they are the ones that matter for anything I would
stamp:

- `claude-setup` is **private, 1 star, 0 forks, 0 external contributors**. Every
  social signal above is a signal we have no way to produce yet.
- `new-recruit` has **no git remote at all**.
- Local `main` is **15 commits ahead of `origin`**, and
  `.github/workflows/ship-gate.yml` is **not among the 3 workflows GitHub knows
  about**. So every green result from the gate **ran only on this machine**. That
  is precisely the gap `claude-command-center` has closed and we have not.
- No reproducible external contributor or issue-filer base.
- No tier-1-press-corroborated launch.
- No organic forks from identifiable non-burner accounts — which
  `just-my-skills` has at 7 stars and we do not have at all.

## 5. Top three moves, ranked by evidence gained per hour

1. **Push the 15 local commits** so `ship-gate.yml` registers and CI can be
   observed going red. 0.5–1h. Needs approval. Without this, our strongest
   claim — a gate with detection power — has the same status as
   `just-my-skills`'s ungraded fixtures: written, never executed by anyone else.
2. **Fix the BEL-corrupted C-026 verify string.** 0.25h. A claim that cannot run
   is not a claim.
3. **Re-run the gate against new-recruit's dirty tree.** Done today: VERDICT
   PASS, with `security` now passing on measurement rather than on a waiver, and
   waivers down from four to two.

## 6. The one thing to build, and it comes from the weakest repo

`just-my-skills` wrote 40 eval cases and never executed one. We have skills with
no eval fixtures at all. The gap is symmetric and theirs is easier to close, so
close ours: a runner that reads trigger-eval fixtures and **grades** them.
Shipped alongside this document as `tools/skilleval/`.
