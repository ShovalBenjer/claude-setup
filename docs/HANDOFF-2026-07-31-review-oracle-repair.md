# Handoff: review-domain oracle repair, and what the thesis job taught the harness

Session 2026-07-30 into 2026-07-31. Lane B. Claim rows:
`session-2026-07-30-sql-concat-precision` in `state/claims.jsonl`, claimed before starting.

The session's paid work was outside this repo: grilling an MSc thesis PDF and its
31-slide HTML deck in `~/Downloads`. Those artifacts stay there. What lands here is the
harness work that came out of it, plus three lesson classes the outside job exposed.

---

## Goal

Close the `review` domain's recurring waiver by fixing the oracle instead of renewing it.
Operator authorised with "go on review" after the gate reported `review WAIVED` for the
third time on the same stated reason.

## Acceptance criteria, and where each is met

| criterion | evidence |
|---|---|
| the two real defects are fixed in the oracle, not waived | `tools/review/panel.py`, sql-concat pattern and new `drop_stale_lines` |
| the fix cannot silently weaken detection | `tests/test_panel_sql_concat.py` 13 cases, `tests/test_panel_stale_lines.py` 7 cases, red before and green after |
| the selftests can still fail | `python tools/audit/mutate.py --spec panel` -> 10 of 10 applied, 10 caught, 0 survived |
| the panel clears its own blocking findings | `python tools/review/panel.py run --project .` -> `VERDICT: PASS (0 high)`, was 5 high |
| the gate is green on this exact tree | `python tools/gate/gate.py run --project .` -> `VERDICT: PASS` |
| no flaky test is introduced into the unit domain | three consecutive full-suite runs, 292 passed each |

## Decisions

**Fixed rather than waived.** The waiver was on its third renewal. Its stated reason was
that all five blocking HIGH findings were pattern matches against comments and docstrings.
That reason was wrong for all five, which is the whole reason this handoff exists.

**Two distinct defects, neither of them comments.**

1. `sql-concat` asked for a SQL verb and, later on the line, a concatenation. It never
   asked for SQL. Three findings were English prose: `"Delete ~380 lines (passive/jargon/
   acronym/length checks + their selftest)"` in two `docs/prior-art` records, and
   `print("  delete .env: " + ("done" if rc == 0 else ...))` in `tools/workspace/
   clean_oren_roast.py`. The rewrite requires SQL structure (`SELECT ... FROM`,
   `INSERT INTO`, `UPDATE ... SET`, `DELETE FROM`) **and** dynamic assembly, as two
   independent lookaheads.

   Writing the test first also exposed a hole: the old pattern required the assembly
   marker to appear *after* the verb, so `f"SELECT * FROM t WHERE a = {x}"` never matched,
   because the `f` prefix sits before `SELECT`. That is the commonest Python injection
   shape and it was going unreported. The new pattern catches it. Net effect is a stricter
   oracle, not a looser one.

2. `added_lines` reported lines the tree no longer contains. It unions three diffs
   (`base...HEAD`, working tree vs HEAD, index) and dedupes by `(path, lineno)`, so the
   branch diff wins. A line added early on a branch and deleted later on the same branch
   survives into the review, carrying a line number now occupied by different text. That
   is exactly what the two `py-shell-true` findings were: real `shell=True` code this
   branch added and removed on 2026-07-27, reported against `tools/map/codemap.py:66`,
   which today is the comment recording that removal. The reviewer was blocking on a
   vulnerability the change under review fixes.

   `drop_stale_lines(project, rows)` keeps only lines the tree still contains at the
   position they claim. It is fail-open when a file is unreadable and drop-when-gone if a
   file no longer exists, because those are different facts that both raise `OSError`.
   This mirrors a rule the panel already enforced in the other direction: its mutation
   spec carries "findings citing a line the change did not add are kept" as a regression
   it must catch.

**The waiver was replaced, not deleted.** `quality-contract.json` `domains.review.waived`
now expires 2026-08-02 instead of 2026-08-12, and its reason records the old reason as
measurably wrong rather than quietly dropping it. What remains waived is only that the
review domain refuses to certify a dirty tree, and this tree carries 130-plus uncommitted
files that are not this session's to commit. Nothing about the code is excused. The
waiver carries its own falsifier and says not to trust its own sentence.

