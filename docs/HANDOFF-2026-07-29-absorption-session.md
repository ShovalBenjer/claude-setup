# Session handoff, 2026-07-29 evening, lane B

Branch `chore/delete-dolt`, three commits, **nothing pushed**. Started from the
operator asking, after 173 sessions in one day, what he and I are each doing wrong.
Ended with the first deletion and the first third-party tool this repo has taken.

## Goal and whether it was met

Goal: diagnose why measured-good research never became working system, and act
rather than write about acting.

Met for the diagnosis and for four concrete actions. Not met for the largest item,
the 806-link corpus, which is briefed but not processed.

## The diagnosis, in one sentence

Every loop in this harness terminates in a written artifact and none terminates in
a deletion or a dependency, so the cheapest path through twelve strong gates is to
write another document. Full version with all arithmetic:
`docs/reflections/2026-07-29-what-is-going-wrong.md`.

## What shipped, with the check that proves it

1. **`e904a05` deleted `tools/dolt`**, 787 lines, the first net-negative refactor in
   51 commits. Evidence it was dead: zero static callers; 103 dolthub rows in
   `state/api-usage.jsonl` all on 2026-07-25 against a public sample db, none since;
   absent from every CI workflow; and its own analysis said "wire it or delete it"
   four days earlier. Verified after: `codemap.py check` clean at 365 dirs,
   `codemap.py prior-art` 26 components all unexpired, 179 tests pass.
2. **`41f5a4c` closed two open branches.** `docs/analysis/2026-07-29-albert-prior-art-verdict.md`
   resolves the albert question: PolyForm Noncommercial 1.0.0, not OSI-approved,
   commercial use prohibited, so the code is unadoptable while the repo stays
   binding prior art. Also not an ancestor, created 2026-07-23. And
   `work-docs/2026-06-09-CONSOLIDATED-adopt-backlog.md` got a measured status header
   instead of ambiguity: 12 of 26 rows checkable, one landed, one void, the rest
   open or expired.
3. **`ed87ed0` filed the ABSORB backlog**, eight rows, none replacing an existing
   ticket. Root cause is ABSORB-01: the prior-art schema's 14 fields include no
   field naming what was absorbed, so absorption is unrepresentable and therefore
   never checked. ABSORB-04 is DONE, the coherence-governor page recommended on
   07-24 and never fetched is now at `docs/analysis/reference/`.
4. **vulture adopted** via `uvx`, zero install footprint. 0 findings at >=80%
   confidence, 70 at >=60%, of which 57 are in `intent-control-plane/src/`.

## Decisions taken, with grounds

- Deleting `tools/dolt` is correct even under the operator's "0 features neglected"
  rule, because three of Dolt's five features were genuinely absorbed on 2026-07-25
  into git-tracked append-only JSONL. The unabsorbed fifth is now ABSORB-02 rather
  than silently gone. Absorb-then-delete, never delete-then-forget.
- Historical documents are not rewritten to satisfy rules written after them. The
  22 slop-lint hits in the June backlog are its original 2026-06-09 body and stay.
- The concurrent session's in-flight `TODO.md` edits were committed rather than left
  beside an active writer, because there is one physical working tree.

## Corrections issued this session

- I did not substitute OpenRouter for DoltHub. `e904a05` changed one help-string
  example in `tools/lib/envload.py` where the `find` subcommand demonstrates
  substring search over `.env` key NAMES. No capability was swapped.
- "No external tools" is false as stated. Transcripts show 1,296 `gh`, 347 `codex`,
  45 `gemini` invocations. They are being called and changing nothing, which is a
  different and worse problem.
- `state/gate-runs.jsonl` has 1,648 rows of which 748 are selftest scratch projects,
  and 989 of 998 commits in it are absent from this repo. Real runs against
  claude-setup: 59. The dependency audit cites 993 as an asset.

## Verified: zero tasks lost

`main` had 55 task rows, the branch has 94. Four rows from `main` are absent by
exact text; all four have successors written by the concurrent session before this
one touched the file (COMPACTION CHURN closed, DECIDE re-measured to 7 hook events,
AUTO-05 closed on Lane A retirement, model default superseded). None was removed
by this session.

## Open risks, ranked

1. **Concurrent writers, and it fired during this session's own verification.**
   The suite went 173 to 179 between two runs 20 minutes apart; the delta is
   `tests/test_selfimprove_scan.py`, written by another session at 19:54 mid-suite.
   This deletion removed no test. ABSORB-03 (worktree isolation per producer) is the
   structural fix and is now ticketed.
2. Nothing is pushed. Three commits and the whole diagnosis exist only on this SSD,
   which is precisely the single-point-of-failure the 07-29 dependency audit named.
3. `panel.py` third waiver, expires 2026-08-12, still needs an operator decision.
4. The 70 vulture findings are untriaged. Some fraction are CLI-dispatch false
   positives and the ratio is unknown.
5. ABSORB-06 stands: the true absorption rate across the ~70 alternatives inside the
   prior-art records is unknown, not zero, because no field exists to check.

## Exact next actions

1. Run `docs/2026-07-29-external-absorption-brief.md` in Claude Desktop with
   `C:\Users\shova\wa-export-archive\self-chat-links-2026-07-29.csv` attached. This
   is the largest unabsorbed pile: 806 unique URLs, 80 GitHub repos, briefed and
   ready. File the returned table against `TODO.md` section ABSORB.
2. Decide the push. `git push -u origin chore/delete-dolt` then a PR per ADR-0012,
   which is the operator's call because it is outward-facing.
3. ABSORB-01, the schema change, because every other absorption row is unverifiable
   until a record can state what it absorbed.
4. Whole-module connectivity analysis, which vulture does not do. Vulture finds
   unused symbols; the operator's observation was about modules that cannot be
   connected at all, and 57 of 70 findings clustering in one package suggests it is
   real.

## What this session did not do

Did not push. Did not process the link corpus. Did not triage the vulture findings.
Did not run the full gate on the final tree, so the branch carries three commits
whose composite tree has never been gated.
