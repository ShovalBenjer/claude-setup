# Engineering standards for הסדנה

Status: reference. Imported from daily-deep-learning 2026-08-04. Lane C standards, held here as cross-lane evidence.

Regrounded 2026-07-26 against the research corpus in `new-recruit/docs` rather
than asserted from memory. This file is the engineering half of
SYSTEM-SPEC-2026-07-26.md: what we build with, how it moves from local to
production, and what the code and documentation must look like.

## 0. Sources and coverage boundary

Read this pass, by targeted section rather than end to end:

- `code-quality-standard-2026-07.md`: Q1 docstring standard in full, Q4 numeric
  thresholds. Q2 typing and Q3 error handling headings only.
- `Next-Gen AI-Native Repo Structure (July 2026).md`: sections 4 docstrings,
  5 LOC budgets, 6 navigation. Sections 1 to 3 by heading.
- `Code Maturity Ladder: POC to Production (2026).md`: Part A stages and exit
  criteria in full.
- `Polyglot Stack Selection (July 2026).md`: B1 Python shortlist, C3 solo
  layouts, C4 boring-language checklist.
- `repo-standards-2026-07-09.md`: all 70 lines.

Not read this pass: the SQL, API-contracts, persistence, testing-pyramid and
UI-UX SOTA documents. They are relevant to unit CONTENT, not to this file.

## 1. Stack

The corpus rule is C4, "one boring language unless proven otherwise". Adding a
language requires a measurable, decision-altering gap and a network boundary.

This repo runs three languages today. Each is justified, and the justification
is written down so it stops being re-argued.

| Surface | Language | Justified because |
|---|---|---|
| The app | Vanilla JS, HTML, CSS | The browser accepts nothing else. No bundler, per the standing non-goal: a build step regresses offline-first for no measured gain. |
| Authoring and gate tools | Python 3.13+ | 7 tracked scripts. Corpus default for scripting and data work. |
| Daemon and sync Worker | TypeScript on Bun and Cloudflare Workers | The Worker runtime is JS-only, so the daemon matching it keeps one toolchain across the network boundary. |

The daemon could collapse into Python and reduce three languages to two. It is
not worth doing: the Worker cannot, so the TS toolchain stays regardless, and
the boundary is already a network call with a typed payload.

Python toolchain, per the corpus shortlist: **uv** for packaging, **Ruff** for
lint and format, **mypy** for types with `ty` noted as the Astral successor but
still beta, **pytest** for tests. None of these are installed here yet.

Rejected for this project, with reasons, so they are not proposed again:
FastAPI, SQLAlchemy, Pydantic and structlog are the corpus defaults for a Python
service. This is not a Python service. The daemon is 200 lines of Bun serving
two routes.

## 2. Environments

The corpus requires stage and production separation. **This repo has no stage.**
Today there are two environments and a gap:

| Environment | Today | Target |
|---|---|---|
| Local | `python -m http.server 8080`. Does not apply `_headers`, so CSP and security headers are untested locally. | Same, plus a documented note that header behaviour is only real on a deploy. |
| Stage | **Does not exist.** | Cloudflare Pages preview deployment per branch and pull request. Applies `_headers`, gets a unique URL, no production traffic. |
| Production | `pages deploy .` on push to main, no approval, no path filter. | Unchanged trigger, but gated on the preview passing. |

The stage gap is why the pipeline gate fails and why proving CI ran the gate
currently requires deploying production. Preview deployments close both.

## 3. Maturity, honestly

Corpus stages: POC, Prototype/MVP, Production, Hardened/Regulated.

**This project is a deployed MVP, not Production.** It has been treated as
production ("i check on finished product"), which is the corpus's named Failure
Mode 2, POC in Prod.

Against the Prototype/MVP to Production exit criteria:

