# Point-in-time reconstruction: what git already answers, and the narrow strip it does not

Date: 2026-07-30
Ticket: ABSORB-02, deferred 2026-07-25 in `docs/analysis/2026-07-25-our-own-dolt.md`
section 4(c) as "roughly 150 lines" to be built "only when a concrete need
appears".
Component: `tools/timetravel/snapshot.py`, 691 lines, stdlib only.
Prior-art record: `docs/prior-art/tools-timetravel.json`.

**Lead with the weakest part: a shadow bare git repository covers most of this
capability in about fifteen lines of shell, I ran it, and it works. The 691
lines buy one property, and if the operator does not want that property this
component should be deleted rather than kept.** Details in section 5.

---

## 1. What the 2026-07-25 deferral said, and what has changed

Section 4(c) proposed "sqlite plus an append-only audit table plus a
point-in-time reconstruction script", motivated by `ledger.sqlite` in the
`new-recruit` repository, which is gitignored there and so has no history.
Section 5 deferred it: add it to `ledger.py` only when "a specific question
about a specific past day that cannot be answered now" appears.

Section 3 of that document is the part that has aged least well, and correcting
it is most of what has changed:

> `state/*.jsonl` is **already git-tracked with real history** [...] So
> point-in-time reconstruction is already one command.

That is true of the ledgers it sampled and false as a statement about `state/`.
It generalised from four tracked files to a directory that also holds ignored
ones. Measured on 2026-07-30 with `git status --ignored --porcelain state/`:

| ignored path | bytes | rows | git history |
|---|---|---|---|
| `state/handback-log.jsonl` | 70,922 | 735 | none |
| `state/hook-fires.log` | 56,391 | 613 | none |
| `state/api-usage.jsonl` | 22,820 | 120 | none |
| `state/openrouter-models.json` | 735,378 | 29,652 | none |
| `state/nvidia-models.json` (untracked) | 12,394 | 613 | none |
| `state/tmp-pointers.tsv` (untracked) | 12,401 | 77 | none |
| `state/bus-cursors/{A,B,C}.txt` | 16 each | 1 each | none |
| `state/sessions/*.json` | 18 KB total | 14 files | none |

Three further things changed since the deferral, none of them predicted by it:

1. `state/handback-log.jsonl` became load-bearing evidence. It was gitignored on
   2026-07-29 for a sound reason, that a Stop hook writing a tracked file
   invalidates the tree fingerprint the gate just took. Later the same day
   `~/.claude/rules/model-selection.md` named that same file as the evidence
   source for the fable falsifier: "compare handback blocks and restart turns
   per session (state/handback-log.jsonl)". A falsifier whose evidence file has
   no history can only ever be evaluated against the present. The two decisions
   were correct separately and collide.
2. `state/sessions/` was added on 2026-07-29, ignored for the same fingerprint
   reason, and it is per-session runtime state.
3. The deferral located the need in another repository's `ledger.sqlite`, which
   lane B owns. The need that actually arrived is in this repository and belongs
   to lane A.

---

## 2. What git already answers, and is not rebuilt here

For any tracked, committed file, `git show <rev>:<path>` is the whole feature.
Diff, history and blame come with it. None of that is reimplemented, and a
proposal to reimplement it should be rejected.

**Verified case, one of the three the ticket named.** `tools/review/panel.py`
line 11 asserted "the codex binary is not installed" while codex-cli 0.146.0 was
installed and authenticated. Git answers this completely and in one command:

```
$ git log --oneline -L 5,15:tools/review/panel.py
6332186 feat(gate): produce a ship verdict the agent does not author
+(dot-claude/bin/external-review-judge.py) and both of its backends are shut on
+this machine: the codex binary is not installed, and Gemini Free Tier is barred
```

`git log -1 --format=%ad --date=iso 6332186` gives 2026-07-25 09:14:55 +0300.
The correction sits in the working tree, uncommitted, dated 2026-07-30. So the
false claim stood **five days**, from 2026-07-25 09:14 until 2026-07-30, and git
supplied the introduction commit, its date, and the exact line. Nothing new was
needed and nothing new was built for it. This case is the argument for the scope
limit, not for the tool.

