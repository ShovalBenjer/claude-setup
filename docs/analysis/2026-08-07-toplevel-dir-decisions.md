# Top-level directory decisions, measured

Point-in-time scan. Measured at `HEAD=f88d3a3393c84d81288c92111923b63043478f41`,
branch `lane-a/waived-domains-are-not-unmeasured`, on a working tree with three
modified `state/*.jsonl` ledgers. **No fetch was performed**, so every git number
below is as-of this local ref and the second clone may already be ahead.

Date note, because `tools/docmap` derives lifecycle status from a filename date:
the measurements were taken on **2026-08-07** at the ref above, and the session
crossed midnight, so the file was finished on **2026-08-08**. The filename keeps
the measurement date, which is the one the numbers belong to.

Nothing here is accepted by this document. Per `accepting-architectures`, each row
is a separate block carrying its own counterargument, and an unanswered block stays
open rather than being implemented under an assumed answer. **Nothing was moved,
created, deleted or renamed for this report.** The only file written is this one.

`docs/CODEBASE-MAP.md` already answers *what each directory is*: 415 directories,
1835 tracked files, 0 without a stated purpose, gate-enforced by
`tools/map/codemap.py check`. What it does not carry is a decision per directory.
That is the gap this fills, for the 15 tracked top-level directories only.

## Method and its limits

Commands are named inline. Three measurement caveats that change how the numbers
read:

1. **`c30` does not separate live from dead in this repo.** Substantive history
   starts 2026-07-23 (`git log --format=%as | tail -1` gives 2026-05-09, but only
   two commits predate 2026-07-23). For 9 of 15 directories the 30-day count, the
   90-day count and the all-time count are the same number. The discriminating
   measurement is *commits ever* plus *what the last commit actually changed*, so
   both are reported. VERIFIED.
2. **A boundary-anchored grep was needed.** A plain `git grep -F "docs/"` also
   matches `work-docs/`, and `.claude/` also matches `dot-claude/`. All reference
   counts below use
   `git grep -lE "(^|[^-A-Za-z0-9_./])<dir>/" -- ':!<dir>/*'`. The `.claude` row is
   reported separately against its literal tracked path because even the anchored
   pattern excludes a preceding `/`, so `~/.claude/` prose does not count and the
   raw number would still be about the user-level tree, not the project-local one.
   VERIFIED.
3. **File counts drifted since the task packet was written.** Packet said
   `dot-claude 336/59` and `tests 32/30`; at this ref
   `git ls-files -- dot-claude | wc -l` gives 338 and 60, `tests` gives 33 and 31.
   `docs`, `tools`, `state`, `dot-agents` match the packet exactly. The packet's
   "25 sys.path.insert calls" measures 23 at this ref
   (`git grep -c 'sys.path.insert' -- 'tools/**/*.py' 'dot-claude/bin/*.py'`,
   summed). Small, and named rather than smoothed over. VERIFIED.

## Decision table

| dir | recommendation | one-line reason |
| --- | --- | --- |
| `.claude` | keep | Wired project-local path Claude Code reads; one artifact, but `dot-claude/bin/external-review-judge.py` writes it. |
| `.github` | keep | GitHub reads this exact path; 17 commits, last today. |
| `docs` | keep, split candidate | Most-committed docs tree (61) and 29 Python files reference it; `docs/analysis` at 39 files is the only sub-split worth a later block. |
| `dot-agents` | contested: merge into `dot-claude/skills`, blocked on 8 skills | No live `~/.agents` exists anywhere, but 8 live skills have their only repo copy here. |
| `dot-claude` | keep, canonical | Only repo tree with a live counterpart that exists (`~/.claude`, 79 skill dirs); 33 commits, last today. |
| `dot-codex` | contested: split, archive `dot-codex/skills`, keep the rest | 33 of 34 loose skill files are one-line pointers to a dead home; the live `.codex/skills` on the Windows side is empty. |
| `home-dotfiles` | archive | 2 commits ever, every live target absent on this machine, and 2 of its 9 files are byte-identical duplicates of 2 others. |
| `intent-control-plane` | contested, close call: keep separate | Only packaged, linted, typed Python and the dependency is one-way, but 4 commits ever and one of its consumers imports a path that does not exist. |
| `master-plans` | merge into `work-docs/root-cleanup-2026-05-28` | 6 of its 8 files are already byte-identical copies inside that directory, and its own purpose row says superseded. |
| `research-papers` | keep frozen | Already declared out of scope by two gate files as read-not-maintained evidence; last commit deleted 43 files. |
| `startup-scripts` | archive | 2 commits ever, content unchanged since the 2026-05-09 export, and no executable consumer references it. |
| `state` | keep | 55 commits, last today, 26 Python files read it; the append-only ledgers are the repo's ground truth. |
| `tests` | keep | 17 commits, last today, 15 Python files reference it; the purpose row understates it and needs correcting. |
| `tools` | keep | 56 commits, last today, 88 non-markdown external references; the working half of the repo. |
| `work-docs` | keep frozen, no new writes | Already the archive destination for `master-plans`; 4 commits, last one cosmetic. |