| Criterion | State |
|---|---|
| Core value validated by real users | PARTIAL. One user, who stopped opening it. |
| Critical path reliable under realistic load | N/A at one user |
| Secrets management enforced | PASS. `daemon/.key` gitignored, Worker uses a bearer secret, gate scanned 108 files clean. |
| Structured logging, one dashboard | FAIL. Neither exists. |
| Rollback documented and manually tested | FAIL. |
| Owner assigned | PASS. |
| Runbook for common failures | FAIL. |
| CI/CD operational, not just builds locally | PARTIAL. Deploys, but only `validate_links.py` gates it. Tests do not run in CI. |
| Authn/authz on user-facing surface | PARTIAL. The site is public and unauthenticated by design; the daemon requires a bearer token. |
| Dependency CVE scan clean | FAIL. No scan exists. |

Target: close logging, rollback, runbook, and the CI test gate. Do not chase
Hardened. SLOs, canary deploys and threat models are not warranted for a
single-user learning app, and the corpus explicitly names over-engineering early
as Failure Mode 1.

## 4. Repo layout and codebase mapping

Corpus dimension 1: a clean tree with the layout its class demands. This project
is a product app, so `src/` layout would apply to a Python package. It has no
Python package, so the rule that binds is the clean-root check and the presence
of a map.

Standing rules:

- One `.git`. No tracked artifacts, backups or caches.
- `docs/CODEBASE-MAP.md` is the map and stays current. It already exists and is
  line-cited, which satisfies the deepened check.
- `docs/adr/` for every non-obvious decision. Does not exist yet.
- Navigation is by the corpus commands: `tree -I '__pycache__|.venv|node_modules'`,
  LOC per file sorted, grep for public symbols.

## 5. README standard

Corpus bar: a reader, human or agent, can orient. Required sections, in order:

1. What this is, one paragraph, including who it is for.
2. Structure, the directory-by-directory one-liner, pointing at the full map.
3. Local preview, the exact command, plus what local does NOT reproduce.
4. Deploy, the exact command and what triggers it.
5. The contract files a contributor must read before changing anything.

The current README covers 1 through 4 in 47 lines and is close to the bar. It
gains a pointer to the standards and the ADR directory.

## 6. Documentation control

Per the docs-control-plane rule: separate current state, proposed design,
historical evidence, and generated output. Date drift-prone claims. Never let a
plan read as a claim that code or deployment exists.

Applied here:

- Current state: `README.md`, `docs/CODEBASE-MAP.md`.
- Proposed design: dated spec and plan files, which say SPECIFIED, not built.
- Historical evidence: `state/` gate artifacts, dated audit assets.
- Generated: `state/gate-runs.jsonl`, scorecards. Never hand-edited.

## 7. Docstrings and comments

Style: **Google**, per the corpus decision. Enforced by ruff `D` rules and
`pydoclint --style=google`.

**Module.** Every Python file opens with a module docstring carrying four
things: a one-line imperative summary, Purpose (why it exists, not what it
does), Contracts (invariants callers may rely on), and Agent-context (which
public symbols an agent should call and which to avoid). Then a `Typical usage`
block. The Agent-context section is an emerging practitioner convention, not a
PEP, and the corpus flags it as such.

**Class.** Every public class. `Attributes:` is mandatory whenever the class
exposes a public attribute not obvious from `__init__`.

**Function.** Required unless it satisfies **all three**: private, at most 10
lines, and obvious from name and signature. Sections by mandate:

| Section | Required when |
|---|---|
| `Args:` | any non-obvious parameter, or one whose annotation does not convey meaning |
| `Returns:` | returns anything non-None |
| `Raises:` | an exception the CALLER must handle. Not internal programming errors. |
| `Examples:` | public API, complex invariants, or anything an agent may call autonomously |

`Examples:` is the "declarative I/O example" bar: show input and output, not
prose about them.

**Inline comments: why, never what.** A comment is justified only when a
competent developer reading the line cold might make the WRONG assumption about
why it is written that way. Never restate the next line. This is the rule behind
"no comments": it bans the restating comment, and requires the non-obvious one.

