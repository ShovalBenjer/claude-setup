Status: point-in-time

# Are the three N/A domains still honest, 2026-08-08

Re-checks `quality-contract.json`'s three N/A domains (e2e, a11y_ux, perf) against
today's tree, not against the date each `na_reason` was written. An N/A that was
true when written and is false now is the same defect class as a stale waiver.
This is a recommendation pass. `quality-contract.json` was not edited and no
domain's status was changed.

Commit checked: `533ddef` (HEAD of `lane-a/waived-domains-are-not-unmeasured`
at the time of this pass; `git status --porcelain -- quality-contract.json`
returned nothing, so the file matched HEAD, VERIFIED).

## Summary table

| domain | verdict | one-line reason |
| --- | --- | --- |
| e2e | keep N/A, restate dated | still true: no served app exists in this repo; the tool that would run e2e is real and is proven elsewhere (daily-deep-learning), and the scratch-project e2e this repo's own product needs already exists under `unit` as `gate.py selftest` |
| a11y_ux | keep N/A, restate dated | mechanically derivative of e2e (reads `state/e2e/last.json`, VERIFIED as the real live mechanism from another project's contract); nothing to grade while e2e is N/A |
| perf | tighten now, replace is the stronger option | the claim "nobody has set a number to measure against" is stale: the `unit` domain's own `_timeout_note` sets a number (900s, falsifier at 600s) that nothing currently records against, because `state/gate-runs.jsonl` has no duration field |

## e2e

**na_reason claim:** claude-setup serves no application of its own; `tools/e2e/flow.py`
and `tools/browser/cdp.py` drive OTHER repositories' running UIs; every `.html`
here is a static export.

**Checked, not accepted:**

- VERIFIED no served app exists in this repo. `grep -rln "app.run(\|uvicorn.run\|Flask(__name__)\|http.server\|HTTPServer\|socketserver" --include="*.py" .` (excluding worktrees and caches) returns only `tools/e2e/flow.py` itself, which stands up an ephemeral local HTTP server solely inside its own `selftest` to serve a synthetic nine-defect page (`tools/e2e/flow.py:1015-1104`), not a real app.
- VERIFIED every `.html` under this tree (`find . -name "*.html"`, excluding worktrees/node_modules) is a static export: dashboards and diagrams in `work-docs/`, research report exports in `research-papers/`, and skill templates in `dot-claude/skills/`. None is served by a route.
- VERIFIED the instrument itself is not vaporware. A dedicated CI job, `browser-instrument-selftest` in `.github/workflows/ship-gate.yml:345-363`, runs `python tools/e2e/flow.py selftest` on `windows-latest` and is deliberately kept out of the `pipeline`/gate verdict. `gh run view <id> --json jobs` on the 5 most recent `ship-gate.yml` runs (databaseId 31246738014, 31246573335, 31223961583, 31223690179, 31223201276, spanning 2026-08-06 to 2026-08-08) shows this job `success` every time. The workflow's own header comment ("that has NOT been confirmed by an actual run of this exact workflow from this environment") is itself now stale, a small separate defect worth naming: the instrument HAS run green repeatedly. Not mine to fix; noting it because it is adjacent to this recheck.
- VERIFIED the tool this na_reason describes genuinely drives another repo's live UI. `state/gate-runs.jsonl` (8571 rows) shows `daily-deep-learning` as a real project with 69 gate runs, and its `quality-contract.json` carries a live e2e domain: a real `cmd` invoking `flow.py audit ${APP_URL}` across 8 routes, and an active waiver (`until: 2026-08-15`) whose text records 40 fail / 373 warn findings from a real CDP session against real Chrome 151 on WSL, including measured contrast down to 1.05:1 and specific dead controls. `new-recruit`'s own e2e domain, by contrast, is N/A for the same reason as claude-setup's: no served app, only a static `file://` dashboard. So the na_reason's claim about what the tool does elsewhere checks out on both the positive case (a real app, real driven findings) and the negative case (another CLI-shaped repo, correctly also N/A).

**Is there a different, honest e2e for this repo's own product?** The task's own
suggested candidate, a real end-to-end run of the gate against a scratch
project, already exists and is already wired into CI. `tools/gate/gate.py`'s
`cmd_selftest` (`tools/gate/gate.py:1213` onward) creates a `tempfile.TemporaryDirectory()`,
`git init`s it, and drives `cmd_run` through roughly eight scenarios: no
contract, a starter contract, an all-waived contract, an expired waiver, a
waiver whose `confirm` string stops matching, and a `confirm` string with no
command to produce it. This is a real, mechanical, end-to-end exercise of this
repo's actual product (the gate's decision logic) against a scratch target,
and it runs today inside the `unit` domain's chained command
(`python tools/gate/gate.py selftest`, part of `quality-contract.json`'s
`unit.cmd`), in CI, on every PR. Proposing a second, separate "e2e" domain that
does the same thing under a different name would be ceremony: duplicated
coverage measuring nothing new. VERDICT on this sub-question: not ceremony to
have, because it already exists; would be ceremony to add again as a distinct
domain.

