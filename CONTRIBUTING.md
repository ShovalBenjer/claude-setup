# Contributing to claude-setup (the Claude OS)

This repository is the canonical home of Shoval Benjer's personal Claude Operating System:
a verification harness, a deployable dotfiles payload (`dot-claude/`, `dot-codex/`,
`dot-agents/`), and the research that shapes both. `CLAUDE-OS.md` is the single source of
truth for mission, structure, and workflow. Read it first. This file is the contributor
entry point: how to set up a machine, name your work, write code that passes the gate, and
ship it through a pull request.

The single cultural rule that explains every other rule here: **prose is not enforcement.**
`work-docs/research/2026-07-07-claude-setup-gap-analysis.md` found that the OS named its own
best practices in `CLAUDE.md` and skills prose while nothing executed them. This repo exists
to invert that: a claim only counts when a running check enforces it. Keep that inversion in
mind when you add a doc, a rule, or a tool.

## 1. Development setup

The harness is Python. The only packaged subproject with its own toolchain is
`intent-control-plane/` (Python via `uv`). Everything else runs against the repo root with a
normal Python 3.11+ environment.

```bash
# 1. Clone and enter
git clone https://github.com/ShovalBenjer/claude-setup.git
cd claude-setup

# 2. Create an environment (uv is preferred; plain venv works too)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # see pyproject.toml; falls back to:
pip install pytest ruff mypy      # minimal gate toolchain

# 3. Run the full contract gate locally before pushing
python3 tools/gate/gate.py run --project . -v

# 4. Verify a single oracle's own selftest
python3 tools/gate/gate.py selftest
```

Windows note. The OS is Windows-first in intent but this machine (and the CI runner) is
Linux. Paths under `/home/shovalbe/` in `dot-claude/` and `dot-codex/` are dead on this host;
`tools/audit/pointers.py scan` is the oracle that reports them. Do not "fix" those paths by
pointing them somewhere real on this machine - they document the operator's live Windows
tree and are deliberately not executable here.

