# Session handoff, 2026-07-27

Lane: **B (harness)**, by the opening prompt, which was about the terminal spawn,
the rc, and settings. The cwd said C the whole time because the desktop shortcut
pinned it. That is now fixed; see "how to start next time".

Everything below names the command that produced it. Anything unverified is
marked as such.

---

## How to start next time (this changed)

The old `Claude new-recruit (Admin).lnk` ran
`wt -d "C:\Users\shova\Downloads\new-recruit" pwsh -NoExit -Command claude`, so
**every** session reported lane C regardless of the work. It also never ran
elevated despite the name.

Five new Desktop shortcuts, each declaring `CLAUDE_LANE` instead of implying it:

    Claude A - concierge        ~/claude-setup
    Claude B - harness          ~/claude-setup
    Claude C - resume engine    ~/Downloads/new-recruit
    Claude D - learning         ~/Downloads/daily-deep-learning
    Claude - choose workspace   interactive: global lane / existing repo / new repo

`session-recall.sh` now reads `CLAUDE_LANE` and opens with the charter. Unset
means it prints **LANE: UNDECLARED** rather than guessing.

The old shortcut is untouched. Delete it when the new ones are habit.

---

## Landed and verified

**GitHub, 9 repos changed**

| repo | change | evidence |
|---|---|---|
| admaven, altius, ML_Study_Guidebook, Bank-Change, CS_188, time-twist, Manage-Warehouse | public to private | `gh api ... --jq .visibility` on each |
| CS_188, Manage-Warehouse | needed unarchive first | archived repos are read-only; 403 on first attempt |
| agenteval-bench, protobuf-fuzz-guard | MIT LICENSE added | API `.license.spdx_id` now MIT on both |
| JSQ-SLQ | fake `build-passing` badge removed, real MIT added | badge was a hardcoded shields.io image; only workflow has 0 runs |
| next.py-solution-campusil | `nextjs` topic removed | repo is one 6.6 KB Python file |
| Power_Transform | README repaired | `Copy code` 3 to 0, `yourusername` 1 to 0, fences 1 to 4 |
| pull-request-podcast, crowd-transcribe | public to private | `ahead_by=0` vs both parents; you authored nothing in either |
| matchiq | **PR #6 opened, NOT fast-forwarded** | branches diverged 57/5; a force-move would have dropped CODEOWNERS |
| oren-roast-hq | tracked `.env` deleted at HEAD, archived | still in 6 commits of history |
| claude-memes-skills | **shipped**: public, 6 topics, description, v1.3.1 tagged | version drift 1.1.0 vs 1.3.1 fixed before tagging |

Public repos: 27 to 18.

**Harness**

- `skill-usage-log.sh` written, tested with positive and negative controls,
  **registered** as PostToolUse matcher=Skill. Writes `state/skill-use.jsonl`.
- `permissions.allow` added, 20 entries. Verified 0 overlap with the 53 deny
  rules; all 5 destructive guards and 28 secret-path rules intact.
- `session-recall.sh`: was hardcoded to one project's memory tree, so every
  session in every project read the home tree. Fixed, verified across 3 projects.
- `panel.py`: judge isolation added (`judge_blind`), plus `screen_for_send`,
  `validate_findings`, `build_note` extracted from `run_external` so the guards
  are testable at all.
- `codemap.py`: **had no selftest verb**; one written, 12 assertions. Dead
  `git(args, cwd)` helper with `shell=True` and zero callers deleted.
- `gate.py`: 8 new assertions on `expired()`. Malformed dates now fail CLOSED.
- **`mutate.py`: 5 specs to 8.** Full run: every mutation in 8 specs applied,
  every one caught, 0 survived.
- `telemetry.jsonl` **created**. A Thompson bandit (`policy.py`, 244 tests,
  marked done as A16 in the platform PRD) had never received a single row.
  Seeded with 10 honestly-graded observations from this session.

**Corpus**

