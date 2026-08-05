# What is left in this repo, and which parts cannot close today

Status: analysis, point-in-time, 2026-08-05
Lane: A
Measured from: `TODO.md` at `7bf26a6`, `gh run` output, and commands re-run this session

The operator asked for the full remaining task list with the intention of finishing
the repository in one session. The list is below. The finish is not available, and the
reason is structural rather than a matter of effort, so the categories are the useful
part of this document.

`TODO.md` carries **106 open rows**. Six of them reach a new session, because
`~/.claude/hooks/session-recall.sh:112` slices `[:6]` and nothing orders the file. That
is itself row one of the FOG section.

## The measurement that changed while this was being written

Another Claude session was committing into the same working tree during this one. HEAD
moved `861249a` to `7bf26a6` mid-analysis, `.git/index` mtime tracked to within five
seconds of each check, and the dirty count moved 49, 35, 37. Two findings recorded
twenty minutes apart were already stale.

That is not an aside. It is the reason this session worked in a git worktree, and it is
the concrete instance of `ABSORB-03(a)`, which names worktree isolation per concurrent
producer as the fix for "the one-tree race that is open risk 1". The race is not
hypothetical and does not need to be argued for any more.

## 1. Ship-blocking on PR #37, which is the only sense in which this repo can be "finished" today

Three domains, two causes. `rules` was the third and is closed by PR #39.

| domain | cause | who can close it |
|---|---|---|
| `rules` | `rules_sync.py` returned FAIL when `~/.claude/rules` is absent, which is every runner. Red by construction. | CLOSED, PR #39. `rules PASS` observed on a real runner. |
| `docmap` | `docs/DOCMAP.md` was committed ahead of the spec and standards files it was generated from. Regenerating against the committed inputs moves 11 rows, and 4 `docs/standards/*` files have no derivable status in committed form. | whoever holds the uncommitted spec and standards edits |
| `unit` | not an independent failure. `tests/test_trycmd.py` pins `docmap selftest` output, so it fails for the row above and nothing else. 417 of 418 pass. | closes with `docmap` |

An earlier reading of mine said the `docmap` cause was untracked documents that CI
cannot see. That was wrong, and diagnosing it in a tracked-only worktree is what
corrected it. The generated map shipped without its inputs; the untracked files are not
involved.

`review` is WAIVED on renewal 4, and the waiver text says the renewal is now the
finding. It refuses to certify a dirty tree, so it cannot go green while any session is
mid-work. Fixing all three of its HIGHs would leave it red anyway, because dirty-tree is
the blocking condition and not the finding count.

## 2. Closable by measurement, at no cost

Rows whose own claim is already refuted by evidence on disk. These are free and they are
the class the memory `findings-go-stale-and-nothing-notices` exists for.

- **REFUTE-02** says live `~/.claude/CLAUDE.md` is DELETED and that nothing noticed for
  two days. It exists, 3610 bytes, mtime 2026-08-03 13:40, restored by the 08-03
  session. The row is stale.
- **Zion #20** says `gemini-review.yml` "has still never been written". It is on disk at
  4868 bytes and the `pipeline` domain names it. The row already says to correct the
  issue rather than delete it, because whether it RUNS is a separate question. It has now
  run: Gemini diff review reports `success` on every run observed today.

## 3. Bounded implementation, no approval needed

Each carries its own stated regression test, which is what makes it bounded.

- **DOCS-02**, `slop_lint.py` has no notion of fenced code blocks, so it lints mermaid
  and code samples as prose. The row states the oracle: a dash inside a fence is CLEAN
  and the identical dash outside it is a HIT, in one file.
- **`strand.py` header check.** `docs-control-plane` rule 1 names `PRD:` / `Ticket:`
  first and 6 of 19 specs carry one. Rule 3 wants `docs/specs/archive/`, which does not
  exist, so that rule is unenforceable by construction. Both extend a tool that already
  parses every spec.
- **RT-3**, print the joint claim under `gate.py run`'s VERDICT: which domains were N/A
  and why, and what a PASS does not assert. The strings already exist in
  `quality-contract.json`.
- **Session-recall ordering.** The row calls the cheap fix a four-character change to the
  hook's predicate, preferring rows marked `[boot]`. The expensive fix is ordering the
  file. Raising the cap is explicitly the wrong answer.
- **`new-recruit` has a 10-domain contract and no run ledger.** One command settles
  whether it has ever run: `gate.py run --project ../new-recruit`.

## 4. Operator-only, and naming why nobody else can decide

- **ZION-01** needs `gh auth refresh -s read:project,project`, which is an interactive
  browser step. Everything on the Zion board is behind it, including ZION-02 and ZION-03.
- **REFUTE-03**, the pre-write snapshot for the pending `settings.json` write is
  incomplete, so that write is not revertable from it. Re-baseline or restore is a
  judgement about intent, not a measurement.
- **API key rotation**, P0. Not reproduced on 2026-07-24 and explicitly not cleared: the
  credential may have been deleted from view or been in a different chat.
- **RATCHET-01** needs `/diverge` first under charters rule 2, and it is the highest-value
  structural row on the list: every defect found on 2026-07-31 was the same shape, a
  number produced and bound to nothing that stops.
- **voice-metrics preservation**, the only live-only skill not committed; its
  `profiles.json` keys include a WhatsApp linkable id.
- **panel.py token-aware pass** and the **completion_gate advice-without-artifact
  extension** are both oracle edits, which this repo requires approval for.

## 5. Cross-lane, so proposal rows and nothing else

- **ABSORB-02**, point-in-time reconstruction for gitignored ledgers. The concrete need
  is `hiring_engine/ledger.sqlite`, which lane B owns.
- **REFUTE-06**, the same ledger, absent at the path the claim names.
- **AUTO-15**, resume rails.

The `new-recruit` Windows copy at `C:/Users/shova/new-recruit` carries **104 uncommitted
files and no git remote**. `docs/charters.md` states that copy "was measured to hold
nothing the WSL tree lacks and is being retired". Those two facts do not agree, and the
disagreement is lane B's to settle.

## 6. Time-windowed, unfinishable today at any effort

- **AUTO-09** scales the nightly to tier-1 repos after 7 clean days.
- **Deterministic preflight** lands its Stop-gate check after two measured weeks.
- **RT-1** and **RT-2** need accumulated data that does not exist yet: a
  `{claimed_confidence, action, verified_outcome}` ledger, and a human approve-or-reject
  ratio. RT-2's own observation is the sharp one, that a rejection rate which has never
  seen a rejection IS the finding.
- **AUTO-18** needs one unattended fire observed, which is a clock, not a task.

## What is not in any category above

The rows in `## P2`, `## P3`, `## P4` and `## Continuous` are older and coarser than the
2026-07-29 onward sections, several are duplicated by later rows written with more
measurement behind them, and at least one (`P-DASH` versus `ABSORB-05`) is explicitly
flagged in-file as the same work under two names. Classifying them honestly needs a
dedup pass over `TODO.md` itself, which is a task and is not this document.

## The counting caveat

106 is the count of lines matching `- [ ]`. Rows written as `- **` are invisible to that
predicate and to session recall, and the FOG section records ten that had the defect. So
106 is a floor, not a total, and no number in this document should be read as the size of
the remaining work.