Subproject. `intent-control-plane/` is a subproject with its own `docs/`, `tests/`, and
`uv.lock` (ADR-0017 made claude-setup's copy authoritative). Work there with:

```bash
cd intent-control-plane && uv run pytest -q && uv run ruff check . && uv run mypy
```

## 2. Branch naming (kebab-case)

Every branch is `kebab-case`. Prefix by intent so the lane topology in `docs/charters.md`
stays readable:

| Prefix | Meaning | Example |
|---|---|---|
| `feat/` | new capability | `feat/docmap-purpose-column` |
| `fix/` | bug or gate red | `fix/ci-pytest-missing` |
| `docs/` | documentation only | `docs/mature-doc-system` |
| `chore/` | maintenance, no behavior | `chore/trim-stale-hooks` |
| `test/` | test-only change | `test/bus-lock-windows-leg` |
| `refactor/` | structure, same behavior | `refactor/skills-sync` |

Never work directly on `main`. PRs merge into `main` only through the PR gate (ADR-0012).
Work with a fresh branch per concern; one branch per logical change keeps review and revert
cheap.

## 3. Commit conventions (Conventional Commits)

Format: `<type>(<scope>): <subject>` - imperative, lowercase subject, no trailing period.

| Type | Use |
|---|---|
| `feat` | new behavior |
| `fix` | correct a defect |
| `docs` | documentation |
| `test` | add/fix tests |
| `refactor` | restructure, no behavior change |
| `chore` | tooling, deps, housekeeping |
| `perf` | performance |
| `build` | build/CI pipeline |

Scope is the directory or tool, e.g. `docs(docmap)`, `fix(gate)`, `feat(bus)`. Good:
`docs: mature documentation system with structure, conventions, and living docs`. Bad:
`updated stuff`. Keep commits small and reviewable; the gate measures per-commit hygiene in
Tier 1.

## 4. Testing requirements (TDD is enforced)

`dot-codex/rules/tdd-enforcement.md` is binding. The cycle is RED → GREEN → REFACTOR:

1. **RED** - write the failing test first. Never assume code works; prove it.
2. **GREEN** - implement the minimum that makes the test pass.
3. **REFACTOR** - format and lint only after the test is green.

Gate tiers (from the same rule):

- **Tier 1 - every commit:** linter 0 errors, formatter 0 violations, type check 0 errors,
  unit tests pass, property/invariant tests pass.
- **Tier 2 - every PR:** all of Tier 1 plus integration, regression, and a coverage floor.
- **Tier 3 - nightly:** fuzz, mutation (target >80%), performance baselines, chaos.
- **Tier 4 - pre-release:** full regression, load, security scan.

Hard rules:

- No mock violations. `dot-codex/rules/no-mocks.md` forbids mocking services, DBs, the file
  system, or the network. Use real in-memory components (`SQLiteStore(':memory:')`), recorded
  VCR/nock cassettes from real APIs, or platform stubs only (e.g. `global.figma`).
- No emojis anywhere - code, comments, commit messages, tests, reports
  (`dot-codex/rules/no-emojis.md`).
- Every production bug gets a permanent regression test before close.
- A new Python component over 300 lines owes `docs/prior-art/<name>.json` with named
  alternatives and an expiry date; an empty alternatives list fails the gate.

## 5. Pull request process

1. Branch from `main`, name it per section 2.
2. Implement behind tests (section 4). Keep each commit conventional and scoped.
3. Run the gate locally: `python3 tools/gate/gate.py run --project . -v`. Do not push red.
4. Push and open the PR against `main`. The PR body must state the intent it satisfies
   (an acceptance checklist, not a summary of the diff).
5. CI runs the `ship-gate.yml` contract (three jobs; read its header comment before
   changing anything - the `pipeline` domain greps for a literal `gate.py run`). A green run
   is required to merge.
6. Code review runs the dual-reviewer fabric: two independent reviews, an agreement gate,
   and provenance on the posted verdict (`CLAUDE-OS.md` L5 / ADR-0004). Address every
   finding or record an explicit, reasoned waiver.
7. Merge via the PR gate only (ADR-0012). No force-push to `main`, no direct commits.

## 6. Code review expectations

Reviewers and authors are held to the same standard as the OS itself:

- **Evidence over assertion.** Claims in the PR or review are tied to a running check, not
  prose. "Looks right" is not a verdict.
- **Small surface.** Review a diff, not a dissertation. Large PRs are themselves a defect;
  split them.
- **Tie severity to impact.** Findings carry a tier (HIGH/MED/LOW) and a root cause, per
  `tdd-enforcement.md` reporting format. Possible issues are labeled "possible" and cite
  evidence; fixes stay under ~15 lines where the fix is mechanical.
- **No slack enforcement.** Prose deliverables pass `tools/slop_lint.py` (no emoji, no spaced
  em/en dash connectors, no banned phrases, density/variance thresholds). A clean slop lint
  is not by itself evidence the content is correct - it gates only the form.
- **Docs are the control plane.** A behavioral change without a matching doc update (PRD,
  spec, ADR, or analysis) is incomplete. `docs/DOCMAP.md` is generated; edit the document's
  own header or `docs/doc-status.txt`, never DOCMAP.md by hand.
- **Stubs are defects.** A placeholder, TODO comment left as content, or "to be wired" note
  is a defect by definition (`CLAUDE-OS.md` L1 capability-honesty matrix). Either wire it or
  remove it.

## 7. Release process

There is no versioned release cadence for the OS itself - the OS is a living configuration
whose "production" state is **merged and smoke-tested** (`dot-codex/rules/production-means-
merged-and-smoked.md`), not a tagged artifact. Concretely:

1. A change reaches production when its PR is merged to `main` **and** the gate is green on
   the merged tree, **and** the change's own evidence command has been observed to pass on
   the real CI runner (a local PASS is not evidence about the runner - see the CI red lesson
   in `TODO.md`).
2. Subprojects (`intent-control-plane/`, `nexus-engine-rs/`, `dashboard/`) may tag releases
   independently; their green gate is necessary and sufficient there.
3. ADRs record decisions that outlive any branch (`docs/adr/`). A new architectural decision
   without an ADR is incomplete. ADR-0016 (lane letters) and ADR-0012 (PR-gate-only
   shipping) bind day-to-day work.
4. Retired content moves to `docs/archive/` with a migration note; nothing is deleted
   silently. See `docs/archive/MIGRATION-NOTES.md`.

## 8. Where to get help

- Mission, layers, and workflow: `CLAUDE-OS.md`.
- Reading order across the doc estate: `docs/INDEX.md`.
- Boot path for a new session: `docs/SESSION-BOOT.md`.
- Quality contract reasoning: `docs/QUALITY-CONTRACT.md`.
- Lane ownership and what not to work on: `docs/charters.md`.
- The research that shapes these rules: `work-docs/research/` (start with the gap analysis
  and the global/per-project suggestions).
