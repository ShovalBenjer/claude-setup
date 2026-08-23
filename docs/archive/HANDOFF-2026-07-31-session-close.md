# Handoff: WSL migration, review-oracle repair, and a duplicated launcher

Session c882fd81, 2026-07-30 into 2026-07-31, roughly 16:40 to 06:40. Lane A (harness).
Claims in `state/claims.jsonl`: `session-2026-07-30-sql-concat-precision`, filed before
starting.

A second session wrote this tree continuously throughout. Four gate runs went red from
its in-flight state, two board specs were written independently on the same night, and
four files were edited by both of us. Every collision is named in section 6, because
none of it was visible from inside either session.

---

## 1. Goal and what actually happened

The session started as a thesis review for a third party and became harness work when
the operator said "go on review". It ended as a WSL migration. The through line is that
each step exposed an instrument that could not answer the question asked of it.

## 2. The review oracle, fixed rather than waived

The `review` domain carried a waiver through three renewals. Its stated reason, that the
blocking findings were pattern matches against comments and docstrings, was wrong for all
five findings. Two real defects, neither of them comments:

- **`sql-concat` never required SQL.** It asked for a SQL verb and, later on the line, a
  concatenation. Three findings were English prose: `"Delete ~380 lines (... checks + their
  selftest)"` in two `docs/prior-art` records, and `print("  delete .env: " + ...)`. Fixed
  with two independent lookaheads requiring SQL STRUCTURE (`FROM`/`INTO`/`SET`) as well as
  dynamic assembly. Writing the test first exposed a second hole: the old pattern required
  the assembly marker AFTER the verb, so `f"SELECT * FROM t WHERE a = {x}"` never matched.
  That is the commonest Python injection shape and it was going unreported.
- **`added_lines` reported lines the tree no longer contains.** It unions three diffs and
  dedupes by `(path, lineno)`, so a line added early on a branch and deleted later still
  surfaces, against a line number now holding different text. Both `py-shell-true` findings
  were this: real `shell=True` code the branch added and removed on 2026-07-27, cited
  against `codemap.py:66`, which today is the comment recording that removal. The reviewer
  was blocking on a vulnerability the change under review fixes. `drop_stale_lines` now
  filters them, fail-open when a file is unreadable and drop-when-gone when it is absent,
  because those are different facts that both raise `OSError`.

Evidence: `tests/test_panel_sql_concat.py` 13 cases, `tests/test_panel_stale_lines.py`
7 cases, both red before and green after. `mutate.py --spec panel` 10 of 10 caught.
Panel went 5 high to 0 high.

A flaky test was introduced and closed in-session. `test_unreadable_file_fails_open`
patched `builtins.open` globally, which breaks pytest's own assertion rewriting depending
on collection order (L-2026-07-30-c). Both affected tests now patch the name in `panel`'s
module namespace. Three consecutive full-suite runs, 292 passed each.

## 3. WSL migration, current state

The migration was blocked on an uncommitted tree and is not any more; `8a4217b` landed
mid-session.

| what | state | evidence |
|---|---|---|
| distro | Ubuntu 2, user `shov`, home `/home/shov`, 950G free | `wsl --list --verbose` |
| repo | `/home/shov/claude-setup`, 53 MB, branch `chore/delete-dolt` at `8a4217b` | staged clone, `--no-hardlinks`, 2m15s |
| toolchain | 12 of 12 present after bootstrap | `make -f tools/wsl/Makefile doctor` |
| tests | run in Linux | `35 passed in 0.15s` |
| config | deployed and translated | `~/.claude` carries 7 hook events, `model: opus[1m]`, `outputStyle: shoval` |
| gh | authenticated, HTTPS | `gh auth status` |

`tools/wsl/` now holds `bootstrap.sh` (one sudo prompt, keepalive, idempotent),
`Makefile` (entry point, `doctor` costs no password), `deploy_config.py` (Windows to
Linux translation), `audit-shortcuts.ps1` and `clean-shortcuts.ps1`.

**Two hooks are deployed broken, on purpose, and flagged:**

- `Notification` calls `powershell.exe`. No Linux equivalent. Fails every time.
- `UserPromptSubmit` points at `intent-control-plane/.venv/bin/python`. Layout corrected
  from Windows `Scripts\python.exe`, but the venv does not exist in the Linux clone. Run
  `uv sync` there to revive it.

**`shovalbe` is not `shov`.** The 53 `skills_sync` drift items and the dead pointers
naming `/home/shovalbe/...` are the operator's OLD JOB (Azure, Figma), not a path to
restore. They are a deletion list, not a migration list. Do not symlink it back.

