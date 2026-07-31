# Root agentic repository standard

Status: active. Owner: lane A. Decided by ADR-0020. First written 2026-07-31.

Every repository the operator owns satisfies this contract, so that an agent
arriving at any of them finds the same things in the same places. The contract is
machine-checked by `.alint.yml` at each repository root. This document holds the
reasoning; the YAML holds the enforcement. Where the two disagree the YAML wins,
because a document that states its own compliance goes stale the first time
somebody fixes something.

## The measured problem

A census of the operator's local estate ran on 2026-07-31 over every `.git`
directory under the home tree, excluding `AppData/Local/Temp`, `scoop`, and
`.codex` (those three contribute thousands of throwaway fixtures from
`enforce-selftest` and `skillscan` runs, which is how an earlier count reached
1,884 apparent repositories). What remains is 31 real repositories.

Across those 31 repositories there are **67 distinct top-level directory names,
and not one name appears in half of them.** The most common is `docs` at 13 of
31. `new-recruit` opens with `Documents`, `archive`, `command_center`, and
`hiring_engine`. `claude-setup` opens with `dot-agents`, `dot-claude`,
`dot-codex`, `github`, and `home-dotfiles`. `oren-roast-hq` opens with `public`,
`src`, and `supabase`. An agent that has learned one of them has learned nothing
about the next.

