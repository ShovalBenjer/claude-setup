# Implementation reasoning, per source file

Status: analysis, point-in-time, 2026-08-05
Lane: A
Applies: docs/adr/0021-rust-for-hot-paths-python-for-oracles.md, file by file
Measured from: `wc -l` over tools/ this session, mutate.py spec output, and each file's
own header docstring. Claims are marked MEASURED (command shown or on disk), STATED
(the file's own docstring says so), or INFERRED (my reading, not verified by a run).

The operator asked why the code is the way it is, at the granularity of loops,
functions, and classes. The honest global answer comes first, because it explains
almost every local choice, and then the per-file table carries what is specific.

## The three decisions that explain most files

**1. Every tool is a flat script of functions with a selftest verb, not a package of
classes.** This repo is a verification harness: most "code" is an oracle whose job is
to disagree with an agent's report (AGENTS.md states this). An oracle's value is that
it is cheap to change and cheap to audit, and the audit path is a human reading one
file top to bottom. Classes earn their place when state and behavior need to travel
together across call sites; a gate domain is a function from a project path to a
(status, evidence) pair, so a class would add a layer with no second user.
MEASURED: gate.py's domains are functions returning `tuple[str, str]` (for example
`review_artifact`, `ci_runs_gate`), dispatched from a table, not subclasses.

**2. Stdlib-only, structurally.** A grep of every import across tools/ finds one
non-stdlib package: `google.antigravity` in tools/antigravity/agy.py, an external
service SDK that cannot be vendored. Everything else is os, re, json, subprocess,
pathlib. The reason is ADR-0021's tiebreaker: the check must still run on a machine
with no toolchain, because an oracle that fails to run is worse than a slow one, and
it fails open. This is also why `python -m pytest` is the only test runner at the
root and why uv appears only inside intent-control-plane, the one packaged subproject.

**3. Plain for loops over comprehension-chains and over vectorization.** The global
numerical-stack rule (Polars, Numba, NumPy) binds hot numerical paths. Nothing in
tools/ is a hot numerical path: the largest input any oracle reads is the repo's own
tracked file list (1,852 files, ADR-0021), once per gate run. At that scale a for
loop with an early `continue` and a named accumulator is the version a reviewer can
audit line by line, and auditability is the product here. Loops that iterate per
tool call live in tools/hookgate, in Rust, which is decision 2 of ADR-0021.

## Why the default generation is .py at all (the Rust question)

ADR-0021 is the binding answer and it is a criterion, not a taste: language follows
the failure mode. Rust where latency compounds per invocation (hookgate runs on every
PreToolUse, MEASURED 2.26 ms), where the borrow checker eliminates a defect class
structurally, or where a long-lived binary processes the whole estate. Python where
the code runs once per gate or session, where defects are logic errors a test
catches, and where the value is that a new mutation operator costs an afternoon
rather than a compile cycle. The one named rewrite candidate (bus.py, justified by
two lock mutants that survived on 2026-08-01) lost its urgency when the 2026-08-04
correction re-measured the spec at 23 of 23 caught; the ADR records that the
rewrite's evidence is now historical and should not proceed on it alone. The better
justified Rust work is inward: src/main.rs and src/rules.rs carry zero `#[test]`
across 319 lines on a binary that fires every tool call.

## Per-file reasoning

Line counts MEASURED this session. Mutation counts are from `mutate.py --spec all`
output in today's CI log.

