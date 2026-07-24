# TODO backlog (generated 2026-06-29)

Agent-pickup-ready backlog, consolidated from TESTING-SOTA-2026-GAPS.md (test/eval coverage) and CODE-HEALTH-2026-GAPS.md (monoliths, bad practices). Both are graded against ~/docs/SOTA-TESTING-CRITERIA-2026.md. This is a low-stakes alpha CLI: keep it proportionate.

How to work this: take the topmost unchecked item, open the cited source section for full acceptance criteria, implement the smallest vertical slice (RED then GREEN), verify, then check the box. Check [x] only when the source doc acceptance criteria are met and verified.

## P0
- [ ] (none)

## P1
- [ ] Split cli.py into a thin dispatcher plus focused modules (size L) | target: src/intent_control_plane/cli.py into the module layout in CODE-HEALTH section 2 | src: CODE-HEALTH-2026-GAPS.md, section 6 P1 (Split cli.py)
- [ ] Isolate the redact security boundary into its own module (size S) | target: src/intent_control_plane/redact.py (move cli.py:21-41) | src: CODE-HEALTH-2026-GAPS.md, section 6 P1 (Isolate the redact security boundary)
- [ ] Wire a commit-time static plus test gate (ruff, type check, unittest) (size S) | target: pyproject.toml + .github/workflows/ci.yml | src: TESTING-SOTA-2026-GAPS.md, section 5 P1 item 1
- [ ] Add an installed-entrypoint smoke test (size S) | target: tests/test_entrypoint_smoke.py | src: TESTING-SOTA-2026-GAPS.md, section 5 P1 item 2

## P2
- [ ] Collapse show/list/serializer duplication into a declarative kind table (size S) | target: src/intent_control_plane/rows.py + commands/records.py (cli.py:406-570) | src: CODE-HEALTH-2026-GAPS.md, section 6 P2 (Collapse show/list/serializer duplication)
- [ ] Centralize the per-command initialize call (size S) | target: cli.py main dispatch / commands handlers (cli.py 16 call sites) | src: CODE-HEALTH-2026-GAPS.md, section 6 P2 (Centralize the per-command initialize call)
- [ ] Property tests for the redaction invariant (idempotency, no-secret-leak, raw-passthrough) (size M) | target: tests/test_redaction_properties.py | src: TESTING-SOTA-2026-GAPS.md, section 5 P2 (redaction invariant)
- [ ] Property tests for the ledger and vector invariants (line-count monotonicity, cosine bounds, init/hive_bind idempotency) (size M) | target: tests/test_invariants_properties.py | src: TESTING-SOTA-2026-GAPS.md, section 5 P2 (ledger and vector invariants)
- [ ] Commit a tiny golden regression fixture for context-pack retrieval (size S) | target: tests/fixtures/golden/otp-routing.json + tests/test_retrieval_regression.py | src: TESTING-SOTA-2026-GAPS.md, section 5 P2 (golden regression fixture)

## Notes
- The cli.py 1458-line monolith split is the headline item: it is the project's one structural defect and unblocks the P2 dedup follow-ups (show/list/serializer collapse and centralized initialize are best done after the split, not before). Pure relocation of 52 functions into ~20 files, gated by the existing unittest suite, no logic rewrite.
- The redact isolation (P1) and the redaction property tests (P2) are distinct: one moves the security boundary into redact.py, the other tests its invariants in-process. Land the move first, then the property tests against the new module.
- No P0: this CLI is local-only with no money / CRM-write / PII-to-model / prod path, so no critical-tier work exists.

## Enhancements 2026-06-30
- (none: all inputs N-A or already covered, see verdict)

## Enhancements 2026-07-05
- [x] Add explicit lifecycle transition records and block illegal ship paths (size S) | target: `state transition`, `state_transitions` table, list/show support | proof: `PYTHONPATH=src rtk uv run --no-project python -m unittest discover -s tests -p 'test_*.py'` => 11 subprocess CLI workflow tests passed; test mix is L5/L8 command-system heavy, not unit/property/static complete
- [x] Add structured review feedback tickets inspired by `cc-htmlfeedback` (size S) | target: `feedback add`, `feedback update`, `feedback_tickets` table, evidence-gated `done` status | proof: same unittest suite => 11 subprocess CLI workflow tests passed; feedback behavior covered by E2E command test, not standalone contract/property tests
- [ ] Build an HTML/spec feedback adapter over `feedback_tickets` (size M) | target: browser/export or local HTML review importer that maps highlighted section, quote, context, and note into `feedback add` records; keep CLI contract as source of truth
- [ ] Add architecture-accountability gates before `SHIPPED` (size M) | target: require RCA/investigation, codebase architecture review, spec review, and verification evidence for high-risk subjects before final transition
- [ ] Add project-scoped git ingestion contracts (size M) | target: `intent git ingest-commit` and `intent git analyze-diff`; global index may route/search only, project adapter owns git root, branch, diff, tests, PR/ADO linkage, revert/outcome truth
- [ ] Add project-scoped tree knowledge snapshots (size M) | target: per-repo tree/architecture snapshot command plus global registry pointer; project adapter owns file tree, package/test topology, routes, ADR/PRD authority, and architecture map
- [ ] Add test-mix reporting to completion evidence (size S) | target: `intent eval smoke` or `doctor` emits applicable SOTA layers covered/gap for this repo; source: `docs/testing_practices.txt`, `docs/SOTA-TESTING-CRITERIA-2026.md`, `TESTING-SOTA-2026-GAPS.md`