## The blocks

### `.claude` (1 file, 0 py)

- Commits ever: **1** (`git log --format='%as %h %s' -- .claude`), 2026-07-31
  `8a4217b`, which added the single tracked file
  `.claude/reviews/codex-first-live-review.json` (32 insertions,
  `git show --stat --format= 8a4217b -- .claude`). VERIFIED.
- External references to the literal tracked path
  (`git grep -l -F '.claude/reviews' -- ':!.claude/*'`): **4**, of which one is
  executable: `dot-claude/bin/external-review-judge.py`. The other three are
  `docs/CODEBASE-MAP.md`, `docs/dir-purpose.txt`, `docs/prior-art/dot-claude-bin.json`.
  VERIFIED.
- Payload or source: neither. It is a **live** location in this repo, read by
  Claude Code and by the `review` domain. It cannot be merged into `state/reviews`
  without changing what a judge writes to.
- **Recommendation: keep.**
- **Against it:** it holds one machine-written JSON, duplicates the role of
  `state/reviews` (which `tools/review/panel.py` owns), and its name is close
  enough to `dot-claude` that it produced a wrong reference count inside this very
  analysis before the pattern was fixed. A reader who cannot tell `.claude` from
  `dot-claude` at a glance is a real cost paid every session.

### `.github` (6 files, 0 py)

- Commits: **17** ever, 17 in 30 days, last 2026-08-07. VERIFIED.
- External references: 55, of which 19 non-markdown. The `pipeline` domain of
  `quality-contract.json` greps these workflow files for a literal `gate.py run`
  invocation, so the path is load-bearing for the gate itself. VERIFIED.
- Payload or source: **live**. GitHub Actions reads this exact path.
- **Recommendation: keep.**
- **Against it:** none found. This is the one row where the counterargument is
  genuinely absent, and saying so is more useful than manufacturing one.

### `docs` (195 files, 0 py, 143 md)

- Commits: **61** ever, all within 30 days, last 2026-08-07. Highest count of any
  directory except `tools` and `state`. VERIFIED.
- External references: **181**, of which 62 non-markdown and **29 from Python**
  (`git grep -lE "(^|[^-A-Za-z0-9_./])docs/" -- '*.py' ':!docs/*'`). The gate reads
  it: `quality-contract.json` names `docs/` 8 times. VERIFIED.
- Payload or source: **source**, and the spine. `docs-control-plane` fixes its
  taxonomy.
- **Recommendation: keep.** One split is worth a later block and not this one:
  `docs/analysis` is at 39 files and `docs/prior-art` at 42, both growing
  monotonically because nothing archives them.
- **Against it:** `docs/` now has 10 subdirectories and 143 markdown files against
  a repo of 1835 tracked files. `tools/docmap` exists precisely because nobody can
  tell which of them are live, which is evidence the tree already exceeds what its
  own index can carry.

### `dot-agents` (218 files, 13 py, 70 skill directories) CONTESTED

- Commits: **6** ever, last 2026-07-31 `24e01de`, which changed **5 files by 10
  lines total** (`git show --stat --format= 24e01de -- dot-agents`), a cosmetic
  sweep. The last commit that added content is 2026-07-25 or earlier. VERIFIED.
