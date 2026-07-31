# PRD: Consolidation, document mapping, and the Linux migration

- Date: 2026-07-30
- Status: APPROVED for autonomous execution (operator, 2026-07-30, "loop until goal is reached")
- Owner: Lane A (harness). Cross-lane actions are called out per phase and need a claim row.
- Supersedes: nothing. Extends ADR-0010, ADR-0011, ADR-0016.
- Companion: `docs/specs/2026-07-30-data-architecture-and-orchestration.md` (the data design),
  published visualization at the artifact URL recorded in the session handoff.

## 0. Why this document exists, and what it is correcting

Four verification agents were run against this estate on 2026-07-30. Between them they
**refuted eleven claims that an earlier version of this plan rested on**, several of which
would have destroyed data. That is the reason this is a PRD and not a task list: the failure
mode here is not fumbling a command, it is acting on a belief that was true once.

The refutations, because they are the requirements:

| claim | refuted by | consequence for this plan |
|---|---|---|
| `oren-roast-hq` needs archiving | already archived 2026-07-27 | re-archiving is a no-op; the open item is credential rotation |
| `wa-export-archive` is mostly re-downloadable | only ~156 MB of 1,070 MB is | the rest is irreplaceable WhatsApp media; RESCUE, never delete |
| `ARCHIVE-OneDrive-Afeka` duplicates a Documents path | 11 reports exist nowhere else; the docx differs by hash | RESCUE before the shell goes |
| removing the `button-rewire` worktree loses nothing tracked | its tree carries a modified `.env` | downgraded to LEAVE |
| `living-codex-build` has 65 source files | 34 files, 32 tracked, 2,719,627 bytes | smaller, and still single-copy |
| `living-codex-build.tar.gz` is a source backup | it contains only `dist/` | the source exists in exactly one place |
| `ledger.csv` does not exist | it does, created 2026-07-30, the ABSORB-07 absorption ledger | 8 rows, 7 undecided |
| `ledger.sqlite` has zero history | 14 dated backups reconstruct 2026-07-25 state | ABSORB-02's premise is false |
| ABSORB-02 names the history gap | the gitignored pile is 63 KB; the untracked pile is 1.83 MB | the real gap is four never-committed ledgers |
| zero issues exist across the estate | 60 exist, 47 in `solosolve-ai` | publication cannot assume an empty tracker |
| `deep_learning_neural_networks` notebook diff is metadata churn | 8 cells against HEAD's 7, real content | it is uncommitted work that exists nowhere else |

Two further facts that reorder the phases:

- **`ship-gate.yml` has never been pushed.** The remote carries only `claude-code-review.yml`
  and `claude-nightly.yml`, and local `main` is 25 commits ahead. The 12-domain gate that
  `CLAUDE.md` treats as the enforcement spine **has never executed in CI on any PR.**
- **Zero of 39 repos have branch protection.** Public repos return 404; private repos return
  "Upgrade to GitHub Pro". ADR-0012 ("autonomy ships only via the PR gate") therefore has no
  mechanical enforcement anywhere, and cannot get any on the private side without spending
  money. That is an operator decision, priced below.

## 1. Goal

One sentence: **make the estate legible, get every irreplaceable thing backed up, and reach a
state where a Linux session is a real option rather than a downgrade.**

Success is three observable conditions:

1. Nothing load-bearing exists on exactly one disk.
2. Every document in the estate is reachable from one index, and every ticket has a target.
3. A WSL session has the same enforcement as a Windows session, proven by hook-fire evidence.

## 2. Non-goals, and the hard prohibitions

**`C:\Users\shova\Pictures` is out of scope entirely.** Operator instruction 2026-07-30, and
it overrides the earlier finding that 13.58 GiB of zips in it were verified redundant
entry-by-entry. That row is withdrawn. Do not measure it, move it, or propose it again.

Also prohibited for the duration:

- No force-push, no history rewriting, no branch deletion on any repo.
- No new PUBLIC repo. New remotes are private; the operator can flip them.
- `C:\Users\shova\Documents` is not touched. It holds the only copy of coursework and
  `אישי/PASSPORT_SHOVAL.pdf`.
- The `.env` committed to `GMShooter/gms-target-coach` is **not** rotated here. It is an org
  repo the operator does not own, and rotation is his call with that org.
- No deletion of anything not on a manifest row that re-verified its own invariants in the
  same run.
- Archive is the default verb. Delete requires `--allow-delete` on top of `--execute`.

## 3. Phase A. Rescue. Nothing else starts until this is done

Ordered by irreversibility, worst first. Every one of these exists on exactly one disk.