**JavaScript.** The app's inline script gets the same discipline through JSDoc
on exported behaviour. It currently carries none.

## 8. Size and complexity budgets

Two corpus documents disagree on function length. `code-quality-standard` Q4
puts green at 20 lines and red above 40. The repo-structure document budgets 30
with a hard limit of 50. Resolved for this repo: **target 20, budget 30, hard
limit 50.** The stricter number is the target because the corpus itself calls 20
the practical bar for agent-legible code.

| Scope | Target | Hard limit |
|---|---|---|
| Function | 20 | 50 |
| Class | 150 | 300 |
| Module | 300 | 500 |
| Test file | 400 | 600 |
| Cyclomatic complexity | 1 to 5 | 10 |
| Cognitive complexity | under 10 | 15 |
| Parameters | 4 | 6 |
| Nesting depth | 3 | 4 |

Radon target: median grade A, no function below B.

One standing exception, declared rather than hidden: `index.html` carries a
113 KB inline script, far past every module budget. Splitting it requires either
a bundler, which is a stated non-goal, or ES modules, which changes the CSP and
service-worker story. It is a known, dated debt, not a passing score.

## 9. Gates and CI

Corpus dimension 5: a pipeline that actually gates, secretlessly, with stage and
production separation. No `|| true`.

Target pipeline:

- On pull request and on push to any non-main branch: run the full gate, then
  publish a Cloudflare Pages preview. This is stage.
- On push to main: run the gate, then deploy production. Gate failure blocks the
  deploy rather than warning.
- Never `|| true`. A gate that cannot run must exit non-zero, which the e2e
  domain already does correctly when the local server is down.

## 10. Measured gaps in this repo

Every line below was checked on disk 2026-07-26, not assumed.

| Gap | Evidence | Severity |
|---|---|---|
| `tools/.venv` is untracked but NOT gitignored, 1315 Python files | `.gitignore` lacks `.venv/` and `__pycache__/` | HIGH. `pages deploy .` would publish an entire virtualenv. |
| `docs/` is published | `deploy.yml` deploys the repo root with no exclusion | HIGH. Every planning document goes public on the next push. |
| `tools/check_inline_js.py` is untracked | `git ls-files tools/` returns 7, the file is not among them | HIGH. The types gate depends on a file not in the repo, so CI cannot reproduce it. |
| No lint config | no `pyproject.toml`, `ruff.toml`, `setup.cfg` | MEDIUM. Fails code-health dimension. |
| No type config | no `mypy.ini` or equivalent | MEDIUM. Same. |
| No `docs/adr/` | directory absent | MEDIUM. Fails repo-org and documentation dimensions. |
| Tests not gated in CI | `deploy.yml` runs only `validate_links.py` | MEDIUM. Fails testing dimension and is the recorded `pipeline` failure. |
| No stage environment | only main deploys | MEDIUM. Root cause of the pipeline gate failure. |
| No structured logging, runbook, rollback, CVE scan | absent | MEDIUM. Blocks the MVP to Production transition. |
| No `AGENTS.md`, no `CHANGELOG.md`, no `Makefile` | absent | LOW. The Makefile is already a wanted item in `research_ladder.json`. |

## 11. Fix order

Cheap and blocking first.

1. `.gitignore` gains `.venv/` and `__pycache__/`. One line each, removes 1315
   files from any deploy.
2. Exclude `docs/` and `state/` from the published site.
3. Track `tools/check_inline_js.py` so the gate is reproducible.
4. Add `pyproject.toml` with ruff and mypy config for the 7 tracked scripts.
5. Add `ci.yml`: gate on pull request and non-main push, publish a preview. This
   creates stage and closes the pipeline domain without touching production.
6. Add `docs/adr/`, and backfill ADRs for the decisions already made: no
   bundler, two design registers, calendar removal, MoSCoW as the tree taxonomy.
7. Add `Makefile` targets: test, gate, serve, deploy.
8. Structured logging in the daemon, then a runbook and a tested rollback.
