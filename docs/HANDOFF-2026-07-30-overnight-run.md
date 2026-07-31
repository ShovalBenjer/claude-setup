# Handoff: overnight autonomous run, 2026-07-30

Running against `docs/prd/2026-07-30-consolidation-and-migration.md`. This file is updated as
phases land, so read the bottom for the current position.

## Read first: one alarm to disregard, and it was raised five times

An agent reported `C:\Users\shova\.git` as deleted with 6 commits unrecoverable, and repeated it
in every subsequent message. **It is a false alarm.** That repo was dissolved deliberately, at
operator instruction, and it was MOVED rather than deleted:

- `C:\ARCHIVE-2026-07-30\home-repo-history\dot-git-moved-2026-07-30`, **194 MB**
- All 6 commits readable: `git --git-dir=<that path> log --oneline` returns b9669d6 through 1f85721
- **4,287 file versions** extracted before the move, covering every version of every path across
  all 6 commits, not just HEAD

The agent was scoped away from `C:\ARCHIVE-2026-07-30\` so it could not see where the repo went.
No undelete or VSS attempt is needed. This is a good demonstration of why the manifest row is
written before the action: the record existed before the agent started worrying.

## Landed, gated PASS

### Phase C1: the four ledgers with no history

`resource-ledger.jsonl` (1,773,987 B, 3,862 rows), `prompt-tickets.jsonl`, `skill-use.jsonl`,
`reclaim-manifest.jsonl` were **untracked AND matched no ignore rule**: zero commits all-time.
Now tracked. **1,829,904 bytes and 4,007 rows** moved from no-history to full-history, which is
54.6% of all ledger bytes.

Two of them are hash-chained, and `bus.py verify` states in its own output that truncation of the
newest rows is uncovered because "nothing outside this file records where the tip should be." A
commit is exactly that external witness. Somebody invested in tamper evidence for files that had
none; one command supplied it.

This corrects ABSORB-02, whose premise is false twice over: it names the 63 KB gitignored pile as
the gap while missing this 1.83 MB one, and it claims `ledger.sqlite` has "zero history" when 14
dated backups reconstruct its 2026-07-25 state.

### `.gitattributes`, added on a narrower ground than the one that prompted it

`git add` warned that LF would become CRLF on two hash-chained ledgers. I claimed that would break
the chain. **I was wrong and I tested it rather than leaving the claim standing**: `bus.py verify`
against the eol-normalised index copy in an isolated tree reports "chain intact across every
chained row", identical to disk. The chain hashes parsed JSON, so line endings cannot reach it. My
contrary result came from a hash formula I guessed.

The file went in for two real reasons instead, both about the Linux migration: a mixed-platform
checkout makes every ledger append look like a whole-file rewrite, destroying the one-line-diff
property that is the whole of what this repo absorbed from Dolt; and a CRLF shebang on a hook
script fails under WSL with a "bad interpreter" error naming an interpreter that exists.

### Phase A2: living-codex-build salvaged, tree now safe to delete

4 files, 42,266 bytes, at `docs/prior-art/living-codex-salvage/` with a README explaining why each
could not be regenerated. The one that mattered was not the code:

**`.openai/hosting.json` holds `project_id: appgprj_6a52f49b099081918bb4674279566794`.** A search
of `claude-setup`, `daily-deep-learning` and `oren-roast-hq` found zero other hits. That was the
only local record able to claim a hosted OpenAI Sites project.

Also salvaged `app/LivingCodex.tsx`, because `CLAUDE-OS.md:168` cites the Living Codex design and
its five mastery dimensions are hardcoded there; deleting the tree would have left the spine
pointing at a design with no artifact.

Two beliefs corrected: the `PUT /api/state 202` lines in its dev log are the **failure** path
(`{saved:false, persistence:"device"}`), so state persistence never once worked; and
`app/chatgpt-auth.ts` is verbatim starter-template code the application never imported.

Every learning capability was superseded by the PWA, mostly by an order of magnitude: 3 trees with
4 hardcoded nodes against 42 nodes over 5 tiers with evidence-gated ranks; "spaced recall" as copy
against a real `[1,3,7,21,60]` ladder; three research entries all labelled `DEMO ENTRY`.

### Phase A3: oren-roast-hq rescue, and it needed two passes

49 files, 513,927 bytes at `C:\ARCHIVE-2026-07-30\rescue\oren-roast-hq\`.

**The first pass was insufficient and the reason is worth carrying forward.** `git stash show -p`
produces a diff, and a diff is worthless without its base. `git merge-base --is-ancestor c3f5365
origin/main` **fails**, and `rev-list origin/main..c3f5365` is 1, so the stash's base commit exists
on no remote and would have been deleted along with the repo. The patch would then have had
nothing to apply to.

Fixed three ways: 43 full file contents extracted at the stash commit, base-independent; the
14,303-byte `oren-local-only.bundle` carrying that commit, verified "is okay"; and the patch plus
its base sha recorded.

**A verification trap, recorded because the wrong number is the memorable one.** The first
reconstruction check reported **9 of 9 files mismatching**, which reads as a failed rescue. It was
the test: the scratch worktree checked out under `core.autocrlf` giving CRLF, while
`git show <rev>:<file>` returns the raw LF blob. Re-run with autocrlf disabled and CR stripped:
**9 of 9 match, 0 mismatch.** The rescue was always fine.

`git bundle` also refused a bare SHA, because it packages refs rather than revisions. Worked around
with a temporary tag, bundled, then deleted the tag; the repo's ref set is unchanged.

**Deliberately not touched:** `.claude/worktrees/button-rewire`, whose tree carries a **modified
`.env`**. Removing that worktree discards an uncommitted secret-bearing delta, so it stays LEAVE
until you confirm those values exist elsewhere. Deleting only its `node_modules` reclaims 541 MB
of the 543 MB with zero risk.

### Phase A4: ARCHIVE-OneDrive-Afeka rescued

12 files copied, **0 hash mismatches**, to `C:\ARCHIVE-2026-07-30\rescue\`.

Copied rather than moved on purpose: the source is 124,547 bytes so leaving it costs nothing, and a
half-completed move across a Hebrew path is a real failure mode. Deleting the shell stays a
separate decision.

The claim that this directory duplicates a Documents path is **refuted**: the blocker reports exist
nowhere else in the home tree, and its `Shoval Benjer.docx` differs from the Documents copy by MD5
(`e04ceaef...` vs `844cb4b2...`), so it is a distinct version.

**One count corrected:** the agent reported 11 blocker reports. There are **10**. All 10 copied,
none missing.

Their timestamps run 2026-07-15 22:18 to 2026-07-20 14:59, meaning a scheduled job kept appending
into the archive path for five days after the migration declared it archived.

## Still running

The study-guide agent: GLM 5.2, Kimi 4, DeepSeek V4 architectures plus the surrounding vocabulary,
with your 315 pre-existing uncommitted lines to be committed **separately and first**, then push.

## Next

Phase A5 (record `wa-export-archive` as rescued-in-place, naming the ~156 MB of 1,070 MB that is
genuinely disposable), then Phase B, the docmap generator. 309 documents exist and
`docs/INDEX.md` reaches 29 of them, which is 9%.

## Waiting on you, unchanged

1. Which `intent-control-plane` is authoritative. Blocks `ecosystem.db` and the repo migration.
2. Branch protection costs money. Private repos need GitHub Pro, and without it ADR-0012 stays
   prose on a repo whose 12-domain gate **has never run in CI**, because `ship-gate.yml` was never
   pushed and local `main` is 25 commits ahead.
3. The `.env` committed to `GMShooter/gms-target-coach`, an org you do not own.
4. Wiring Codex would reverse ADR-0007, which removed it.
5. Anything requiring a public repo.