- External references: 23, of which 8 non-markdown and **1 from Python**. The
  non-markdown referencers are `quality-contract.json`, `tests/test_codemap.py`,
  `tools/audit/skills_sync.py`, `state/*.jsonl`, `.github/workflows/ship-gate.yml`.
  `skills_sync.py` reads it as a **sibling** tree in a preference order
  (`LIVE`, `dot-agents`, `dot-codex`), not as a deploy source. VERIFIED.
- Payload or source: **payload with no live target.** `~/.agents` is ABSENT on WSL
  and `/mnt/c/Users/shova/.agents` is ABSENT on Windows
  (`ls -d ~/.agents* /mnt/c/Users/shova/.agents`). VERIFIED.
- **But:** 8 skills that are live in `~/.claude/skills` have their only repo copy
  here: `domain-model github-triage improve-codebase-architecture
  request-refactor-plan to-issues to-prd ubiquitous-language write-a-skill`
  (`comm -23 <live names> <dot-claude names>` then checked against `dot-agents`).
  Hashing each live directory against its `dot-agents` copy (sha1 over sorted
  per-file sha1) gives **4 IDENTICAL** (`domain-model`,
  `improve-codebase-architecture`, `ubiquitous-language`, `write-a-skill`) and
  **4 DIVERGED** (`github-triage`, `request-refactor-plan`, `to-issues`, `to-prd`).
  VERIFIED.
- The mechanism by which those 8 reached the live tree is **unmeasured**.
  `dot-claude/bin/sync-skills.sh` unions `$HOME/.claude/skills` with
  `$HOME/.codex/skills` only; it never reads `dot-agents`
  (`grep -nE "dot-agents|skills" dot-claude/bin/sync-skills.sh`). No script in the
  repo copies `dot-agents` anywhere. ASSUMED: they were installed by hand.
- **Recommendation: merge into `dot-claude/skills`, blocked on those 8.** One
  canonical repo tree, and `dot-claude` is the only candidate because it is the
  only one whose live counterpart exists. The merge cannot start until the 8
  live-only names are promoted, and 4 of them require choosing between the repo
  body and the live body first.
- **Against it:** the merge is not a move, it is 21 content decisions.
  `dot-claude/skills` and `dot-agents/skills` share 31 names, of which **10 are
  byte-identical and 21 DIVERGED**. Add 38 names that exist only in `dot-agents`.
  Picking by timestamp is not a decision (TODO row B says so explicitly) and
  destroys whatever the divergence was for. A directory nobody is confused by
  today costs nothing; a half-finished merge costs every session after it.

### `dot-claude` (338 files, 60 py, 75 skill directories)

- Commits: **34** ever, 33 in 30 days, last 2026-08-07. VERIFIED.
- External references: 97, of which 50 non-markdown and 17 from Python. VERIFIED.
- Payload or source: **payload, with a live target that exists.** `~/.claude`
  holds 37 top-level entries and 79 skill directories
  (`ls -1d ~/.claude/skills/*/ | wc -l`). VERIFIED.
- Deploy drift, measured: of the 71 names present in both `dot-claude/skills` and
  live, **44 are byte-identical and 27 DIVERGED**. 4 repo skills are not live
  (`jira-read`, `jira-task-draft`, `prod-deploy-rules`, `writing-great-skills`).
  **0 live skills are missing from the union of the three repo trees**, so live is
  still a clean subset of the repo and the redundancy is entirely upstream.
  VERIFIED.
- **Recommendation: keep, and treat as canonical.** Canonical by evidence, not by
  preference: it is the only tree whose live counterpart exists on this machine.
- **Against it:** 27 of 71 shared names already differ from the tree they are
  supposed to be a committed copy of. A canonical tree that disagrees with the
  running one in 38 percent of shared cases is a claim about intent, not a
  measurement of authority, and the direction of each of the 27 is not established
  here.

### `dot-codex` (333 files, 12 py) CONTESTED