| File | Lines | Why it is shaped the way it is |
|---|---|---|
| tools/gate/gate.py | 1450 | The contract executor. Domains are functions dispatched by name from quality-contract.json, so adding a domain is one function plus one JSON entry, and an unconfigured domain fails as UNCOVERED rather than passing silently. Shells out to codemap/panel rather than importing them (STATED at the codemap call site: the evidence in the report is the command a human reruns, and one implementation instead of two that drift). |
| tools/review/panel.py | 1311 | Persona review over added lines only. Regex patterns, not an AST, and that is a documented limit, not an accident: it reviews diffs that may not parse (markdown, YAML, partial hunks), and its verdict block prints what it cannot see. The 2026-08-04 comment-strip fix (`code_only()`) exists because matching a comment that quotes a dangerous call is the L-2026-07-31-b oracle-shape failure; two checks that read comments on purpose are exempted by name. |
| tools/bus/bus.py | 1243 | Hash-chained append-only ledger. File locking around append, verify recomputes the chain. Highest branch complexity in the repo (41, MEASURED 2026-08-03) and the one file where ADR-0021 found a defect class a borrow checker would have eliminated; its mutation spec is the repo's largest at 23. Query and reporting stay in the same file so the chain has one implementation of `row_hash`, imported by tests via `from bus import ...`. |
| tools/audit/mutate.py | 251 | The falsifiability layer: applies named mutations to a copy of each oracle and requires the oracle's own selftest to go red. Exit 2 distinguishes "a spec could not run" (baseline red) from exit 1 "a mutant survived", which is how today's docmap baseline failure surfaced in CI as its own signal. Specs live in tools/audit/mutations/ and are globbed, so a new spec is picked up without editing the runner (STATED in 308435e). |
| tools/docmap/docmap.py | 532 | Derives status/class/lane for 991 documents and checks the committed DOCMAP.md matches. Selftest is hermetic over synthetic inputs, plus the check compares generated output to the committed file, which is what caught this week's defect: the map was committed ahead of its inputs. Class rules are functions over path strings, no classes, because the whole derivation is stateless. |
| tools/docmap/strand.py | 356 | Two rules over governed docs: declared status from a fixed vocabulary, and referenced-by-something-that-is-not-INDEX. INDEX is excluded because it links everything by construction, making the rule vacuous (STATED in its docstring, printed in its report). Its own limit is printed too: link-counting cannot see a document that is linked and ignored. 9 pinning tests exist because its first parser rejected two legitimate status forms, the oracle-checks-its-ruled-shape failure, twice. |
| tools/docmap/atlas.py | 283 | Corpus structure: clusters, near-duplicate pairs by Jaccard over hashed five-word shingles. Shingling in pure Python because the corpus is 420 documents, not 4 million; the output (state/atlas.json) is regenerable, so the file is data, not a ledger. |
| tools/map/codemap.py | 520 | Directory purposes. 13 mutations all caught. The check that a registry row beside a self-documenting directory is an error (not an override) exists so there is exactly one source of truth per directory. |
| tools/audit/skills_sync.py | 751 | Measures drift between dot-claude/ payload and the live ~/.claude tree, in both directions, because deployment is the failure mode this repo keeps logging (a 16-skill cut existed in the repo and in 0 live skills). Today's fix (bca96c6) repaired a comparator bug in its drift count. |
| tools/audit/rules_sync.py | 281 | Same for rules, split into DRIFT (needs a live tree; reports NOT RUN when absent) and SHRINK (payload plus git history only, runs anywhere). The split is between the checks, not the hosts: an absent live tree narrows what is asserted and never widens it to a pass, and an EMPTY live directory stays a failure because a deployment that exists and holds nothing was destroyed (STATED in 308435e, which is the third recorded instance of the host-shape lesson). 10 mutations, 10 caught. |
| tools/trycmd/trycmd.py | 498 | CLI snapshot testing with `[..]` wildcards and `...` elision. Elision exists because argparse wraps --help to a terminal width this repo does not control, and a check that fails for a reason nobody can act on gets deleted, not fixed (STATED in its mutation regressions). 11 mutations, 11 caught. |
| tools/timetravel/snapshot.py | 724 | Content-addressed snapshots with at-or-before resolution. Nearest-neighbour resolution is explicitly a mutation (caught): a later snapshot is evidence about a later moment, and answering a question about the past with present bytes is the worst failure for this tool because the output is well-formed and confident. 10 mutations, 10 caught. |
| tools/refute/refute.py | 509 | Runs each recorded claim's own falsifier. Claims without falsifiers are the disease this repo treats; the tool is the enforcement of the claims ledger's schema. |
| tools/audit/pointers.py | 508 | Finds hooks and skills that are dead paths. Exists because 12 of 29 hook files were one-line stubs pointing at a home directory that does not exist on this machine, and a hook that cannot run fails open and reports nothing. |
| tools/slop_lint.py | 114 | Prose gate: banned phrases, em/en dashes as connectors. Regex over lines, no NLP dependency, because the gate must run everywhere and its false positives are cheap to inspect. Known open gap (TODO row DOCS-02): no notion of fenced code blocks. |
| tools/hookgate/ (Rust) | 319 + 313 py regen | The one per-invocation path. Rust with fancy-regex and serde_json, lto and opt-level 3, MEASURED 2.26 ms on PreToolUse. regen_rules.py generates its rule table from Python so the rules have one authored source. Gap owed regardless of ADR-0021: zero unit tests inside the binary. |
| tools/e2e/flow.py, tools/browser/cdp.py | 1143, 738 | Browser harness. cdp.py speaks raw CDP over a websocket rather than importing playwright, keeping the stdlib-only property; the cost, documented in ship-gate.yml's header, is hardcoded Chrome paths that make it Windows-shaped, so CI keeps its selftest in a separate job that is not merge-blocking. |

Files under 300 lines follow the same shape (functions, selftest, stdlib) and are
covered by the audit sweep in docs/analysis/2026-08-03-code-audit-analysis-sweep-and-
research-provenance.md, which parsed all 93 Python files; this document does not
restate it.

## Where the reasoning is thin, named rather than smoothed over

- `tools/supply/verify.py` (807 lines) and `tools/openrouter/client.py` (467) were not
  reread this session; their rows are absent above rather than invented. INFERRED
  only that they follow the house shape.
- The 300-line prior-art rule means every component above that size owes a record in
  docs/prior-art/ with named alternatives; the 2026-08-03 audit measured zero missing,
  keyed by directory. That check, not this document, is the enforcement.
- The class question has one real exception worth naming: trycmd.py uses a small
  `Step` object, because a parsed step is state (argv, expected output, expected exit)
  that travels together through parse, run, and compare. That is the criterion working,
  not an inconsistency.