---

## 3. What git cannot answer

Two disjoint populations of bytes, both outside git by construction.

### 3a. Permanent: files matched by .gitignore

No revision contains them, so no revision can be asked. This is not a git
failure and not a policy mistake. The ignore rules are correct: these are
machine-local telemetry, and committing the Stop-hook log would make the gate's
own tree fingerprint self-invalidating.

The cost was already paid once and written into `.gitignore` itself, above
`state/bus-cursors/`:

> Ignored deliberately, with one consequence accepted: a cursor's prior value is
> then unrecoverable, which is how lane B's pre-reset value was already lost on
> 2026-07-25.

That is a measured loss with a date on it, recorded in the file that caused it.
It is the strongest single item of evidence in this document, because it is not
a hypothetical about a future question.

### 3b. Transient: tracked files overwritten before any commit

**The `review` waiver incident, 2026-07-30.** The ticket asks whether git can
say when the waiver in `quality-contract.json` changed from "until 2026-08-12"
to "until 2026-08-02". It cannot, and the reason is worth stating precisely
because it is not the reason the ticket assumed.

`quality-contract.json` is tracked. `git log --oneline -- quality-contract.json`
returns exactly two commits, `8d40794` and `4940617`. Neither contains either
waiver. Both waivers were written into the working tree during a single session,
the second overwriting the first, and the file has not been committed since. Git
answers correctly that it was never told. The bytes of the 2026-08-12 waiver,
including its stated reason, exist nowhere.

So this is not a gitignored-ledger case. It is a third class the 2026-07-25
analysis never considered: **a file the gate READS as authority while a session
OVERWRITES it, where the intermediate value is authoritative for the duration of
a gate run and then gone.** A waiver is exactly that shape. It licenses a domain
to fail, it is read by an oracle, and its supersession leaves no trace.

`git stash` and a WIP commit both cover this class, and both require somebody to
decide *before* the overwrite that this intermediate state will matter later.
On 2026-07-30 nobody knew that. That is what makes periodic capture different in
kind from voluntary capture, and it is the only defensible reason to include the
transient class in a tool aimed at the permanent one.

---

## 4. What was built

`tools/timetravel/snapshot.py`, stdlib only, append-only, write-once.

- **Targets are derived, not listed.** `git status --porcelain --ignored -- state`
  supplies the ignored and untracked population; `git diff --name-only HEAD`
  filtered through `TRACKED_WATCH` supplies the dirty-tracked one. A ledger added
  next month is covered without anyone updating a list, the same principle
  `codemap.py` uses when it derives prior-art obligations from line count.
- **`TRACKED_WATCH` is `quality-contract.json` plus everything under `state/`.**
  Deliberately not the whole `git diff HEAD` set. The first real run took the
  full dirty tree: 171 paths and 7.4 MB, mostly documentation. A tool that copies
  the working tree is a backup, not a ledger history. Narrowed to 43 paths.
  `--all-dirty` restores the wide behaviour for anyone who wants it.
- **Content-addressed.** Blobs live at `objects/<aa>/<sha256>` and are written
  once. Two consecutive runs over the repository produced 42 new blobs then 1,
  so an unchanged ledger costs a manifest entry and no bytes.
- **Committed evidence, local content.** `state/timetravel/.gitignore` ignores
  `objects/` and leaves `manifest.jsonl` tracked, matching
  `state/snapshots/.gitignore` (`*/files/`) and for the same stated reason. Path,
  size and sha256 prove *when* a ledger moved without carrying *what* it said, so
  `log` and `changed` answer from a fresh clone and only `at --content` needs
  this machine.
- **Degradation instead of refusal.** A file over 4 MB is recorded with its hash
  and `captured: false`, so "it changed at 14:00" still answers even though "here
  is what it said" does not.

Verbs: `snap`, `at`, `log`, `changed`, `verify`, `selftest`.

Two real defects were found during construction and are pinned by assertions
rather than described:

1. Two `snap` calls in one shell pipeline both stamped `20:57:38Z`. Ordering is
   this tool's only product, so second resolution was insufficient. Stamps are
   now millisecond-resolution and `next_ts()` refuses to append a row that does
   not sort strictly after the previous one, which also covers a backwards clock.