- Commits: **4** ever, last 2026-07-31 `24e01de`, which touched **42 files by
  exactly 1 line each** (`git show --stat --format= 24e01de -- dot-codex`), a
  punctuation sweep. The last content commit is 2026-07-25 or earlier. VERIFIED.
- External references: 33, of which 14 non-markdown and **0 from Python**.
  VERIFIED.
- Structure, measured rather than inherited from the purpose rows:
  `dot-codex/skills` holds **28 real skill directories and 34 loose files** at its
  root (`git ls-files -- dot-codex/skills | awk -F/ 'NF>3'` vs `NF==3`), against
  75 and 0 for `dot-claude/skills` and 70 and 0 for `dot-agents/skills`.
  **33 of those 34 loose files are one-line pointers into `/home/shovalbe/`**, a
  home directory that does not exist on this machine (this repo's user is `shov`).
  Example: `dot-codex/skills/dispatch` is 38 bytes and reads
  `/home/shovalbe/.claude/skills/dispatch`. The 34th is
  `heidegger-reflection.md`, a real 4069-byte document. VERIFIED.
- Payload or source: **payload whose live target is empty.** `~/.codex` is ABSENT
  on WSL. `/mnt/c/Users/shova/.codex` EXISTS and is live (`logs_2.sqlite` written
  2026-08-04, `config.toml` 2026-08-02), and it **has a `skills` directory that is
  empty**, last modified 2026-07-20 (`ls -la /mnt/c/Users/shova/.codex`,
  `ls /mnt/c/Users/shova/.codex/skills`). The `codex` binary resolves to
  `/mnt/c/Users/shova/AppData/Roaming/npm/codex`, so the runner is a Windows
  install. VERIFIED.
- **Recommendation: split.** Archive `dot-codex/skills` (33 dead pointers plus 28
  directories deploying to an empty target). Keep `dot-codex/rules`,
  `dot-codex/automations`, `dot-codex/bin`, `dot-codex/hooks`, which are the parts
  with a live analogue on the Windows side.
- **Against it, and it is strong:** the Codex host is demonstrably live to
  2026-08-04. An empty live `skills/` is equally consistent with "the deploy was
  never run" as with "the payload is dead", and the second reading is the one that
  would destroy work. Of the 53 names shared with `dot-claude/skills`, **21 have a
  real body on the codex side** and 10 of those 21 DIVERGE from the `dot-claude`
  version, so archiving takes out the only copy of 10 differing bodies.
- Execution cost if taken: archiving cannot create a directory without a
  `docs/dir-purpose.txt` row and a `codemap.py write`, because
  `codemap.py check` fails on an undocumented tracked directory. The precedent
  destination is `state/retired-<date>/`, following `state/retired-2026-07-25`.
  Both the row and the regeneration are out of scope for this report.

### `home-dotfiles` (9 files, 0 py)

- Commits: **2** ever. 2026-05-09 `910dec2` (initial export) and 2026-07-24
  `8d2277b`, which added `AGENTS.md`, `RTK.md`, `TESTING-SOTA-2026-GAPS.md`
  (110 insertions). Nothing since. VERIFIED.
- External references: 12, of which 5 non-markdown, and **all 5 are bookkeeping**:
  `CODEOWNERS`, `docs/doc-status.txt`, and three `state/*.json` backlog or backup
  files. **0 from Python.** No executable consumer. VERIFIED.
- Payload or source: **payload with every target absent.** `~/.mcp.json` ABSENT,
  `~/.claudeignore` ABSENT, `crontab -l` returns `no crontab for shov`. VERIFIED.
- Internal duplication: 4 of its 9 files are 2 duplicate pairs.
  `.crontab.bak-2026-05-03` is byte-identical to `dot-crontab-bak-2026-05-03`, and
  the same for the `-2026-05-04-pre-path` pair (`git ls-files -s` grouped by blob
  sha). VERIFIED.
- **Recommendation: archive.** The 3 markdown files added 2026-07-24 are content
  and should move to `docs/` first if they are still wanted; the 6 dotfile
  backups have no target.
- **Against it:** those 3 markdown files are the newest thing here and were added
  deliberately, so the tree is not uniformly dead. And the two crontab backups are
  the only surviving record of the pre-WSL schedule, which is exactly the class of
  artifact a harness repo exists to remember. Nine files cost nothing to keep.

### `intent-control-plane` (116 files, 90 py, 20 md) CONTESTED

- Commits: **4** ever, last 2026-07-31 `24e01de` (the punctuation sweep). The last
  functional commit is 2026-07-25 `90780b5`, the sqlite handle fix. VERIFIED.
- External references: 31, of which 11 non-markdown and 2 from Python by path.
  VERIFIED.
- Import edges, measured in both directions:
  - **Forward, tools into the package: 6 files.** `dot-claude/bin/gastown-spawn.py`,
    `dot-claude/bin/jira-time-stop.py`, `dot-claude/bin/self-improve.py`,
    `tools/bus/backfill_session_telemetry.py`, `tools/intent/capture_turn.py`,
    `tools/intent/tickets.py` (the last only in a comment saying it deliberately
    does not import). VERIFIED.
  - **Reverse, package into tools: 0 files.**
    `git grep -nE "(^|[^A-Za-z_])(from|import) +tools[. ]|sys\.path.*tools" --
    'intent-control-plane/**/*.py'` returns nothing. The dependency is one-way and
    acyclic. VERIFIED.
- **One consumer is broken.** `dot-claude/bin/self-improve.py:27` inserts
  `$HOME/projects/intent-control-plane/src` on `sys.path` before importing
  `intent_control_plane.harness`. `/home/shov/projects` does not exist on this
  machine. `tools/bus/backfill_session_telemetry.py` uses a repo-relative
  `parents[2] / "intent-control-plane" / "src"` and resolves correctly. VERIFIED.
  This is the `pointers.py` dead-path class, not a new one.
- Payload or source: **source**, and the only packaged one (`pyproject.toml`,
  `uv.lock`, src-layout, hatchling wheel target `src/intent_control_plane`).
- **Recommendation: keep separate.** The `types` domain is
  `compileall ... . && cd intent-control-plane && uv run ruff check . && uv run
  mypy`, so this is the only tree under real static checking, and folding it into
  the unpackaged `tools/` would end that. Direction of travel should be the other
  way.
- **Against it:** the boundary is nominal. 4 commits ever, 116 files, and its
  consumers reach it through `sys.path.insert` rather than through the package it
  declares, which means the wheel target buys nothing that a directory would not.
  Meanwhile `tools/` is 100 Python files with 56 commits and no lint, no types and
  no package at all. Defending the boundary preserves lint over 90 files that
  barely change while leaving 100 files that change daily unchecked, which is the
  wrong side of the split to be protecting.

### `master-plans` (8 files, 0 py, 8 md)

- Commits: **2** ever. 2026-05-09 `910dec2` (initial export) and 2026-07-31
  `24e01de`, which changed **1 line in 1 file**. No content change in 90 days.
  VERIFIED.
- External references: 10, of which 3 non-markdown: `state/atlas.json`,
  `tools/docmap/atlas.py`, `tools/docmap/docmap.py`. All three are the document
  classifier reading it, not a consumer using it. VERIFIED.
- **6 of its 8 files are byte-identical to copies inside
  `work-docs/root-cleanup-2026-05-28`** (blob sha comparison over
  `git ls-files -s`): `FIX-BWRAP-WSL.md`,
  `claude-code-experimental-features.md`, `claude-setup-master-plan-2026-05-02.md`,
  `claude-setup-tasks-2026-05-02.md`, `claude-skills-scatter-2026-05-03.md`,
  `cleanup-proposal.md`. VERIFIED.
- Payload or source: **source**, superseded. Its own row in `docs/dir-purpose.txt`
  says "superseded by the newer docs/adr and docs/prd".
- **Recommendation: merge into `work-docs/root-cleanup-2026-05-28`,** which
  already holds 6 of the 8.
- **Against it:** 2 of the 8 are not duplicates.
  `CLAUDE-CODE-MASTER-PLAN-2026-05-03.md` exists only here. The second is weaker
  than it first looks and the check is worth naming: `claude-skills-triage-2026-05-03.md`
  is a third blob (`0635d0cfff97`, 26296 bytes) against an identical pair in
  `research-papers/home-md` and `work-docs/root-cleanup-2026-05-28`
  (`8d2f6d5aa819`, 26298 bytes), but `diff` between the master-plans copy and the
  work-docs copy reports **exactly one changed line, and the change is stripped
  trailing whitespace** on line 339. That is the 2026-07-31 sweep, not a content
  fork, so the merge does not have to pick a winner. VERIFIED. What does remain:
  `tools/docmap/atlas.py` and `state/atlas.json` name the path, so the move is not
  free, and one genuinely unique file would be lost if the merge were done as a
  delete.

### `research-papers` (130 files, 5 py, 84 md)

- Commits: **2** ever. 2026-05-09 `910dec2` and 2026-08-04 `e25214a`
  (`fix(panel): a quotation of a dangerous call is not a dangerous call`), which
  **deleted 43 files, 7658 lines, and added none**
  (`git show --stat --format= e25214a -- research-papers`). The only recent
  activity on this tree is deletion. VERIFIED.
- External references: 35, of which 18 non-markdown. It is named in `.alint.yml`
  as an excluded glob, in `docs/prior-art/out-of-scope.txt` as "corpus and
  employer-context material held as evidence; read, not maintained", in
  `quality-contract.json`, and in `.github/workflows/ship-gate.yml`. Every one of
  those references is an **exemption**, not a use. VERIFIED.
- Payload or source: **neither, it is evidence.** Read-only corpus.
- Residual duplication: 12 of the 16 files in `research-papers/home-md` have a
  byte-identical twin elsewhere in the repo (blob sha count over
  `git ls-files -s`). VERIFIED.
- **Recommendation: keep frozen.** Two gate files already classify it as
  read-not-maintained, and that classification is the decision. `home-md` is the
  one sub-block worth reopening later, since it is now mostly duplicate.
- **Against it:** it is 130 files exempted from every check the repo runs, its own
  purpose row says "not a maintained codebase", and it is one of the named reasons
  this repo cannot be made public (employer identifiers). A tree that is exempt
  from the gate, duplicated elsewhere, and a publication blocker has three
  independent reasons to live outside the repo, and "already declared out of
  scope" is a description of the status quo rather than an argument for it.

### `startup-scripts` (7 files, 0 py, 1 md)

- Commits: **2** ever. 2026-05-09 `910dec2` and 2026-07-25 `73cb7d5`, which
  **deleted** `claude-meme-hooks-startup.sh` (344 lines) and added nothing. The
  surviving 7 files are unchanged since the initial export. VERIFIED.
- External references: **5**, the lowest of any tracked top-level directory, of
  which 3 non-markdown: `docs/doc-status.txt`, `state/bus.jsonl`,
  `state/lessons.jsonl`. Two of those three are append-only logs, which is a
  mention rather than a reference. **0 from Python.** VERIFIED.
- Payload or source: **payload aimed at other repositories.** The scripts
  bootstrap `campaign-analysis`, `qc-telephony`, `siu` and vision projects, none
  of which is this repo.
- **Recommendation: archive.**
- **Against it:** per `repo-topology` the projects these bootstrap are separate
  repos this session does not own, so archiving here may be removing the only
  surviving copy of a bootstrap that another repo still needs and cannot see.
  Seven shell scripts also cost nothing to keep, and the strongest measurement
  against them (5 external references) is a measurement of this repo's attention,
  not of their usefulness elsewhere.

### `state` (43 files, 2 py, 3 md)

- Commits: **55** ever, all in 30 days, last 2026-08-07. VERIFIED.
- External references: 149, of which 59 non-markdown and **26 from Python**.
  VERIFIED.
- Payload or source: **neither, it is live operational state.** Append-only
  ledgers; `state/bus.jsonl` is hash-chained and `tools/bus/bus.py verify` checks
  it.
- **Recommendation: keep.**
- **Against it:** `state/` has accumulated 3 archive subtrees of its own
  (`retired-2026-07-25`, `snapshots`, `timetravel`, `backups`) alongside the live
  ledgers, so the directory that is the repo's ground truth is also becoming its
  attic. That is a later split block, not an argument against keeping it.

### `tests` (33 files, 31 py, 0 md)

- Commits: **17** ever, all in 30 days, last 2026-08-07. VERIFIED.
- External references: 171, of which 53 non-markdown and 15 from Python.
  VERIFIED.
- Payload or source: **source.**
- **Doc versus git disagreement, git wins.** `docs/dir-purpose.txt` line 151 says
  `tests` is a "Single pytest file exercising the prove-implementation
  proof/loop-audit scripts". `git ls-files -- tests | grep -c '\.py$'` gives **31**.
  Reported rather than silently corrected: fixing that row is a one-line change to
  `docs/dir-purpose.txt` plus a `codemap.py write`, both outside this report's
  write budget.
- **Recommendation: keep.**
- **Against it:** `tests/` is not the repo's test root and the name says it is.
  Every oracle carries its own selftest run as a named CI step,
  `intent-control-plane` has its own 120-file suite, and `tests/cmd` holds a
  different kind of check again (literate CLI snapshots). A newcomer reading the
  directory name will look in the wrong place for most of the verification in this
  repo.

### `tools` (138 files, 100 py, 9 md)

- Commits: **56** ever, all in 30 days, last 2026-08-07. VERIFIED.
- External references: **195**, of which **88 non-markdown** and 29 from Python,
  the highest non-markdown count in the repo. `quality-contract.json` names
  `tools/` 15 times. VERIFIED.
- Payload or source: **source**, and the working half of the repo.
- **Recommendation: keep.** The measured gap is not location, it is checking: no
  package, no ruff, no mypy, and 23 `sys.path.insert` calls doing the job an
  installed package would. Closing that is a separate block and a real one.
- **Against it:** keeping `tools/` as loose scripts is the status quo defended by
  nothing measured. 100 Python files that change daily sit outside every static
  check the repo runs, while 90 files that changed 4 times sit inside all of them.
  To be explicit about what this row does and does not recommend: **the
  recommendation is keep, and open a separate block for packaging.** The
  counterargument is about that later block, not about relocating `tools/` now,
  and if such a block is opened the measurements favour `tools/` moving under the
  package rather than the package dissolving into `tools/`.

### `work-docs` (265 files, 2 py, 179 md)

- Commits: **4** ever, last 2026-07-31 `24e01de` (the punctuation sweep). The last
  content commit is 2026-07-29 `41f5a4c`. VERIFIED.
- External references: 36, of which 16 non-markdown. Like `research-papers`, it is
  named in `.alint.yml` as an excluded glob and in
  `.github/workflows/ship-gate.yml`, so most references are exemptions. VERIFIED.
- Payload or source: **neither, it is an archive**, and already the destination
  for 6 of the 8 `master-plans` files.
- **Recommendation: keep frozen, no new writes.** It is the archive of record; a
  frozen archive that receives new writes stops being either.
- **Against it:** at 265 files it is 14 percent of the repo's tracked files and
  the second-largest tree, it is exempt from every check, and its own purpose rows
  in `docs/dir-purpose.txt` describe `work-docs/meetings` and `work-docs/qa` as
  "Dormant" and `work-docs/root-cleanup-2026-05-28` as "Retired". A tree that
  describes itself as dormant and retired in its own registry has stated the
  archive case better than this report can.

## The skill-fork claim, re-measured

TODO row B (measured 2026-08-05) says: **"Three skill trees hold 45 FORKS, not 45
copies"**, with 118 distinct names across `dot-agents` (70), `dot-claude` (74),
`dot-codex` (61) and live `~/.claude/skills` (40); 67 names in more than one tree;
22 byte-identical and 45 DIVERGED.

Re-measured at this ref, over the same four trees so the comparison is
apples-to-apples (three repo trees by `git ls-files`, live by
`ls -1d ~/.claude/skills/*/`; content hashed as sha1 over sorted per-file sha1):

| quantity | TODO row B, 2026-08-05 | measured 2026-08-07 |
| --- | ---: | ---: |
| distinct names, 4 trees | 118 | **121** |
| `dot-agents/skills` | 70 | **70** |
| `dot-claude/skills` | 74 | **75** |
| `dot-codex/skills` | 61 | **62** |
| live `~/.claude/skills` | 40 | **79** |
| names in more than one tree | 67 | **84** |
| of those, byte-identical | 22 | **30** |
| of those, DIVERGED | 45 | **52** |

**The claim still holds and understates the problem: 52 forks, not 45.** VERIFIED.

Two corrections to how it should be read:

1. **The live count of 40 does not reproduce.** Live now holds **79** skill
   directories. Live is not under git, so the "git wins" tiebreak does not apply;
   disk wins, and disk says 79. Whether the tree gained 39 skills in two days or
   the 2026-08-05 measurement counted something narrower is **not established
   here**. ASSUMED: a deploy ran between the two measurements. The three repo-tree
   counts reproduce within one, which is why this row stands out.
2. **A third of the `dot-codex` "forks" are not forks, they are broken pointers.**
   Restricting to names with a **real body** in two or more trees:
   - across all four trees: 82 such names, **30 identical, 52 DIVERGED**;
   - across the three repo trees only: 50 such names, **17 identical, 33 DIVERGED**;
   - `dot-claude` versus live: 71 shared, **44 identical, 27 DIVERGED**.

   Separately, 37 names have a real body in exactly one tree (no fork is possible)
   and 2 names have no real body anywhere. The 33 one-line pointers into
   `/home/shovalbe/` inflate any name-level count and are a **wiring defect**, the
   same class `tools/audit/pointers.py scan` exists to catch, not a divergence
   that needs a merge decision.

## What could not be measured

- **How the 8 `dot-agents`-only skills reached the live tree.** No script in the
  repo copies `dot-agents` anywhere; `sync-skills.sh` unions the two live homes
  only. ASSUMED hand-installed. This is the single unknown that most affects the
  `dot-agents` decision.
- **Whether `/mnt/c/Users/shova/.codex/skills` is empty because the deploy never
  ran or because Codex skills were abandoned.** The directory exists, is empty,
  and was last modified 2026-07-20. Both readings fit. Operator knowledge, not a
  measurable.
- **Live `~/.claude/skills` history.** It is not under version control, so the
  40-to-79 change cannot be dated or attributed. `state/snapshots` holds one
  manifest from 2026-07-25 and `state/timetravel` covers the gitignored ledgers,
  neither of which spans 2026-08-05 to 2026-08-07.
- **Direction of the 27 repo-versus-live skill divergences.** Which side is ahead
  was established for exactly one name previously (`grill-me`, where the repo is
  ahead and live is stale, per the correction recorded in TODO). The other 26 are
  unmeasured, and byte count is not evidence of currency: that is the exact error
  the `grill-me` correction records.
- **Whether the second clone has advanced.** No fetch was performed, deliberately,
  so every git number is as-of `f88d3a3`.

## Two notes on this file itself

1. **Committing it costs a map regeneration.** `docs/CODEBASE-MAP.md` carries a
   per-directory tracked-file count and records `docs/analysis | 39`. This is the
   40th file at that level. `tools/map/codemap.py check` reads `git ls-files -z`,
   so it does not see the file while it is untracked, but it will fail on the
   count once the file is committed. `python tools/map/codemap.py write` is the
   fix and is outside this report's write budget.
2. **The working tree was being written by another process during this scan.** At
   start, `git status` showed 3 modified `state/*.jsonl` ledgers. At finish it
   showed 10 modified files including `tools/audit/pointers.py`,
   `quality-contract.json` and two `docs/prior-art/*.json`, plus 2 new untracked
   Python files and a newly tracked `dot-claude/skills/i-have-adhd`.
   `codemap.py check` fails at this ref for that reason and not because of this
   file: its diff names `dot-claude/skills/i-have-adhd`,
   `dot-claude/skills/whatsapp-query`, `state` and `tests`, none of which this
   scan touched. Every number above was read from `git ls-files` and `git log` at
   `f88d3a3`, so it is unaffected, but a re-run will not reproduce the working-tree
   state.