**A flaky test was introduced and then closed in-session.** `L-2026-07-30-c` was filed
against `test_unreadable_file_fails_open` after it failed once in a full-suite run and
passed alone. Cause was mine: patching `builtins.open` globally with monkeypatch also
breaks pytest's assertion rewriting, capture and traceback machinery, so whether it failed
depended on collection order. Both affected tests now patch the name in `panel`'s module
namespace instead. Lesson closed with the evidence.

## Changed files in this repo

```
tools/review/panel.py                  sql-concat lookaheads; drop_stale_lines; called from added_lines
tests/test_panel_sql_concat.py         NEW, 13 cases, verbatim false positives from the 2026-07-30 tree
tests/test_panel_stale_lines.py        NEW, 7 cases, module-scoped patching only
quality-contract.json                  review waiver replaced, 2026-08-12 -> 2026-08-02
state/claims.jsonl                     one claim row, before starting
state/lessons.jsonl                    L-2026-07-30-c closed; L-2026-07-31-a/b/c appended
docs/CODEBASE-MAP.md                   regenerated (see risk 3)
docs/reflections/2026-07-30-thesis-and-deck-review.md   NEW
docs/HANDOFF-2026-07-31-review-oracle-repair.md         NEW, this file
```

## Lessons filed

- **L-2026-07-31-a**, a waiver renewed twice on a stated reason nobody ever executed. The
  waiver shipped a falsifier (an AST walk of the final file) which passed, and it passed
  for a different reason than the one written beside it, which launders a wrong diagnosis
  into an audited one. Rule: a waiver's reason must name the mechanism, and its falsifier
  must be able to distinguish that mechanism from every other reason the command could pass.
- **L-2026-07-31-b**, the gate checks the ruled form of a style rule and not the property
  it protects. `slop_lint.py` passes prose that reads as machine-written because it gates
  banned phrases and connector dashes, not hyphen density or sentence-length variance.
  `voice-metrics/SKILL.md:21` already calls "no em dashes" RULED. Same shape as
  L-2026-07-29-g.
- **L-2026-07-31-c**, a reviewer's own numbers went unchecked until an independent
  recount, and four of about fifteen were wrong, including a decimal-to-hex slip that
  weakened the argument it was supporting. Rendering the artifact in a browser then
  overturned three more findings that had been derived from CSS text.

## Remaining risks

1. **The review domain is still WAIVED, by design.** It goes PASS only against a
   committed tree. Clearing it means committing, and 130-plus changed files here belong
   to other sessions.
2. **`drop_stale_lines` changes what the panel reports across the board**, not only the
   five findings it was written for. Reviewed lines went 75,932 to 74,672 and medium
   findings 27 to 20. Every dropped line is one the tree does not contain at the claimed
   position, which is the intent, but nobody has audited the 1,260 individually.
3. **Another session was writing to this repo concurrently.**
   `docs/prior-art/tools-reclaim.json` appeared at 18:33 and turned `codemap` red
   mid-session. Regenerating with `codemap.py write` swept that file into the map, so this
   session's map regeneration includes another session's work.
4. **`slop_lint` still cannot see the property that matters** (L-2026-07-31-b). Until it
   can, a clean `slop_lint` is not evidence that prose does not read as generated, and
   nothing in this session's reporting should be read as claiming otherwise.

## Exact next action

`python tools/gate/gate.py status` should report a green run for the current tree. Then
either commit this branch so `review` can go PASS on its own artifact and the waiver can
be deleted rather than renewed, or leave it and let the 2026-08-02 expiry force the issue.

The follow-up worth picking up next is L-2026-07-31-b: port a hyphen-density and
sentence-variance check from `~/.claude/skills/voice-metrics/voice_score.py` into
`tools/slop_lint.py`, with thresholds fitted against the operator's corpus rather than
guessed. It is filed in TODO.md.

## What did NOT happen, and is not claimed

No commit, no push, no PR. No change to `panel.py`'s line-versus-tree architecture beyond
the filter. No touch of either `intent-control-plane` copy. No change to any other check's
pattern. The thesis and deck deliverables were not moved into this repo and should not be:
they are a third party's work product and live in `~/Downloads`.
