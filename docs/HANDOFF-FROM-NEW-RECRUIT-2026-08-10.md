# Handoff from new-recruit, 2026-08-10: 169 files handed back, 450 duplicates found

Companion to `HANDOFF-FROM-NEW-RECRUIT-2026-07-29.md`. Written by the
new-recruit side; claude-setup owns what happens next to the inbox.

## What arrived

`docs/inbox-from-new-recruit/` now holds 169 files plus three whole trees
(`.agents/`, `.codex/`, `.kilo/`) that new-recruit was carrying and does not
own. Nothing has been merged into this repo's own directories. The inbox is a
staging area on purpose: the receiving repo reviews before absorbing, because
new-recruit cannot know which of these claude-setup already superseded.

The move was made by `new-recruit/scripts/repo_scope.py` against the per-file
ledger in `new-recruit/scripts/repo-scope.json`. Every rule there carries a
`why`, so the reason any single file was handed over is readable without asking.

## The measurement worth keeping

774 of new-recruit's 2,161 files were **byte-identical copies of files already
in this repository**. Content hash, not filename: new-recruit's copies carry
mojibake filenames (`API Design and Contracts SOTA Γאפ July 2026.md`) where this
repo has the correct em dash, so a name comparison sees two different files and
a hash comparison sees the truth. Anyone auditing either repo by filename has
been counting the same document twice.

Where they were:

| tree in new-recruit | files | already here |
|---|---|---|
| `docs/` | 319 | 227 |
| `.codex/` | 257 | 220 |
| `.agents/` | 217 | 167 |
| `.claude/` | 119 | 99 |
| `Documents/` | 57 | 34 |
| `mcp-servers/` | 795 | 22 |

The 450 that were still identical at apply time were moved to
`new-recruit/archive/duplicates-of-claude-setup/`, not deleted, and the tool
re-hashes both sides before touching anything.

Worktrees were excluded from the index when computing this. A file whose only
other copy lived in `.claude/worktrees/thinking-instrument/` does not count as
held by this repo, because a worktree is a transient checkout. Twenty-four of
the matches pointed there before that exclusion was added; all twenty-four also
had a canonical twin, so the total did not change, but the next audit should
keep the exclusion.

## What the inbox contains, by kind

1. **Research prompts and their reports** (`docs/research/prompts/*`, ten files,
   2026-07-12 and 2026-07-27). The reports themselves were already here in
   `work-docs/`; the prompts that produced them were not. They belong together.
2. **Repo and harness standards** unique to the new-recruit copy:
   `2026-07-26-repo-target-architecture.md`, `2026-07-26-repo-consolidation-goal.md`,
   `2026-07-26-memory-architecture.md`, `2026-07-26-commit-pr-review-upgrade.md`,
   `2026-07-09-harness-maturity-plan.md`, `2026-05-13-hive-adoption-plan.md`.
   Note that `2026-07-26-repo-consolidation-goal.md` contradicts itself about
   where the WhatsApp self-chat export should live (ADR-0002 open item 4 in
   new-recruit records the three incompatible instructions at `:299`, `:371-373`
   and `:379`). Absorbing it without resolving that carries the contradiction in.
3. **Skill drafts** as loose `.txt`: `create-prd-skill4.txt`,
   `data-exploration-skill.txt`, `data-viz-skill.txt`, `sales-account-skill.txt`,
   `conent-creation-skill.txt` (sic), `testing_practices.txt`.
4. **`docs/root-cleanup-2026-05-28/`**, 21 files, the output of a May cleanup
   that was itself never absorbed anywhere.
5. **Three vendor harness trees**: `.agents/` (229 files), `.codex/` (269),
   `.kilo/` (3,452, almost all `node_modules`). These are seeded from this
   repo's `dot-agents/` and `dot-codex/`. What is in the inbox is the drift.

## What new-recruit kept, and why it is not yours

`.claude/rules/` and `.claude/commands/` stay in new-recruit and are tracked
there, byte-identical to `dot-claude/` here **on purpose**: that is what a
distributed contract looks like, and the dedup pass explicitly exempts them.
If this repo ever changes one of those rules, new-recruit does not find out.
That is an open coupling, not a solved one.

## What is still unresolved and needs a call from the operator, not from here

- `new-recruit/dist/` holds `claude-setup-FULL-20260508.zip`, 496 MB. It is a
  build output of THIS repo sitting in that one. Ledgered as `to-claude-setup`
  but not moved: a 520 MB write into another repo is not something an automated
  pass should do quietly.
- `new-recruit/projects/` (21,490 files, 3.9 GB) and
  `new-recruit/work-archive-2026-07-12/` (1.4 GB of git bundles) are the
  previous employer's repos. They are resume-claim evidence under new-recruit's
  CLAUDE.md, so they cannot simply be dropped, and two of them carry nested
  `.git` directories that `repo-topology.md` forbids outright.
