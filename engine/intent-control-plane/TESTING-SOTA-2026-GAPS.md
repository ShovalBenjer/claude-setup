# Testing SOTA 2026: gap analysis and open items

> Generated 2026-06-29 against ~/docs/SOTA-TESTING-CRITERIA-2026.md.
> Status legend: have / partial / gap / n-a. Evidence is file:symbol.

## 1. Project profile

- type-tags: python-cli, dev-tooling (local-first, no external service, no PII at the model boundary, no deploy).
- stack: Python >=3.12 (running 3.13.12), pure stdlib, zero runtime deps, uv-managed. SQLite + JSONL on local disk only.
- surface: console script `intent` (pyproject.toml: `[project.scripts] intent = intent_control_plane.cli:main`); source at src/intent_control_plane/cli.py.
- risk surface: none of money / CRM-write / PII-to-model / telephony / prod / media. It captures raw prompts to a local ledger and redacts before any model-facing copy (cli.py:redact), but nothing is deployed and nothing leaves the box (foundry mode is local_only, cli.py:foundry_status).
- applicable rubric scope: pack 3.G only, plus a light pass of the universal spine L0 / L1 / L2 / L9. Everything else is n-a for an alpha local CLI.
- current maturity: L1 ad hoc (see section 4). Expected and acceptable for a zero-dependency alpha dev tool.

## 2. Current test state (verified, not assumed)

- One test file: tests/test_local_alpha.py, 11 test methods, run via stdlib `unittest` (tests subclass `unittest.TestCase`).
- Verified pass: `PYTHONPATH=src rtk uv run --no-project python -m unittest discover -s tests -p 'test_*.py'` -> `Ran 11 tests OK`, exit 0 on 2026-07-06.
- Test shape: every test spawns the CLI as a subprocess (tests/test_local_alpha.py:run_intent uses subprocess.run on `python -m intent_control_plane.cli`) against a fresh tempdir base. These are end-to-end command tests, not unit tests: they exercise init, capture+redaction, extract, context-pack, evidence, doctor, list/show, eval smoke, hive bind, jira assess, index rebuild/search, session brief, foundry status, hive sync, retention sweep, state transitions, illegal transition rejection, and evidence-gated feedback tickets.
- pytest is not installed and not a dependency (pyproject.toml dependencies = []); the suite only runs under `unittest`. No test runner is pinned.
- No CI: no .github/workflows, no azure-pipelines.yml, no pre-commit config (verified by directory scan).
- No static-analysis config: no ruff / mypy / ty config in pyproject.toml or elsewhere; ruff is not invoked anywhere.
- No property tests, no regression fixture directory under version control (the `evals/golden` dir is created at runtime by cli.py:initialize, not committed).

### 2.1 Current test type mix

| Layer | Current status | Evidence | Meaning of the latest `11 OK` |
|---|---|---|---|
| L0 static/formal | gap | no ruff/type gate | `11 OK` does not prove lint, type, import hygiene, dead code, or security patterns. |
| L1 unit | gap | no direct in-process tests of pure functions | `11 OK` does not isolate `redact`, `term_vector`, `cosine`, `infer_constraints`, `infer_proof`, or transition guards as units. |
| L2 property | gap | no Hypothesis or property suite | `11 OK` does not prove invariants such as redaction idempotency, cosine bounds, ledger monotonicity, or idempotent init/bind behavior over generated inputs. |
| L5/L8 command-system behavior | have for local CLI verbs | tests/test_local_alpha.py subprocess CLI tests | `11 OK` mainly proves CLI workflows execute against a fresh local tempdir and persist/read expected SQLite/JSONL state. |
| L6 contract | partial | typed JSON command responses are asserted ad hoc | There is no standalone schema/contract fixture for CLI JSON response shape. |
| L9 regression/golden | partial | eval-smoke fixture is created inside the test | Regression mechanism exists, but no committed golden fixture protects retrieval behavior across future changes. |
| L3/L4/L7/L10 | n-a for this alpha CLI today | no external input parser, service boundary, DB server, network, load profile | Do not add fuzz/mutation/integration/load until a real risk surface exists, except lightweight mutation later if the project graduates. |

