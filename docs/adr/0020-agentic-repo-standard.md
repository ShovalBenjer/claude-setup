# ADR-0020: one repository standard for the estate, enforced by adopted alint

Date: 2026-07-31
Status: accepted
Lane: A (harness)

## Context

The operator owns many repositories and an agent arriving at one of them has to
guess where things are. A census on 2026-07-31 over every `.git` directory under
the home tree, excluding `AppData/Local/Temp`, `scoop`, and `.codex` (those three
hold thousands of throwaway fixtures from `enforce-selftest` and `skillscan`
runs, which is how an earlier count reached 1,884 apparent repositories), found
**31 real repositories with 67 distinct top-level directory names and no name
present in half of them.** The most common is `docs` at 13 of 31.

Against the population this is far below a convergence nearly everyone reached.
Hora, Montandon and Costa, arXiv:2605.16701, ICSME 2026, measured 10,000
repositories comprising 10,904,237 files and 1,970,740 directories at a 2026
snapshot: README.md 95.3%, .gitignore 95.0%, LICENSE 73.1%, `.github` 82.5%,
`workflows` 77.3%. This estate is at 58.1%, 58.1%, 29.0%, 41.9%, and 41.9%. It
sits at or above the population only where the population has not converged
(`docs`, `tests`, `CLAUDE.md`) and far below it everywhere the matter is settled.

Three specific defects forced the timing:

1. Root `CLAUDE.md` in this repository is **untracked**. The file that sets lane,
   gate, and prose rules for every Claude session is not in version control, so
   it cannot be reviewed or diffed and a fresh clone gets none of it. Alongside
   it sit four more hand-maintained agent files: `CLAUDE-OS.md` (24,458 bytes),
   `dot-claude/CLAUDE.md` (3,610), `dot-codex/AGENTS.md` (31),
   `home-dotfiles/AGENTS.md` (5,975).
2. `dot-codex/AGENTS.md` already uses the pointer pattern and is already broken:
   its 31 bytes read `@/home/shovalbe/.codex/RTK.md`, a WSL path absent from this
   machine.
3. Kilo Code moves reviewer instructions into a repository `REVIEW.md`
   (https://kilo.ai/docs/automate/code-reviews/overview). Zero of the 31
   repositories have one.

GitHub issue #21 scoped this work and it was never written; `docs/standards/`
did not exist before this ADR.

## Decision

Adopt **alint** (https://github.com/asamarts/alint, v0.14.1, Apache-2.0 or MIT)
and express the standard as a per-repository `.alint.yml`. Do not write a
bespoke conformance checker for repository shape.

The reasoning is `prior-art-gate`. alint ships 89 rule kinds across 13 families
and 22 bundled rulesets, including `oss-baseline@v1`, `ci/github-actions@v1`,
`docs/adr@v1`, `hygiene/no-tracked-artifacts@v1`, and two aimed at this exact
problem, `agent-hygiene@v1` and `agent-context@v1`. Its `extends:` mechanism
composes bundled, local, and SRI-pinned HTTPS rulesets, which is the shape of an
estate whose repositories share a spine and differ in stack. Writing our own
would mean reimplementing published rule kinds to check facts a maintained tool
already checks.

`todogroup/repolinter`, the previous generation, was **archived 2026-02-06** and
names no successor, so it is a design reference and not a dependency.

One row cannot be expressed as a filesystem fact. Row 6, the per-repository
GitHub Project, is reached through `tools/audit/repo_project.py`, wired in as an
alint `command` rule, carrying its own `selftest` verb per this repository's
convention so `tools/audit/mutate.py` has something to run against it.

The standard's six rows and the defect behind each are in
`docs/standards/agentic-repo-standard.md`. That document explains; `.alint.yml`
enforces. Where they disagree the YAML wins.

## Consequences

Measured against `claude-setup` itself on 2026-07-31, `alint check` reports 117
violations across 24 failing rules. Of the 21 rules this standard contributes,
**12 pass and 9 fail**:

| Rule | Level | What is wrong |
|---|---|---|
| `r1-license-exists` | error | no root LICENSE |
| `r1-agents-md-exists` | error | no root AGENTS.md |
| `r1-claude-md-is-a-pointer` | error | root CLAUDE.md is 6,229 bytes of prose, and untracked |
| `r1-pointer-target-is-in-repo` | error | `dot-codex/AGENTS.md` points outside the repo |
| `r1-no-competing-root-agent-files` | warning | `CLAUDE-OS.md` is a second root authority |
| `r2-review-md-exists` | error | no REVIEW.md |
| `r4-codeowners-exists` | error | three live workflows, no CODEOWNERS |
| `r4-issue-template-exists` | error | no `.github/ISSUE_TEMPLATE/` |
| `r4-no-dotless-github-dir` | error | the dead `github/` staging duplicate is still tracked |

None of these are fixed by this ADR, on purpose. Choosing a license is the
operator's call, and collapsing five agent files into one is a content migration
that deserves its own review, not a side effect of landing a standard. They are
follow-up tickets under issue #21. A standard that arrived green would only mean
its author had tuned it until it passed.

The bundled rulesets also fired: 4 tracked Python cache directories, 2 files
carrying bidi control characters, 15 GitHub Actions steps unpinned to a sha, and
`TODO.md` flagged as a scratch doc at the root.

### Costs accepted

- alint is **pre-1.0**; rule names and schema may move. Mitigated by `@v1`
  revision pins in `extends:` and by recording v0.14.1 here.
- alint needs a **recent Rust toolchain**. This machine held Rust 1.85.0 and
  `cargo install alint --locked` failed with eight `E0658` errors on let-chain
  syntax; it built only after `rustup update stable` reached 1.97.1, and a clean
  release build takes over ten minutes. Repositories without Rust consume the
  Docker image or the npm package instead. This portability tax is the strongest
  argument for having written our own, and it is accepted rather than dismissed.
- `.alint.yml` is a new tracked file in every repository. Rollout is per
  repository, gated on that repository's owner, not a sweep.

### Not decided here

`quality-contract.json` is untouched, so `alint check` is not yet a gate domain.
Making it one is a separate decision that should wait until the nine failures
above are closed, because adding a domain that fails on day one makes the gate
report noise rather than signal.

## Falsifier

If, by **2027-01-31**, repositories that conform do not produce measurably fewer
lane errors in `state/lessons.jsonl` and fewer restarts in
`state/handback-log.jsonl` per session than non-conforming ones, this standard is
ceremony and this ADR should be superseded.