2. `parse_when()` could not read the tool's own printed stamps, so copying a
   timestamp out of `log` into `at` raised `ValueError`. That is the primary
   workflow. Fixed, with a round-trip assertion.

**Do not wire this to a Stop hook.** Appending to a tracked manifest as a side
effect of ending a turn is the exact loop that got `state/handback-log.jsonl`
ignored in the first place.

---

## 5. The strongest counterargument, run rather than assumed

A bare git repository whose work-tree is this repo covers the gitignored case
completely. Executed 2026-07-30 in a scratch repository:

```
git init -q --bare state/tt/shadow.git
export GIT_DIR=state/tt/shadow.git GIT_WORK_TREE=.
git add -f state/ignored.jsonl && git commit -qm t1
# ...overwrite the file...
git add -f state/ignored.jsonl && git commit -qm t2
git log --oneline -- state/ignored.jsonl     -> 99e5ca8 t2 / b024c3b t1
git show b024c3b:state/ignored.jsonl         -> {"cursor":7}
```

That is content addressing, deduplication, history, diff and blame, with seven
years more hardening than anything written here, for fifteen lines. It also
handles the dirty-tracked class, since `git add -f` does not care.

One property separates it, plus two costs:

1. **Its evidence is its object store.** Binary zlib packs and a binary index.
   There is nothing plaintext to commit into the main repository, so the
   content-local plus manifest-committed split that `state/snapshots/` uses, and
   that was a hard requirement for this work, is not expressible. A fresh clone
   learns nothing about when a ledger moved.
2. **A nested git directory perturbs the outer repository.** In the same test,
   `git status --porcelain --ignored` collapsed to a single `!! state/` row once
   the shadow existed. The gate reads git status.
3. No selftest verb, so `tools/audit/mutate.py` has nothing to run against it.

Honest reduction available: a wrapper that runs the shadow commit and then emits
a plaintext manifest from `git ls-tree` would close gap 1 in roughly 60 lines
rather than 691. That is named in the prior-art record as the design to build if
this component is ever rewritten.

---

## 6. Evidence

Reproduction of both measured incidents, in a scratch repository, comparing the
two answers directly:

```
occurrences of the superseded waiver in `git log -p --all`   0
python tools/timetravel/snapshot.py at <t1> --path quality-contract.json --content
  -> {"waived_until":"2026-08-12","reason":"first"}
python tools/timetravel/snapshot.py at <t1> --path state/secret-ledger.jsonl --content
  -> {"cursor":7}
```

`selftest`: 33 assertions, exit 0, every planted defect caught. It covers the
boundary direction of `resolve_at` (at-or-before, never nearest), version
collapsing so an hourly snapshotter does not report 24 versions a day of an
untouched file, deletion detection, window semantics for `changed`, blob fan-out
collision, the `TRACKED_WATCH` anchoring, timestamp monotonicity, and the
print-then-read round trip.

`verify`: 2 snapshots, 43 distinct blobs, 0 missing, 0 corrupt.

`python tools/map/codemap.py check` and `prior-art` both pass with the new
directory and record in place.

Not run: `tools/audit/mutate.py --spec` against this component, because it has no
spec entry yet. `tools/gate/gate.py run` was not executed, so no claim is made
about the full contract.

---

## 7. Recommendation

**Ship it, narrowly, and revisit on one condition.**

The gitignored population is real, non-trivial in size, includes the evidence
file a live falsifier depends on, and has already caused one recorded loss. The
transient waiver class is real and voluntary capture does not cover it. Those
justify periodic capture.

They do not by themselves justify 691 lines of Python over fifteen lines of
shell. What justifies that is the committed-manifest requirement, and only that.
So the recheck condition is stated plainly in the prior-art record: **if the
operator drops the requirement that the evidence be committed while the content
stays local, delete this component and use the shadow repository.**

One thing this does not do, and should not be read as doing: it does not absorb
option 4(c) for `hiring_engine/ledger.sqlite`. That is a database, its unit is
rows and not files, it lives in another repository, and lane B owns it. ABSORB-02
should stay open with its scope narrowed to that half.