Future completion reports must state both:

```text
test result: command + pass/fail
test mix: which SOTA layers were exercised, which applicable layers remain gaps
```

For this repo today, the honest wording is:

```text
11 unittest subprocess CLI workflow tests pass.
Coverage is command-system/regression-smoke heavy.
Static, unit, property, installed-entrypoint, and committed-golden coverage remain open.
```

## 3. Gap analysis (applicable criteria only)

Pack 3.G (low-stakes CLI / dev-tooling) and the light universal-spine layers it names:

| criterion | status | evidence (file:symbol) | note |
|---|---|---|---|
| L0 static: ruff lint gate | gap | no ruff config; pyproject.toml has no [tool.ruff] | code is clean and typed (`from __future__ import annotations`, full annotations in cli.py) but nothing enforces it. |
| L0 static: type check (mypy/ty) | gap | no [tool.mypy] / ty config anywhere | cli.py is fully type-annotated, so a strict check would mostly pass today; it just is not wired. |
| L1 unit: pure logic in isolation | gap | no in-process tests; tests/test_local_alpha.py:run_intent shells out for every assertion | pure functions exist and are trivially unit-testable: cli.py:redact, cli.py:term_vector, cli.py:cosine, cli.py:infer_constraints, cli.py:infer_proof, cli.py:extract_goal. None are called directly. |
| L1 unit: behavior coverage of CLI verbs | partial | tests/test_local_alpha.py:LocalAlphaTests (11 subprocess workflow methods) | every command path is touched end-to-end, which is real coverage, but at the slowest layer and with no isolation of the logic units. |
| L2 property: invariants (roundtrip, idempotency, bounds) | gap | no Hypothesis; not a dependency | clear invariants are untested: redact idempotency and no-secret-leak (cli.py:redact, cli.py:SECRET_PATTERNS), ledger line-count monotonicity (cli.py:ledger_append), cosine bounds 0..1 and self-similarity (cli.py:cosine), init / hive_bind idempotency (cli.py:initialize, cli.py:hive_bind). |
| L9 regression: blessed fixture / golden master | partial | cli.py:eval_smoke reads `evals/golden/*.json` fixtures, but the dir is runtime-created (cli.py:initialize) and the one fixture is written inside the test (tests/test_local_alpha.py:test_eval_smoke_uses_golden_retrieval_fixtures) | the smoke-eval mechanism exists, but there is no committed regression fixture, so a retrieval regression in cli.py:build_context_pack would not be caught in CI. |
| smoke test of the `intent` entrypoint | partial | tests invoke `python -m intent_control_plane.cli` (tests/test_local_alpha.py:run_intent), never the installed `intent` console script (pyproject.toml:[project.scripts]) | the module entry is smoked; the packaged entry point is not, so a broken console-script wiring would ship undetected. |
| L3 fuzz / L4 mutation / L5 component / L6 contract / L7 integration / L8 E2E-system / L10 non-functional | n-a | pack 3.G scope note in SOTA-TESTING-CRITERIA-2026.md:287 | no external service, no DB server, no network surface, no protocol contract, no load profile. Correctly excluded; do not add. |
| AI planes (section 2), security (4.1), PII (4.2), money/CRM (4.3), prod (4.4) | n-a | no model call, no auth, no PII to model, no writes to external systems, no deploy | considered and excluded. Redaction (cli.py:redact) is a local hygiene feature, not a model-boundary PII gateway, so 4.2 does not bind here. |

## 4. Coverage score and maturity

Applicable criteria scored (have=1.0, partial=0.5, gap=0, n-a excluded). No 2x risk weighting applies (no money / CRM / PII / prod surface).

- L0 static: 0 / 2 = 0.0 (ruff gap, type-check gap).
- L1 unit: (0 + 0.5) / 2 = 0.25 (no isolation unit tests; E2E verb coverage partial).
- L2 property: 0 / 1 = 0.0.
- L9 regression + entrypoint smoke: (0.5 + 0.5) / 2 = 0.5.
- Overall = sum(2.0 of 7.0 weighted points) / 7 applicable = 0.29.