**Recommendation:** keep N/A. The reason is still factually true today, not
merely inherited from 2026-07-25. Restate it dated (2026-08-08) rather than
rewording, and add one sentence noting that the scratch-project e2e this repo's
own product would want already runs under `unit`, so a future proposal to add
a distinct e2e domain here should have to argue why `gate.py selftest` does not
already cover it.

## a11y_ux

**na_reason claim:** reads the e2e report at a stricter threshold; there is no
e2e report because there is no served app; if this repo ever grows a UI, both
domains move to a real `cmd`.

**Checked, not accepted:** the claim that a11y_ux "reads the e2e report at a
stricter threshold" describes a real mechanism, not an invented one. VERIFIED
via `tools/gate/gate.py`'s `default_contract()` generator (`gate.py:367-373`),
which is what `gate.py init` writes for a new project: `a11y_ux` carries
`read_report: state/e2e/last.json`, `max_warn: 0`, and a comment that it
"reads the e2e report and fails on accessibility and mobile layout warnings,
which the e2e domain only reports." This is not hypothetical: `daily-deep-learning`'s
live contract shows the same shape in production, filtering e2e's findings to
`contrast, target, label, name, text, overflow, image, head, layout` kinds and
excluding `flow` (dead-control) findings, currently WAIVED with the same
2026-08-15 expiry as its e2e domain because "it inherits the e2e domain's
situation exactly."

Because e2e is genuinely N/A for claude-setup (verified above), a11y_ux has
nothing to grade. There is no independent honest measurement for a11y_ux that
does not first require e2e to produce a report; a11y_ux cannot exist ahead of
its input.

**Recommendation:** keep N/A, restate dated. No tightening needed beyond
matching e2e's restatement, since the current wording already states the
"if e2e goes live, so does this" condition correctly and that condition is
still unmet.

## perf

**na_reason claim:** no performance budget is declared for claude-setup; every
budget-shaped string in the tree is either another project's historical
Lighthouse evidence or code that reports p95 without enforcing a threshold;
nobody has set a number to measure against.

**Checked, not accepted:**

- VERIFIED the Lighthouse half of the claim. `grep -rniE "lighthouse" -l .`
  (excluding worktrees/caches/research-papers/work-docs prose mentions) finds
  real Lighthouse JSON only at
  `work-docs/audits/2026-06-29-hedg-com-website-engineering-audit/evidence/lighthouse_desktop.json`
  and `lighthouse_mobile.json`, exactly the "another project's historical
  evidence" the na_reason names (a website audit for a different company's
  site, not claude-setup).
- VERIFIED the p95-without-threshold half. `grep -rniE "p95|p99" --include="*.py" .`
  (excluding worktrees/dot-claude/dot-agents payload skills) finds
  `intent-control-plane/src/intent_control_plane/observe.py:54,63`, which
  computes `p95_ms` and `p50_ms` from run durations and returns them in a
  dict. Read the function: it is an observability query, not a gate. Nothing
  wraps the return value in an assertion, threshold, or failing exit code.
  This matches the na_reason exactly.
- NOT true as stated: "nobody has set a number to measure against." VERIFIED
  `quality-contract.json`'s own `unit` domain carries `timeout: 900` and a
  `_timeout_note` (added 2026-07-31, six days after this perf na_reason was
  written 2026-07-25) that names an actual budget with provenance: the root
  suite grew from 70 tests/47s to 331 tests/182s, the chained `unit` command
  timed out at 300s three times under load on 2026-07-31, and the note ends
  with an explicit falsifier: "if the suite passes 600s this number is hiding
  growth again and the split is overdue." That is a number, with a command
  that produces it, with a stated action to take when it moves. It is filed
  under `unit`'s `timeout` field, not under `perf`, but by the na_reason's own
  standard ("nobody has set a number") it falsifies the claim as written today.
- VERIFIED nothing currently reads that number. `state/gate-runs.jsonl` rows
  contain the keys `{blocking, project, domains, project_path,
  waivers_unconfirmed, dirty, ts, partial, fingerprint, verdict, commit}` and
  no duration field (checked by unioning keys across all 8571 rows with a
  short Python pass). So the falsifier the `unit` domain wrote for itself
  cannot currently be evaluated: the number exists, the trigger condition is
  written down, and nothing measures wall-clock to compare against it.
