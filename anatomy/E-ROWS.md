# E-ROWS - enforced standards registry (claude-setup)

Book mechanisms become standards only when a running hook enforces them.
Each row below is a structured record of one such mechanism; the record is
not the enforcement. The enforcement column names the exact code or test
that runs. A row whose hook does not exist does not ship.

| ID | Title | Source issue | Enforcement | Status |
|----|-------|--------------|-------------|--------|
| E-0001 | Undeclared tradeoff fails the panel | #374 | `tools/review/e_rows.py::check_undeclared_tradeoff` via `panel.run_local` | enforced |
| E-0002 | High-risk prompt/schema/evidence edits need a declared regression scope | #373 | `tools/review/e_rows.py::check_edit_risk` via `panel.run_local` | enforced |
| E-0003 | Memoized review decisions, fingerprint-guarded keys | #372 | `tools/review/e_rows.py::ReviewDecisionCache` via `panel.cmd_run` | enforced |

Status values: `enforced` (hook runs and is tested), `partial` (hook runs,
coverage incomplete), `proposed` (no hook; never merges). Superseded rows
are marked superseded with a pointer, never deleted. Row ids are never
reused.

Row records live in `e-rows/E-NNNN-<slug>.md`. Tests live in
`tests/test_erows.py`, one class of cases per row.