Maturity level: L1 ad hoc (unit-style tests run, but no CI gate, no static gate, no property layer). This is the expected and acceptable rung for a zero-dependency alpha dev tool; the rubric explicitly says do not over-test pack 3.G.

Single highest-leverage gap: no CI gate at all. The code is already clean and typed, so wiring ruff + a type check + the existing unittest run into one commit gate (P1, item 1) buys the most safety per hour and unblocks every later item.

## 5. Open items (prioritized, agent-pickup-ready)

Five items. P1 = real near-term risk for this tool; P2 = quality hardening. No P0 (no prod / money / PII path exists).

- [P1] Wire a commit-time static + test gate (ruff, type check, unittest)
  - why: zero gate today, so a syntax slip, an unused import, or a broken verb ships silently; the code is already lint-clean and fully typed, so the gate is nearly free and protects every future change.
  - acceptance: `[tool.ruff]` in pyproject.toml (line-length 100, rules E/F/I); a strict type check passes on src/; one `.github/workflows/ci.yml` (or local pre-commit) runs ruff check, the type check, and `python -m unittest discover -s tests` on push and fails red on any error.
  - tool / path: ruff + ty (or mypy --strict) + stdlib unittest; pyproject.toml + .github/workflows/ci.yml.
  - size: S.

- [P1] Add an installed-entrypoint smoke test
  - why: the suite only runs `python -m ...` (tests/test_local_alpha.py:run_intent); a broken `intent = intent_control_plane.cli:main` mapping (pyproject.toml:[project.scripts]) would pass tests and fail for the user on first run.
  - acceptance: a test does `uv run intent --base-dir <tmp> init` (or invokes the installed script) and asserts exit 0 plus a created intent.db; runs in CI.
  - tool / path: stdlib unittest + subprocess against the console script; tests/test_entrypoint_smoke.py.
  - size: S.

- [P2] Property tests for the redaction invariant
  - why: cli.py:redact is the one quasi-security behavior (keeps secrets out of model_text); example-based coverage in test_capture only checks two literal strings, so a pattern gap in cli.py:SECRET_PATTERNS is easy to miss.
  - acceptance: Hypothesis tests asserting (a) idempotency `redact(redact(t)[0])[0] == redact(t)[0]`, (b) any input containing a generated `sk-proj-...` or `KEY=...` token yields state `redacted_for_model` and the token absent from the output, (c) secret-free text is returned unchanged with state `raw_local`.
  - tool / path: Hypothesis (add as a dev dependency); tests/test_redaction_properties.py importing cli.redact directly (in-process, fast).
  - size: M.

- [P2] Property tests for the ledger and vector invariants
  - why: cli.py:ledger_append must keep one line per event with a monotonic line number, and cli.py:cosine / cli.py:term_vector must stay bounded and self-consistent; these are roundtrip / idempotency / bounds invariants that example tests do not pin.
  - acceptance: properties asserting (a) N captures produce exactly N ledger lines with strictly increasing `:line` refs, (b) `cosine(v, v)` is in (0, 1] for any non-empty `term_vector(text)` and `cosine(a, b) == cosine(b, a)`, (c) re-running `init` / `hive_bind` with the same args leaves row counts unchanged (idempotency).
  - tool / path: Hypothesis; tests/test_invariants_properties.py importing cli functions directly.
  - size: M.

- [P2] Commit a tiny golden regression fixture for context-pack retrieval
  - why: cli.py:eval_smoke already grades retrieval against `evals/golden/*.json`, but no fixture is committed (the test writes its own), so a regression in cli.py:build_context_pack ranking is invisible to CI.
  - acceptance: a committed fixture under tests/fixtures/golden/ (case_id, repo_path, task, expected_event_ids) plus a test that seeds the matching capture, runs `eval smoke`, and asserts `passed >= 1, failed == 0`; if `build_context_pack` stops returning the expected event, the test fails.
  - tool / path: stdlib unittest + the existing eval-smoke path; tests/fixtures/golden/otp-routing.json + tests/test_retrieval_regression.py.
  - size: S.