- `~/.claude/corpus-operator-inputs/`: 587 real prompts, FTS5 index, 537
  deduplicated standing rules.
- Repo root 137 to 43 entries, 1.0 GB moved to `~/wa-export-archive/`.

---

## Blocked on you

1. **Rotate the 13 credentials in `oren-roast-hq`**, starting with
   `SUPABASE_SERVICE_ROLE_KEY`. The file is deleted at HEAD and the repo is
   private and archived. **The values are still in 6 commits of history.**
   Force-push is in your own deny list, and would not help anyway: GitHub keeps
   unreferenced objects reachable by SHA. Rotation is the only fix.
2. **Merge matchiq PR #6 before archiving that repo.** Archive first and the
   9-byte README is frozen over a 40-test pipeline, and archived repos are
   read-only.
3. **Decide on the 16 repos** whose only 2026 commits are the 2026-07-23 sweep
   (identical `ci: update Claude always-fresh PR review workflow` at 02:02 and
   02:27 across unrelated repos). Genuinely active: `daily-deep-learning` (62
   commits / 5 days), `claude-setup` (28/4), `ShovalBenjer` (17/10).
4. **`argmax_solution`** is public with an unverified `if: always()` fake-green
   CI claim. Never checked.

---

## Corrections made this session, so they are not relearned

- **"Build vector retrieval, not keyword" was wrong.** BM25-FTS over verbatim is
  0.745 MRR vs 0.645 for vectors. BM25 degrades on *distilled* text only.
- **"Package the harness as a Claude Code plugin" was wrong.** That is host
  lock-in. The CLI contract is already host-agnostic.
- **"97% of your transcript was compaction summaries" was wrong.** 3.3% of bytes,
  28.5% of the token budget.
- **The compaction-churn env-var theory was wrong.** Neither var is set anywhere.
  The cause was window size: 148 of 152 compactions fell in the two days the
  window resolved to ~127k instead of ~674k.
- **"Nobody measures whether compaction preserves task success" was wrong.**
  Slipstream, CompactionRL, ACON, ContextForge all do.
- **`claude-memes` is a fourth entrant, not a first.** `claude-notifications-go`,
  `bells-and-whistles`, `claude-code-notification`, and a marketplace
  sound-notifications plugin all exist. `ratatui-image` already does the
  multi-protocol terminal rendering including capability detection. The surviving
  differentiator is inline-in-terminal, which works over SSH and in cloud
  sessions where a desktop notification goes nowhere.

---

## Open, mine, unblocked

- Fold `docs/prd/2026-07-27-full-setup-architecture.md` into the **active**
  `docs/prd/2026-07-10-platform-standard.md`, which says in its own text
  "do not spawn dated notes". Writing that dated note was a violation.
- `prior_art` gate domain FAILs: 8 directories with substantial Python and no
  record (`tools/audit` 1417 lines, `tools/bus` 857, `dot-claude/hooks` 791,
  `tools/dolt` 787, `tools/snapshot` 826, `tools/skilleval` 578,
  `tools/openrouter` 461, `tools/map` 432).
- `sql-concat` fires on prose in `docs/prior-art/*.json`. Narrowing it is an
  oracle edit and needs your approval every time.
- `claude-setup` has 21+ unpushed commits. `review` cannot go green until they
  land, and `ship-gate.yml` is absent from the remote.

---

## Gate state at close

`new-recruit`: **PASS** (build, security, docs, review; unit/types/pipeline
waived, pre-existing, expiring 2026-08-01, none created by me).

`claude-setup`: **FAIL** on `review` and `prior_art`. `codemap` went FAIL to PASS.
Zero findings against any file changed this session. Two of the four high
findings are false positives of the prose-matching kind.

## Not verified

The `claude-memes` v1.3.1 release build had not finished. No repo was re-read
while writing this. `Natural_Language_Proccessing` reproducibility, `Catering`'s
full README, and whether archived repos can be deleted directly are all unknown.