Compare that against the population. Hora, Montandon and Costa, *What's Inside a
GitHub Repository? An Empirical Study on the Contents of 10K Projects*
(arXiv:2605.16701, accepted to ICSME 2026, revised 2026-07-13,
https://arxiv.org/abs/2605.16701) analysed 10,000 repositories comprising
10,904,237 files and 1,970,740 directories at a 2026 snapshot, against 6,371
repositories in 2021 and 2,591 in 2016.

| Artifact | 10K study, 2026 | This estate, 31 repos | Gap |
|---|---|---|---|
| README.md | 95.3% | 58.1% (18/31) | -37.2 |
| .gitignore | 95.0% | 58.1% (18/31) | -36.9 |
| LICENSE | 73.1% | 29.0% (9/31) | -44.1 |
| .github | 82.5% | 41.9% (13/31) | -40.6 |
| workflows | 77.3% | 41.9% (13/31) | -35.4 |
| src | 60.1% | 29.0% (9/31) | -31.1 |
| docs | 37.4% | 41.9% (13/31) | +4.5 |
| tests | 35.5% | 35.5% (11/31) | 0.0 |
| CLAUDE.md | 9.0% | 12.9% (4/31) | +3.9 |
| AGENTS.md | 8.5% | 6.5% (2/31) | -2.0 |
| REVIEW.md | not measured | 0% (0/31) | n/a |

The estate is at or above the population exactly where the population has not
converged (`docs`, `tests`, `CLAUDE.md`) and far below it on every artifact that
almost everyone else already ships. The three worst gaps are LICENSE, `.github`,
and README. This is not a case of the operator working ahead of a convention; it
is a case of skipping the settled part.

The census script and its output are reproducible: enumerate `.git` parents,
exclude the three noise trees, then test for each artifact by path existence.

## What this standard adopts rather than invents

`todogroup/repolinter` was the previous generation of repository-shape linting
with JSON and YAML rulesets. It was **archived on 2026-02-06**
(https://github.com/todogroup/repolinter) and its README names no successor, so
it is available as a design reference and not as a dependency.

`alint` (https://github.com/asamarts/alint) is the live tool in that slot: a
language-agnostic linter for repository shape, files, and content, written in
Rust, dual-licensed Apache-2.0 or MIT. At **v0.14.1** it ships **89 rule kinds
across 13 families**, 12 auto-fix operations, and **22 bundled rulesets**.

Three properties decided the adoption:

1. Its `extends:` mechanism composes rulesets from bundled names
   (`alint://bundled/<name>@<rev>`), local paths, and HTTPS URLs with SRI
   pinning. One shared base plus a per-repository overlay is exactly the shape
   of a 31-repository estate whose members share a spine and differ in stack.
2. Its bundled set already covers most of what this standard needs:
   `oss-baseline@v1`, `ci/github-actions@v1`, `docs/adr@v1`,
   `hygiene/no-tracked-artifacts@v1`, `hygiene/lockfiles@v1`, plus per-ecosystem
   baselines for Rust, Node, Python, and Go. Two of them, **`agent-hygiene@v1`
   and `agent-context@v1`**, are aimed at the AGENTS.md problem directly.
3. Its `command` rule family shells out, which is the only way a filesystem
   linter can reach a GitHub Projects fact (row 6).

Writing our own checker would mean reimplementing existing published rule kinds
to check facts that a maintained tool already checks. The `prior-art-gate` rule
forbids exactly that. The counter-evidence is recorded honestly below under
"Known costs of this choice".

### Known costs of this choice

- alint is **pre-1.0**. Rule names and the config schema may move under us. The
  mitigation is that `extends:` pins a revision (`@v1`), and the version this
  standard was written against is recorded here and in ADR-0020.
- alint needs a **recent Rust toolchain**. On 2026-07-31 this machine held Rust
  1.85.0 and `cargo install alint --locked` failed with eight `E0658` errors on
  let-chain syntax in `alint-core`. It built only after `rustup update stable`
  moved the toolchain to 1.97.1, and a clean release build takes over ten
  minutes. Any repository in the estate that has no Rust toolchain pays that
  cost once, or consumes the tool from `ghcr.io/asamarts/alint:v0.14.1` or from
  npm as `@asamarts/alint`. This is a real portability tax and it is the
  strongest argument for having written our own instead.
- A per-repo `.alint.yml` is a **new tracked file in 31 repositories**. Rollout
  is per repository and gated on that repository's owner, not a sweep.

## The rows

Each row states the rule, then the defect in this estate that produced it. A row
with no local defect behind it is not in this table.

### 1. Required root files

`README.md`, `LICENSE`, `.gitignore`, and `AGENTS.md` are required at the root of
every repository. `CLAUDE.md`, when present, is an **11-byte pointer whose entire
content is `@AGENTS.md`** followed by a newline. No other agent-instruction file
lives at the root.

The defect: `claude-setup` hand-maintains five overlapping agent-instruction
files. `CLAUDE-OS.md` at 24,458 bytes, root `CLAUDE.md` at 6,229 bytes,
`dot-claude/CLAUDE.md` at 3,610 bytes, `dot-codex/AGENTS.md` at 31 bytes, and
`home-dotfiles/AGENTS.md` at 5,975 bytes. Two of them are worse than redundant:

- Root `CLAUDE.md` is **untracked**. `git status --porcelain CLAUDE.md` returns
  `?? CLAUDE.md`. The file every Claude session reads first, which sets the
  project's rules for lanes, gates and prose, is not under version control. It
  cannot be reviewed, it cannot be diffed, and a fresh clone gets none of it.
- `dot-codex/AGENTS.md` already uses the pointer pattern and it is already
  broken: its 31 bytes are `@/home/shovalbe/.codex/RTK.md`, a WSL path that does
  not exist on this Windows machine. This is the same dangling-pointer class
  `tools/audit/pointers.py scan` was built for.

So the rule is not merely "use a pointer". It is: **the pointer target is a path
inside this repository**, and every file the pointer chain reaches is tracked.
`nexu-io/open-design` (https://github.com/nexu-io/open-design) ships both
`AGENTS.md` and `CLAUDE.md` at its root alongside `CONTEXT.md`, and its README
delegates rather than restating: "Before changing or documenting daemon storage
paths, you MUST read `AGENTS.md`". One authority, many doors into it.

`LICENSE` is required because it is the single largest gap in the table above at
-44.1 points, and because a repository with no license is legally closed to the
collaborators and the review bots the operator wants to attract.

### 2. REVIEW.md

`REVIEW.md` is required at the repository root, committed to the base branch that
pull requests target, and no longer than 10,000 characters.

Kilo Code's documentation (https://kilo.ai/docs/automate/code-reviews/overview)
specifies the filename `REVIEW.md` at the repository root, requires that it be
committed to the base branch used by pull requests so that a branch cannot alter
the criteria by which it is judged, and truncates the file past 10,000
characters with a note in the review summary footer. It cannot override Kilo's
safety constraints, read-only mode, or platform API rules.

A naming discrepancy is on the record and unresolved: Kilo's launch post of
2026-06-12 (https://blog.kilo.ai/p/code-reviews-md) calls the file **REVIEWS.md**
throughout, while the current documentation calls it **REVIEW.md**. This standard
follows the documentation, since it is the newer of the two and is the page the
product links from its settings. A repository may ship `REVIEWS.md` as a
same-content copy until the vendor settles it; the checker warns rather than
fails on that case.

The migration deadline in the brief, that the reviewer custom-instructions text
box is removed for everyone on 2026-08-31, comes from a vendor email dated
2026-07-30 12:50 held by the operator. **Neither fetched vendor page states that
date**, so it is recorded here as operator-supplied and not as a verified
citation. The standard does not depend on it: REVIEW.md is worth having whether
or not the box disappears.

What REVIEW.md contains for us, and how it differs from AGENTS.md:

| | AGENTS.md | REVIEW.md |
|---|---|---|
| Reader | an agent about to change the repo | an agent about to judge a change |
| Tense | how to build here | what to reject here |
| Contains | lanes, boot path, commands, gotchas | severity calibration, paths to skip, verification expected, summary style, sub-agent budget |
| Fails when | an agent does the wrong lane's work | a reviewer nitpicks generated files |

The two must not duplicate. REVIEW.md links to AGENTS.md for the build facts and
carries only the judging policy. For this repository that means naming
`docs/CODEBASE-MAP.md` and the `state/*.jsonl` ledgers as generated or
append-only and therefore out of scope for style comment, stating that a
weakened oracle is a blocking finding regardless of diff size, and setting the
sub-agent budget by diff size.

### 3. Expected directory set

Derived from what the 31 repositories already do, ranked by how many of them use
the name. Nothing here is invented.

| Directory | In estate | Holds | Required |
|---|---|---|---|
| `docs/` | 13/31 | prose: specs, ADRs, analysis, handoffs | yes |
| `tests/` | 11/31 | the executable oracles | yes when code exists |
| `src/` | 9/31 | the shipped source | yes when code exists |
| `.github/` | 13/31 | see row 4 | yes |
| `state/` | 5/31 | append-only ledgers, see row 5 | when the repo has agents |
| `tools/` | 3/31 | verification instruments, not product | optional |
| `scripts/` | 4/31 | one-shot operator scripts | optional |
| `public/`, `assets/` | 6/31, 4/31 | static web assets | web repos only |

`dist/` at 5/31 and `node_modules/` at 3/31 are tracked build output and
dependencies. Both are defects, not directories, and the standard requires them
gitignored. `alint`'s `hygiene/no-tracked-artifacts@v1` is the rule that catches
them.

Nothing forces a repository to have `src/`. The rule is conditional: **if a
repository has code, that code is under one of `src/`, or a language-conventional
root the ecosystem ruleset names.** The failure this prevents is the estate's
current shape, where source sits under `command_center`, `hiring_engine`, and
`worker` with no way to tell from outside which is which.

### 4. `.github/` contents

Required: `.github/workflows/` with at least one workflow, `.github/CODEOWNERS`,
and `.github/ISSUE_TEMPLATE/` with at least one template.

The defect: `claude-setup` has `.github/workflows/` with three live YAMLs and
**nothing else**. No `CODEOWNERS`, no `ISSUE_TEMPLATE`, no
`PULL_REQUEST_TEMPLATE.md`, no `dependabot.yml`. It also carries a second
directory named `github/` with no dot, a dead staging duplicate that GitHub never
reads, which is precisely the confusion a checker removes. The standard requires
that a repository have no top-level `github/` directory.

CODEOWNERS matters more than it looks in a single-operator estate: it is the
mechanism that assigns a reviewer automatically, and the operator's plan is to
wire several review bots to these repositories.

### 5. State and ledger conventions

Where a repository holds agent state, it lives under `state/` and follows the
conventions this repository already enforces:

- Ledgers are **append-only JSONL**, one object per line, named `<topic>.jsonl`.
- A ledger whose content is local telemetry, a lock, or a cursor is
  **gitignored**, and the ignore line carries a comment saying why. This
  repository already does that for `state/api-usage.jsonl`,
  `state/bus-cursors/`, and `state/handback-log.jsonl`.
- Shared state is committed. `state/bus.jsonl` is hash-chained and
  `python tools/bus/bus.py verify` checks it, so a rewrite of history is visible.
- Gitignored state that matters carries a **committed manifest** naming what
  should exist, so that an absent file is distinguishable from an ignored one.

The defect this closes is the one recorded in `~/.claude/rules/hidden-trees.md`:
`tools/audit/pointers.py` reported `~/projects/campaign-analysis` absent five
times when it was 1,626 files sitting in an ignored tree. An ignored tree with no
manifest cannot be told apart from a missing one, and an audit will report clean
while missing more than it examined.

### 6. Per-repository GitHub Project

Every repository with a GitHub remote has a GitHub Project linked to it, and
every open issue in that repository appears on the project board.

The board of record is **Zion**, project number 3 under owner `ShovalBenjer`
(`PVT_kwHOBTKVvM4At4WJ`), confirmed by `gh project list --owner ShovalBenjer` on
2026-07-31, which also shows `solosolve-ai-project` (4) and a phantom-limb
project (2). Issue #21, the epic that scoped this standard, is already on Zion
with status unset, which is itself the defect: a board that items reach without
status is an inbox, not a plan.

Per-repository projects feed Zion rather than replace it. A repository project
tracks that repository's issues; Zion carries the operator's cross-repository
view. The link direction is repository project to Zion, so that closing a repo
means archiving one board and not editing a shared one.

This is the only row a filesystem linter cannot see. It is checked by an alint
`command` rule shelling out to `gh`, which fails soft when `gh` is unauthenticated
so that an offline clone still lints.

## Conformance

Run at any repository root:

```
alint check
```

The result of running it against `claude-setup` itself is in ADR-0020 and in the
report accompanying this document. It does not pass.

## What would falsify this standard

If, six months after adoption, the repositories that conform are not measurably
faster for an agent to start work in, this standard is ceremony. The observable
proxy already exists: `state/lessons.jsonl` records lane errors and
`state/handback-log.jsonl` records restarts. A conforming repository should
produce fewer of both per session than a non-conforming one. If that difference
is absent by 2027-01-31, revisit ADR-0020.