| # | what | bytes at risk | destination | acceptance |
|---|---|---|---|---|
| A1 | `deep_learning_neural_networks` uncommitted diff: 315 lines across `util.py`, `words.py`, plus a staged submodule deletion whose gitlink `63b368aaee74ec077abcc8f66f0c8fbd4c712a07` is the ONLY surviving pointer, because the repo has no `.gitmodules` | ~2 files + 1 unrecorded URL | commit to its branch and push; write the gitlink into a note file first | `git rev-list --count @{u}..HEAD` returns 0 after push, and the note file names the commit id |
| A2 | `living-codex-build` source, no remote, 1 commit, 32 tracked files | 2,719,627 | operator said no remote for it, so copy to `C:\ARCHIVE-2026-07-30\` AND wait for the validation agent's salvage list | the validation report exists and its salvage list is satisfied |
| A3 | `oren-roast-hq` `stash@{0}` (9 files, +186/-164) plus untracked `supabase/migrations/20260528000000_rule_activations.sql` (718 B) and `src/routes/whatsapp.tsx` (6,101 B) | ~46 KB | `git stash show -p > archive/oren-stash-0.patch` plus copy the two untracked files | the patch file exists and applies cleanly with `git apply --check` |
| A4 | `ARCHIVE-OneDrive-Afeka-2026-07-20`: 11 `hiring-loopcv-chrome-closed-blocker-*.md` reports that exist nowhere else, plus a `Shoval Benjer.docx` that differs from the Documents copy by hash | 124,547 | fold into `Documents\מדעי נתונים\קוח\` under a dated subfolder | all 11 reports resolvable at the new path; hashes match the originals |
| A5 | `wa-export-archive` personal media and chat exports | ~965 MB of 1,070 MB | leave in place, mark RESCUED-IN-PLACE, do not move 965 MB across a 9P boundary for no reason | a manifest row recording the decision and the 156 MB that IS disposable |
| A6 | `new-recruit` 35 commits, no remote; `solosolve-clustering` 20 commits, remote returns 404 | two histories | audit for credentials and PII, then push each to a NEW PRIVATE remote | `gh repo view` succeeds and `rev-list --count @{u}..HEAD` is 0 |

**A6 is the one that needs care.** `new-recruit` has never been pushed, so a first push
publishes all 35 commits at once. The audit is not optional: `HANDOFF-TO-LEARNING-2026-07-27`
records seven repos with live public damage including a tracked `.env` with a
`SUPABASE_SERVICE_ROLE_KEY` and a filename embedding a 9-digit national-ID-shaped number.
Audit every commit's tree, not just HEAD.

## 4. Phase B. Document mapping. The visibility problem, quantified

The operator named this as the opportunity, and it measures worse than it reads.

| class | count |
|---|---|
| `docs/adr/` | 16 |
| `docs/prd/` | 2 |
| `docs/specs/` | 12 |
| `docs/analysis/` | 25 |
| `docs/reflections/` | 3 |
| `docs/prior-art/` | 28 |
| `docs/HANDOFF-*` | 11 |
| `docs/` root | 21 |
| `work-docs/` | 191 |
| **total** | **309** |
| **referenced by `docs/INDEX.md`** | **29, or 9%** |

So 280 documents are reachable only by knowing they exist. Three "map" documents already
exist and each maps something different: `INDEX.md` (3,607 B, curated, 9% coverage),
`SYSTEM-MAP.md` (20,631 B), `CODEBASE-MAP.md` (75,557 B, generated, directories not
documents). None of them maps documents to their status.

### B1. Build `tools/docmap/docmap.py`, modelled on `codemap.py`

Not a hand-written index, because a hand-written index is what decayed to 9%. A generated one,
with the same contract `codemap.py` already enforces: generated file, hand edit reads as drift,
gate fails on an undocumented entry.

Per document it must record: path, class (adr/prd/spec/analysis/reflection/handoff/prior-art),
date from the filename or frontmatter, **status** (current / superseded-by / historical-record /
stale-flagged), what supersedes it, and whether anything links to it. Orphans and contradictions
are the output that matters, not the listing.

Acceptance: `python tools/docmap/docmap.py check` exits 0, `docs/DOCMAP.md` covers 309 of 309,
and the `docs` gate domain gains it. Plus a selftest and a mutation control, per the four-layer
rule.

### B2. Reconcile the contradictions the handoff agent found

These are already identified and must land as document edits, not as tickets:

- Every handoff dated 2026-07-29 or earlier uses the pre-ADR-0016 lane letters and is **right
  for its date**. `docmap` must record scheme-1 versus scheme-2 per document so a reader is not
  silently misled.
- `state/claims.jsonl`'s newest row is dated 2026-07-30 and says `lane: B` for harness work.
  Post-renumber that means the resume engine. The renumber was violated once, one row deep, on
  the day it landed. Append a correcting row; do not edit the existing one.
- `CLAUDE.md` says the root suite is "~47s, 70 tests". It is 179 tests. Also `CLAUDE.md` is
  **untracked**.
- `docs/analysis/2026-07-29-local-dependency-audit.md` cites "993 gate verdicts" as an asset.
  59 are real runs against this project; 748 of 1,648 rows are selftest scratch.

### B3. Ticket targets

Of 62 open tickets, **four name repos that do not exist in the estate** (`AUTO-15`,
`ABSORB-02`, the case-ledgers domain row, `AUTO-12/13/14`). Those cannot be filed anywhere until
Phase A6 gives `new-recruit` a remote. This dependency is why ticket publication is Phase E and
not Phase B.

## 5. Phase C. The substrate

Per the companion spec, whose scope narrows ADR-0011 and which is now approved by the same
instruction that approved this PRD.

### C1. The cheapest action in the whole plan, and the largest

`git add` the four ledgers that are untracked AND match no ignore rule:
`resource-ledger.jsonl` (1,773,987 B, 3,862 rows), `prompt-tickets.jsonl`, `skill-use.jsonl`,
`reclaim-manifest.jsonl`. Zero new code. Converts **1,829,284 bytes and 4,007 rows**, which is
54.6% of all ledger bytes, from no-history to full-history.

Two of them are hash-chained, and `bus.py verify` states in its own output that truncation of
the newest rows is uncovered because "nothing outside this file records where the tip should
be." A commit is exactly that external witness. Somebody invested in tamper evidence for files
with no tip witness; this supplies it for one command.

For each: either `git add` it, or add it to `.gitignore` **with a stated reason**. The current
state is not a decision, it is an omission, and this estate's whole discipline is that a
decision leaves a record.

### C2. `state/ecosystem.db`, with `gate-runs` as its first tenant

Not all 12 ledgers. `bus.jsonl` is structurally barred (hash chain), and six should stay files.
`gate-runs.jsonl` is the only ledger with real growth (473 rows/day, 229 KB/day) and a real
query shape (latest verdict per fingerprint per project), which `ship_gate_stop.py` performs by
scanning 1.1 MB on every turn.

Include the `materializations` table keyed by `(asset, fingerprint)` so `gate.py` can skip a
domain whose asset is already fresh. Today all 12 re-execute every run at 80 seconds even when
11 inputs did not change. **That is the measured win, and it is a query rather than a framework.**

Bitemporal columns (`valid_from`, `valid_to`, never UPDATE in place) rather than Dolt. Dolt is a
MySQL server for a 16,644-row estate whose oldest record is 8 days old, and DoltHub free hosts
public databases only while this data is resumes and ATS routing.

**BLOCKED PREREQUISITE:** `TODO.md` bootstraps this from the intent-control-plane schema, and
`intent-control-plane` exists **twice** (1,037 Python files under claude-setup, 616 under
`new-recruit/projects`, both touched since 2026-07-01). `HANDOFF-2026-07-30-session-close.md`
says nothing should be merged until the operator answers which is authoritative. Until then C2
proceeds by **reading** both schemas and building fresh, merging neither.

### C3. `ledger.sqlite` hygiene

Ten tables, **zero explicit indexes**, `journal_mode=delete` rather than WAL. Every history
query filters on `ts`, unindexed. Cheaper than any versioning work. Cross-lane: needs a claim
row.

## 6. Phase D. Reclamation, Pictures excluded

Withdrawn from the earlier plan: the 13.58 GiB of Pictures zips. Remaining verified rows:

| target | bytes | verb |
|---|---|---|
| `search_by_ingredients/.git/lfs/objects` (4 GGUF blobs, no ref-reachable commit holds an LFS pointer) | 8,977,908,320 | delete-artifact |
| `oren-roast-hq/.claude/worktrees/button-rewire/node_modules` | 486,989,749 | delete-artifact |
| `oren-roast-hq/node_modules` | 462,833,597 | delete-artifact |
| `living-codex-build` vendored subtrees (99.64% of the tree) | ~756 MiB | delete-artifact, AFTER A2 |
| `Web_Scraping` staged 3.56 GB mp4 blob, unreachable from every ref and reflog | 3,564,392,611 | unstage + gc |
| `new-recruit/work-archive-2026-07-12/` (all 17 entries hash-match the sibling zip) | 1,495,985,542 | delete-artifact, KEEP the zip |
| `pytorch_test` (50 of 33,373 files outside site-packages, all vendored) | 2,222,217,700 | delete-artifact |
| `Documents/ארכיון-zip/EBOOKS.zip` (28 of 28 entries match) | 100,130,719 | delete-artifact |
| two Chrome automation profiles, referenced by nothing | 378,949,210 | delete-artifact |
| `home node_modules` (resolves one dep: the abandoned `nodegh.io` CLI, not GitHub's gh) | 33,279,088 | delete-artifact |
| `SQL2025` (24 MSI products name it as LastUsedSource, patch pending reboot) | 1,165,495,889 | **archive**, not delete |
| `kafka` (2 of 233 files carry hand edits; configured, never run) | 127,076,309 | archive, keep the 2 configs browsable |
| gastown `config/` + `pipelines/` + `reports/` (2 of 8 cron jobs recorded only here) | ~1.5 MB | archive |
| 4 repos fully pushed and clean after a fresh fetch | ~113 MB | delete-local-pushed |
| `Launcher BlackWolf`, `Windows10Upgrade` | 2,148,387,272 | **vendor uninstaller**, never `rm` |
| 5 empty non-junction dirs, broken symlink, 3 stale temp files, `Library` | ~150 KB | delete-artifact |

`.tmp.driveupload` stays: two `GoogleDriveFS.exe` processes are live and the measuring `du`
itself raced a vanishing file. `scoop` stays: deleting it uninstalls `gh`, `supabase` and `7z`,
all three live on PATH.

Every row runs through `tools/reclaim/reclaim.py`, which re-verifies invariants immediately
before acting and writes the manifest row before the action, never after.

## 7. Phase E. GitHub

Ordered by the agent's finding that the enforcement spine has never run in CI.

1. **Push `ship-gate.yml`.** 25 unpushed commits mean the 12-domain gate has never executed on
   a PR. Everything else in this phase matters less.
2. **Branch protection decision, operator-only, costs money.** Private repos need GitHub Pro.
   Options: pay, make `claude-setup` public (it contains a WhatsApp LID and sensitive paths, so
   no), or accept the gate is advisory. Until answered, ADR-0012 stays prose.
3. **Publish tickets: 52 as-is, 6 rewritten, 4 dropped.** The 6 rewrites are non-negotiable:
   `P0` advertises a possibly-unrotated credential and its search signature; `voice-metrics`
   names a WhatsApp LID (PII by this repo's own policy); `ABSORB-07` embeds two absolute paths
   including one into a directory the repo marks SENSITIVE; `ABSORB-03` characterises a named
   third party's licensing and authorship; `ABSORB-05`/`P-DASH`/the CCC-study row are three
   copies of one competitive-framing item; the learning-card row names a private group.
   The 4 drops are status annotations and one self-refuting row whose own text argues that
   adding tickets is the wrong shape.
4. **Six milestones**, derived from the ids rather than invented: enforcement-layer-live,
   oracle-hygiene, calibration-and-measurement, absorption-schema (strict ordering, ABSORB-01
   blocks the rest), ecosystem-substrate (the only declared critical path), deployment-and-drift.
   No priority labels: the section headers already encode P0/P1/P2 and double-encoding is worse
   than none.
5. **Wire Gemini first.** Its secret has been present since 2026-07-24 and unused, and AI Studio
   has a free tier. Then Claude review is already on 22 repos, though whether it has ever run
   green is unverified. **The six-reviewer plan cannot be built as stated**: NVIDIA has no
   review Action, Kilocode is a GitHub App or a CLI step rather than an Action, and Codex and
   Qwen both need paid keys. Qwen stays parked: the on-disk `QWEN_API_KEY` is a 116-character
   non-key. Wiring Codex would reverse ADR-0007, which removed it, so that is an operator call.
6. **Project 3 (Zion, `PVT_kwHOBTKVvM4At4WJ`)** views, workflows and insights. Two other
   projects exist that were not in the brief: `solosolve-ai-project` and a phantom-limb one.

## 8. Phase F. Linux readiness. The answer to "should I reboot on Linux"

**No, not yet, and today it would be a downgrade to an ungoverned session.** Measured:

| | Windows `~/.claude` | WSL `~/.claude` |
|---|---|---|
| `settings.json` | 12 hook entries | **ABSENT** |
| `hooks/` | 29 files | **ABSENT** |
| `skills/` `commands/` `rules/` | populated | **ABSENT** |
| credentials | present | **ABSENT** |
| `CLAUDE.md` | present | **ABSENT** |

A Linux session today has no `safety_gate` (17 deny rules), no `completion_gate`, no
`ship_gate_stop`, no slash commands, no rules, and is not logged in.

What already exists on the Linux side: kitty 0.32.2 with a validated config, bun 1.3.14, claude
2.1.220, `hookgate` built and differentially verified, `~/work/` on ext4 with 952 GB free, and
`tools/workspace/start-claude.sh` which resolves ext4 first and falls back to `/mnt/c`.

### F1 to F5, in order, each with an acceptance test

- **F1. Decide the authoritative PreToolUse gate.** Three designs are on disk and the slowest is
  deployed: two Python hooks (242.5 ms), `pretooluse_gate.py` (117 ms, staged, unwired),
  `hookgate` (2.26 ms Linux, verified, unwired). Repointing hooks without deciding bakes the
  242 ms pair into the new config. Acceptance: one design named in `settings.json`, the others
  removed or explicitly marked as alternates.
- **F2. Deploy the harness into the distro.** `~/.claude` needs settings, hooks, skills,
  commands, rules. `skills_sync.py check` currently measures drift against the Windows copy
  only, so it needs a second target. Acceptance: `skills_sync.py check` reports both trees.
- **F3. Rebuild what cannot move.** `capture_turn.py` runs under a **Windows venv inside the
  repo being moved**, so intent capture dies silently unless rebuilt for Linux.
  `notify-toast.ps1` is Windows-only by nature and stays behind interop. Acceptance:
  `pointers.py scan` clean against the Linux tree.
- **F4. Migrate the repos to ext4** with copy, verify by `git fsck` plus a tracked-file hash
  comparison, then remove the original. Only after Phase A6 gives the no-remote ones a remote.
- **F5. Prove enforcement fires.** Acceptance is **`state/hook-fires.log` lines written by the
  harness after the move, per hook**, not a settings diff. This is lesson L011's own closing
  evidence: a repointed hook is STAGED until a fire log proves it ran.

### F6. This reverses a recorded decision and must say so

ADR-0006 recorded a **Windows-first purge** that retired WSL paths, and `TODO.md` still carries
"Purge WSL-era paths" as open. L018 measured 108 files whose entire content is a dead absolute
Linux path from a previous machine. Moving back to WSL can be correct now, because the reason
then was dead pointers and the reason now is a measured 110x, **but it must be reversed in a new
ADR with both dates**, or the next session finds two contradicting rules and no way to tell
which is current.

## 9. Phase G. Assigned side tasks

- **G1. Study guide.** Update with GLM 5.2, Kimi 4, DeepSeek V4 architectures, plus the
  surrounding vocabulary (MLA and KV compression, MoE routing, MTP, FP8/FP4, attention kernel
  lineage, RoPE scaling, RL post-training). Commit the operator's pre-existing 315 uncommitted
  lines separately and first. Push. Close the task. **Running.**
- **G2. `living-codex-build` validation** against the learning platform, then delete entirely.
  Salvage list required before deletion, because it has no remote and one commit. **Running.**

## 10. Sequencing and the stop conditions

```
A (rescue, all 6)  ──►  B (docmap)  ──►  C1 (git add ledgers)
                                    └──►  C2/C3  ──►  D (reclaim)
A6 ────────────────────────────────────────────────►  E (tickets need targets)
F1/F2/F3 ──► F4 ──► F5 ──► F6 (the ADR)
```

**Stop and wait for the operator on exactly these:**

1. Which `intent-control-plane` is authoritative. Blocks C2 and F4.
2. Branch protection: pay for Pro, or accept advisory. Blocks E2.
3. Rotating the `GMShooter` org `.env`.
4. Wiring Codex, which reverses ADR-0007.
5. Anything requiring a public repo.

Everything else proceeds. When a phase blocks, move to the next and record why rather than
stalling.

## 11. What would falsify this PRD

- If Phase A finds that any "single copy" item has a copy elsewhere, the rescue ordering was
  built on a bad inventory and the whole plan needs re-measuring, not patching.
- If `gate-runs.jsonl` is never actually queried by fingerprint in practice, C2's strongest
  case collapses and `ecosystem.db` weakens to "lessons and claims".
- If `hook-fires.log` shows no lines after F4, the migration is staged and not done, whatever
  the settings file says.
- If the docmap generator cannot classify a document's status without a human, then status is
  not a derivable property and B1 should be a curated index with an expiry date instead.