- Found, but does not refute the na_reason: `intent-control-plane/src/intent_control_plane/repo_health.py`
  defines real enforced thresholds, `FILE_BUDGET = (300, 500)`,
  `FUNC_BUDGET = (30, 50)`, `CLASS_BUDGET = (150, 300)` (soft, hard), and a
  `Finding` that classifies a violation as `"hard" if loc > budget[1] else "soft"`.
  This is budget-shaped code that DOES enforce a threshold, a third category
  the na_reason's "either/or" framing does not name. But it is a
  lines-of-code/maintainability budget, not a performance/latency budget, and
  VERIFIED it is wired into nothing: no entry in `intent-control-plane/pyproject.toml`'s
  `[project.scripts]`, no reference from `tools/gate/gate.py`,
  `quality-contract.json`, or any CI workflow, only its own test file
  (`intent-control-plane/tests/test_repo_health.py`) exercises it. It belongs
  in this report as evidence the na_reason's taxonomy is not exhaustive, not
  as a counterexample to "no performance budget."

**Is there a different, honest perf for this repo?** Two candidates surfaced
by this check, evaluated against the ceremony test (does anyone act on it):

1. Gate wall-clock, evaluated against the `unit` domain's own falsifier. The
   repo already wrote down the number (600s) and the action ("the split is
   overdue"). Recording actual run duration into `state/gate-runs.jsonl` and
   comparing it to that written falsifier is not ceremony: it completes a
   commitment the repo already made and cannot currently check. This is the
   strongest candidate found.
2. PreToolUse hook latency. VERIFIED hooks exist and run on every tool call
   (`dot-claude/settings.json` wires `SessionStart`, two `PreToolUse` entries,
   `PreCompact`, two `Stop` entries, `Notification`, `UserPromptSubmit`), so a
   slow hook does tax every command, matching the task's own framing. But
   ASSUMED, not verified: no measurement anywhere in the tree currently times
   any hook, and no prior falsifier or commitment exists for it the way the
   `unit` timeout note has one. Worth having eventually; ranks behind
   candidate 1, which has a pre-existing written falsifier waiting for data
   rather than a new commitment to invent.

**Recommendation:** replace N/A with a real check is the stronger option, but
the immediate, cheaper move is to tighten the wording now, because the false
half of the claim ("nobody has set a number") is fixable in the reason text
without new code, while a real check requires building duration capture first.
Exact shape for the real check, if the operator wants to build it: extend
`state/gate-runs.jsonl` rows with a `duration_s` field (wrap the top-level
`run()` timer already present in `gate.py:187` at the `cmd_run` call site),
then give `perf` a `cmd` such as
`python tools/gate/gate.py perf-check --against-falsifier 600` (does not exist
yet; named here as the shape, not built, per the no-new-code-beyond-the-report
constraint of this pass) that reads the last N rows of `gate-runs.jsonl` and
fails if the recorded duration exceeds the 600s falsifier the `unit` domain's
own note already names. That reuses a number this repo already committed to
acting on, rather than inventing a new one, which is the difference between a
real check and ceremony here.

## What I could not check

- Whether `browser-instrument-selftest`'s green runs prove Chrome exists at
  the exact hardcoded path `cdp.py`'s `CHROME_CANDIDATES` expects on
  `windows-latest`, versus some other resolution path succeeding instead. The
  job's `success` conclusion is VERIFIED via `gh run view`; the internal
  reason it succeeds was not traced line by line inside `cdp.py`.
  ASSUMED to be the documented path.
- Whether any `PreToolUse` hook is currently slow enough to matter. No timing
  instrumentation exists to check this either way; flagged as an open
  candidate, not a finding.
- Whether `repo_health.py`'s LOC budgets were ever intentionally wired and
  then removed, or never wired at all. Only current-state absence was
  checked (`grep` across the manifest, gate, and workflows), not `git log`
  on that file's history.
- The `63s` CI gate wall-clock figure named in the task prompt as an example
  was not independently confirmed against a real `gh run view` duration for
  the `gate` job specifically; recent `ship-gate.yml` runs completed in
  roughly 1m13s-1m24s total per `gh run list` (VERIFIED, that is the whole
  workflow including `falsifiability`, `supply-chain`, and
  `browser-instrument-selftest` running in parallel, not the `gate` job's own
  duration in isolation). Treat any single-job perf number as ASSUMED until
  read from `gh run view --json jobs` per job.

## Note for the operator

This file needs a real inbound link (not `docs/INDEX.md`) or
`tools/docmap/strand.py check` will fail it under R2 reachability. A TODO.md
row pointing at this file satisfies that; I did not add one, since the task
said the operator would.