## 4. The launcher I duplicated

`tools/workspace/start-claude.sh` already existed, 184 lines, dated 2026-07-30. It runs
in WSL under kitty, carries the post-ADR-0016 letters, offers `1 global / 2 project /
3 new`, prefers ext4 with a VISIBLE fallback so the speed penalty is not mysterious, and
runs `gate.py init` on a new repo so a fresh project starts red rather than unmeasured.

I did not look for it and built three `wt.exe`-based shortcuts that bypass it. All three
are deleted, along with the script that made them, and the three pre-ADR-0016 shortcuts
from 07-27. The Desktop now carries one generation: five gen-2 shortcuts plus the admin
one. Recorded as a plan-deviation row.

**Open gap, inspected and NOT fixed:** `discover_projects` lists any directory with a
`.git` under four roots and has no notion of archived, so the menu offers eight projects
of which five are dead:

```
active    claude-setup 2026-07-31   daily-deep-learning 2026-07-31   new-recruit 2026-07-29
archived  search_by_ingredients 2025-07-05   deep_learning_neural_networks 2024-12-20
          Web_Scraping 2024-08-25   GMShoot (no commits)   moneyballz (no commits)
```

Proposed, unbuilt: recency filter first (self-maintaining), `.claude-archived` marker for
exceptions in both directions, a `9 show archived` escape hatch so nothing is unreachable,
and zero-commit repos shown as a separate category since they may be scaffolds never
started rather than work abandoned.

## 5. Zion

31 items, 7 custom fields created and populated (165 writes, 0 failures), 76.8 estimated
hours. Priority P0 3 / P1 11 / P2 13 / P3 4. Ingestion S1 through S6, sized so S1 fits a
25-minute gap.

**The board is PUBLIC** while the repo is private. Found by a subagent, verified twice via
REST and GraphQL. One thesis-related epic was pushed and deleted; the re-publish dry run
proves it cannot return.

I set `Lane` to the pre-ADR-0016 letters by trusting a stale SessionStart context over
ADR-0016, which `CLAUDE.md` explicitly warns about. The other session corrected it.

## 6. Concurrency, which is the finding under all the others

Two agents, one tree, no mutual visibility.

- `codemap` went red mid-run when the other session added `docs/prior-art/tools-reclaim.json`
- `unit` went red three times from `rules.rs` being regenerated during a test run
- both sessions wrote a GitHub-native board spec on the same day; mine was applied, its
  was UNEXECUTED and measured against a state I had already changed
- four files were edited by both of us: `publish_backlog.py`, `panel.py`,
  `test_ghpub_backlog.py`, `dir-purpose.txt`
- I restored a JSON from the git index to undo an edit and destroyed two epics of
  uncommitted work, recovered by parsing them back out of the published issue bodies
- four consecutive gate PASS verdicts landed on four different tree hashes

`state/claims.jsonl` is supposed to prevent this and did not, because a claim is a log and
not a lock.

## 7. Lessons and deviations filed

- `L-2026-07-30-c` CLOSED: the flaky test was mine and is fixed, with evidence
- `L-2026-07-31-a`: a waiver renewed twice on a stated reason nobody executed. Its
  falsifier PASSED, for a different reason than the one written beside it, which launders
  a wrong diagnosis into an audited one
- `L-2026-07-31-b`: the prose gate checks the ruled form, not the property. Zero em dashes
  but 2.8% hyphen compounds and sentence stdev 14.8. `voice-metrics/SKILL.md:21` already
  calls "no em dashes" RULED
- `L-2026-07-31-c`: a review's own numbers went unchecked until an independent recount
  found four wrong, including a decimal-to-hex slip that weakened the argument it supported
- `state/plan-deviations.jsonl` created, seeded with two rows: the mask-comments plan that
  would have disabled the oracle it was fixing, and the read-the-CSS plan that a four
  minute render overturned

## 8. Exact next action

1. `gh auth login` is done; nothing blocks Linux work now. Open **Claude A - harness** from
   the Desktop and confirm hooks fire there as they do on Windows.
2. Decide when the Windows copy freezes. Until then both trees drift and no cutover is safe.
3. The 107 ignored paths that no clone carries still have no at-risk list. That is the one
   piece that can actually lose data.
4. `review` stays waived until 2026-08-02 and clears by committing.

## 9. Not claimed

No push, no PR, no merge to main. `start-claude.sh` untouched. `tools/hookgate/` untouched.
No file moved or deleted in any repo except six Desktop shortcuts and one script of my own.
The thesis deliverables stay in `~/Downloads` and were deliberately not absorbed here.
